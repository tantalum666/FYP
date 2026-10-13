# Mounted feature acceptance on ba8cf2a9

Source: `ba8cf2a9516525b9778ab00214cf3bebc6a0ac60`; tree: `e04b2b5409c287ad55cc734ab328ce9623bc68b9`. Exact checkout: `fyp-narrow-ba8c`. This report covers the later staged metadata search, selected-task watches, capacity and terminal-history work. Earlier layout/build evidence remains in `qa/2026-10-13-ba8cf2a9`; earlier kernel acceptance remains in `qa/2026-10-13-4e508411`. Those results are not rerun or promoted to new-source feature claims here.

No production source/Git edit, push, merge, deployment, model change, paid provider call, credential/security setting change, microphone, hardware, public website request, or sandbox weakening occurred. No narrow source fix is requested. The original user worktree and localhost:8832 data were not opened or changed. Existing 5190/8843 services and previous QA/runtimes were preserved.

## Execution and evidence boundary

Fresh schema3 synthetic runtime: `runtime/features-ba8cf2a9/app`. Startup received a new scoped approval for an isolated loopback listener on `127.0.0.1:5191`, PID10431, session74297, maximum3600 seconds, starting `2026-10-13T15:12:11.276600+00:00`. The prior layout listener was already stopped and its database was not reused. Production built assets were reused; no new download/build or broad unit suite was performed.

The QA launcher uses `scheduler=False`, disables providers/capture/browser/computer/replay/connectors and migrations, and permits only local task/watch mutations, session creation and metadata search. A test-owned one-second loop invokes the production offline task-change comparator. Fixture seed: three fictional tasks, two sources, four67-byte explicitly labelled QA report files,24 cancelled work records, and one cancelled terminal watch with one seed review. Seeded work/file/history is test data, not agent execution evidence. Mutations described below were performed through the actual mounted browser UI.

The launcher injects exactly one search503, one capacity503 and one committed-watch-save503. `fixture-controls-used.jsonl` identifies these controls. Watch save used a bounded two-second delay. Search clear used a four-second delay, but the response was not captured; no successful late-response fence claim is made.

Every numbered capture has a PNG and AX text. Screenshots are actual browser captures, not SSR/script-generated acceptance. Visual review completed for14(search Chinese narrow),28b(watch list/budget),43(recovered watch),50(restored terminal history),53(capacity Chinese) and54(capacity unavailable), in addition to native date-entry diagnostic images21b/21c. Other screenshots are retained supporting captures, not individually claimed as visually reviewed. Main desktop viewport1280×800; narrow Chinese search390×844. The previous separate layout report covers its fuller EN/ZH desktop/narrow card matrix; this phase does not claim that entire new-feature matrix.

## Metadata search — observed pass

- Empty-query browse yielded30 records, first20 then next10; previous-page navigation worked. Typing/filter changes alone did not submit and the displayed last-submitted result summary remained accurate.
- Explicit English Work query `Fictional quarterly review` returned two exact distinct IDs: `811a7d6a43c14de2a7a9464d481f5f09` and `468082b1864348d4b8633def01f40695`. Repeated Search clicks kept two results. Opening the first showed the correct cancelled run and associated files, without resuming work.
- Returning from work detail to Search resets query/type and waits for an explicit submission. This is recorded navigation behavior, not a confirmed defect. File-detail close preserved its search query/filter/results.
- File query returned the current, earlier and unlinked reports with truthful relationship labels. Exact earlier artifact `1664bcffc7a842c382bb1716b0b9dc7d` was inspected; Preview text displayed the67-byte synthetic report. No download was initiated.
- Body-only marker `BODY_ONLY_SENTINEL_246` returned zero metadata hits. Exact source-filename search returned the intended source; its actual preview contained the body marker. Thus metadata matching and content preview were distinct.
- A one-shot503 search read showed a recoverable generic error while retaining terms/type. Explicit Search recovered the same result.
- Chinese narrow query `虚构季度回顾` with Work filter returned exact run `4b60c54ed3fd46a78026dd57168b47b1`; Chinese Files returned artifact `b3fd5448a5be4ca3b0890fc3e94dcd46`. Unrelated query returned an honest zero-result state. Document width390 matched viewport390. Query text was not put into the URL.

Evidence:01–19, especially03,06–16.19's trace contains an empty responses array. Captures18/19 show cleared search remaining empty, but do not prove receipt/rejection of a late response. Treat the stronger scenario as unverified.

## Selected-task watch lifecycle — observed pass

Primary watch: `8a5be8d47ef24a068252829fd1ecc646`, title `Fictional project progress — lab and update`. Explicit tasks were Lab `bace19f512db4bcf98efed915671e807` and Project `e430d26ca6c547b1ad8fc8e3cf2dae74`; fields were only status and progress. Expiry was2026-10-20T16:00UTC, lifetime budget5/daily3, with explicit retention checked after final edits. Creation produced no initial review,0/5 and zero pending.

- Actual task editor changed the Lab next step, an unwatched field; the watch stayed quiet. An actual progress-note save produced review `42f124acdcdb456493090e9fa729f615`v1. Actual Mark complete confirmation then changed status and coalesced into the same reviewv2, status+progress, with only one lifetime budget unit and one pending review.
- Compile current task evidence opened an explicit Work composer for exactly those two task IDs. Scope selection was locked, review/run unavailable, retention off. Closing and discarding did not start a run or acknowledge the review. Reopening still showed one pending review.
- Repeated Acknowledge clicks yielded one acknowledged reviewv3, zero pending, and no new budget consumption.
- Pause was confirmed. Reopening the Lab task while paused did not alert. Resume from now was confirmed and reset the baseline to current values, retained the spent1/5 budget, and produced no backlog alert.
- Actual reopen of unselected task `a103fdc7b2304562b50d59b84260d7b6` produced no watch review.
- Cancel preview followed by Keep unchanged retained Active state. A subsequent confirmed cancellation produced Cancelledv4, retained history and kept the saved slot charged. Chinese terminal-state/budget labels matched.

Evidence22–39. Important capture naming limits:21/21b/21c had incomplete/blank native date input;21d was diagnostic.27 was only the task-completion confirmation preview; actual save is27b.28 shows progress-onlyv1;28b AX has the coalesced status+progressv2.

## Committed-save reply recovery — observed pass, limited wire proof

Recovery watch `a3cfacdda4ff42419689e5d883ad547c`, title `虚构回执恢复关注`, selected only the Project task and status. Double-clicked enrollment during a two-second fixture delay created one definition. The fixture then returned503 after the actual commit. UI showed the unique Active watch, locked the draft/actions and offered only Retry same request; slots were3, pending0.

Clicked that original retry control. The normal UI recovered with one matching watch and unchanged slots3. It was subsequently cancelled through the normal confirmation control. There is no unknown pending write or instruction to retry it now.

Evidence40–44 and `fixture-controls-used.jsonl` at15:53:09. The raw original operation ID was not captured:42/43 response trace arrays are empty. The observed same-request recovery and no duplicate count are supported; exact wire-key equality is not claimed.42's screenshot was still pending retry; normal completion is43. A direct read-only sqlite query failed with unable-to-open-database; no escalation, alternative access route or immutable bypass was attempted. Use the approved launcher's closeout inventory as backend support.

## Terminal-history maintenance — reversible portion observed pass

Main watch exactID `8a5be8d47ef24a068252829fd1ecc646` was Cancelledv4 with spent1/5 and acknowledged history. Trash preview displayed1 definition/2 baselines/1 review and zero slots released. Cancelling that preview kept it unchanged. A fresh confirmed Move to Trash placed exactly that history in Trash; all three slots remained charged.

Restore preview displayed the same ID/history. Confirmed restoration returned it to terminal history, still Cancelled, same spent budget, no new alert or Work, Trash0, slots3/lifetime identities3. The two other terminal watches remained listed.

Permanent-removal preview showed the exact same watch, evaluationv4/retentionv3,1 definition/2 baselines/1 acknowledged review, one possible saved-slot release and opaque retry receipts retained. It was cancelled. An action-time confirmation question was presented for this exact item; no affirmative response was received before closing the browser. No purge was submitted. The normal product cannot restore a purge, so browser confirmation policy requires a fresh explicit action-time answer even for this fictional fixture. This gate is not an auto-review denial.

Evidence45–52. Permanent purge/slot reclamation, stale/expired maintenance preview failure, repeated maintenance submission and interrupted-maintenance recovery remain unverified. Reversible Trash/Restore preserved the review and did not restart the watch. No approved action is pending in the browser.

## Capacity — observed pass for reads/recovery

Chinese and English displayed Sources2/100 with125 reserved bytes, Work24/100, Outputs4/400 with268 reserved bytes, Watches3/20. Source bytes equal76+49; artifact bytes equal4×67. Cancel and Trash had kept all three watch slots charged.

One injected capacity503 explicitly replaced numeric usage with unavailable/unknown wording, never zero. The existing exact Chinese cancelled work record remained clickable and opened its detail with its saved67-byte artifact. Explicit Refresh capacity recovered the same counts/bytes. English restoration displayed identical figures and advisory wording about reservations rather than disk space. No file download, Work execution or stop mutation was needed.

Evidence53–56,58. This proves optional capacity-read failure does not prevent existing inspection. Active-work stop under capacity failure and actual full-capacity admission rejection were not tested. Expanded capacity at narrow width and its full EN/ZH interrupt/repeated matrix were not tested in this phase.

## Safe offline availability and closeout

Assistant displayed Voice service not configured with Start conversation disabled in Chinese and English. No microphone, transcription, model or voice-to-Work action was attempted. Work's saved public-capture panel displayed new captures disabled/unavailable and existing-history inspection available. No public capture, website contact, source verification or capture-to-Work action was attempted. Evidence57/59 supports availability limits only, not voice/public acquisition or general cross-app capability.

Language restored to English. Temporary device metrics cleared. Only acceptance tab9 closed. The service stopped automatically at `2026-10-13T16:12:11.518534+00:00`; session74297 returned exit0 and5191 had no listener at16:12:19. No extension was requested. `fixture-closeout.json` confirms schema3,3 tasks,6 private files,24 cancelled Work records,3 cancelled retained watches and2 reviews. Model/tool calls, text AI usage, agent steps, connector intents, computer jobs and public captures are all0. The main restored watch is Cancelledv4/retentionv3; the recovery watch is Cancelledv2/retentionv1. Thus no active watch or Work execution remains in this fixture.

Exact HEAD/tree were rechecked and production checkout `git status --short` was empty. Previous ba8 report/manifest and4e report bytes/hashes still match their accepted identities. Evidence59 is an offline disabled capture surface, not a website acquisition. This offline FYP UI acceptance is distinct from manual testing of the separate demo app and actual general cross-app agent execution.

Unverified remaining items: permanent purge pending explicit action-time approval; stronger late-search-response fence; exact retry wire-key equality; maintenance error/interruption matrix; full narrow/device matrix for these new feature panels; capacity saturation/active-stop case; actual voice-to-Work and public capture. Previously blocked native CSV Save, production MCP nonpublic-DNS access, real provider and paired-identity gates were not retried. No production defect was confirmed by this phase.
