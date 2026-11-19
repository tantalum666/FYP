# Alice flight booking on the iPhone 17 Pro Simulator

On 19 November 2026 the installed native app processed a Chinese booking request in its ordinary Alice conversation. GPT‑6.2 Sol used the existing official OpenAI Session and the application Function `sandbox_flight_quote`. The operator made both price decisions in the simulator. LetsFG returned simulated PNR **5SMZA7** and captured **HK$36.25** on its simulated Visa ending 4242. A separate process reopened the supplier booking and matched the original quote, revised approval, PNR, currency and capture. Real card charges were HK$0. [Sanitized receipts](receipts.json) · [product contract](../../../desk-companion/docs/conversation-flight-booking.md) · [provider sandbox](https://letsfg.co/developers/docs/api-sandbox/index.html).

## What appeared in the conversation

| Step | Simulator and independent observations |
| --- | --- |
| Request | From Alice’s normal home composer, entered a Chinese request for FR4315 on 25 November, HKG to HND, one adult, no checked bag. It explicitly requested a price-change rehearsal. The app showed Full access. The visible app was the installed `dev.group2.deskcompanion` on iOS 26.5. |
| Quote | Alice displayed **FR4315**, local departure **19:00**, arrival **22:10**, and **HK$34.00** for one adult. The matching local record had no approval, upstream order reference, PNR or capture. |
| First approval | The operator tapped **Book for HK$34.00**. Only afterwards did the local record acquire its upstream order reference. The approved amount was 3,400 HKD minor units; capture and PNR were empty. |
| Repricing | The card showed **HK$34.00 → HK$36.25**, the deadline **22:54:25 HKT**, and distinct acceptance and decline controls. Before the tap, the authorized amount was still HK$34.00. |
| Second approval | Tapped **Accept HK$36.25** on that card. Only that decision raised the locally approved total to HK$36.25. The existing order went on processing. The card showed neither a capture nor a PNR before the terminal provider read. |
| Final receipt | The card displayed **5SMZA7**, **HK$36.25 simulated charge** and **HK$0 real charge**. Fresh vendor GET independently returned `sandbox=true`, `state=completed`, the same PNR and captured HKD amount. |
| Follow-up | After the backend restarted, entered “帮我查回这笔订单的订座编号和扣款结果” in the same native conversation. Alice returned the same PNR, simulated and real amounts from its verified receipt. Order count and OpenAI admissions were unchanged during the follow-up. |

The dated screenshots and the two provider IDs are in the operator’s private `alice-flight-chat-20261119` directory. The public receipt records screen digests and a local reference hash. The synthetic timetable, test PNR and simulated payment do not reserve airline inventory. No Singapore Airlines account was created.

## Divergences and repair

The first ordinary model call requested the correct Function and itinerary. Its provider read returned no verifiable quote. No order was created. Subsequent direct reads with the same adapter returned FR4315 at HK$34.00. The exact upstream cause of that first transient response was unavailable. The adapter now retries one transient **search**. An uncertain booking submission retains its original idempotency key.

A first fast-mode order exposed a short human decision window. The simulator showed an increase to HK$37.21; the approval arrived after expiry. A separate provider GET confirmed a failed outcome, null capture, empty PNR and released hold. Reprice rehearsals now use the human-paced provider scenario. Alice displays the provider deadline and checks the active round before sending an answer. The successful HK$36.25 case above used a new, explicitly approved quote.

## Release, scope and cost

The successful booking ran on application source `02feaffa`. The Mac backend serving the simulator subsequently moved to `03ca29d3` for chat-scoped follow-up and recovery. The iOS/frontend sources are identical across those commits. The installed native app was left on its receipt. All 77 active native frontend files matched the checked build, and the final shared backend passed its database, protected-data, A3 v9 and account checks. The previously published Pi `85e6aa94` was outside this change. An operator can return the local service to its retained release and environment backup. Raw backups, the FYP key, provider IDs and the simulated passenger payload were excluded from the published record.

Three real OpenAI quote attempts produced six model-input/Function-continuation admissions in total, including the transient read and the fast-mode rehearsal. At closeout the Mac ledger showed an additional **US$0.48 in unresolved reservations** and **US$0.36 available** in its previously authorized share of US$10 for 19 November. These six entries had no itemized token usage. The platform-billed amount for this run was unavailable. The approvals, polling and local receipt follow-up issued no additional model requests.

Read the project entry, current product and handoff, recent booking decisions, commerce research index, earlier LetsFG receipts, ordinary Sessions and UI contracts, offline trip reapproval, provider sandbox documentation and existing native release procedure. Used the official Functions guide, iOS simulator/debugging tools and the actual native WebView. The simulator mirror and signed app were used for the UI. The debugger inserted the Chinese text into the focused ordinary input; send and both approval actions used visible on-screen controls. No direct API submission replaced those UI actions.

Four focused regression cases covered quote-only admission, accepted or refused increases, scoped access, duplicate/cached reviews, incorrect captures, lost creation acknowledgement and transient search recovery. Two further cases covered follow-up after loss of in-memory chat state and explicit forgetting. Each affected slice ran locally. The frontend typecheck/build, native build/install, actual supplier journey and independent readback were checked. Existing full suites, older paid trials and hardware tests were not repeated. The changes were self-reviewed and published on the existing feature PR.
