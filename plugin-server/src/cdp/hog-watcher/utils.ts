import { Redis } from 'ioredis'

import { RedisPool } from '../../types'
import { timeoutGuard } from '../../utils/db/utils'
import { now } from '../../utils/now'
import { HogWatcherObservationPeriod, HogWatcherRatingPeriod, HogWatcherState, HogWatcherStatePeriod } from './types'

const REDIS_TIMEOUT_SECONDS = 5

export const OBSERVATION_PERIOD = 10000 // Adjust this for more or less granular checking
export const RATINGS_PERIOD_MASK = OBSERVATION_PERIOD * 2 // What number of periods to wait for before writing a rating
export const DISABLED_PERIOD = 1000 * 60 * 10 // 10 minutes
export const MAX_RECORDED_STATES = 10
export const MAX_RECORDED_RATINGS = 10
export const MAX_ALLOWED_TEMPORARY_DISABLES = MAX_RECORDED_STATES / 2
export const MIN_OBSERVATIONS = 3

export const OVERFLOW_THRESHOLD = 0.8
export const DISABLE_THRESHOLD = 0.5

export const BASE_REDIS_KEY = process.env.NODE_ENV == 'test' ? '@posthog-test/hog-watcher' : '@posthog/hog-watcher'

export const calculateRating = (observation: HogWatcherObservationPeriod): number => {
    // Rating is from 0 to 1
    // 1 - Function is working perfectly
    // 0 - Function is not working at all

    const totalInvocations = observation.successes + observation.failures
    const totalAsyncInvocations = observation.asyncFunctionSuccesses + observation.asyncFunctionFailures
    const successRate = totalInvocations ? observation.successes / totalInvocations : 1
    const asyncSuccessRate = totalAsyncInvocations ? observation.asyncFunctionSuccesses / totalAsyncInvocations : 1

    return Math.min(1, successRate, asyncSuccessRate)
}

export const periodTimestamp = (timestamp?: number): number => {
    // Returns the timestamp but rounded to the nearest period (e.g. 1 minute)
    return Math.floor((timestamp ?? now()) / OBSERVATION_PERIOD) * OBSERVATION_PERIOD
}

export const deriveCurrentStateFromRatings = (
    ratings: HogWatcherRatingPeriod[],
    states: HogWatcherStatePeriod[]
): HogWatcherState => {
    // States are pruned by a max length rather than time
    if (states.length > MAX_RECORDED_STATES) {
        states = states.slice(states.length - MAX_RECORDED_STATES)
    }

    const currentState = states[states.length - 1] ?? {
        timestamp: now(),
        state: HogWatcherState.healthy,
    }

    if (currentState.state === HogWatcherState.disabledIndefinitely) {
        return HogWatcherState.disabledIndefinitely
    }

    // If we are disabled for a period then we only check if it should no longer be disabled
    if (currentState.state === HogWatcherState.disabledForPeriod) {
        if (now() - currentState.timestamp > DISABLED_PERIOD) {
            return HogWatcherState.overflowed
        }
    }

    if (ratings.length < MIN_OBSERVATIONS) {
        // We need to give the function a chance to run before we can evaluate it
        return currentState.state
    }

    const averageRating = ratings.reduce((acc, x) => acc + x.rating, 0) / ratings.length

    if (currentState.state === HogWatcherState.overflowed) {
        if (averageRating > OVERFLOW_THRESHOLD) {
            // The function is behaving well again - move it to healthy
            return HogWatcherState.healthy
        }

        if (averageRating < DISABLE_THRESHOLD) {
            // The function is behaving worse than overflow can accept - disable it
            const disabledStates = states.filter((x) => x.state === HogWatcherState.disabledForPeriod)

            if (disabledStates.length >= MAX_ALLOWED_TEMPORARY_DISABLES) {
                // this function has spent half of the time in temporary disabled so we disable it indefinitely
                return HogWatcherState.disabledIndefinitely
            }

            return HogWatcherState.disabledForPeriod
        }
    }

    if (currentState.state === HogWatcherState.healthy) {
        if (averageRating < OVERFLOW_THRESHOLD) {
            return HogWatcherState.overflowed
        }
    }

    return currentState.state
}

export const mergeObservations = (observations: HogWatcherObservationPeriod[]): HogWatcherObservationPeriod[] => {
    const merged: Record<number, HogWatcherObservationPeriod> = {}

    observations.forEach((observation) => {
        const period = periodTimestamp(observation.timestamp)
        merged[period] = merged[period] ?? {
            timestamp: period,
            successes: 0,
            failures: 0,
            asyncFunctionFailures: 0,
            asyncFunctionSuccesses: 0,
        }

        merged[period].successes += observation.successes
        merged[period].failures += observation.failures
        merged[period].asyncFunctionFailures += observation.asyncFunctionFailures
        merged[period].asyncFunctionSuccesses += observation.asyncFunctionSuccesses
    })

    return Object.values(merged).sort((a, b) => a.timestamp - b.timestamp)
}

export async function runRedis<T>(
    redisPool: RedisPool,
    description: string,
    fn: (client: Redis) => Promise<T>
): Promise<T> {
    const client = await redisPool.acquire()
    const timeout = timeoutGuard(
        `${description} delayed. Waiting over ${REDIS_TIMEOUT_SECONDS} seconds.`,
        undefined,
        REDIS_TIMEOUT_SECONDS * 1000
    )
    try {
        return await fn(client)
    } finally {
        clearTimeout(timeout)
        await redisPool.release(client)
    }
}
