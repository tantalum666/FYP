# Group 2 Project Contract

## 2026-11-23 Add a confirmed flight to the desk calendar

Alice can use the verified flight receipt from this conversation to prepare a private local calendar event. Show the complete itinerary in the desk timezone, wait for a separate calendar confirmation and read the saved event back. A repeat action must preserve a later local edit or deletion. [Journey](desk-companion/docs/conversation-flight-booking.md#add-a-booked-test-flight-to-the-desk-calendar).

## 2026-11-22 Match flight choices to the owner’s calendar

When asked to avoid existing commitments, Alice checks the published itinerary against the locally saved busy calendar. Show only verified fits within the owner’s search constraints, keep overnight arrival dates visible and recheck the calendar at confirmation. If the owner’s schedule changes, offer a different unbooked fare under the same constraints and ask for a fresh decision. The normal home remains one line. [Acceptance](output/qa/2026-11-22-calendar-aware-fares/verification.md).

## 2026-11-21 Focus the conversation and follow an approved order

Alice’s home shows one short current result or a link to review a quote. In Conversation, a transaction has one current presentation. Older orders and itemized receipts open on demand. A flight choice requests a fresh quote. Changed prices still require explicit approval. Once work is underway the desk can check the original order while the conversation is away and bring back a verified result or a necessary decision in that same login and chat. Preserve drafts, account privacy and the active review. [Native comparison and follow-up](output/qa/2026-11-21-quiet-order-followup/verification.md).

## 2026-11-21 Buyer cancellations and unavailable flights in ordinary chat

For a paid shippable test purchase, the owner can request a full pre-dispatch cancellation and reopen the original charge, refund and net. For a flight, allow an owner to stop an active supplier booking and separately verify its hold, charge and booking reference. Preserve the seller’s post-ticketing rules. If the selected flight is unavailable, offer eligible alternatives with local times and all-in sandbox fares, and await the owner’s new selection and approval. The Simulator verified Woo order #21 at HK$12 refunded in full and a released HK$52 LetsFG hold. [Acceptance](output/qa/2026-11-21-commerce-aftercare/verification.md).

## 2026-11-20 Overseas marketplace shopping and cancellation

The separate Link Agent Wallet acceptance uses the official CLI and the owner-connected FYP profile. Link approved a 180-day recurring test authorization of US$500 per month for the FYP sandbox. The testing path limits each order to US$10. The US$1 tissue order remains unpaid. The original issuer response contained Link's published test fixture, which fails the card-number checksum required at this checkout. The operator supports the two scope formats observed across authorizations and refreshes. [Payment evidence](output/qa/2026-11-20-overseas-shopping-sandboxes/verification.md#approved-recurring-test-allowance) · [Issuer fixture diagnosis](output/qa/2026-11-20-link-wallet-diagnosis/verification.md).

The owner selected overseas sandboxes first. A marketplace acceptance needs an all-in quote, the owner's approval, a paid sandbox order, immediate buyer cancellation before dispatch, any required seller decision, and a completed full refund matching the same order and currency. Reconfirm changed checkout terms through the existing approval flow. A verified Amazon Pay test buyer completed a US$14.30 KitchenSmart demo order. On the separate FYP merchant, the same buyer paid US$1.00 for pocket tissues via Amazon Pay. The full refund reached `succeeded` and the hosted receipt showed US$0.00 net. The earlier standard Visa control refunded US$0.75. eBay rejected activation. The owner confirmed submission of the official registration review. [Current account status](output/qa/2026-11-21-shopping-next-step/verification.md). The buyer-side marketplace cancellation and the installed Alice WooCommerce shopping path have separate acceptance records. [Provider evidence](output/qa/2026-11-20-overseas-shopping-sandboxes/verification.md).

## 2026-11-19 Shopping in ordinary Alice conversation

The owner can name one product and quantity in regular chat. WooCommerce quotes the product, selected Hong Kong delivery rate and HKD total. A changed checkout needs a new owner decision, including for a lower amount. The desk reopens the Woo order, Stripe PaymentIntent and captured test Charge. Native acceptance produced order #17 at HK$46 from an original HK$42 quote. [Product behavior](desk-companion/docs/conversation-shopping.md) · [acceptance](output/qa/2026-11-19-alice-shopping-conversation/verification.md).

## 2026-11-19 Owner-approved flight booking in ordinary Alice chat

Use LetsFG for simulated bookings. The owner sees the exact flight and HKD total before booking and must separately approve a supplier increase. Alice checks the original provider record for a matching PNR and captured amount. The iPhone 17 Pro Simulator completed FR4315 at HK$36.25 after an initial HK$34 quote. [Product behavior](desk-companion/docs/conversation-flight-booking.md) · [device and provider evidence](output/qa/2026-11-19-alice-flight-conversation/verification.md).

## 2026-11-19 Flight booking sandbox

Use LetsFG’s public sandbox for the FYP booking flow with synthetic passenger data. The initial provider acceptance covers a Hong Kong to Tokyo search, matching test reservation and capture, duplicate suppression, and release of a price-increase hold after refusal. Kiwi remains the source for real public fare research. At the provider-only acceptance, ordinary Alice had quote authority. Its subsequent owner-confirmed sandbox booking capability is recorded above. An airline-hosted booking has separate evidence and access requirements. [Provider receipts and Singapore Airlines option](output/qa/2026-11-19-flight-booking-sandbox/verification.md).

## 2026-11-19 Original Pi and regional travel testing

The original Pi now runs the Web and native Simulator release `85e6aa94`. Its device screen showed Alice connected. Original data, A3 v9 and both Google grants passed on-device checks. For ticketing, Duffel’s current signup menu requires a listed incorporation jurisdiction and omits Hong Kong and mainland China. At that point a supplier booking receipt was still pending. [Pi and signup verification](output/qa/2026-11-19-pi-release/verification.md).

## 2026-11-19 Merchant sandbox payment acceptance

Two isolated FYP Stripe Checkout orders using a public test Visa and a simulated Link Checkout buyer were returned as paid by the provider, with independently matched payment intents and captured test charges. A deliberate refusal received zero. These are QA merchant payments. The live product continues to perform reviewed research, with buyer Agent Wallet authorization and independent travel-supplier order evidence still open. [Sandbox acceptance and supported platforms](output/qa/2026-11-19-test-checkouts/verification.md).

## 2026-11-19 Live flight search and cost reporting

Normal Web and native Simulator run `85e6aa94`. Alice can propose Kiwi.com's read-only flight connector for general flight requests. The owner's consent covers the displayed itinerary. The existing official OpenAI session invokes only the fare-search tool without a browser environment. Airline-specific website requests retain their selected source. The cheapest live HKG–HND result in the November 25 nonstop acceptance was HK$2,006 with one checked bag. Its weight and final payable amount remain unconfirmed. The diagnostics screen distinguishes official UTC cost reports from the local Hong Kong spending guard. [Current acceptance](output/qa/2026-11-19-flight-ledger/verification.md).

## 2026-11-19 Shopping and flight quotes in conversation

Alice can prepare a public price lookup, show its quantity or itinerary for approval, and return the price, its basis, source and observation time in the same conversation. The desk calculates eligible selling-unit and multi-buy subtotals. An airline minimum, unverified seat, or missing required baggage, taxes or delivery leaves the corresponding total unconfirmed. A follow-up reopens the saved receipt. Both purchases and ticket issuance remain outside this public research action. The implementation is on [PR 134](https://github.com/tantalum666/FYP/pull/134). The live shopping result, limitations of the two hosted airline runs, and native Safari handoff are recorded in [acceptance](output/qa/2026-11-19-shopping-flight/verification.md).

## 2026-11-18 Normal 6.2 Sol release

The owner selected GPT‑6.2 Sol for normal reasoning and the managed browser. Mac Web and native Simulator now run `00780e44`. Voice audio stays on GPT‑Live 1 with A3 version 9 and delegates to 6.2 Sol. The official browser's independent operator model is bound to admission and execution. The Pi was unavailable during the 18 November rollout. Its retained update was installed on 19 November. FYP API authorization runs through the end of 24 November under US$20 per Hong Kong day. [Delivery, real browser and budget receipt](output/qa/2026-11-18-sol62-deployment/verification.md).

## 2026-11-18 Live text model acceptance

The owner authorized one US$0.25 acceptance, explicitly chose client-side spending controls after the upstream budget field was rejected, and selected GPT‑6.2 Sol for the trial. The live session returned the configured Asia/Hong_Kong timezone, correctly compared Singapore in the same session and was deleted with independent 404 readback. Its 30,476 total tokens include 20,076 cached inputs. The test batch is closed. At the time of this isolated acceptance the installed text model was GPT‑6.1 Sol and the audio model was GPT‑Live 1. The subsequent rollout is recorded above. [Receipt](output/qa/2026-11-18-live-text-clock/verification.md).

## 2026-11-18 Ordinary conversations and paced proactive updates

Ordinary OpenAI text now uses official Sessions and Functions on the source branch. The business layer retains typed tools, owner approvals and effect receipts. A compatible follow-up reuses the same scoped session. Selected documents retain the existing Responses attachment path. Alice groups up to three current findings into one interruption and keeps each acknowledgment separate. [Text contract](desk-companion/docs/official-text-sessions.md) · [Research](research/2026-11-18-always-on-personal-agent.md) · [Verification](output/qa/2026-11-18-official-text-sessions/verification.md).

## 2026-11-18 Current priority: contextual proactive assistance and reviewed integration

Owner requests useful automatic follow-up without configuring a separate schedule or approving every read. Reviewed/fixed PR124–128 are now merged through [PR129](https://github.com/tantalum666/FYP/pull/129) atc51ece41, with all original merged statuses and tested-tree equality independently read back. [Publication receipt](output/qa/2026-11-17-proactive-agent-merge/publication.json). The implemented research path can analyze changes in saved facts, tasks, calendar and bounded connected-account previews when background inference is enabled. It supports citations, relevance filtering, quiet controls and deduplication. A fresh “follow this email” request starts read-only tracking under the existing proactivity preference, including Ask mode. Off pauses both research and mail checks. This supersedes the older requirement that every thread require another seven-day approval card; legacy manually approved grants retain their original expiry. Sending, purchases and general software writes retain their separate policies.

The new path reuses official OpenAI Responses with native strict structured output, without a custom agent loop. Multi-step browser tasks continue through official Agents; deliberate future scheduled reasoning should use official Automations. `AGENTS.md` now requires checking current official capabilities and exact API/SDK types before implementation. The subsequent ordinary-text migration is recorded above. [Proactive contract](desk-companion/docs/proactive-research.md), [research](research/2026-11-18-proactive-assistance-and-official-reuse.md).

Actual API tests exposed and repaired response timeouts and hosted-browser readiness/approval/cancellation/cleanup defects. Six real read-only research cases and a natural-language follow/stop flow passed; mail transport was synthetic. The final official hosted browser read a public catalogue, inspected stock, calculated a fictional shipping/currency comparison and deleted its session, with an independent result check. Earlier failed attempts are retained. [Current QA](output/qa/2026-11-17-proactive-agent-merge/verification.md) distinguishes local tests, real models, actual sites and untested merchant transactions.

On 18 November the owner requested the normal rollout and selected the iPhone Simulator for mobile acceptance. Mac Web, the rebuilt native app and the Raspberry Pi kiosk served `c607759e` in that rollout. Both servers retain their original stores, A3 version 9 and independent Gmail and Calendar grants. The installed background model setting is off. The prior US$5 batch is closed. The Pi retains its 2.4 GHz configured ceiling and enabled RTC timer. [Deployment evidence](output/qa/2026-11-18-three-end-rollout/verification.md).

## 2026-11-17 Replacement-adapter stability check

Owner replaced the adapter/charger and requested stability testing at original performance. Pi reported3000mA capability;8c67ddbe/Alice kiosk/API/application services active andCPU maximum2.4GHz. A planned10-minute observation ended on SSH timeout after485seconds/98samples:18samples showed current undervoltage/throttling, board ADC4.647–4.939V, temperatures47.7–77.9°C, all98local API health checks OK. Kernel events include fresh undervoltage during the observed interval. This power path has **not passed stability**, regardless of unchanged application settings; loss of SSH alone is not proof of a reboot. No deliberate power cycle, performance cap, model call or CI. [Evidence](output/qa/2026-11-17-pi-supply-check/verification.md).

## Historical 2026-11-17: Pi deployment and automatic wake

Owner requests latest Pi deployment and reports automatic restart still failing. Pinned VPS access returned; application8c67ddbe was staged/hashed/activated and read back on Pi, with its original A3version9, Google grants, database/schema and2.4GHz CPU maximum preserved. The next observed boot also served the same release. Three endpoints now have the same application source; current Pi availability remains intermittent.

Fresh readback found the RTC timer disabled, marker absent and hardware alarm empty. Enabled actual persistent renewal and confirmed a moving alarm; after a normal shutdown trial, logs show an alarm-following boot interrupted by undervoltage and a later return. Owner is unsure about manual intervention in the first trial, so that trial alone cannot establish autonomous recovery. The corrected early service/timer pair is installed and actual boot ordering verified: alarm finished at4.680seconds before sysinit6.454seconds. A later coordinated trial exceeded its220-second window, but the owner subsequently observed self-start and a fresh alarm/boot chain supports delayed autonomous recovery. Repeated undervoltage and intermittent access remain; stable recovery is not accepted. [Current QA](output/qa/2026-11-17-pi-mainline-wake/verification.md). No firmware, paid call or CI; no rejected CPU cap reinstated.

## Historical 2026-11-17: official execution mainline

Owner now explicitly requests making the official execution path primary. New conversation drafts and the current browser form/API default to the official managed executor; legacy omitted-engine requests and local continuation keep their original behavior. GPT Live/Responses remains the voice layer. FYP keeps task/account/permission/result binding and the existing job worker, with no parallel generic planner or queue.

Registered official sign-in forms are now rendered inside the same job, with a separate owner account-read choice, original-session/version/privacy/provider fences, no credential persistence or automatic submission retry. Interrupted SSE reopens the same session and reconciles the canonical turn/items; empty202 and lost deletion replies are handled. Account-read consent is not purchase/send/payment authority. QR/passkey/CAPTCHA, cross-job cookie persistence and real merchant acceptance remain separate gaps.

Local full backend **2,428 passed**, frontend **391 passed**, types/build/Ruff and actual desktop/phone synthetic-provider journeys passed. Tests cover default routing, same-job sign-in, missed/duplicate network events, expiry/cancel, no stored credentials and independently verified report hashes. Mac8831/native Simulator now run8c67ddbe, with build/hash/A3/account/data readback. The final scope-receipt correction passed54focused checks after the full pass. Pi was subsequently activated and read back at8c67ddbe in the wake follow-up above; present connectivity is still intermittent. The new paid-trial budget is still unanswered, so no real call occurred. [Current QA](output/qa/2026-11-17-official-mainline/verification.md). A3, user data and existing account grants remain protected. [Execution contract](desk-companion/docs/managed-browser.md).

## 2026-11-17 Preserve performance and recover from powered shutdown

Owner rejects keeping Alice slowed/disabled as the workaround. Normal CPU maximum 2.4 GHz, container and display/autostart settings were restored; temporary recovery limit/hold disabled. Persistent diagnostic logging and private backups remain. Fix the executable-bit defect in the Pi session launcher so restored autostart can actually invoke it. This supersedes the reduced-performance operating plan below, not its historical evidence.

An existing-firmware RTC one-off alarm was followed by an intermediate boot near the alarm time, then undervoltage at 5.9 seconds before networking. This supports wake capability but not complete recovery. Do not call a later manual power-cycle an automatic success. A same-version EEPROM configuration proposal was prepared but withdrawn; no flash is authorized by a stale reply to that superseded question. The later Pi follow-up enabled and verified persistent renewal; full autonomous recovery and early-boot timing remain separate acceptance limits. Preserve performance and explain that software cannot guarantee startup through an actual supply collapse. [Current wake evidence](output/qa/2026-11-17-pi-auto-wake/verification.md).

## Historical 2026-11-16: Pi automatic shutdown

Historical 16 November phase: owner resumed frequent Pi power-off diagnosis on dormitory Ethernet. Fresh access confirmed 13 kernel undervoltage episodes; older logs had been volatile. A private backup and persistent logs were verified. A temporary display/container hold and 1.5 GHz ceiling passed 8 minutes/97 samples without new undervoltage. The owner subsequently rejected retaining this reduced-performance mode; it was removed as recorded above. Original diagnostic evidence remains, but it is not the current operating configuration or proof of a permanent repair. [Recovery evidence](output/qa/2026-11-16-pi-power-recovery/verification.md).

## 2026-11-16 Daily speech, proactive help and continuous local observation

Owner reports spoken slash/dot formatting, stutter, missing HK7-day weather and weak proactive follow-up. New software adds a real HKO forecast tool to text/voice, speech-only title hints, bounded in-speech silence preservation and adaptive playback buffering while retaining A3. Existing task/nudge state now drives one concise Alice-home cue with explicit complete/progress/hour-later responses and saved next-step suggestions. Late daily opening can catch up; privacy/quiet/proactivity rules and owner-reported completion remain explicit.

The browser camera now feeds the existing personal-calibration engine through local CPU inference and a short owner-bound landmark lease. First opt-in/calibration is followed by automatic app/navigation recovery; no repeated chat-camera button. One producer, source/lease fencing, pause/stop, local assets and visible camera status are retained. No video recording or cloud vision. Mobile background execution and real accuracy are not presumed. [Behavior/setup](desk-companion/docs/daily-presence.md), [QA](output/qa/2026-11-16-alice-daily-presence/verification.md).

Actual physical Mac input returned15valid uncalibrated observations and stopped; synthetic local-model lifecycle and desktop/phone task actions passed. The complete backend suite2370passed before the final small Live silence/effort update, which then passed30focused lifecycle checks;389frontend checks/types/build passed. A fresh authorized USD0.20voice round used58.493seconds and estimatedUSD0.11280236 with complete receipts. It verified task/forecast tool reads and A3, but final full speech was truncated by the cap. Delivery hashes are recorded separately; this is not a claim of complete voice quality, posture accuracy or autonomous commerce.

## 2026-11-16 Unified release and official execution layer

Owner requested the complete current software on all three endpoints, renewed Google/Microsoft authorization and further cross-app/shopping/travel work. PR123 merged as7d7ab9fa; the full baseline, including reviewed Grok features, was activated on Mac and Pi with native Simulator frontend parity. Original stores/keys/A3 were retained. Mac Gmail reconnection and Calendar consent passed actual provider read checks. Pi received its own Google consent and both provider reads passed; Microsoft app registration/consent remains blocked at the personal-account human-verification step. [Current QA](output/qa/2026-11-16-agent-runtime/verification.md).

Reuse official execution infrastructure where it fits. Live supports Responses tool delegation; the managed Agents API supplies the browser/agent harness. This branch adds an **opt-in** public-research executor to the existing JobService, with owner admission, exact origins, bounded session lifetime, cancellation, deletion readback and report integrity. It does not add another planner or queue. Old local/browser jobs remain compatible. No voice-to-managed-browser, authenticated account takeover, real payment or ticket acceptance is implied. [Execution contract](desk-companion/docs/managed-browser.md) and [official source review](research/2026-11-16-official-agent-runtime.md).

The one newly authorized paid trial independently verified two public book prices, then deleted its session. Usage was absent: the entire US$1 remains reserved and this round is closed. No further paid request is authorized by the implementation or deployment.

## 2026-11-21 Alice’s everyday face and silhouette

At the size of the ordinary phone home, Alice’s resting face should show a readable nose tip and lip line. Listening and thinking have distinct expressions. Relief, embarrassment at a compliment and an apology use the existing ordinary Session reply to carry their tone. Brow and eyelid timing can differ from the mouth, and audible speech takes priority on the lips. Fit the existing uniform to a modest increase in chest fullness while preserving the everyday body proportions and clearance for returning hands and sleeves. Compare the same home camera before and after, also checking the clothed side profile. [Simulator, film and measured fit](output/qa/2026-11-21-alice-face-fit/verification.md).

## 2026-11-21 Relaxed arms on the ordinary home

At rest, Alice’s upper arms hang near vertical and her elbows remain softly bent. Both wrists settle beside the skirt. The timing of a gesture should be judged from the visible starting pose, the movement and its return. Shape the wide uniform around a lowered elbow and cuff. Fingers have a relaxed cascade, the palm cups on its little-finger side, and the thumb wraps around the outer index finger when gripping. Validate the front and side views on the normal home. [Native comparison and hand close-ups](output/qa/2026-11-21-alice-relaxed-stance/verification.md).

## 2026-11-21 Hand anatomy and everyday voice

Rotation along the arm belongs to the forearm. Gratitude and laughter keep the palm turned toward Alice, with the free arm clear of the working sleeve. Rehearse both sides and interruptions, including the full lift and return. Review the skinned hand, face, coat, sleeves and moving hair. The native before/after film and the per-gesture audit distinguish exposed fingers, skin naturally covered by the cuff, and textile contacts. [Acceptance](output/qa/2026-11-21-alice-hands-live11/verification.md).

The daily voice connection uses GPT-Live-1.1 over the existing server WebSocket. A3 v9 and GPT-6.2 Sol delegation remain selected. The local wake path handles time between conversations. WebRTC standby fits short pauses within an already-open WebRTC call and keeps its microphone track active. [Official standby behavior](https://developers.openai.com/api/docs/guides/live-conversations#managing-idle-sessions).

## 2026-11-21 Expressive reactions in ordinary Alice conversation

Alice’s reply should show a response appropriate to what the person actually said. Good news, disappointment, gratitude, surprise, shared humor, curiosity and encouragement have distinct facial and body performances. Routine replies can stay neutral. Select the delivery alongside the words in the existing ordinary OpenAI Session. Authoritative tool receipts retain their normal path. Preserve quiet intervals, the licensed character, foot contact and the static reduced-motion presentation.

Home also has casual gestures, including tucking hair behind an ear and adjusting a sleeve. The Web and native Simulator release is `88fbc532`. Four real text turns were checked against the rendered reaction and the scoped response receipt. [Film and acceptance](output/qa/2026-11-21-alice-expressive-conversation/verification.md).

## 2026-11-21 Alice movement during conversation

Alice should make eye contact, glance and turn with a short delay between the eyes, head and shoulders. A greeting uses unequal hand sweeps. During speech the hand presents a point, adds a smaller emphasis and settles. A change to listening lets the arm finish moving down. Keep the feet planted and the whole hand visible during the lift and return. Preserve quiet pauses, the current avatar, and the reduced-motion poster. Mac Web and the iPhone 17 Pro Simulator run these movements at frontend `64485c7f`. [Simulator comparison and verification](output/qa/2026-11-21-alice-natural-motion/verification.md).

## 2026-11-16 Motion variety and personal-agent status

Alice now uses short contextual motions with quiet pauses: nod/smile, curious tilt, compact open-hand explanation, glances, shoulder relaxation and pondering, alongside the corrected wave. Tap responses vary and finish cleanly; shared timing prevents a visually finished gesture from swallowing the next tap. Mac web and native Simulator updated with A3/model/size preserved; Pi remained unreachable and received no new rollout. [16 November motion QA](output/qa/2026-11-16-alice-variety/verification.md).

The [personal-agent status map](desk-companion/docs/personal-agent-status.md) distinguishes source, delivered runtime and real acceptance. The earlier motion-only overlay/status audit below is historical: full runtime deployment and Mac Google consent were completed later on16November as recorded above. Continuous mailbox follow-up, real browser owner takeover and merchant payment/ticketing remain incomplete.

## 2026-11-13 Alice presentation motion

Owner asks for a livelier Alice and subsequently rejected the reversed palm and stiff first wave. Both hands now use the corrected normalized wrist roll, slower staggered elbow/wrist motion and light finger relaxation, checked against Alice's actual rig. Preserve dominant mobile size, framing, calendar/composer access, A3 and business/approval boundaries; motion stops with navigation/visibility and respects reduced motion. [Motion contract](desk-companion/docs/avatar.md) / [correction QA](output/qa/2026-11-13-alice-motion-repair/verification.md).

The compatible motion frontend is active on the original Mac web runtime and the rebuilt native iOS Simulator, and its files were atomically activated/read back on Pi. Pi's device page was checked from Mac; its physical kiosk opened, but the relay disconnected before the character finished loading. Pi local motion/performance is therefore **not accepted**. Source publication, native installation, Pi asset activation and Pi physical rendering remain separate states. A3 is preserved; no paid call or CI.

## 2026-11-11 Current integration review

Merged source in PR121 (main44185f7a, all24original PRs confirmed merged) now combines the current Alice/A3/attachments baseline with Grok's conversation Work continuation, local next-step/availability/meeting/waiting/reply answers, memory follow-ups, saved checklists/schedules, purchase preferences, offline trip quotes, cited notes and held choices. [Review evidence](output/qa/2026-11-11-grok-review/verification.md) and [exact PR inventory](output/qa/2026-11-11-grok-review/pr-inventory.json) distinguish local verification and publication from deployment.

The compact Alice home remains primary. Optional forms belong in Work & tools or expandable Memory controls. Attachments keep their provider path even when a follow-up matches a local shortcut. Private goals/facts cannot leak through paired display, hidden context, stale receipts or system notifications. Shopping confirmation/update/approval uses the version the owner actually saw, and a cheaper substitute needs an original total for comparison.

Offline quotes, checklists and purchase receipts are explicitly local rehearsal/records, not live purchases or tickets. The shipped browser has no interactive owner-control transport: a wall pauses the job, but takeover/return controls are unavailable until a capable driver exists. Existing controlled-browser and Gmail self-send evidence is preserved; no fresh paid call, runtime deployment or physical-device claim is made by this review. The dated entries below retain their original scope.


9 November2026 composer update: compact + menu, real chat attachments, consistent dark controls, one file-subview back control and generic cloud-sharing wording are active on Mac and the rebuilt native app. Pi main feature release was independently activated/verified, then its forwarding connection became unavailable; only the last safe-area CSS follow-up remains unconfirmed there. File selection stays local until Send; same-operation recovery preserves drafts. A3 remains selected, all budgets closed, no CI. [Current UI QA](output/qa/2026-11-09-composer-attachments/verification.md) separates live transport/render checks, mocked provider results and device availability.

9 November 2026 current voice update: the owner selected **A3 / Alice · Taiwan Light** as the default on Web, phone and Pi, superseding the earlier original-A selection. Mac and Pi version9settings match A3's exact existing voice ID/original description; both serve the same cached A3 WAV. Phone browser shares Mac; the running native Simulator app connects to Pi8891 and inherits Pi's choice. Original A remains available. No paid generation, source rebuild or service restart was needed. All audition budgets remain closed. [Current activation QA](output/qa/2026-11-09-a3-default/verification.md) / [voice brief](planning/2026-11-09/alice-sweet-taiwan-voice.md).

Earlier9 November technical result: isolated Mac V2ProPlus CPU generated six cases, but that reference is now rejected for Alice's sound. Cantonese numeric accuracy and interruption/latency stability remain open. Classroom Ethernet/VPS/app/OpenAI metadata connectivity passed, with preview recovery through the existing reconnecting launcher. [Trial QA](output/qa/2026-11-09-sovits-classroom/verification.md). The new Outlook plugin identity is confirmed; FYP Microsoft registration/consent are separate and pending.

8 November2026 evening: latest captions wrap on a dark background; the immersive technical footer is removed, and phone agenda space follows the real conversation height without shrinking Alice. Actual voice selection is verified; Alice · Bright and cached trilingual samples are available. The fresh USD1round is closed at conservativeUSD0.346456, all receipts finalized. FYP now has its own browser-authorized Gmail sender; one self-email and independent readback passed. Microsoft365/Teams/SharePoint software is prepared with actual authorization deferred by the owner. [Current QA](output/qa/2026-11-08-caption-mail-voice/verification.md) / [app contract](desk-companion/docs/connected-apps.md).

7 November 2026 later repair: complete27-tool Live startup, explicit built-in Mac microphone selection and full browser wake/query/playback/idle recovery now pass. Old schema conversion lost business title fields; the earlier restricted-query smoke test did not cover that full catalog. Fresh repair ledger closed at conservative USD0.1864995 under USD0.50. Post-input useful playback6.393seconds remains above the approximate5second target. [Repair evidence](output/qa/2026-11-07-alice-wake-repair/verification.md).

7 November 2026 current UI/voice update: Web, phone and Pi share the dark Alice home. Phone retains a large Alice with full month, clock/date and location-aware weather (Hong Kong fallback); prompts never repeat automatically after location failure. GPT Live is the primary voice route, Realtime retained explicitly. A fresh synthetic identity/calendar voice trial passed at conservative USD0.0518613333, budget closed. Local wake and cloud sessions are separate. [Current contract](desk-companion/docs/alice-home.md) / [QA](output/qa/2026-11-07-alice-home-wake/verification.md).

10 November 2026: the same browser job can pause at a login, SMS/OTP, captcha, or payment wall so the owner can take over and hand that job back. Offline fixtures only; no live JD login, payment, or new paid model call. [QA](output/qa/2026-11-10-owner-takeover/verification.md).

7 November 2026 update: real OpenAI browser and text/tool tests now ran on Pi through the owned VPS. Shopping constraints/continuation, flight comparison, browser-result-to-calendar drafting and in-flight cancellation passed on explicitly fictional inputs. Real JD stopped at verification; Cathay did not load. One owner test email was drafted by FYP and delivered/read back through the connected Codex Gmail tool; FYP itself still has no sender connection.31generation requests, USD0.37970163 conservative accounting, fresh USD1 ledger closed. No real order, booking, ticket or human voice acceptance. [Actual results](output/qa/2026-11-07-live-agent-eval/verification.md) / [current handoff](handoff.md).

11月4日历史合并：Grok PR78–82已通过[PR83](https://github.com/tantalum666/FYP/pull/83)合并，代码合并89dc92f与验收树一致：离线邮箱、购物和日程样本接入既有事务/Work/通知/备份；已修复恢复、去重、撤销、过期消息、冲突与回执校验问题。新增建议卡片显示具体对象、来源和确认效果。最终本地验证及GitHub状态见[审查QA](output/qa/2026-11-04-grok-journey-review/verification.md)。真实邮箱、商店、支付、机票和真实日历账户仍未接通。

用户随后明确要求合并74–77。[PR85](https://github.com/tantalum666/FYP/pull/85)已将74–77合入main（b663204，验收树一致）；统一软件包含主对话、Alice、OpenAI/本地唤醒和跨应用Work，并保留刚完成的Grok修复；[本轮QA](output/qa/2026-11-04-merge-74-77/verification.md)记录完整1769后端/319前端及实际页面检查。上述是11月4日历史节点；11月6日已恢复Pi软件并实际部署新版。实验预算仍关闭、无CI。

历史整合基线：2026-10-31。PR5 已按用户明确授权修复并合并（代码合并 `9b655e1`，与已测候选完整树一致）。本轮兼容整合：保留 Alice／Omni／权限及真实应用执行器，接入持久 Work、来源与产物、事务变化跟踪、定期检查和显式保存会话；事实统一保留在 owner_memories。迁移及发布状态见[本轮QA](output/qa/2026-10-31-pr5-repair/verification.md)与[兼容契约](desk-companion/docs/pr5-integration.md)。此前 PR70 已合入 #19／#64–#69，#4／#15／#16 的旧界面由当前主线取代。Grok #20–#59及#60已通过[PR61](https://github.com/tantalum666/FYP/pull/61)合入main（软件合并c2037cd），原41个PR状态均已核对。当前方向为 **Desk Companion个人AI助理**。本分支基于完成归档的main，整合Grok #20–#59和#60的Alice／统一Omni／网页／手机软件，修复权限、上下文、恢复和跨栈兼容问题。分支推送、PR合并、目标设备部署及真实模型验收分别记录；此前跨端权限／事务接续与OpenAI受限真实评测已完成；现已实现受限 Chromium／Calc／Writer 执行，并跑通脚本驱动的复杂任务、改口和重启恢复；语音模型自主完成仍未验收。结果见[交接](handoff.md)、[本轮QA](output/qa/2026-10-30-application-execution/verification.md)与[实际交付门槛](desk-companion/docs/delivery-readiness.md)。合并基线的[整合QA](output/qa/2026-10-28-grok-review-merge/verification.md)保留历史范围。

## 当前要求

三位学生、一台桌面原型；默认英文、支持简体中文。组号统一Group 2，身份与计划分工以[成员资料](planning/2026-09-14/group-2-details.json)为准。**本学期以完成软件和AI为主，硬件尽量完成Luwu机械臂与树莓派集成。**清扫、自动回座、无线充电与光学整机保留研究，不作为本学期软件交付的前置。

- 三端以深色Alice主场景进入，保持自适应、大尺寸虚拟形象和可见的半透明输入区；手机左侧保留完整月历、时间、天气和待办，较矮屏幕允许信息区独立滚动；Mac媒体先本机预览，显式分享后才发画面。界面详情按需展开。手机、电脑及Linux触摸屏共享业务数据；设备常亮页独立构图。手机使用全屏Alice首页与按需Plan／More，保留虚拟形象和简洁操作。
- 个人 Agent 的目标包括邮件跟踪、建议和语音生活事务代办。离线邮箱/购物/日程样本已实现同一事务接续、拥有者核对、静音延后通知和联合备份；它们不能代替真实账号、订单或出票验收。[研究总入口](research/personal-agent-research-index.md)保留真实旅程目标。
- 同一助理贯通文字、语音、短期上下文、经批准的长期记忆、日历和事务。**默认OpenAI：独立文字／托管浏览器和Live委托推理GPT‑6.2 Sol，语音GPTLive1，Realtime2.1保留显式对照；Qwen保留历史已测候选，不作静默回退。**Qwen Audio／Gemini已有协议适配；OpenAI Realtime2.1与GPT-Live1＋Luna已完成一轮虚构业务／合成语音实测，Mini有英文参照。真人同条件比较仍待；不能把协议模拟当成真实效果。
- 真实、受限的电脑／软件操作是核心；先推进Linux。允许范围、批准、取消、超时、未知结果和独立读回由程序控制。默认每次询问；拥有者可在输入框旁／设置中显式启用完整权限，对新请求中的已支持软件操作授予持续授权。模型不能更改权限或自行确认，实体输出仍独立批准。见[权限契约](desk-companion/docs/assistant-permissions.md)。
- 日历等简单查询约5秒提供有用回答是体验目标。工具等待、首音、首个有用词与作业完成分别计时。
- Alice声音先验收音色和自然感，再推进集成：甜、轻软、可爱而自然的台湾国语女声；英语和粤语仍需自然、保持同一角色。原创音色按年轻成年女性设计，不靠变调或夸张奶音代替自然度。已被用户否决的LJSpeech参考样本只保留技术记录。当前按用户最新明确要求将A3作为三端默认，保留原版A便于切回；A1已否决、A2尚不满意，三语与真人声学效果仍分别验收。
- 角色为AliceChan，保留原貌、作者署名与CC BY-SA4.0；不恢复被否决的自行制作脸发路线。旧A1研究与作者源按历史保存。
- 固定相机→个人标定→可见性／持续条件→具体反馈→新观察复测仍是必做主线。遮挡／缺帧为无法判断，不宣称医学诊断、情绪／专注评分或长期健康改善。

## 当前分支实现与边界

| 模块 | 已实现 | 仍须独立验证 |
|---|---|---|
| 应用连接 | Google/Microsoft共享OAuth、Gmail/Outlook邮件核对发送、外部只读查询；Mac Gmail本人测试实际送达；16November Mac/Pi Gmail/Calendar新授权及真实读请求通过 | 微软注册/授权、持续真实邮件跟进、全邮箱增量同步、Office云端编辑和真实商务操作仍待 |
| 日历／事务 | 持久CRUD、重复／例外、冲突、提醒、进展／跟进、版本与操作ID、草稿确认；离线夹具可增量更新同一事务；Mac Google Calendar真实读取通过 | 复杂生产数据、持续外部同步和远程通知另验 |
| AI会话 | GPT Live语音与Responses文字复用业务工具／批准及有限上下文；Realtime保留对照；短期重放、记忆失效、逐轮时限；选中事务经服务端读取并绑定会话 | 新选型同条件比较、真人声学／泛化、成本与长期资源运行 |
| 软件结构 | 手机拆成首页、计划、管理、环境与日历读取；网页／手机／Pi共用自动本地连接、会话恢复及日程编辑；读取去重、迟到响应和未保存保护 | 完整跨设备故障矩阵和辅助技术验收 |
| 网页／手机 | 三端深色Alice首页、可见输入区与按需Plan／More；手机完整月历／时间／天气，保留共享操作卡片／权限和草稿；较矮屏幕信息区独立滚动 | 原生触控／软键盘完整流程、真机、功耗和温度 |
| 记忆／人格 | 网页／手机可搜索、更正、删除有效事实；模型可检索全部有效事实，旧事实删除／到期也清旧重放；按需查看档案／目标／别名／检查记录；受支持的新事实操作可由完整权限授权。2026-11-10 起，拥有者批准后可在指定本地时间提起一条记忆跟进，安静时段和关闭主动提醒会推迟同一条。同日可再批准一次早晨核对，把多条已到期的跟进合成一条并引用仍有效的事实 | 不承诺永久聊天档案或供应商删除旧留存。这些跟进仍是离线行为，不是真实推送或邮箱验收 |
| 持久 Work／跟进 | 选定来源／现有事务、持久决策／提问／恢复、独立文件核验、变化审阅及本地定期检查；普通聊天与显式保存会话的标识分开 | 选定邮件元数据跟进/原线程回复已有本地协议与UI证据；真实持续验收、全邮箱事件、模型自主完成复杂任务和远程通知仍待 |
| 电脑作业 | 原有笔记／指定目录／Mousepad及受限Chromium/Calc/Writer/PDF；新增原生computer调用的公开浏览器、实际输入／截图、显式状态接续和停止恢复，仍用同一队列 | 真实模型已通过受控购物／航班和取消检查；真实商家账户／交互接管、语音自主浏览器任务、任意桌面GUI及远端PC仍待 |
| 坐姿／输出 | 固定关键点与标定逻辑、复测、回放隔离；命名预设、期限、停止与驱动回执 | 真人标注／误报／准确率、Luwu驱动及台架／物理急停 |
| 交换与平台 | ICS、只读分享、事实／人格／作业备份、拥有者合并恢复、私有SQLite副本、诊断和默认关闭Web Push；Google只读、Linux安装、iPhone Keychain／Widget／App Intents | 公网／真实TLS配对、原生通知交付、学校服务器及App Store |

旧运行目录须先停服务并核对备份，再执行显式 schema 1→2→3 迁移；原 PR5 的 personal_memories 另有兼容转换。Pi此前已实际完成schema3迁移；本轮浏览器功能不增加数据库迁移。

实现职责与新增协议见[维护契约](desk-companion/docs/software-maintenance.md)，原业务边界见[架构](desk-companion/docs/architecture.md)。本分支保留main较新的Vite8.3.5，不回退旧工作区的8.3.1。

## 当前证据

11月7日：Pi上的真实OpenAI已操作Chromium完成受控购物改价／数量／折扣／运费与显式状态接续、航班比较及跨日时区检查；同一FYP工具服务生成日历草稿，经测试拥有者确认后独立读回且重复确认不重复创建。真实京东遇验证即停，国泰页面加载失败；原生邮箱仍未连接。测试邮件由Codex Gmail连接器协助送达并读回，与Pi独立发信明确区分。[本轮详细QA](output/qa/2026-11-07-live-agent-eval/verification.md)。

11月6日：合并候选1949后端／328前端；浏览器功能1991全后端、后续33项配置／OpenAI／浏览器检查、330前端及类型／构建通过。真实Chromium操作覆盖购物改价／数量／折扣／运费、航班日期／人数／行李／跨日到达、公开测试网站导航及停止后接续。规划由离线协议脚本驱动，不是实时模型自主通过，真实订单／出票0。[浏览器契约](desk-companion/docs/computer-use.md)与[研究更新](research/2026-11-06-general-browser-and-openai.md)。

11月4日整合证据见[本地验证](output/qa/2026-11-04-grok-journey-review/validation-summary.json)及[兼容检查](output/qa/2026-11-04-grok-journey-review/compatibility.json)。下文数字保留其原日期，不视为本次重跑或真实账号验收。

10月30日应用执行轮全后端524项、前端89项及类型／Vite构建通过，另有真实 Linux Chromium／Calc／Writer／PDF、进程与应用重启、文件 SHA／mtime、同日程 ID 更新和网页／手机浏览器批准／取消证据。核心服务沿用原任务／作业／权限边界；没有新增模型成绩或原生构建结论。10月29日OpenAI的504／15及此前权限489／89保留各自日期与范围。实际网页／手机检查覆盖对话内一次允许、完整权限自动执行、取消／到期、丢失响应后的恢复、未发文字保留、权限撤回与事务结果接续；文件由独立API／SHA读回验证。28–29日版本曾重建、安装、启动到iPhone17Pro／iOS26.5并看到新版权限入口；本轮应用执行代码没有重新做原生构建。镜像点击仍未可靠触发页面转换，因此原生触控／软键盘不算通过。之前459／89记忆和450／89整合结果保留原日期与范围。

既有2026-10-23–24真实Qwen／合成输入结果保留其原日期：40条有效实际开声计时p50=3.0741s、p95=3.8889s；不是本轮重测，也不是真人有用词或Pi成绩。10月29日OpenAI评测包含16次真实短会话，其中11次为最终控制条件下的检查；不能与旧Qwen实际播音计时直接混合排名。用户新授权节省使用OpenAI额度，本轮采用5美元小上限，返回usage保守估算0.3035168833美元，账单未核；测试已结束，预算账本已关闭。旧Qwen预算仍关闭；11月6日的明确OpenAI配置已取代当时的none预览，配置就绪不等于付费推理验收。

## 身份、数据与硬件

默认不开摄像头／麦克风，不持久保存原始音视频；外部密钥只留后端。模型不能更改拥有者权限、任选路径或启动任意电脑动作；已授权的软件动作由独立PermissionService核验并调用原有业务服务。回执丢失先核验，不重放未知写入。配对身份不等于拥有者管理权。

应用默认以`DESK_AUTO_OWNER=1`自动连接可信的本机工作区，移除所有应用端密码表单和Sign out入口；仅直接回环、无转发、可信本地来源可取得普通8小时Cookie。公网与配对设备仍保留原权限边界，真实远程手机使用可信HTTPS／配对。会话恢复不自动重试业务写入。旧口令API只保留兼容／恢复用途。[连接契约](desk-companion/docs/passwordless-device.md)。

硬件组的[11 月 17 日采购评审、外壳 V3 和 ArUco 打印资料](research/2026-11-17-hardware-progress/README.md)记录硬件研究的最新进度。商品预算 HK$1,944.43，待核运费。V3 保持 320 × 200 × 200 mm，由六块面板和一件可拆 Qi 发射支架组成。H2D 打印包另含五块 ArUco 薄片，学校配置切片、部件尺寸、实际装配和回充待核。[10 月 26 日原审核稿](research/2026-10-26-hardware-procurement-review/README.md)保留历史。

**Pi软件已恢复推进；只暂停自动红灯调查。**宿舍网线通过443管理中转恢复访问，main abf6387/schema3已经部署；新免登录／Alice／应用运行环境已经部署，四项真实应用作业与恢复通过。教室与大陆网络保留配置，但不能将宿舍本轮结果当作在其他地点重测。用户澄清红灯先出现、之后才拔插电源，旧“正常按键重启”表述无效；保留已核对的开机后软件／主机身份结果。Luwu与Mini硬件研究、采购批准、接线、台架及连续运行分开；[硬件成员资料](research/2026-10-23-mini-robot-hardware/README.md)不代表本轮实物成绩。

## 保存与协作

退役Senplate维持[统一归档](archive/senplate/README.md)，学校原件与既有报告不改、不代签或提交。旧软件工作区及私有备份继续保留；本分支只发布可复现软件、分发素材、规范与本轮选定QA，不上传凭据、运行数据库或个人限定作者原件。

开工按最新[AGENTS](AGENTS.md)精简阅读，验证只在本地完成，不使用GitHub CI，也不把Actions／账户额度列为待办；重要进度在检查后推送独立分支／PR。当前唯一下一步以[handoff](handoff.md)为准。

## 2026-10-28 整合规则

临时聊天与引用指向使用登录／事务隔离的有界RAM；业务回执独立持久保存，重新登录只能显式恢复已知同一拥有者操作，不能重放旧聊天。只读工具重新查询当前数据；删除不因重试复活事实。备份最终应用和目标草稿决定都要求拥有者，恢复作业不携带批准或运行令牌，导入路径重新校验。

网页／手机共享身份切换边界，权限降低清掉私人聊天与诊断；同身份预览续期保留输入。流式EOF不代表完成，必须保留原操作编号供明确恢复。学校Progress Report I及其他原件没有因本次代码整合而修改或提交。

## 2026-10-29 OpenAI实时语音评测

独立[评测工具](desk-companion/docs/openai-voice-evaluation.md)复用现有工具／业务服务，测试Realtime2.1与GPT-Live1＋Luna的英／普／粤日历、待确认记忆和合成插话；Mini只测英文参照。初次语言跟随失败、Live收尾过早及含糊记忆回应用例保留，不只发布成功样本。模型输出录音可试听；收包首音包含铺垫语，不是首有用词或真人／Pi成绩。用户批准的本机密钥仅留Git忽略配置；没有开启常驻OpenAI服务。

## 2026-10-30 更复杂的真实应用验收

用户认为“编辑器写笔记→浏览器预览”过于简单。它降为冒烟检查；主验收改为[跨应用演示准备包](planning/2026-10-30/complex-application-acceptance.md)：核对资料、网页报价、真实电子表格公式、文档／PDF、日历／事务，以及中途预算／数量／日期改口和断线恢复。固定材料与参考核验已经完成；本轮新增[真实应用执行与恢复](output/qa/2026-10-30-application-execution/verification.md)：初始 Aster 809.60 港币、改口后彩印不可行、脚本澄清黑白后 Delta 669.24 港币，五份实际产物及原日程更新通过。此为受控脚本验收，非语音 Agent 自主任务通过。

新增独立类型的 application 动作和持久阶段投影，保留原六种笔记动作；[运行契约](desk-companion/docs/application-execution.md)说明单队列、依赖／来源哈希、暂存发布和未知写入只读恢复。内容正确、真实应用执行、语音 Agent 独立完成三项分别验收。下一步是复用这些工具的模型任务接续与离线变体；普通聊天接续和真人同任务语音比较仍待；OpenAI App接入在独立PR77继续。旧付费轮与 Pi 继续关闭／暂停，本轮模型调用为零。
