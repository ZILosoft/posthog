import LRUCache from 'lru-cache'

import { Hub, Team } from '../types'
import { PostgresUse } from '../utils/db/postgres'
import { GroupType, HogFunctionInvocationGlobals } from './types'

export type GroupsMap = Record<string, GroupType>
export type GroupsCache = Record<Team['id'], GroupsMap>

// Maps a fingerprintfor easy lookup like: { 'team_id:merged_fingerprint': primary_fingerprint }
type ExceptionFingerprintByTeamType = Record<string, string>

const FINGERPRINT_CACHE_AGE_MS = 60 * 10 * 1000 // 10 minutes

export class GroupsManager {
    fingerprintMappingCache: LRUCache<number, Record<string, string[]>> // team_id: { primary_fingerprint: merged_fingerprints[] }

    constructor(private hub: Hub) {
        // There is only 5 per team so we can have a very high cache and a very long cooldown
        this.fingerprintMappingCache = new LRUCache({ max: 1_000_000, maxAge: FINGERPRINT_CACHE_AGE_MS })
    }

    private async fetchExceptionFingerprintMapping(teams: Team['id'][]): Promise<ExceptionFingerprintByTeamType> {
        const exceptionFingerprintMapping: ExceptionFingerprintByTeamType = {}

        // Load the cached values so we definitely have them
        teams.forEach((teamId) => {
            const cached = this.fingerprintMappingCache.get(teamId)

            if (cached) {
                Object.entries(cached).forEach(([primaryFingerprint, mergedFingerprints]) => {
                    mergedFingerprints.forEach((mergedFingerprint) => {
                        exceptionFingerprintMapping[`${teamId}:${mergedFingerprint}`] = primaryFingerprint
                    })
                })
            }
        })

        const teamsToLoad = teams.filter((teamId) => !this.fingerprintMappingCache.get(teamId))

        if (teamsToLoad.length) {
            const result = await this.hub.postgres.query(
                PostgresUse.COMMON_READ,
                `SELECT fingerprint, merged_fingerprints, team_id
                FROM posthog_errortrackinggroup
                WHERE team_id = ANY($1) AND merged_fingerprints != '{}'`,
                [teamsToLoad],
                'fetchExceptionTrackingGroups'
            )

            const groupedByTeam: Record<number, Record<string, string[]>> = result.rows.reduce((acc, row) => {
                if (!acc[row.team_id]) {
                    acc[row.team_id] = {}
                }
                const stringifiedFingerprint = encodeURIComponent(row.fingerprint.join(','))
                acc[row.team_id][stringifiedFingerprint] = row.merged_fingerprints
                return acc
            }, {})

            // Save to cache
            Object.entries(groupedByTeam).forEach(([teamId, errorTrackingGroups]) => {
                this.fingerprintMappingCache.set(parseInt(teamId), errorTrackingGroups)
                Object.entries(errorTrackingGroups).forEach(([primaryFingerprint, mergedFingerprints]) => {
                    mergedFingerprints.forEach((mergedFingerprint) => {
                        exceptionFingerprintMapping[`${teamId}:${mergedFingerprint}`] = primaryFingerprint
                    })
                })
            })
        }

        return exceptionFingerprintMapping
    }

    /**
     * This function looks complex but is trying to be as optimized as possible.
     *
     * It iterates over the globals and creates "Group" objects, tracking them referentially in order to later load the properties.
     * Once loaded, the objects are mutated in place.
     */
    public async enrichGroups(items: HogFunctionInvocationGlobals[]): Promise<HogFunctionInvocationGlobals[]> {
        const exceptionEventItems = items.filter((x) => x.event.name === '$exception')
        const byTeamType = await this.fetchExceptionFingerprintMapping(
            Array.from(new Set(exceptionEventItems.map((global) => global.project.id)))
        )

        exceptionEventItems.forEach((item) => {
            const fingerprint: string[] = item.event.properties['$exception_fingerprint']

            if (fingerprint) {
                const team_id = item.project.id
                const primaryFingerprint = byTeamType[`${team_id}:${encodeURIComponent(fingerprint.join(','))}`]

                if (primaryFingerprint) {
                    item.event.properties['$exception_fingerprint'] = primaryFingerprint
                }
            }
        })

        return items
    }
}
