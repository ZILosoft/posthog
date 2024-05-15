import { LemonTable, LemonTag, LemonTagType } from '@posthog/lemon-ui'
import { BindLogic, useValues } from 'kea'
import { TZLabel } from 'lib/components/TZLabel'
import { EventDetails } from 'scenes/events/EventDetails'
import { logsSceneLogic } from 'scenes/logs/logsSceneLogic'
import { SceneExport } from 'scenes/sceneTypes'

import { AutoLoad } from '~/queries/nodes/DataNode/AutoLoad'
import { dataNodeLogic } from '~/queries/nodes/DataNode/dataNodeLogic'
import { LoadNext } from '~/queries/nodes/DataNode/LoadNext'
import { Reload } from '~/queries/nodes/DataNode/Reload'
import { Query } from '~/queries/Query/Query'
import { NodeKind } from '~/queries/schema'

import { logsDataLogic } from './logsDataLogic'

export const scene: SceneExport = {
    component: LogsScene,
    logic: logsSceneLogic,
}

export function LogsScene(): JSX.Element {
    const props = {
        key: 'logs',
        query: {
            kind: NodeKind.LogsQuery,
            dateRange: {
                date_from: '7d',
            },
        },
    }

    return (
        <BindLogic logic={logsDataLogic} props={props}>
            <BindLogic logic={dataNodeLogic} props={props}>
                <SomeComponent />
            </BindLogic>
        </BindLogic>
    )
}

const SomeComponent = (): JSX.Element => {
    const { data, responseLoading, query } = useValues(logsDataLogic)

    return (
        <div className="relative w-full flex flex-col gap-4 flex-1 h-full">
            <div className="flex gap-4 justify-between flex-wrap">
                <div className="flex gap-4 items-center">
                    <Reload />
                    <AutoLoad />
                </div>
            </div>

            <div className="py-2 max-h-60 overflow-hidden">
                <h2>Log volume</h2>
                <Query
                    key="logs"
                    readOnly={true}
                    query={{
                        kind: NodeKind.InsightVizNode,
                        full: false,
                        embedded: true,
                        fitParentHeight: true,
                        source: {
                            kind: NodeKind.TrendsQuery,
                            filterTestAccounts: false,
                            breakdownFilter: {
                                breakdown_type: 'event',
                                breakdown: '$level',
                            },
                            series: [
                                {
                                    kind: 'EventsNode',
                                    event: '$log',
                                    name: '$log',
                                    math: 'total',
                                },
                            ],
                            interval: 'day',
                            trendsFilter: {
                                display: 'ActionsBar',
                            },
                        },
                    }}
                />
            </div>

            <LemonTable
                dataSource={data}
                loading={responseLoading}
                columns={[
                    {
                        title: 'Timestamp',
                        key: 'timestamp',
                        render: (_, log) => {
                            return <TZLabel time={log.timestamp} showSeconds />
                        },
                    },
                    {
                        title: 'Level',
                        key: 'level',
                        width: 80,
                        render: (_, log) => {
                            const logLevels: Record<string, LemonTagType> = {
                                WARNING: 'warning',
                                VERBOSE: 'success',
                                INFO: 'success',
                                DEBUG: 'success',
                                ERROR: 'danger',
                            }
                            return (
                                <LemonTag type={logLevels[log.level.toUpperCase()] ?? 'default'}>
                                    {log.level.toUpperCase()}
                                </LemonTag>
                            )
                        },
                    },
                    {
                        title: 'Message',
                        key: 'msg',
                        render: (_, log) => {
                            const namespace = log.namespace ? (
                                <span className="text-[color:var(--purple)]">[{log.namespace}] </span>
                            ) : null

                            return (
                                <>
                                    {namespace}
                                    {log.msg}
                                </>
                            )
                        },
                    },
                ]}
                expandable={{
                    expandedRowRender: (log) => {
                        return (
                            <EventDetails
                                event={{
                                    id: log.uuid,
                                    distinct_id: log.distinct_id,
                                    event: log.event,
                                    elements: [],
                                    timestamp: log.timestamp,
                                    properties: JSON.parse(log.properties),
                                }}
                            />
                        )
                    },
                }}
                footer={<LoadNext query={query} />}
            />
        </div>
    )
}
