import { LemonInput } from '@posthog/lemon-ui'
import { useActions, useValues } from 'kea'
import { OperatorSelect } from 'lib/components/PropertyFilters/components/OperatorValueSelect'
import { insightVizDataLogic } from 'scenes/insights/insightVizDataLogic'

import { StickinessOperator } from '~/queries/schema'
import { EditorFilterProps, PropertyOperator } from '~/types'

export function StickinessCriteria({ insightProps }: EditorFilterProps): JSX.Element {
    const { stickinessFilter } = useValues(insightVizDataLogic(insightProps))
    const { updateInsightFilter } = useActions(insightVizDataLogic(insightProps))

    const stickinessCriteria = stickinessFilter?.stickinessCriteria
    const currentOperator = stickinessCriteria?.operator ?? PropertyOperator.GreaterThanOrEqual
    const currentValue = stickinessCriteria?.value ?? 1

    /*
    const toggledLifecycles = (insightFilter as LifecycleFilter)?.toggledLifecycles || DEFAULT_LIFECYCLE_TOGGLES
    const toggleLifecycle= (name: LifecycleToggle): void => {
        if (toggledLifecycles.includes(name)) {
            updateInsightFilter({ toggledLifecycles: toggledLifecycles.filter((n) => n !== name) })
        } else {
            updateInsightFilter({ toggledLifecycles: [...toggledLifecycles, name] })
        }
    }
     */

    const operators: StickinessOperator[] = [
        PropertyOperator.LessThanOrEqual,
        PropertyOperator.GreaterThanOrEqual,
        PropertyOperator.Exact,
    ]

    return (
        <div className="flex items-center gap-2">
            At least once and also
            <OperatorSelect
                className="flex-1"
                operator={currentOperator}
                operators={operators}
                onChange={(newOperator: PropertyOperator) => {
                    updateInsightFilter({
                        stickinessCriteria: { operator: newOperator as StickinessOperator, value: currentValue },
                    })
                }}
            />
            <LemonInput
                type="number"
                className="ml-2 w-20"
                defaultValue={currentValue}
                min={1}
                onChange={(newValue: number | undefined) => {
                    if (newValue !== undefined) {
                        updateInsightFilter({ stickinessCriteria: { operator: currentOperator, value: newValue } })
                    }
                }}
            />
            times per interval
        </div>
    )
}
