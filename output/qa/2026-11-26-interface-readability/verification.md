# Alice reminder actions and settings contrast

26 November 2026. Application `14e50899` was self-reviewed against `3a755f76`. The original reports came from the ordinary Mac interface. All captured examples below use a private test store with fictional reminders and no external connector grants.

## Reminder actions

The previous desktop layout put the edges of the three buttons 0 CSS pixels apart. The primary button measured 40 pixels high and the other two measured 34. The existing wrapping action row now contains the three buttons. Follow-up status stays above the row. The source disclosure and each button keep their own controls.

| Rendered surface | Result |
| --- | --- |
| Desktop Web, 1336 px | Three 44 px-high targets on one row with 14 px between neighbors in English and Chinese. [Desktop capture](reminder-desktop.png). |
| Narrow Web, 393 and 320 px | Buttons wrap as space requires and stay inside the card. Wrapped rows have a 6 px gap. Both languages and both color schemes passed. [320 px capture](reminder-narrow.png). |
| Native iPhone Simulator, 402 px | The installed Capacitor app showed three 44 pt-high targets and a second row in English. The two measured gaps were 14 and 6. |

In the compiled UI, clicking the three controls on three distinct sample findings produced a linked follow-up task, a 60-minute deferral and a dismissal. Each receipt named the intended finding. After following, the status appeared and the create-task button disappeared. Reloading and opening the narrow conversation preserved that status.

## Settings text

Workspace panels inherited a light-mode fallback for their foreground. The search field used the browser placeholder color. The workspace palette now supplies both colors, and management dialogs opened from Home receive the same palette as those opened from Settings.

| Text in Connections | Prior dark | Current dark | Current light |
| --- | ---: | ---: | ---: |
| Apps heading | 1.07:1 | 13.48:1 | 16.07:1 |
| Search apps placeholder | 3.06:1 | 6.71:1 | 5.60:1 |

Chrome measurements use the rendered text over its composited background. Both languages passed the 4.5:1 text target in the four Settings panels and the Home shortcut to Connections, in light and dark mode. A separate pass opened directory rows and available detail disclosures. The checks covered displayed, enabled text and placeholders. Search narrowed the list to Gmail, both directory filters worked, and the Gmail row expanded on the native dark screen. [Chinese Connections dialog](connections-dark.png) · [Simulator capture](simulator-connections.png).

## Release and checks

The production build and the existing snooze contract passed. The rendered follow-up test now measures the clickable rectangles. A new Connections test checks the heading and placeholder on both entry routes in both themes. Its first run exposed a missing allowed origin on the temporary test server. After using that server’s actual loopback origin, the test passed. The fixture used local data and the UI checks made no paid model calls.

The ordinary Mac served the new bundle. A fresh visit to its actual Connections dialog returned heading `#eeeff3` on `#232429` and placeholder `#b1b2bf` on `#2a2b31`. The release switch verified retained sessions and messages, configuration, account grants and all 145 existing database tables. The ordinary iPhone Simulator received the app in place, with all 79 packaged resources and seven durable-data checks verified. The visual Simulator check used a separate installation of this same build and an isolated store. The Pi update is staged from the previously observed device version `92acac8e`; installation on the Pi is pending.

Read scope covered the current sections of `AGENTS.md`, `product.md`, `handoff.md`, `decision-log.md`, the contribution and publication guidance, the reminder and workspace sections of the interface-copy contract, and the preceding integration and workspace QA. Inspected the rendering component, shared theme, responsive rules, modal entry points, relevant tests and release receipts. Updated the interface-copy contract, product contract, decision log, work log and current handoff. The release operator retains the previous Mac bundle and Simulator package for rollback.
