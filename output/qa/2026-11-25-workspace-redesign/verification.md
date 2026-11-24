# Alice’s secondary screens

25 November 2026, Hong Kong. The accepted application revision is `b759950c579f94bc374b31932e63c9dc12e06412`. The normal Mac previously ran `cc759345`; the change branch began at public main `cc8350c5`. Operator records and backup copies are private. The illustrations below contain invented task, calendar and reminder data.

[Desktop task detail](desktop-tasks.jpg) · [Chinese iPhone task detail](iphone-tasks.jpg) · [Six other workspace views](workspace-views.jpg) · [Measurements](checks.json).

## Reproduction and outcome

On the everyday Mac at 1280 × 720 there were 17 open notice receipts. The previous shared header placed every notice in the same horizontal flex row. Line wrapping produced a 591.5-pixel band and put the Tasks title 649.5 pixels from the top. Old notices appeared on Calendar and other pages that used the same header.

After installing this release, the same Mac at the same viewport had a zero-height notice band. The Tasks title began 27.5 pixels from the top. Inbox still showed all 17 receipts in three groups. Opening Inbox and returning to Tasks retained those receipts. No owner dismissal was performed. The local test store independently verified that dismissing one selected receipt dropped the count by exactly one and retained the others. A 25-receipt backend case covered pagination when a prior page’s last receipt had already been dismissed.

## References used in the redesign

| Product surface examined | Observation applied to Alice |
| --- | --- |
| OpenAI’s official desktop Codex walkthrough, including the automation form and review queue. The local Codex window was unavailable to automation. [OpenAI’s walkthrough](https://openai.com/index/introducing-the-codex-app/) | A stable place for work, a separate place to review outcomes and one primary action per view. Alice keeps the task list and selected task together on wide screens. |
| Installed Grok Bot 1.2.3. Opened its app directory and Settings and returned to the prior conversation. [Grok Bot settings](https://docs.x.ai/grok-bot/settings-and-notifications) | The search and connection state are visible in the directory. Selecting a specific app reveals its permissions and actions. Settings preserves the selected category on return. |
| Meta’s design article and its published mobile interface previews. The private Muse app required sign-in. [Meta’s design article](https://muse.ai/blog/how-we-designed-muse) · [Muse mobile screens](https://apps.apple.com/us/app/muse-from-meta/id6760173601) | Let a personal update lead back to its conversation. On phones, give the active task the screen and keep a short row of workspace destinations. |

Following the owner’s feedback, we replaced the first green-sidebar concept with a compact neutral rail and a restrained selection color. The wide and narrow presentations share their underlying task, memory, permission and notice operations.

## Acceptance from ordinary entry points

| Entry | Observed on synthetic data |
| --- | --- |
| Today and Tasks | Opened the exact task from Today. Desktop kept the list and selection together. Phone restored the list, search and filters. Editing a note and switching tasks offered keep/discard. A later task had its own evidence. |
| Calendar and Records | Switched day, week and month, moved to a later month and back, and saved a calendar event. Its name was independently present in the Calendar category of Records. The CSV export remained available. |
| Inbox | Morning/evening groups expose individual dates, explanations and dismissals. A personal update opened the existing expanded conversation. Unconnected display access was denied by the owner endpoint. Foreground alerts distinguish arrivals from old items resurfacing through pagination. |
| Saved memories and Assistant style | Searched saved memories, created a synthetic memory and read it through the API. Cancelling Forget preserved it. Edit, tools, instructions and existing voice selections were reachable. |
| Settings, Connections and Diagnostics | Changed categories with an unsaved settings value and returned to that draft. Searched for Gmail and inspected effective access. Traversed import/share, calendar/companion, posture and app connections at both widths. Opened Work & tools, changed its sample input, observed the draft guard, restored the original value and closed it. |
| Responsive layout and keyboard | Nine Web destinations in English at 1320 × 860 and Chinese at 390 × 844. No uncaught page errors, hidden-overflow content or horizontal document scroll in those samples. Rail collapse persisted on reload, the narrow drawer returned focus on Escape, and visible text contrast was sampled on all nine pages in light and dark. |
| Home and hardware views | At 1280 × 720, production bundles before and after gave identical rectangles and sampled colors/font sizes for the Home avatar area, agenda, conversation, composer and More control on the same data and clock. The shared busy-only calendar rendered without event titles. The 800 × 480 kiosk opened a task and preferences within bounds, including a click during startup. |
| Native iPhone | In the actual installed Capacitor WKWebView on an isolated iPhone 17 Pro running iOS 26.5, opened the app directory, returned to the same Settings category and selected a Chinese task. The 402 × 874 view showed the task’s saved progress and four bottom controls with zero horizontal overflow. The screenshot came from Simulator. |

The changed notification and nudge tests passed (10). Targeted frontend regressions passed (15), plus four trip-quote checks after correcting the initial draft state. The TypeScript and production Web build, targeted Ruff checks and secret scan passed. The existing Vite chunk-size and Starlette test-client warnings were observed. This was a self-review with local rendered acceptance against a synthetic store that blocked external connections. Closed provider and payment trials were not used for the redesign.

## Fixes found during acceptance

The older desk software treated an untouched trip fixture as a draft because it compared the prefilled value to an empty string. That prevented closing the entire Work & tools panel. The guard now compares with its initial or last loaded value. An early kiosk tap also used to be lost while authentication was still loading. The kiosk now remembers the requested panel and reveals it after authentication. Low-contrast secondary labels in the calendar and dark task inspector were corrected. A stale text assertion in the reminders test now checks its existing owner-only control.

## Release and scope

Mac Web serves this revision at the usual address. The release switch independently checked the persistent store (142 tables before and after), retained conversation and protected settings, effective app authorizations and A3 v9. The everyday iPhone Simulator received the matching build in place. The installer independently compared all 79 packaged resources and six durable app-data checks. The original Pi’s relay did not accept its connection. A versioned package from its recorded `92acac8e` base is retained by the operator. Hardware and a physical iPhone were not exercised in this pass. Mac and Simulator rollback copies are retained with their deployment receipts.

Read the project agent entry, current product sections for Home and ordinary conversation, handoff, relevant recent decisions, contribution workflow, public-agent research index and interface-copy contract. Inspected changed React, notification, scope, device and native paths and the global review guidance for release and UI checks. Updated the project entry, product contract, interface guidance, decisions, work log and handoff. The public record contains synthetic screenshots and aggregate measurements.
