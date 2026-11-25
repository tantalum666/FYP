# Alice’s standing Gmail reminders

25 November 2026, Hong Kong. Application `83bcf577` builds on the workspace release `b759950c`. The observations below distinguish a provider read, a suggestion in the ordinary conversation, a local notice, a push-provider acknowledgement and an alert actually seen by the owner. The public record contains aggregate numbers and synthetic examples only.

## The normal desk

The Mac launch service was running with ordinary proactivity enabled and a registered Chrome subscription. Its 19:36 Gmail read returned `APP_CONNECTION_FAILED`. Its 19:42 read succeeded and returned ten previews with the same grant. An independent read through the registered FYP Gmail client confirmed ten Google metadata responses. No Google reauthorization was needed. The service’s previous generic error does not identify the HTTP status or cause of that individual failure.

The old release showed zero actionable suggestions. It had marked all 11 stored suggestions obsolete. Yesterday's 12 distinct cited Gmail messages were all outside the newest ten. There were two earlier local notice batches. The “browser” records identify writes to the browser queue. The older version discarded the Web Push sender’s success count, so those rows alone do not establish external acceptance or device display.

The existing OpenAI daily ledger ended on 24 November. On 25 November it reported inactive. The monitor remained in local mail mode. None of the ten sampled current previews matched an explicit local action cue. Mail retrieval and source reconciliation do not require a paid request.

## Correction

The source projection uses the current grant’s bounded recent inbox for discovery. For a pending or previously delivered suggestion, Alice can also recheck the inbox as of the original finding time. A scheduled refresh makes at most one additional ten-message Gmail query. References must match the existing fingerprint of both the content and the grant. Earlier message IDs are not passed to another account. The look-back is limited to seven days and the start of the current grant. Checked links have a bounded in-memory lifetime. The model does not receive the look-back results as new mail.

A temporarily unavailable provider hides unverified evidence. A temporary error by itself cannot close a still-current pending notice. Late delivery requires a positive match with current evidence. A previously delivered suggestion can be read under its original time in ordinary chat. Its appearance in chat does not create a second notice, wake Alice on Home or authorize an action. Explicit dismissal, lost authority, stopped threads and expired or changed evidence constrain the projection. An expired Gmail refresh grant offers reconnection. A temporary failure is described in Settings with automatic retry.

The existing notifier now records `web_push_accepted` separately after its sender reports at least one successful subscription. A 2xx from a push service still does not show that the device displayed the notification. The native iOS shell already schedules calendar reminders locally. It has no APNs receiver for unsolicited Gmail updates in a closed native app.

## Independent checks

- Started the actual application scheduler with an isolated Gmail transport and the paid allowance closed. With zero browser pages open, a pickup email produced one suggestion and one generic notification. Simulated an upstream 503, then a changed newest inbox. Reopening ordinary chat showed precisely one suggestion with its original timestamp and original Gmail thread. The test receiver had one payload. No model, mail send, shopping or booking call ran.
- Local behavioral tests exercised old delivered rows across restart, positive link matching, stopped or changed account, explicit consent failure, archived mail, dismissal, bounded retries, quiet-hour delivery and the distinction between a local browser queue row and accepted push. The affected backend selection passed 25 tests and the existing conversation timeline passed six. TypeScript, Vite, targeted Ruff checks and the source diff check passed. The existing Starlette test client deprecation and Vite bundle-size warning remain.
- Used the normal grant to independently recheck old evidence. Three earlier suggestions matched exact currently authorized originals before installing. The production readback is recorded below.

## Engineering references

Read the project agent entry, current product and handoff, latest workspace and personal-agent decisions, the proactive-assistance, app connections and Web Push contracts, and relevant sections of the personal-agent research index. Inspected the scheduled worker, connected Gmail reader, OAuth error handling, original application ledger, source validation, notification transport, ordinary conversation and native notification code. The official structured Responses call, product scheduler and existing Gmail access remain the execution path. Hosted agent automations run scheduled sessions. The current repair concerns local evidence lifetime and receipt accounting. [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs) · [OpenAI scheduled automations](https://developers.openai.com/api/docs/guides/agents-api/sessions/automations) · [Gmail error handling](https://developers.google.com/workspace/gmail/api/guides/handle-errors).

The code and acceptance received a local self-review. No stored mailbox subject, private link, account identifier or credential is published. [Synthetic reopened chat](fixture-reopened.jpg).
## Deployment readback

The normal Mac served `83bcf577`. Its authenticated, scheduled read at 20:15 Hong Kong time returned ten eligible inbox previews. The ordinary workspace API returned three previously delivered suggestions verified against their original messages and zero new active suggestions. A fresh browser opened the normal Alice Home, expanded Conversation and found three dated cards. All three had a link to the original Gmail source and the matching original time. [Sanitized measurements](checks.json). The day's initiative ledger still showed zero paid analyses and zero new proactive notices, with one active browser subscription. No synthetic notification was sent to the owner.

The Mac release switch verified the existing data in 142 tables, owner grants, stored conversations and A3 v9. On this busy Mac, the initial operator HTTP preflight timed out. With a longer localhost read timeout the same build, account and rollback checks passed. The independently installed iPhone 17 Pro Simulator WKWebView showed the original dated test message and its source at 402 × 874. The ordinary Simulator then received the same build in place with 79 asset comparisons and six durable data checks. The original Pi relay did not connect. Its update package was built from its recorded `92acac8e` base and retained privately. A physical iPhone and closed-native-app push were outside this verification.
