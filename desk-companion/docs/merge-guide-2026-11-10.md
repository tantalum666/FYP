> HISTORICAL contributor integration rehearsal. The reviewed combined implementation, repairs and actual validation are recorded in [11 November QA](../../output/qa/2026-11-11-grok-review/verification.md). Historical instructions to keep failures or avoid #97 do not govern the current owner-authorized integration.

# Merge guide for open Grok Bot pull requests — 10 November 2026

Completed by Grok Bot via a Cursor cloud agent on 10 November 2026, for Codex. This is a merge plan, not a merge. Codex merges. Do not modify PR #97 or any Codex branch. Do not force-push. Do not rebase these branches. No paid model call was made while checking this plan.

This pull request only adds this guide and the QA note under `output/qa/2026-11-10-merge-plan/`. It does not edit `handoff.md`, `work-log.md`, `decision-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, or `product.md`. Those files are the conflict surface below. Merge this guide whenever; it does not change those conflicts against current `main`.

`origin/main` at the check was `855e60ee9f413de84474e3e0b9975b9b9a3d5fbc` (7 November live-agent handoff, PR94 merged).

The check used a local throwaway branch, `cursor/merge-integration-throwaway-1da6`, created from that `main`. Each head below was brought in with ordinary `git merge` (no rebase, no squash). That branch was not pushed and is not a pull request.

## Do not merge from this file until Codex is merging

- **#97** `codex/alice-home-wake-20261107` at `ebf6d91751ff69f6acec0813f7eb69a1ed53dc5d` stays a Codex pull request. A dry merge onto the combined Grok tree is listed at the end. It was aborted. Nothing was pushed to that branch.
- Drafts #73, #87, and #88 stay untouched.
- Do not reopen a paid round. The USD1 live ledger stays closed.
- `test_public_unicast[::ffff:93.184.216.34]` still fails on this Python. Leave it. #98 does not fix it.
- #98 does fix `test_restart_runs_only_the_approved_folder_job`.

## Order

Merge each **head** into `main` with a merge commit, top to bottom. Do not use “Rebase and merge”. Stack children contain their parents, so merge the parent head into `main` first, then merge the child head into `main`. That is what the conflict notes describe. Retargeting a child onto `main` and rebasing it will replay commits and will not match this check.

| Step | PR | Head | Tip | At this step |
| --- | --- | --- | --- | --- |
| 1 | [#98](https://github.com/tantalum666/FYP/pull/98) | `cursor/folder-job-restart-clock-fc55` | `c37d194b97f8cf7974730dba2f73dafc58398479` | fast-forward, no conflicts |
| 2 | [#95](https://github.com/tantalum666/FYP/pull/95) | `cursor/conversation-work-reshow-verified-b9a2` | `19745987f62d2a044ec6c0be690e11268532524a` | living docs |
| 3 | [#96](https://github.com/tantalum666/FYP/pull/96) | `cursor/conversation-work-continue-once-51ee` | `195ccc7c0d2fd088fce117f8275b921f516444cc` | living docs |
| 4 | [#99](https://github.com/tantalum666/FYP/pull/99) | `cursor/conversation-work-second-continue-3b11` | `53f22fffc964ee11291d5675f12c16adc3d0646c` | living docs |
| 5 | [#101](https://github.com/tantalum666/FYP/pull/101) | `cursor/owner-browser-takeover-c60c` | `259a30469dd57dc880ebd668d9c9cda3f854afe6` | living docs |
| 6 | [#102](https://github.com/tantalum666/FYP/pull/102) | `cursor/memory-followup-112e` | `fa66d4b003326149804a365aefaaebede29c0534` | living docs |
| 7 | [#103](https://github.com/tantalum666/FYP/pull/103) | `cursor/memory-morning-checkin-c3a3` | `a23c09d135b66e44e250596249288d657cc58c38` | `handoff.md` only |
| 8 | [#104](https://github.com/tantalum666/FYP/pull/104) | `cursor/offline-trip-quotes-1593` | `eb7f6c05a00586cac3d99ad5c8f7ef3326a29c08` | clean, including `app.py` and `runtime.py` |
| 9 | [#105](https://github.com/tantalum666/FYP/pull/105) | `cursor/trip-quote-reapproval-2cfb` | `baf3032d85b6c224eddd7db5af8065910525a6a2` | clean |

Stacks, already true on these tips: #95 is an ancestor of #96, #96 of #99, #102 of #103, #104 of #105. #98, #101, #102, and #104 each sit directly on `855e60ee`.

## Living-doc rule for every conflicted step

`handoff.md`, `START_HERE_NEXT_CHAT.md`, `AGENTS.md`, `decision-log.md`, `work-log.md`, and `research/personal-agent-research-index.md` are docs. No Python or TypeScript file conflicted in steps 1–9.

`decision-log.md` and `work-log.md` conflict because each pull request appends its own section at the same end. Keep every new `##` section from both sides, in merge order (the section already on the branch, then the incoming section). Do not drop a section because a later “剩余” still talks about that work as future work. The older sentence stays as history. The handoff’s single next step is what is still absent after that merge.

`handoff.md` and `START_HERE_NEXT_CHAT.md` are rewritten by each slice, so a conflict marker often covers only the new opening. Git then keeps the incoming replacement and drops the other side’s body when that side only inserted a paragraph. Do not accept that deletion. Keep both:

- the folder-job clock paragraph from #98
- the 7 November live-evaluation sections that are on `main` (Actual results, Runtime and recovery, closed USD1 ledger, Pi source `d40457fe`, PR94)
- each incoming slice’s current behavior, evidence, and explicit non-goals

`AGENTS.md` conflicts only in the HTML comment banner. Keep one banner. Name every behavior already merged: re-show, one continue, a second continue while the run is open, the injected folder-job clock, offline owner takeover, the memory follow-up, and the morning check-in. Say that a live JD login is not done, that `test_public_unicast[::ffff:93.184.216.34]` remains, and that mailbox, shopping, and offline-calendar decide branches are unchanged.

`research/personal-agent-research-index.md` auto-merged in this order. If a different order conflicts, keep every `工程更新` / `工程补充` paragraph and the longer capability-table cell.

## Code that must survive even when git auto-merges

#102/#103 and #104/#105 both edit `desk-companion/backend/desk/runtime.py` and `desk-companion/backend/desk/app.py`. In this order those files auto-merged. Confirm the result; do not drop a side if a later merge conflicts.

`Runtime.tick` keeps the existing quiet-release calls and adds trip quotes and memory follow-ups:

```python
self.mailbox.release_quiet_notices()
self.shopping.release_quiet_notices()
self.trips.release_quiet_notices()
self.offline_calendar.release_quiet_notices()
self.memories.expire()
self.memory_followups.tick()
```

Also keep `self.memory_followups = MemoryFollowUpService(self)` and `self.trips = TravelQuoteService(self)`.

`create_app` keeps `memory_followup_routes(...)` next to `memory_routes`, and `trip_routes(...)` after `offline_calendar_routes`. `mailbox_routes`, `shopping_routes`, and `offline_calendar_routes` stay.

`desk-companion/backend/desk/exchange.py` is not edited by any of #95–#105. Leave these three portable keys in place. Memory follow-ups and trip quotes do not add a fourth backup bundle:

- `mailbox_bundle`
- `shopping_bundle`
- `offline_calendar_bundle`

#99’s decision text says the mailbox, shopping, and offline-calendar decide branches are unchanged. Do not rewrite those journey matchers while taking the second-continue slice.

## Per-step resolutions

### 1. #98 — clean

Fast-forward `855e60ee..c37d194`. The restarted folder-job test passes `app.state.store.clock`. Production approval, expiry, and execution already shared that clock. No conflict.

### 2. #95 — docs

Conflict markers:

- `START_HERE_NEXT_CHAT.md`
- `decision-log.md`
- `handoff.md`
- `work-log.md`

`AGENTS.md` auto-merged to #95’s banner (#98 did not edit it). `research/personal-agent-research-index.md` auto-merged: the re-show sentence was added to the 2026-11-06 engineering paragraph and to the multi-step capability row.

Resolution:

- `decision-log.md`: keep `## 2026-11-10 Folder-job restart keeps the injected clock` and `## 2026-11-07 把已合并的 #94 同步进对话 Work 栈`. The earlier `## 2026-11-07 同一条对话再次读出已核验结果` auto-merged and stays.
- `work-log.md`: keep the folder-job clock section, then `Later ask re-shows the verified Work result`, then `Sync main after #94 into the re-show branch`.
- `handoff.md` / `START_HERE`: keep the clock paragraph and the re-show behavior (a later status ask reads the verified file and does not run the executor). Restore the 7 November live-evaluation body from #98/`main`. Next step at this point is #96, plus owner takeover, which this slice does not implement.

### 3. #96 — docs

Conflict markers:

- `START_HERE_NEXT_CHAT.md`
- `decision-log.md` (one bullet)
- `handoff.md`

`work-log.md` auto-merged and already contains both the continue section and the earlier re-show sections. `research/personal-agent-research-index.md` auto-merged and names both the status re-read and the explicit continue. `AGENTS.md` auto-merged onto #96’s banner and dropped the re-show wording. Put the re-show clause back into that one banner so both behaviors are named. Also name the injected clock, which #98 never wrote into `AGENTS.md`.

`decision-log.md`: the only marker is the last bullet of the #94 sync section. Keep the longer sentence, which is #96’s: the sync still does not implement JD takeover, #96’s explicit continue stays, and a run that is still open does not yet accept another explicit step. The new section `## 2026-11-07 明确要求后把同一项 Work 离线推进一步` auto-merged above that and stays.

`handoff.md`: keep the clock paragraph, the re-show bullets, and #96’s continue behavior (`Continue this work.` / `继续这项工作。` takes one `advance_one` when a single current run is clear). A status question only re-reads. Next step at this point is #99.

### 4. #99 — docs

Conflict markers:

- `AGENTS.md` (banner)
- `START_HERE_NEXT_CHAT.md`
- `decision-log.md`
- `handoff.md`

`work-log.md` and the research index auto-merged. The research capability row now says a later explicit ask advances the run only while it is open, and a finished, cancelled, failed, or expired run stays closed.

`decision-log.md`: keep the previous sync bullet, then append `## 2026-11-10 运行仍开着时，下一次明确要求再推进一步` in full. That section’s boundary line stays: 邮箱、购物和离线日程的决定分支不改.

Banner and handoff name all three Work behaviors plus the clock fix. A second explicit continue is one more `advance_one` only while that same run is open. No new store, queue, or provider call. Next product step after this stack is owner takeover (#101).

### 5. #101 — docs

Conflict markers:

- `AGENTS.md`
- `START_HERE_NEXT_CHAT.md`
- `decision-log.md`
- `handoff.md`
- `work-log.md`

`product.md` auto-merged: the 10 November takeover paragraph is inserted above the 7 November update, and the rest of the contract stays.

Code (`computer_use*.py`, `jobs.py`, `permissions.py`, the job card, and `test_owner_takeover.py`) merged with no markers.

`decision-log.md` and `work-log.md`: keep every section already on the branch, then append `## 2026-11-10 Same-job owner takeover at a verification wall` and the work-log section `## 2026-11-10 Owner takeover and return on the same browser job`.

Handoff keeps Work re-show / continue / second continue, the clock fix, the live-evaluation detail, and takeover: the same computer-use job pauses in `owner_takeover` at a login, SMS/OTP, captcha, or payment wall. Only the admitting owner can take over and hand that same job back. Alice does not type or store a password, code, or card. This is an offline fixture, not a live JD login. Next step: a live owner pass needs its own scoped session.

### 6. #102 — docs

Conflict markers:

- `START_HERE_NEXT_CHAT.md`
- `decision-log.md`
- `handoff.md`
- `work-log.md`

`product.md` auto-merged. Keep #101’s takeover paragraph and extend the 记忆／人格 row with the 2026-11-10 follow-up sentence. Do not replace that row with the pre-follow-up sentence.

The research index auto-merged the paragraph that one saved memory can be raised once at an owner-approved local time.

`runtime.py` and `app.py` took #102’s inserts with no marker. `memory_followups.py` is new.

Append `## 2026-11-10 Owner-approved memory follow-up` to the decision log and the matching work-log section. Handoff keeps takeover and Work, and adds the follow-up. Quiet hours hold that same row. Forgetting the fact cancels it and keeps the wording out of the notice. Next memory slice at this point is #103. Takeover is already in the tree; do not write that it is only “proposed separately”.

### 7. #103 — `handoff.md` only

Conflict markers: `handoff.md` (opening paragraph and the next-step paragraph).

`decision-log.md`, `work-log.md`, and `product.md` auto-merged. The 记忆／人格 row keeps both the single follow-up and the morning check-in: one approved check-in cites several due follow-ups that are still active. `notify.py` and `memory_followups.py` merged with no marker.

Handoff: keep the clock paragraph and add the morning check-in paragraph. The check-in reuses `memory_followups.tick`. There is no second scheduler and no mailbox. The next step no longer says the check-in is still to build. A live JD pass remains a separate scoped session.

### 8. #104 — clean, including the code overlap

No conflict markers. `app.py` and `runtime.py` auto-merged with #102/#103. Confirm `Runtime.tick` matches the block above: mailbox, shopping, trips, offline calendar, then `memory_followups.tick`. `exchange.py` still exports `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` and nothing else was added there. Trip quotes are an offline fixture on the existing task/notice path. They are not a fourth portable bundle.

### 9. #105 — clean

No conflict markers. Changes stay inside `travel_quotes`, the trip-quote UI/tests, `desk-companion/docs/offline-trip-quotes.md`, and the new reapproval QA. A changed quote needs a fresh owner approval. #104’s hold-on-one-task behavior stays.

## Combined tests

Run on the combined tree after step 9, before the #97 dry merge. No paid provider call.

Backend, from `desk-companion/`:

```sh
export PYTHONPATH="$PWD:$PWD/backend"
uv run --no-sync pytest -q --tb=line
```

`PYTHONPATH` must include the `desk-companion` root. This environment’s pytest 9.1.1 does not import `scripts.*` when `tool.pytest.ini_options.pythonpath` is only `backend`. With that path set, collection succeeds.

Result: **2103 passed, 1 failed**, 464.71s. The only failure is the known `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]` (`is_public_unicast('::ffff:93.184.216.34')` is false because `IPv6Address.is_reserved` is true for `::ffff:0:0/96`). `test_restart_runs_only_the_approved_folder_job` passed. Two warnings: Starlette/`httpx` deprecation in `TestClient`, and an empty `pytest.raises` match in `test_mcp_connectors.py`.

Frontend, from `desk-companion/frontend/`:

```sh
npm test
```

Result: **338 passed, 0 failed**, 0 skipped. That is `node --experimental-strip-types --test tests/*.test.ts`, which is the package `test` script.

## Dry merge of #97

After step 9, `git merge --no-commit --no-ff origin/codex/alice-home-wake-20261107` (`ebf6d917`) conflicted. The merge was aborted. #97’s branch was not updated and was not pushed.

No code file had a conflict marker. These code files auto-merged and still contained the Grok behavior as well as #97’s additions: `runtime.py` (Microsoft apps and outbound mail, while mailbox, shopping, trips, offline calendar, and `memory_followups.tick` remained), `app.py`, `text_ai.py` (chat attachments plus the existing `conversation_work.turn`), `api.ts`, `ComputerJobsPanel.tsx`, `JobActionCard.tsx`. `test_folder_jobs.py` had no diff, so the injected-clock assertion stayed. `exchange.py` was not in the merge diff. Re-read those auto-merged files when #97 is actually merged; a marker-free merge can still drop a call. The required `Runtime.tick` block and the three bundle keys above still apply.

Conflict markers, all documentation:

| File | Kind | Hunks | What collided |
| --- | --- | --- | --- |
| `AGENTS.md` | living doc | 1 | Banner. Ours names the Grok slices and the clock fix. Theirs is the 9 November composer / A3 banner. Keep one banner with both. |
| `START_HERE_NEXT_CHAT.md` | living doc | 1 | Ours is the combined 10 November continuation. Theirs is the 9 November PR97 checkout note. Keep both status paragraphs. Do not revert takeover, Work, memory, or trip quotes to “not started”. |
| `decision-log.md` | living doc | 1 | Both sides append at the end. Keep every `##` from the Grok slices and every `##` from #97, including Shared Alice home, local wake, GPT Live, and the later voice/composer/mail entries. |
| `work-log.md` | living doc | 1 | Same append. Keep the Grok sections from #98 through #103 and #97’s sections from 7 November onward. |
| `handoff.md` | living doc | 3 | Ours is the combined Grok handoff, including the retained 7 November live-evaluation detail. Theirs is the 9 November Alice/composer handoff. Keep both bodies. One next step must still say a live JD pass needs its own scoped session, and must also keep #97’s own next step (read the pinned Pi relay before the prepared safe-area follow-up; do not blindly restart). |
| `research/personal-agent-research-index.md` | living doc | 1 | Opening status only. Keep #97’s 9 November A3 paragraph and 8 November Gmail paragraph, and the 7 November live-update paragraph. The `工程更新` paragraphs and the 2026-11-10 memory paragraph below the marker were not inside the conflict. Do not delete them. |
| `product.md` | product contract | 2 | Opening status: keep #101’s takeover sentence and #97’s 9/8/7 November composer, A3, Gmail, and Alice-home paragraphs. Table: the 应用连接 row and the GPT Live AI会话 row auto-merged from #97 and should stay. The conflict is the 网页／手机 row and the 记忆／人格 row. Keep #97’s 网页／手机 text (三端深色 Alice 首页、月历／时间／天气、较矮屏幕独立滚动). Keep the combined 记忆／人格 text, which adds the 2026-11-10 follow-up and the morning check-in. #97’s side of that row is the older sentence and drops those two behaviors. |
| `desk-companion/docs/conversation-work.md` | feature contract | 1 | Keep #97’s `## Current interface boundary — 8 November 2026` (Voice input / Work conversion cards are gone from ordinary Conversation; the server steer APIs remain). Keep the combined 10 November paragraph that status asks re-show, one explicit continue advances once, and a later explicit ask takes one more step only while the run is open. #97’s 6 November paragraph is the older goal-change text and does not replace the later sentences. |

## After the nine Grok pulls are on main

Offline owner takeover, Work re-show and two explicit continues, the folder-job clock, one memory follow-up, one morning check-in, and offline trip-quote hold plus reapproval are in the same tree. A live JD login, native unattended mail monitoring, payment, and a new paid round are not. #97 remains Codex’s separate pull request. Merge it after the nine, using the conflict list above, still with a normal merge and no force-push.
