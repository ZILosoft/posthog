import { useValues } from 'kea'
import { renderFeedbackWidgetPreview, renderSurveysPreview } from 'posthog-js/dist/surveys-module-previews'
import { useEffect, useRef } from 'react'

import { Survey } from '~/types'

import { NewSurvey } from './constants'
import { surveysLogic } from './surveysLogic'

export function SurveyAppearancePreview({
    survey,
    previewPageIndex,
}: {
    survey: Survey | NewSurvey
    previewPageIndex: number
}): JSX.Element {
    const surveyPreviewRef = useRef<HTMLDivElement>(null)
    const feedbackWidgetPreviewRef = useRef<HTMLDivElement>(null)

    const { surveysHTMLAvailable } = useValues(surveysLogic)

    useEffect(() => {
        if (surveyPreviewRef.current) {
            renderSurveysPreview(survey, !surveysHTMLAvailable, surveyPreviewRef.current, previewPageIndex)
        }

        if (feedbackWidgetPreviewRef.current) {
            renderFeedbackWidgetPreview(survey, !surveysHTMLAvailable, feedbackWidgetPreviewRef.current)
        }
    }, [survey, previewPageIndex])
    return (
        <>
            <div ref={surveyPreviewRef} />
            <div ref={feedbackWidgetPreviewRef} />
        </>
    )
}
