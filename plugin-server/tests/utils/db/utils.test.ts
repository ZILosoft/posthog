import { personInitialAndUTMProperties } from '../../../src/utils/db/utils'

describe('personInitialAndUTMProperties()', () => {
    it('adds initial and utm properties', () => {
        const properties = {
            distinct_id: 2,
            $browser: 'Chrome',
            $current_url: 'https://test.com',
            $os: 'Mac OS X',
            $os_version: '10.15.7',
            $browser_version: '95',
            $referring_domain: 'https://google.com',
            $referrer: 'https://google.com/?q=posthog',
            utm_medium: 'twitter',
            gclid: 'GOOGLE ADS ID',
            msclkid: 'BING ADS ID',
            $elements: [
                { tag_name: 'a', nth_child: 1, nth_of_type: 2, attr__class: 'btn btn-sm' },
                { tag_name: 'div', nth_child: 1, nth_of_type: 2, $el_text: '💻' },
            ],
            $app_build: 2,
            $app_name: 'my app',
            $app_namespace: 'com.posthog.myapp',
            $app_version: '1.2.3',
        }

        expect(personInitialAndUTMProperties(properties)).toMatchInlineSnapshot(`
            Object {
              "$app_build": 2,
              "$app_name": "my app",
              "$app_namespace": "com.posthog.myapp",
              "$app_version": "1.2.3",
              "$browser": "Chrome",
              "$browser_version": "95",
              "$current_url": "https://test.com",
              "$elements": Array [
                Object {
                  "attr__class": "btn btn-sm",
                  "nth_child": 1,
                  "nth_of_type": 2,
                  "tag_name": "a",
                },
                Object {
                  "$el_text": "💻",
                  "nth_child": 1,
                  "nth_of_type": 2,
                  "tag_name": "div",
                },
              ],
              "$os": "Mac OS X",
              "$os_version": "10.15.7",
              "$referrer": "https://google.com/?q=posthog",
              "$referring_domain": "https://google.com",
              "$set": Object {
                "$app_build": 2,
                "$app_name": "my app",
                "$app_namespace": "com.posthog.myapp",
                "$app_version": "1.2.3",
                "$browser": "Chrome",
                "$browser_version": "95",
                "$current_url": "https://test.com",
                "$os": "Mac OS X",
                "$os_version": "10.15.7",
                "$referrer": "https://google.com/?q=posthog",
                "$referring_domain": "https://google.com",
                "gclid": "GOOGLE ADS ID",
                "msclkid": "BING ADS ID",
                "utm_medium": "twitter",
              },
              "$set_once": Object {
                "$initial_app_build": 2,
                "$initial_app_name": "my app",
                "$initial_app_namespace": "com.posthog.myapp",
                "$initial_app_version": "1.2.3",
                "$initial_browser": "Chrome",
                "$initial_browser_version": "95",
                "$initial_current_url": "https://test.com",
                "$initial_gclid": "GOOGLE ADS ID",
                "$initial_msclkid": "BING ADS ID",
                "$initial_os": "Mac OS X",
                "$initial_os_version": "10.15.7",
                "$initial_referrer": "https://google.com/?q=posthog",
                "$initial_referring_domain": "https://google.com",
                "$initial_utm_medium": "twitter",
              },
              "distinct_id": 2,
              "gclid": "GOOGLE ADS ID",
              "msclkid": "BING ADS ID",
              "utm_medium": "twitter",
            }
        `)
    })

    it('priorities manual $set values', () => {
        const properties = {
            distinct_id: 2,
            $os_version: '10.15.7',
            $browser_version: '95',
            $browser: 'Chrome',
            $set: {
                $browser_version: 'manually $set value wins',
            },
            $set_once: {
                $initial_os_version: 'manually $set_once value wins',
            },
        }

        expect(personInitialAndUTMProperties(properties)).toMatchInlineSnapshot(`
            Object {
              "$browser": "Chrome",
              "$browser_version": "95",
              "$os_version": "10.15.7",
              "$set": Object {
                "$browser": "Chrome",
                "$browser_version": "manually $set value wins",
                "$os_version": "10.15.7",
              },
              "$set_once": Object {
                "$initial_browser": "Chrome",
                "$initial_browser_version": "95",
                "$initial_os_version": "manually $set_once value wins",
              },
              "distinct_id": 2,
            }
        `)
    })

    it('initial current domain regression test', () => {
        const properties = {
            $current_url: 'https://test.com',
        }

        expect(personInitialAndUTMProperties(properties)).toEqual({
            $current_url: 'https://test.com',
            $set_once: { $initial_current_url: 'https://test.com' },
            $set: { $current_url: 'https://test.com' },
        })
    })

    it('treats $os_name as fallback for $os', () => {
        const propertiesOsNameOnly = {
            $os_name: 'Android',
        }
        expect(personInitialAndUTMProperties(propertiesOsNameOnly)).toEqual({
            $os: 'Android',
            $os_name: 'Android',
            $set_once: { $initial_os: 'Android' },
            $set: { $os: 'Android' },
        })

        // Also test that $os takes precedence, with $os_name preserved (although this should not happen in the wild)
        const propertiesBothOsKeys = {
            $os: 'Windows',
            $os_name: 'Android',
        }
        expect(personInitialAndUTMProperties(propertiesBothOsKeys)).toEqual({
            $os: 'Windows',
            $os_name: 'Android',
            $set_once: { $initial_os: 'Windows' },
            $set: { $os: 'Windows' },
        })
    })

    it('add initial campaign properties unless set_once initial properties are set', () => {
        // baseline, ensure they are added
        const properties1 = {
            utm_medium: 'foo',
        }
        expect(personInitialAndUTMProperties(properties1)).toMatchInlineSnapshot(`
            Object {
              "$set": Object {
                "utm_medium": "foo",
              },
              "$set_once": Object {
                "$initial_utm_medium": "foo",
              },
              "utm_medium": "foo",
            }
        `)

        // not add if set_once initial campaign properties are set
        const properties2 = {
            utm_medium: 'foo',
            $set_once: {
                $initial_utm_source: 'bar',
            },
        }
        expect(personInitialAndUTMProperties(properties2)).toMatchInlineSnapshot(`
            Object {
              "$set": Object {
                "utm_medium": "foo",
              },
              "$set_once": Object {
                "$initial_utm_source": "bar",
              },
              "utm_medium": "foo",
            }
        `)

        // not add if set_once initial campaign properties are set
        const properties3 = {
            utm_medium: 'foo',
            $set_once: {
                $initial_referring_domain: 'example.com',
            },
        }
        expect(personInitialAndUTMProperties(properties3)).toMatchInlineSnapshot(`
            Object {
              "$set": Object {
                "utm_medium": "foo",
              },
              "$set_once": Object {
                "$initial_referring_domain": "example.com",
              },
              "utm_medium": "foo",
            }
        `)
    })

    it('handles a real anonymous event from posthog.com', () => {
        // I trimmed the feature flag properties as there were tons of them and they don't add anything to the test
        const properties = {
            $os: 'Mac OS X',
            $os_version: '10.15.7',
            $browser: 'Chrome',
            $device_type: 'Desktop',
            $current_url: 'https://posthog.com/?__posthog_debug=true',
            $host: 'posthog.com',
            $pathname: '/',
            $raw_user_agent:
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            $browser_version: 128,
            $browser_language: 'en-GB',
            $screen_height: 1329,
            $screen_width: 2056,
            $viewport_height: 1096,
            $viewport_width: 1122,
            $lib: 'web',
            $lib_version: '1.163.0',
            $insert_id: 'ju0g6rn6zhrjfmgs',
            $time: 1727102048.001,
            distinct_id: '01921f4d-8b9a-7142-97b9-8cb51b09021f',
            $device_id: '01921f4d-8b9a-7142-97b9-8cb51b09021f',
            $initial_person_info: {
                r: '$direct',
                u: 'https://posthog.com/',
            },
            utm_source: null,
            utm_medium: null,
            utm_campaign: null,
            utm_content: null,
            utm_term: null,
            $console_log_recording_enabled_server_side: true,
            $session_recording_network_payload_capture: {
                capturePerformance: {
                    network_timing: true,
                    web_vitals: true,
                    web_vitals_allowed_metrics: null,
                },
                recordBody: true,
                recordHeaders: true,
            },
            $session_recording_canvas_recording: {},
            $replay_sample_rate: null,
            $replay_minimum_duration: 2000,
            $autocapture_disabled_server_side: false,
            $web_vitals_enabled_server_side: true,
            $web_vitals_allowed_metrics: null,
            $exception_capture_endpoint_suffix: '/e/',
            $exception_capture_enabled_server_side: true,
            $referrer: '$direct',
            $referring_domain: '$direct',
            token: 'XXX',
            $session_id: '01921f4d-8b9a-7142-97b9-8cb31fcf8f91',
            $window_id: '01921f4d-8b9a-7142-97b9-8cb442641547',
            $lib_custom_api_host: 'https://internal-t.posthog.com',
            title: 'PostHog - How developers build successful products',
            $is_identified: false,
            $process_person_profile: false,
            $lib_rate_limit_remaining_tokens: 99,
        }

        expect(personInitialAndUTMProperties(properties)).toMatchInlineSnapshot(`
            Object {
              "$autocapture_disabled_server_side": false,
              "$browser": "Chrome",
              "$browser_language": "en-GB",
              "$browser_version": 128,
              "$console_log_recording_enabled_server_side": true,
              "$current_url": "https://posthog.com/?__posthog_debug=true",
              "$device_id": "01921f4d-8b9a-7142-97b9-8cb51b09021f",
              "$device_type": "Desktop",
              "$exception_capture_enabled_server_side": true,
              "$exception_capture_endpoint_suffix": "/e/",
              "$host": "posthog.com",
              "$initial_person_info": Object {
                "r": "$direct",
                "u": "https://posthog.com/",
              },
              "$insert_id": "ju0g6rn6zhrjfmgs",
              "$is_identified": false,
              "$lib": "web",
              "$lib_custom_api_host": "https://internal-t.posthog.com",
              "$lib_rate_limit_remaining_tokens": 99,
              "$lib_version": "1.163.0",
              "$os": "Mac OS X",
              "$os_version": "10.15.7",
              "$pathname": "/",
              "$process_person_profile": false,
              "$raw_user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
              "$referrer": "$direct",
              "$referring_domain": "$direct",
              "$replay_minimum_duration": 2000,
              "$replay_sample_rate": null,
              "$screen_height": 1329,
              "$screen_width": 2056,
              "$session_id": "01921f4d-8b9a-7142-97b9-8cb31fcf8f91",
              "$session_recording_canvas_recording": Object {},
              "$session_recording_network_payload_capture": Object {
                "capturePerformance": Object {
                  "network_timing": true,
                  "web_vitals": true,
                  "web_vitals_allowed_metrics": null,
                },
                "recordBody": true,
                "recordHeaders": true,
              },
              "$set": Object {
                "$browser": "Chrome",
                "$browser_version": 128,
                "$current_url": "https://posthog.com/?__posthog_debug=true",
                "$device_type": "Desktop",
                "$os": "Mac OS X",
                "$os_version": "10.15.7",
                "$pathname": "/",
                "$referrer": "$direct",
                "$referring_domain": "$direct",
                "utm_campaign": null,
                "utm_content": null,
                "utm_medium": null,
                "utm_source": null,
                "utm_term": null,
              },
              "$set_once": Object {
                "$initial_browser": "Chrome",
                "$initial_browser_version": 128,
                "$initial_current_url": "https://posthog.com/?__posthog_debug=true",
                "$initial_device_type": "Desktop",
                "$initial_os": "Mac OS X",
                "$initial_os_version": "10.15.7",
                "$initial_pathname": "/",
                "$initial_referrer": "$direct",
                "$initial_referring_domain": "$direct",
                "$initial_utm_campaign": null,
                "$initial_utm_content": null,
                "$initial_utm_medium": null,
                "$initial_utm_source": null,
                "$initial_utm_term": null,
              },
              "$time": 1727102048.001,
              "$viewport_height": 1096,
              "$viewport_width": 1122,
              "$web_vitals_allowed_metrics": null,
              "$web_vitals_enabled_server_side": true,
              "$window_id": "01921f4d-8b9a-7142-97b9-8cb442641547",
              "distinct_id": "01921f4d-8b9a-7142-97b9-8cb51b09021f",
              "title": "PostHog - How developers build successful products",
              "token": "XXX",
              "utm_campaign": null,
              "utm_content": null,
              "utm_medium": null,
              "utm_source": null,
              "utm_term": null,
            }
        `)
    })
    it('handles a real identified event from posthog.com', () => {
        // I trimmed the feature flag properties as there were tons of them and they don't add anything to the test
        // I also censored the token
        const properties = {
            $os: 'Mac OS X',
            $os_version: '10.15.7',
            $browser: 'Chrome',
            $device_type: 'Desktop',
            $current_url: 'https://posthog.com/web-analytics',
            $host: 'posthog.com',
            $pathname: '/web-analytics',
            $raw_user_agent:
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            $browser_version: 128,
            $browser_language: 'en-GB',
            $screen_height: 1329,
            $screen_width: 2056,
            $viewport_height: 1096,
            $viewport_width: 1122,
            $lib: 'web',
            $lib_version: '1.163.0',
            $insert_id: 'fz2kbdhxt7w1tr0i',
            $time: 1727102534.107,
            distinct_id: '01921f52-d3b3-7460-ad9e-f173b1118922',
            $device_id: '01921f52-d3b3-7460-ad9e-f173b1118922',
            $initial_person_info: {
                r: '$direct',
                u: 'https://posthog.com/?__posthog_debug=true',
            },
            utm_source: null,
            utm_medium: null,
            utm_campaign: null,
            utm_content: null,
            utm_term: null,
            $console_log_recording_enabled_server_side: true,
            $session_recording_network_payload_capture: {
                capturePerformance: {
                    network_timing: true,
                    web_vitals: true,
                    web_vitals_allowed_metrics: null,
                },
                recordBody: true,
                recordHeaders: true,
            },
            $session_recording_canvas_recording: {},
            $replay_sample_rate: null,
            $replay_minimum_duration: 2000,
            $autocapture_disabled_server_side: false,
            $web_vitals_enabled_server_side: true,
            $web_vitals_allowed_metrics: null,
            $exception_capture_endpoint_suffix: '/e/',
            $exception_capture_enabled_server_side: true,
            $referrer: '$direct',
            $referring_domain: '$direct',
            token: 'XXX',
            $session_id: '01921f52-d3b2-703f-b62a-7defe01f09c7',
            $window_id: '01921f52-d3b2-703f-b62a-7df08296f81a',
            $lib_custom_api_host: 'https://internal-t.posthog.com',
            $prev_pageview_last_scroll: 556,
            $prev_pageview_last_scroll_percentage: 0.0460531765095668,
            $prev_pageview_max_scroll: 559,
            $prev_pageview_max_scroll_percentage: 0.04630166487202849,
            $prev_pageview_last_content: 1652,
            $prev_pageview_last_content_percentage: 0.12544612347178982,
            $prev_pageview_max_content: 1655,
            $prev_pageview_max_content_percentage: 0.12567393120206546,
            $prev_pageview_pathname: '/',
            $prev_pageview_duration: 158.734,
            title: 'PostHog - How developers build successful products',
            $is_identified: false,
            $process_person_profile: true,
            $lib_rate_limit_remaining_tokens: 97.05999999999999,
            $set_once: {
                $initial_referrer: '$direct',
                $initial_referring_domain: '$direct',
                $initial_current_url: 'https://posthog.com/?__posthog_debug=true',
                $initial_host: 'posthog.com',
                $initial_pathname: '/',
            },
        }

        expect(personInitialAndUTMProperties(properties)).toMatchInlineSnapshot(`
            Object {
              "$autocapture_disabled_server_side": false,
              "$browser": "Chrome",
              "$browser_language": "en-GB",
              "$browser_version": 128,
              "$console_log_recording_enabled_server_side": true,
              "$current_url": "https://posthog.com/web-analytics",
              "$device_id": "01921f52-d3b3-7460-ad9e-f173b1118922",
              "$device_type": "Desktop",
              "$exception_capture_enabled_server_side": true,
              "$exception_capture_endpoint_suffix": "/e/",
              "$host": "posthog.com",
              "$initial_person_info": Object {
                "r": "$direct",
                "u": "https://posthog.com/?__posthog_debug=true",
              },
              "$insert_id": "fz2kbdhxt7w1tr0i",
              "$is_identified": false,
              "$lib": "web",
              "$lib_custom_api_host": "https://internal-t.posthog.com",
              "$lib_rate_limit_remaining_tokens": 97.05999999999999,
              "$lib_version": "1.163.0",
              "$os": "Mac OS X",
              "$os_version": "10.15.7",
              "$pathname": "/web-analytics",
              "$prev_pageview_duration": 158.734,
              "$prev_pageview_last_content": 1652,
              "$prev_pageview_last_content_percentage": 0.12544612347178982,
              "$prev_pageview_last_scroll": 556,
              "$prev_pageview_last_scroll_percentage": 0.0460531765095668,
              "$prev_pageview_max_content": 1655,
              "$prev_pageview_max_content_percentage": 0.12567393120206546,
              "$prev_pageview_max_scroll": 559,
              "$prev_pageview_max_scroll_percentage": 0.04630166487202849,
              "$prev_pageview_pathname": "/",
              "$process_person_profile": true,
              "$raw_user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
              "$referrer": "$direct",
              "$referring_domain": "$direct",
              "$replay_minimum_duration": 2000,
              "$replay_sample_rate": null,
              "$screen_height": 1329,
              "$screen_width": 2056,
              "$session_id": "01921f52-d3b2-703f-b62a-7defe01f09c7",
              "$session_recording_canvas_recording": Object {},
              "$session_recording_network_payload_capture": Object {
                "capturePerformance": Object {
                  "network_timing": true,
                  "web_vitals": true,
                  "web_vitals_allowed_metrics": null,
                },
                "recordBody": true,
                "recordHeaders": true,
              },
              "$set": Object {
                "$browser": "Chrome",
                "$browser_version": 128,
                "$current_url": "https://posthog.com/web-analytics",
                "$device_type": "Desktop",
                "$os": "Mac OS X",
                "$os_version": "10.15.7",
                "$pathname": "/web-analytics",
                "$referrer": "$direct",
                "$referring_domain": "$direct",
                "utm_campaign": null,
                "utm_content": null,
                "utm_medium": null,
                "utm_source": null,
                "utm_term": null,
              },
              "$set_once": Object {
                "$initial_browser": "Chrome",
                "$initial_browser_version": 128,
                "$initial_current_url": "https://posthog.com/?__posthog_debug=true",
                "$initial_device_type": "Desktop",
                "$initial_host": "posthog.com",
                "$initial_os": "Mac OS X",
                "$initial_os_version": "10.15.7",
                "$initial_pathname": "/",
                "$initial_referrer": "$direct",
                "$initial_referring_domain": "$direct",
              },
              "$time": 1727102534.107,
              "$viewport_height": 1096,
              "$viewport_width": 1122,
              "$web_vitals_allowed_metrics": null,
              "$web_vitals_enabled_server_side": true,
              "$window_id": "01921f52-d3b2-703f-b62a-7df08296f81a",
              "distinct_id": "01921f52-d3b3-7460-ad9e-f173b1118922",
              "title": "PostHog - How developers build successful products",
              "token": "XXX",
              "utm_campaign": null,
              "utm_content": null,
              "utm_medium": null,
              "utm_source": null,
              "utm_term": null,
            }
        `)
    })
})
