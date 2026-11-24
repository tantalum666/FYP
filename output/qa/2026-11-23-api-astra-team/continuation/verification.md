# Independent Work and Routines acceptance

| Component | Reviewed revision | Outcome |
| --- | --- | --- |
| Routines | API contributor `a2ee3822bf9a1d409095dafb466240c107b9ae03` | One selected occurrence skipped. Next weekly occurrence delivered on time. |
| Work | API contributor `361f36bbb64f7af4767ad288ce7fb933237507ce` plus integrating developer's repair `fcd1fb1a0df4e74bdc34628c93f9624877610f78` | Uploaded-source continuation recovered after restart and duplicate delivery. The neighboring approval kept its original identity. |

The reviewer used immutable Git exports, ordinary FastAPI/SSE and Chrome composer entry points, synthetic private SQLite stores, a fixed service clock and independent receipt reads. Baseline `e06c5149204fbb9d0125aefc626b5fd1395de5ac` created the original runs, schedules, history and grants. Isolated service tests recorded zero outbound connections. Native devices, OS notifications and paid provider behavior were outside this exercise.

## Routines

On the baseline, the request returned a calendar summary and both weekly routines ran. On the contributed branch, entering “明天这一次不用提醒我，之后照常” in the ordinary composer showed **Fern inventory** and **Bench inventory**, both scheduled for Sunday at 01:45 in Australia/Lord_Howe. The owner selected Fern and confirmed. A fresh read showed exactly April 4, 2027 in its skipped dates. Bench retained the original version and schedule.

| Independent check | Observation |
| --- | --- |
| Approval and privacy | Confirmation without a selection, or with an unlisted ID, returned 422. Paired-device confirmation and replay under Hide private returned 403. Repeating the accepted choice returned the same receipt. Substituting Bench afterward returned 409. |
| Repeated clock hour | On April 4 Fern produced no run or delivery at either copy of 01:45. Bench ran once at 14:45 UTC on April 3. The following week, Fern and Bench both ran at 01:45 on April 11, exactly 15:15 UTC on April 10. Early ticks, a backward clock adjustment and duplicate ticks produced no additional run. |
| Downtime | Starting late on the skipped date kept Fern quiet. Starting after the next weekly occurrence evaluated that latest eligible instant once. The previous March history remained readable. |
| Browser | At 1280 × 860, confirmation was disabled until selection, the result appeared in chat, and the independent routine read agreed. At 390 × 844 the selector and confirmation fit without horizontal page overflow. The closed mobile selector clipped the end of the long date/zone label. Chrome reported no application error. |

## Work

The first Work commit failed on a valid uploaded CSV. One versioned choice from the ordinary chat returned `REQUEST_FAILED` (500), leaving four existing checkpoints. In `agent_runs.py` lines 951 and 981–983 at `361f36bb`, the new claim held a SQLite write transaction while source authorization called `sources.metadata`. Source verification opened a second write transaction in `file_store._status` and SQLite reported `database is locked`. The same two-run journey passed when only task data was selected.

The integrating developer moved full file verification outside the claim transaction and retained an atomic publication check. On a copy of the **actual store from the failed attempt**, the repaired backend accepted the **original operation key** and added one outcome checkpoint to the same run.

| Independent check | Observation |
| --- | --- |
| Interrupted owner journey | A fresh composer found both legacy runs. Its versioned choice remained usable after another process restart. Simultaneous copies of the selected request returned the same step ID. The upload-backed run reached succeeded. The other run kept its original pending proposal. Chrome also completed this path and independently read back that checkpoint with no app errors. |
| Decline and shutdown | An explicit decline reconciled the existing effect to rejected and its run to partial. Graceful shutdown separately canceled its outstanding draft and paused its parent as designed. The repaired continuation reconciled that cancellation. No new task, run, proposal, computer job or model-usage row appeared. |
| Authorization and integrity | Another login could not open the original chat (404). A paired device received 403. The wrong task scope moved neither run. A revised goal required a fresh acknowledgment. Forgetting its linked chat prevented rediscovery. A one-byte CSV alteration returned `409 RUN_SOURCE_UNAVAILABLE` without advancing work. |

A pre-feature conversation whose RAM buffer disappeared before a durable association was recorded still returns 404 for its old chat ID. The same retained run is recoverable from a fresh composer under the original login. Conversations linked on the new build reopened under their original IDs.

**Scope read.** Repository entry and handoff, product sections on conversation, proactivity and identity, continuation decisions, global review handbook, and relevant Work conversation, agent-run and Routines contracts. Inspected ordinary chat and approval entry points, both affected services, receipt handling, rendered controls and applicable existing tests.

## 23 November supplement · approval status and quiet catch-up

**Approval status, `ee4c01591ac12603cec7546075937a6b0a8f027b` (tree `4e07a466`).** The ordinary composer listed a HK$23.45 shop quote, a flight revised from HK$73.64 to HK$82.46, and the original Work draft. The query and its replay left business records unchanged. An expired quote and purchases in another chat and another login stayed out of that answer. For “Yes.” an inferred sibling-chat quote prompted clarification. Explicit selection of that foreign quote returned 404. No merchant operation occurred.

The follow-up **“Yes, confirm it.”** exposed a defect in this snapshot. Under Ask first, it created a task-note draft. Under Full access it saved the unintended note, changing the task from version 1 to 2. The controls “Yes.” and “Confirm.” requested a specific choice and produced zero writes. The affected assent matcher is in `approval_status.py` lines 22–53. The API Work continuation and Routines skip results above were assessed independently.

**Quiet catch-up, `06d5aa05645d5011940f9247ee425347d0d12f24` (tree `4e64b0c5`).** Four locally verified refund changes arrived at 22:19 Hong Kong time on a synthetic desk with quiet hours from 22:00 to 23:00. The home remained quiet. Two chats in the original login and a chat in a different login could see exactly their own one, two and one changes. Repeated questions left all four inbox items open. Stored notices contained only a refund outcome code.

After restarting the service, the owner explicitly marked the one displayed change as read. Replaying that operation reproduced its original count. A new acknowledgment of the same page reported zero and the three unrelated items remained open. Wrong-login and wrong-chat acknowledgments returned 404, hidden-private returned 403, and replay after forgetting the chat returned 404. The queries and acknowledgments added no merchant call, payment, job or model usage.

**Narrow-screen routine selection, 23 November.** At `bafa10a7a33c0cd716c609a7f669ffe4cb88e57d`, the 390 × 844 Chrome composer displayed each selected schedule in two complete lines below its closed selector. Switching choices replaced “2027-04-04 06:40 · America/North_Dakota/New_Salem” with “2027-04-04 20:25 · America/Argentina/ComodRivadavia”. All text fit the 266-pixel detail area and the page stayed 390 pixels wide. Returning to “Choose a routine” removed the detail and disabled confirmation. Selection changes issued zero mutation requests. Independent reads found all four routine definitions, histories, skipped dates and the pending review unchanged. [Cropped selection control](routine-selection-390.png).

## Repaired owner assent and basket compatibility

The API contributor repaired the ambiguous assent at `4f320ab2`. The same normal HTTP/SSE case previously returned an unintended task write in Full access. On the corrected Work branch and again on its integration after the combined checkout merge, Ask and Full each displayed the three pending decisions and asked for a specific target. The task stayed at version 1, new proposals were zero and provider calls were zero. A full mixed Woo basket in the overview displayed “2 种商品” with its HK$33 total. A same-total commercial reprice now asks for review of changed terms and prints the amount once. [Independent result](approved-target-fix.json).
