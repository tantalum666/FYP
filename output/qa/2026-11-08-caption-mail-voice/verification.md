# Group 2 · Captions, voice and connected apps

8 November2026. Local tests, rendered UI, paid synthetic speech, native Gmail delivery, and activation are recorded separately. No GitHub CI.

## Reading and selected scope

Continued this active task rather than restarting prior acceptance. Focused entry/current sections: AGENTS.md; product.md current requirements and implementation boundaries; handoff.md; START_HERE_NEXT_CHAT.md; decision-log.md November7–8decisions; current and dialogue-voice QA; personal-agent-research-index dated current scope and previously-read comparison sections. Alice home and OpenAI wake contracts were read; current maintenance/conversation sections, application-connectors authority/credential boundaries and changed implementation were reviewed. Long historical files were not relabelled as wholly reread. OpenAI documentation, frontend debugging/React and email-reliability guidance had been applied earlier in this same task; relevant current primary-source references are in connected-apps.md.

Owner scope: readable latest caption; remove immersive technical footer; inspect stutter/effective voice; actual email sending. Later owner decisions replaced the temporary SMTP/password prototype with official browser app authorization, included Microsoft, and expressly deferred Microsoft's actual authorization. Google policy/client setup was separately approved, then Gmail consent was completed personally by the owner. Original owner-preview dirty notes were preserved.

## Final implementation and local checks

Latest caption has a dark, bounded wrapping background. Conversation retains separate turns and no Voice input cards. New ResizeObserver-based conversation footprint prevents the phone's agenda from extending behind variable-height caption/input content, without resizing Alice. Optional action cards retain readable dark contrast; actual errors/reviews remain visible after removing the immersive provider/microphone line.

Shared AppOAuth owns PKCE, one-use state, cancellation, account version and encrypted credentials. Static app manifests and bounded Google/Graph readers reuse existing AssistantService tools/proposals. Gmail/Outlook send only from owner review, reserve an attempt before sending, recover accepted results and do not retry uncertain writes. Final tool catalog30. No credentials are collected in product UI and no Codex account token is transferred.

2103backend tests passed (415.48s),351frontend tests passed, typecheck/build and scoped Ruff passed. The two backend warnings are existing Starlette httpx deprecation and empty-regex pytest warnings. The build retains the existing large renderer chunk warning.42focused app/mail/legacyCalendar checks include callback-origin binding, PKCE/refresh, cancelled or replaced authorization, privacy/account changes, exact endpoints, no pagination chasing, sender choice, draft expiry, response loss, once-only sending and conservative unknown writes. Subsequent layout/copy-only changes passed build and actual browser inspection; backend source remained unchanged.

## Actual browser checks

Separate Chrome QA origin8832used production client/protocol/display code and a visibly labelled offline replay, with synthetic silent capture and no provider access. Long Chinese response on desktop wrapped in a548.84px dark surface; provider/mic footer absent. On393×852phone, measured agenda bottom542and conversation top554:12px separation. On320×568,264vs276.41; expanded history bottom413and composer top413, independently scrollable without overlap or horizontal overflow. A first phone render revealed the old fixed reserve still overlapped the longer caption; the measured-footprint fix was then reapplied and inspected. The screenshot before this fix is not a final pass. Temporary overrides were cleared.

Actual normal Mac Apps UI opened Google's official FYP client login/consent with callback5190. Owner completed consent. Apps changed to the owner account plus Reconnect/Disconnect/Prepare a test email. The test draft showed exact From/To/Subject/body and expiry; one Send click returned provider acceptance. Microsoft entries truthfully show setup pending. No app-password form remains.

## Native Gmail acceptance

A dedicated FYP Google project/client was created, not an existing unrelated project's credential. External/Testing, one owner test user, Gmail/Calendar APIs enabled, six approved loopback callbackURIs. Client secret resides only in mode600 private files. Google Calendar permission is not granted merely because its API/client is configured.

Mac FYP sent subjectFYP email test/bodyTest to the owner once. An independent Gmail API GET using FYP's own authorized token read the exact returned provider message ID: From/To/subject/plain-text body matched; SENT and INBOX were both present; local attempts=1. This replaces the earlier connector-assisted-only limitation for Mac Gmail. The provider rewrote the submitted MIME Message-ID, so correlation uses the actual Gmail message ID and content. The first readback helper incorrectly examined the message wrapper instead of its MIME payload; correcting that reader required no additional send. No third-party mail was sent. Public summary excludes account/token/message/proposal identifiers.

Microsoft365 covers Outlook mail/calendar, OneDrive file directory, ToDo and OneNote lists; Teams/SharePoint are organization-only. Office document editing, realMicrosoftaccount operations and unattended email monitoring are not claimed. VTC developer access was denied; owner chose to defer authorization. Google/Microsoft backend transport is an API adapter with app-style OAuth; the generic MCP public/synthetic policy remains unchanged.

## Paid voice result and limits

Fresh ceilingUSD1, synthetic audio only. CLOSED conservative accountingUSD0.346456;5sessions finalized, all6delegated response receipts received. Original/Gleam/Bright samples returned actual speech and matching requested/provider voice echoes. Normal Mac selects Alice · Bright; real samples are cached for repeat listening without new generation. No claim that text receipt alone proves natural Cantonese pronunciation or that a cute voice must sound natural to every listener.

First fullbrowser attempt failed: a delivered email review was still subject to the speech deadline, and a fixed fixture clock made the card look expired. Both were corrected. The second fullbrowser run succeeded with29tools,3delegated responses,49providerseconds, Mandarin/email draft/English+Cantonese and actual browser output acknowledgement. Email transport in that paid fixture was mocked; real Gmail delivery is the separate acceptance above. First audible output after inputs was1.488/1.633/1.254seconds, including acknowledgments; not first useful task-answer latency. Final30-tool OAuth integration was verified locally, without reopening the budget.

CaptureTimeline now requires sustained120ms onset; PlaybackSchedule uses80ms initial/120ms recovery lead with bounded30second queued audio and diagnostics. Rebuffers can include intentional tool pauses, so are not simply a stutter count. turn_review acknowledges a delivered pending proposal without claiming speech or sending. Effective-voice metadata and failures are private diagnostics. Human acoustics/AEC, physicalPi audio and long-running naturalness remain separate work.

## Operation, publication and next step

Mac API8831/Vite5190runs current source with owner-approved private Googleclient; a new stopped/checkpointed backup was verified before OAuth tables/config activation. Earlier backup and all closed budget ledgers remain. The22-file Pi backup was retrieved and hash-verified off-device. Source232b065 is now active on Pi with305verified files, both app/application services active, exact servedfrontend and original owner keys retained. Google client config and Alice · Bright/threecachedsamples are installed privately. Pi Gmail/Calendar are configured but unconsented; Mac account tokens were not copied. The first activation failed because the operator package omitted the wake-model configuration, and automatically rolled back. The corrected manifest includes all five tracked config files; isolatedPi workspace returned200 before the successful retry. See [activation](activation-summary.json). Publication is recorded separately. No hardware/power diagnosis was resumed.

Updated contracts: product, decision-log, shared home, desktop conversation, voice/wake, maintenance, connected-apps, application-connectors and research index. Handoff/work-log/entry and activation/publication status are finalized at closeout. Private audio/screenshots/rawtestlogs/OAuthcredentials/backups are outside Git under ~/.config/desk-companion/caption-mail-voice-20261108/ and ~/.config/desk-companion/google-oauth/.


Final UI/cleanup: the updated Pi preview8891 visibly showed Desk connected, Alice, calendar/time/weather, composer and local wake switch with no provider/microphone footer. Owner Web/phone/Pi previews and the actual Gmail connection result were retained. Offline QA tab/server8832 closed and all temporary device-metric overrides cleared. Final frontend351checks passed again after the measured-layout addition. Source and boundary-aware secret scan passed; a broad initial pattern only matched a historical desk-companion path. All current entry/handoff/work-log files were updated and local links checked before publication.
