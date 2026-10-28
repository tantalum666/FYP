# Group 2 · Grok and current software integration

28 October 2026, Asia/Hong_Kong. The owner authorized review, repair and merge of Grok PRs **#20–#59**, then explicitly included **#60**, preserving the current Alice, mobile and unified Omni baseline. This record concerns software integration; school reports, Pi deployment, live models and hardware remain separate.

## Source and publication

- Base: `46ac1679f57191b8ed4ff51ff15829cb81c83cc4`.
- #60 baseline: `8e7fe6b05aa92c207002e7e82fb455d8bca605d9`.
- Combined pre-fix review candidate: `188f7b504ca4ab9107c1754d499f3991655999f6`.
- Current fix checkout: `/Users/tantalum/.codex/worktrees/grok-reviewed-fixes/FYP`, branch `codex/grok-integration-20261028`.
- [Captured PR inventory](pr-inventory.json), [merge events](merge-events.json), [dependency tips](integration-order.json), [head verification](head-verification.json). All 41 captured heads are included by ancestry and were unchanged at prepublication readback; main was still46ac167.
- Final branch/PR/merge receipts will be recorded in [publication.json](publication.json). At preparation of this record, publication and merge are pending. A local merge commit or successful push alone is not a main merge.

The original Grok guide is preserved as historical evidence in `docs/merge-guide.md` and [the captured source](merge-guide-source.md). Its rehearsal excluded the newer Omni/mobile baseline and reported three failures; it was not a passed combined release.

## Reviewed and repaired behavior

| Area | Defect or integration conflict | Resulting contract / evidence |
| --- | --- | --- |
| Current baseline | Old-base branches overlapped modern App, AssistantPanel, Linux executor and phone/session work | Preserved #60 layouts, Alice, shared session/editor services and all three executor families; no return to old monolithic App/login or phone tab bar |
| Tool validation | Schema serialization filled omitted nested calendar fields | `exclude_unset` preserves unmentioned notes, location, reminders and visibility through the real policy path; tested after confirmation |
| Memory and context | Global SQL transcripts bypassed login/task RAM scopes and survived forgetting | Existing Conversations owns RAM continuity; HTTP and non-Omni owner views reuse it. No global transcript producer. Login/task changes and memory revisions are tested |
| Read tools | Persistent cached query results could replay forgotten facts | Read results are fresh, with per-call timeout state only. Effects retain durable idempotence; forgetting cleans/tombstones matching historical copies without deleting execution keys |
| Recovery | Stream EOF cleared the unknown operation; generic recovery parsed SSE as JSON | Only a terminal receipt acknowledges completion. Same-key SSE recovery clears matching input/error and preserves unconfirmed drafts. Reauthentication can recover a known same-owner receipt without replaying old chat |
| Owner boundaries | Backup apply and goal-tagged generic drafts did not recheck owner authority | Paired list/decision/apply denial, owner success and cached-receipt denial tested through actual HTTP routes |
| Imported jobs | Incomplete requests broke listing; folder fingerprints could rebind approved work; Linux actions were rejected | Complete stored-intent/schema/digest checks, normal real-path checks and recomputed fingerprint. Nonterminal imports remain unapproved review jobs; all executor families can round-trip |
| Principal transition | Successful owner-cookie expiry fallback retained private chat/diagnostics | Shared workspace subtree remounts on changed principal kind/id, clears obsolete pending data and fences late responses. Same-principal preview renewal preserves unsent input |
| Cross-stack rules | Local fact drafts lacked audit/stream events; dedup invalidated a ranking fixture | Fact draft path records the real tool; ranking fixture now has distinct equally relevant facts. No ranking assertion weakened |
| Provider behavior | Fake adapter lacked streaming; fallback reused one usage row for two requests | Offline fake stream works; every actual network attempt reserves its own call slot and cannot exceed the cap |
| Other continuity | Recall focus was global; hidden goals broke summaries; fallback announcement ignored proactivity | Recall focus is conversation-local RAM; hidden goals are omitted safely; both announcement paths use the same saved proactivity rule |
| UI | Alias edits lacked a guard, profile could remain stale, recovery left old errors, duplicate-confirm label was misleading | Guarded alias form, refreshed profile, truthful recovery copy and explicit confirmation. Advanced memory sections are disclosed on demand |

The removed `test_agent_loop_handoff.py` only asserted exact prose/order and names from the superseded unimplemented second-model design. It was retired rather than keeping nonexistent APIs in current handoff prose. Functional suites remain; the new cross-login “forget that” test verifies the actual replacement behavior.

## Verification

| Check | Observed result |
| --- | --- |
| Initial combined candidate | 15 backend failures /422 passes;87 frontend passes; macOS build caught case-sensitive helper/component naming collision |
| Fixed backend |450 passed; one existing Starlette/httpx test-client deprecation |
| Fixed frontend |89 passed; TypeScript and production Vite build pass |
| Lint / whitespace |Ruff and Git whitespace checks pass at source checkpoint; publication check repeated before commit; staged scan0 findings and54-commit range scan0 findings |
| Dependency install |Locked uv environment, `npm ci --ignore-scripts`; npm reported0 vulnerabilities |
| Offline scenarios |Aggregate script and its registered suites are covered by the normal tests; no live evaluation flag enabled |
| Desktop UI |1365×900; meaningful page content, no framework overlay, Alice sidebar and shared assistant preserved |
| Mobile UI |390×844; full-screen Alice, Plan/More, New→Save→Plan and web readback, More→Memory, alias Continue-editing guard |
| Auth fault |Actual expired-cookie fallback proved on frozen backend; controlled workspace/session/diagnostic responses proved fixed UI clears private chat and cached diagnostic metadata |
| Stream fault |Server completed one draft; test removed final SSE receipt. Original operation ID retained, explicit recovery cleared it, one draft existed and active memory count remained0 |
| Preview renewal |Expired only the isolated fixture runtime's sessions. Unsent input survived and the next message succeeded |

Published text logs normalize trailing console whitespace; the original local output is preserved under `.runtime/review-local-history`. Logs: [backend](backend-final.txt), [frontend](frontend-final-test.txt), [build](frontend-final-build.txt), [focused recovery](recovery-focused.txt). Browser results: [structured record](browser-verification.json), [desktop](web-final.png), [phone home](phone-home.png), [phone memory](phone-memory.png). Expected401/403 or connection-failure entries came from controlled expiry/interception/server restart; the phone console had no errors/warnings. The older large-bundle advisory remains; it is not treated as a failed build or measured performance result.

The browser test runtime is `.runtime/grok-review-preview`, on web5191/API8832, with explicit loopback preview, `text=fake`, `voice=none`, background/extraction/push/executors off. Only fictional QA data was created. Test interceptors were removed. The normal5190 preview and private databases in older worktrees were not migrated or overwritten.

## Independent review evidence

Codex Security scan `ee5973d1-4844-4694-bb21-824456410b0c` is completed and sealed for the immutable **pre-fix**188f7b5 range. Preflight was ready; a fresh architecture pass and disjoint source-review assignments accounted for196 authoritative source items. New files were read fully; existing files were reviewed through changed hunks and necessary controls/callers. This is not a claim of reading every archived repository file.

Eleven candidates received explicit dispositions: ten low-severity findings across the scopes above, and one owner-only/default-off push-destination candidate rejected because no lower-privilege input path was established under the actual single-owner/operator model. The report does not claim unauthenticated compromise, arbitrary filename overwrites, automatic restored-job execution, or real hardware impact.

Frozen proofs used temporary databases and scripted services. They reproduced cross-login transcript mixing, forgotten read-cache output, paired backup/goal decisions, malformed imported-job failure, and restored directory binding. The directory proof inspected the actual bound destination without executing a filesystem job. The original UI path was traced statically and its backend identity transition exercised; the fixed UI was checked with controlled browser responses. All corresponding fixes are independently tracked by the tests/browser evidence above rather than rewriting the sealed snapshot.

Local sealed report (not copied into Git): `/Users/tantalum/.codex/state/plugins/codex-security/scans/FYP/188f7b504ca4ab9107c1754d499f3991655999f6_20261028T024147Z_btycz227/report.md`.

Tool-reported cumulative accounting: total79,093,702 tokens; input78,886,920; cached input76,860,544; coverage complete across10 recorded threads. This is the workbench's reported cumulative/cached accounting, not a new project-model API charge or a cost estimate.

## Data, assets and documents

No credentials, databases, private backups, installed dependencies or private authoring originals belong in the commit. The first staged scan flagged a fictional recovery operation UUID under a generic `key` field; the evidence field is now named `operation_id`, with no secret-scanner allowlist added. A final commit scan also recognized twelve source-file hashes under credential-like filenames as generic keys; the manifest now uses explicit `path`/`sha256` records, each digest independently recomputed. Runtime assets are inherited from #60, including Alice attribution/licences; no new character or school-report binary was authored. Preserve #4/#5/#15/#16 and hardware#19 separately.

Updated contracts: root entry/product/handoff/decision/work log and contribution status; software maintenance; agent loop and its handoff; SSE; memory; modules; architecture; computer jobs; Omni; operator guide. The old merge rehearsal and software report chapter are explicitly historical. [Reading record](reading-record.json) and [publication checks](checks.json) states actual files/ranges rather than claiming a full Markdown library read.

## Remaining limits

No new live model quality/latency/acoustics, paid budget, external push delivery, native Simulator installation/touch/keyboard, real phone, Pi/Wayland, Luwu or physical safety acceptance occurred. Earlier #60 native visual proof remains dated evidence. Tool-schema-inclusive budgeting, realtime policy follow-up limits and memory-query's latest40-fact input remain stated module limits. Hosted Actions status must be read separately; the prior account-level restriction did not execute tests, and no billing or branch-protection setting is changed by this task.
