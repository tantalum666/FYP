# Merge guide for open Grok Bot pull requests — 11 November 2026

Completed by Grok Bot via a Cursor cloud agent on 11 November 2026, for Codex. This is a merge plan, not a merge. Codex merges. Do not modify PR #97 or any Codex branch. Do not force-push. Do not rebase these branches. No paid model call was made while checking this plan.

This pull request only adds this guide and the QA note under `output/qa/2026-11-11-merge-plan/`. It does not edit `handoff.md`, `work-log.md`, `decision-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `product.md`, or the 10 November guide on [PR #107](https://github.com/tantalum666/FYP/pull/107) (`desk-companion/docs/merge-guide-2026-11-10.md`, which is not on `main` yet). Those living files are the conflict surface below. Merge this guide whenever; it does not change those conflicts against current `main`.

`origin/main` at the check was `855e60ee9f413de84474e3e0b9975b9b9a3d5fbc` (7 November live-agent handoff, PR94 merged). Main had not moved since the 10 November guide.

The check used a local throwaway branch, `cursor/merge-integration-throwaway-f524`, created from that `main`. Each head below was brought in with ordinary `git merge` (no rebase, no squash). That branch was not pushed and is not a pull request. None of #98, #95, #96, #99, #101, #102, #103, #104, #105, #108, #109, #110, #111, or #112 were modified. No fix was pushed, because the combined tree did not add a failure beyond the known public-unicast case.

## Do not merge from this file until Codex is merging

- **#97** `codex/alice-home-wake-20261107` at `ebf6d91751ff69f6acec0813f7eb69a1ed53dc5d` stays a Codex pull request. A dry merge onto the combined Grok tree is listed at the end. It was aborted. Nothing was pushed to that branch.
- Drafts #73, #87, and #88 stay untouched. #94 stays merged.
- Do not reopen a paid round. The USD1 live ledger stays closed.
- `test_public_unicast[::ffff:93.184.216.34]` still fails on this Python 3.12. Leave it. #98 does not fix it.
- #98 does fix `test_restart_runs_only_the_approved_folder_job`. On this combined tree that test passed.

## Order

Merge each **head** into `main` with a merge commit, top to bottom. Do not use “Rebase and merge”. Stack children contain their parents, so merge the parent head into `main` first, then merge the child head into `main`. That is what the conflict notes describe. Retargeting a child onto `main` and rebasing it will replay commits and will not match this check.

| Step | PR | Head | Tip | At this step |
| --- | --- | --- | --- | --- |
| 1 | [#98](https://github.com/tantalum666/FYP/pull/98) | `cursor/folder-job-restart-clock-fc55` | `c37d194b97f8cf7974730dba2f73dafc58398479` | fast-forward, no conflicts |
| 2 | [#95](https://github.com/tantalum666/FYP/pull/95) | `cursor/conversation-work-reshow-verified-b9a2` | `19745987f62d2a044ec6c0be690e11268532524a` | living docs |
| 3 | [#96](https://github.com/tantalum666/FYP/pull/96) | `cursor/conversation-work-continue-once-51ee` | `195ccc7c0d2fd088fce117f8275b921f516444cc` | living docs |
| 4 | [#99](https://github.com/tantalum666/FYP/pull/99) | `cursor/conversation-work-second-continue-3b11` | `53f22fffc964ee11291d5675f12c16adc3d0646c` | living docs |
| 5 | [#101](https://github.com/tantalum666/FYP/pull/101) | `cursor/owner-browser-takeover-c60c` | `259a30469dd57dc880ebd668d9c9cda3f854afe6` | living docs |
| 6 | [#102](https://github.com/tantalum666/FYP/pull/102) | `cursor/memory-followup-112e` | `fa66d4b003326149804a365aefaaebede29c0534` | living docs; `runtime.py` / `app.py` auto-merge |
| 7 | [#103](https://github.com/tantalum666/FYP/pull/103) | `cursor/memory-morning-checkin-c3a3` | `a23c09d135b66e44e250596249288d657cc58c38` | living docs |
| 8 | [#104](https://github.com/tantalum666/FYP/pull/104) | `cursor/offline-trip-quotes-1593` | `eb7f6c05a00586cac3d99ad5c8f7ef3326a29c08` | clean, including `app.py` and `runtime.py` |
| 9 | [#105](https://github.com/tantalum666/FYP/pull/105) | `cursor/trip-quote-reapproval-2cfb` | `baf3032d85b6c224eddd7db5af8065910525a6a2` | clean |
| 10 | [#108](https://github.com/tantalum666/FYP/pull/108) | `cursor/saved-skills-d761` | `02779034f81f44575ee3d55728ba62fd84b7673b` | clean, including `app.py`, `runtime.py`, `TaskPanel.tsx` |
| 11 | [#109](https://github.com/tantalum666/FYP/pull/109) | `cursor/skill-schedule-be49` | `531426bb13868d85db211ef8df2fe1a25498a538` | clean; schedule is inside `RoutineService.tick` |
| 12 | [#110](https://github.com/tantalum666/FYP/pull/110) | `cursor/staple-purchase-card-ffeb` | `3313dc2d2c3ac8e9c6668326dee4c63678d65f54` | clean, including `runtime.py`, `app.py`, `TaskPanel.tsx` |
| 13 | [#111](https://github.com/tantalum666/FYP/pull/111) | `cursor/source-briefs-fa6c` | `9dec212fb5fc004aa6ff2b2336786cce36f644a2` | clean, including `runtime.py`, `app.py`, `MemoryPanel.tsx` |
| 14 | [#112](https://github.com/tantalum666/FYP/pull/112) | `cursor/held-choices-2645` | `1e32628e706e5a6a901f4c11fc4714646f42de8a` | one import conflict in `runtime.py` |

Stacks, already true on these tips: #95 is an ancestor of #96, #96 of #99, #102 of #103, #104 of #105, #108 of #109. #98, #101, #102, #104, #108, #110, #111, and #112 each sit directly on `855e60ee`. #108 through #112 do not edit `handoff.md`, `AGENTS.md`, `decision-log.md`, `work-log.md`, `START_HERE_NEXT_CHAT.md`, or `product.md`.

## Living-doc rule for every conflicted step

`handoff.md`, `START_HERE_NEXT_CHAT.md`, `AGENTS.md`, `decision-log.md`, `work-log.md`, and `research/personal-agent-research-index.md` are docs.

`decision-log.md` and `work-log.md` conflict because each pull request appends its own section at the same end. Keep every new `##` section from both sides, in merge order (the section already on the branch, then the incoming section). Do not drop a section because a later “剩余” still talks about that work as future work. The older sentence stays as history. The handoff’s single next step is what is still absent after that merge.

`handoff.md` and `START_HERE_NEXT_CHAT.md` are rewritten by each slice, so a conflict marker often covers only the new opening. Git then keeps the incoming replacement and drops the other side’s body when that side only inserted a paragraph. Do not accept that deletion. Keep both:

- the folder-job clock paragraph from #98
- the 7 November live-evaluation sections that are on `main` (Actual results, Runtime and recovery, closed USD1 ledger, Pi source `d40457fe`, PR94)
- each incoming slice’s current behavior, evidence, and explicit non-goals

`AGENTS.md` conflicts only in the HTML comment banner. Keep one banner. After step 14 it should name: re-show, one continue, a second continue while the run is open, the injected folder-job clock, offline owner takeover, one memory follow-up, the morning check-in, and that a live JD login is not done. Say that `test_public_unicast[::ffff:93.184.216.34]` remains, and that mailbox, shopping, and offline-calendar decide branches are unchanged. #108–#112 do not edit this banner; do not drop the earlier names when a later auto-merge replaces it.

## Code that must survive even when git auto-merges

#102/#103 and #104/#105 both edit `desk-companion/backend/desk/runtime.py` and `desk-companion/backend/desk/app.py`. In this order those files auto-merged. #108, #110, #111, and #112 edit the same two files again. Only #112 produced a marker, and it was the import block.

`Runtime.tick` after step 14, confirmed on the combined tree:

```python
self.mailbox.release_quiet_notices()
self.shopping.release_quiet_notices()
self.trips.release_quiet_notices()
self.offline_calendar.release_quiet_notices()
self.memories.expire()
self.memory_followups.tick()
self.nudges.tick()
self.goals.tick()
self.jobs.expire()
self.routines.tick()
self.voice.work.cleanup()
self.purchase_cards.release_quiet_notices()
```

`routines.tick` is where #109 appends the skill schedule. Inside `RoutineService.tick`, after the routine history trim:

```python
skills = getattr(self.runtime, "saved_skills", None)
if skills is not None and skills.release_due(conn):
    changed = True
```

That is the appended skill-schedule step. It is not a second scheduler and it is not a new line in `Runtime.tick`. A due occurrence prepares one pending run, or the occurrence is skipped and not replayed.

Also keep these constructors: `self.memory_followups`, `self.trips`, `self.saved_skills`, `self.purchase_cards`, `self.source_briefs`, `self.held_choices`.

`create_app` after step 14 keeps the existing routers and adds the new ones beside their neighbors:

- `memory_followup_routes` immediately after `memory_routes`
- `held_choice_routes` immediately after `goal_routes`
- `saved_skill_routes` immediately after `digest_routes`
- `source_brief_routes` immediately after `sources_routes`
- `purchase_card_routes` immediately after `google_routes` and before `mailbox_routes`
- `trip_routes` immediately after `offline_calendar_routes`

`mailbox_routes`, `shopping_routes`, and `offline_calendar_routes` stay.

`desk-companion/backend/desk/exchange.py` is not edited by any of #95–#112. Leave these three portable keys in place. Memory follow-ups, trip quotes, saved skills, purchase cards, source briefs, and held choices do not add a backup bundle:

- `mailbox_bundle`
- `shopping_bundle`
- `offline_calendar_bundle`

#99’s decision text says the mailbox, shopping, and offline-calendar decide branches are unchanged. Do not rewrite those journey matchers while taking the later slices.

`SCHEMA_VERSION` in `public_capture_schema.py` stays **3**. None of these fourteen pull requests change that constant. #108–#112 create their own tables with `CREATE TABLE IF NOT EXISTS` on first use (`saved_skills` / `saved_skill_runs` / `saved_skill_schedules` / `saved_skill_occurrences`, `purchase_cards` / `purchase_offers` / `purchase_claims`, `source_briefs` / `source_brief_sources` / `source_brief_claims`, `held_choices` / `held_choice_effects`). There is no shared migration function and no schema-version collision.

There is no shared i18n catalog. Copy uses inline `t(english, chinese)`. No two of these pull requests edited the same call. A scan of the combined frontend found existing English strings that already have more than one Chinese rendering in different components. New labels that reuse an existing English word, with a different Chinese string in another component, are `Source` (资料 on the source-brief panel, 来源 elsewhere), `Text` (正文 vs 文字), `Resume` (恢复 on the saved-skill panel, 继续 elsewhere), and `Active` (启用中, which matches routines, vs 待处理 on the task panel). `t` does not look those up in one dictionary, so they do not overwrite each other. That is not a merge defect.

Frontend navigation ids in `App.tsx` stay `assistant`, `today`, `calendar`, `tasks`, `memory`, `persona`, `records`, `device`, `diagnostics`. New surfaces are panels, not new nav entries:

- `TaskPanel` renders `SavedSkillsPanel` and `PurchaseCardPanel`
- `MemoryPanel` renders `SourceBriefPanel`
- the tasks page in `App.tsx` renders `HeldChoicePanel` under `TaskPanel`

Route prefixes do not overlap: `/api/saved-skills`, `/api/purchase-cards`, `/api/source-briefs`, `/api/held-choices`, `/api/trips`.

## Per-step resolutions

### 1. #98 — clean

Fast-forward `855e60ee..c37d194`. The restarted folder-job test passes `app.state.store.clock`. Production approval, expiry, and execution already shared that clock. No conflict.

### 2. #95 — docs

Conflict markers:

- `START_HERE_NEXT_CHAT.md` (opening)
- `decision-log.md` (both sides append at the end)
- `handoff.md` (opening only)
- `work-log.md` (both sides append at the end)

Cause: #98 inserted a clock paragraph at the same end that #95 rewrote. Git’s non-overlapping remainder is #95’s replacement, which deletes the 7 November live-evaluation body that #98 did not touch.

Resolution:

- `decision-log.md`: keep `## 2026-11-10 Folder-job restart keeps the injected clock`, then `## 2026-11-07 把已合并的 #94 同步进对话 Work 栈`. The earlier `## 2026-11-07 同一条对话再次读出已核验结果` auto-merged and stays.
- `work-log.md`: keep the folder-job clock section, then `Later ask re-shows the verified Work result`, then `Sync main after #94 into the re-show branch`.
- `handoff.md` / `START_HERE`: keep the clock paragraph and the re-show behavior (a later status ask reads the verified file and does not run the executor). Restore the 7 November live-evaluation body from #98/`main`. Next step at this point is #96, plus owner takeover, which this slice does not implement.
- `AGENTS.md` auto-merged to #95’s banner (#98 did not edit it). `research/personal-agent-research-index.md` auto-merged: the re-show sentence was added to the 2026-11-06 engineering paragraph.

### 3. #96 — docs

Conflict markers:

- `START_HERE_NEXT_CHAT.md` (opening)
- `handoff.md` (three hunks: opening, evidence paragraph, next step)

`decision-log.md` auto-merged. The last bullet of the #94 sync section became #96’s longer sentence: the sync still does not implement JD takeover, #96’s explicit continue stays, and a run that is still open does not yet accept another explicit step. `## 2026-11-07 明确要求后把同一项 Work 离线推进一步` auto-merged above that and stays.

`work-log.md` auto-merged and already contains both the continue section and the earlier re-show sections. `research/personal-agent-research-index.md` auto-merged and names both the status re-read and the explicit continue.

`AGENTS.md` auto-merged onto #96’s banner and dropped the re-show wording. There was no conflict marker. Put the re-show sentence back, and name the injected clock, which #98 never wrote into `AGENTS.md`.

`handoff.md`: keep the clock paragraph, the live-evaluation body, the re-show behavior, and #96’s continue behavior (`Continue this work.` / `继续这项工作。` takes one `advance_one` when a single current run is clear). A status question only re-reads. Keep both evidence paragraphs. Next step at this point is #99.

### 4. #99 — docs

Conflict markers:

- `AGENTS.md` (banner)
- `START_HERE_NEXT_CHAT.md` (opening)
- `handoff.md` (three hunks: opening, evidence, next step)

`decision-log.md`, `work-log.md`, and the research index auto-merged. The new section `## 2026-11-10 运行仍开着时，下一次明确要求再推进一步` stays in full. That section’s boundary line stays: 邮箱、购物和离线日程的决定分支不改. The research capability row says a later explicit ask advances the run only while it is open, and a finished, cancelled, failed, or expired run stays closed.

Banner and handoff name all three Work behaviors plus the clock fix. A second explicit continue is one more `advance_one` only while that same run is open. No new store, queue, or provider call. Next product step after this stack is owner takeover (#101).

### 5. #101 — docs

Conflict markers:

- `AGENTS.md` (banner)
- `START_HERE_NEXT_CHAT.md`
- `decision-log.md` (append)
- `handoff.md` (three hunks: title/clock paragraph, the `## Actual results` heading versus #101’s `## Done`, and the next step)
- `work-log.md` (append)

`product.md` auto-merged: the 10 November takeover paragraph is inserted above the 7 November update, and the rest of the contract stays.

Code (`computer_use*.py`, `jobs.py`, `permissions.py`, the job card, and `test_owner_takeover.py`) merged with no markers.

`decision-log.md` and `work-log.md`: keep every section already on the branch, then append `## 2026-11-10 Same-job owner takeover at a verification wall` and the work-log section `## 2026-11-10 Owner takeover and return on the same browser job`.

Handoff keeps Work re-show / continue / second continue, the clock fix, the live-evaluation detail, and takeover: the same computer-use job pauses in `owner_takeover` at a login, SMS/OTP, captcha, or payment wall. Only the admitting owner can take over and hand that same job back. Alice does not type or store a password, code, or card. This is an offline fixture, not a live JD login. Next step: a live owner pass needs its own scoped session.

### 6. #102 — docs, code auto-merged

Conflict markers:

- `START_HERE_NEXT_CHAT.md`
- `decision-log.md` (append)
- `handoff.md` (opening, and the next-step paragraph)
- `work-log.md` (append)

`product.md` auto-merged. Keep #101’s takeover paragraph and extend the 记忆／人格 row with the 2026-11-10 follow-up sentence. Do not replace that row with the pre-follow-up sentence.

The research index auto-merged the paragraph that one saved memory can be raised once at an owner-approved local time.

`runtime.py` and `app.py` took #102’s inserts with no marker. `memory_followups.py` is new. `memory_followups.tick()` sits after `memories.expire()`. `memory_followup_routes` sits next to `memory_routes`.

Append `## 2026-11-10 Owner-approved memory follow-up` to the decision log and the matching work-log section. Handoff keeps takeover and Work, and adds the follow-up. Quiet hours hold that same row. Forgetting the fact cancels it and keeps the wording out of the notice.

#102’s own next-step text still says browser takeover “is already proposed separately”, because that branch was cut from `main` before #101. Do not leave that as the combined next step. Takeover is already in the tree. Next memory slice at this point is #103.

`AGENTS.md` had no marker. The banner was extended with the follow-up sentence so a later rewrite does not have to recover it from a dropped auto-merge.

### 7. #103 — docs

Conflict markers:

- `decision-log.md` (the last bullet of the follow-up section, plus the new morning-check-in section)
- `handoff.md` (opening paragraph and the next-step paragraph)
- `work-log.md` (the follow-up “remaining” bullet, plus the new section)

Cause: #103 is stacked on #102 and edits the same closing bullet #102 added, while the combined tree had already rewritten that bullet to say takeover is merged.

Resolution: keep the longer combined bullet (takeover is already in this tree; this slice did not edit it). Drop the duplicate short bullet that still calls takeover an open proposal. Append `## 2026-11-10 One morning check-in for several memory follow-ups` and the matching work-log section in full. The check-in reuses `memory_followups.tick`. There is no second scheduler and no mailbox.

`product.md` auto-merged. The 记忆／人格 row keeps both the single follow-up and the morning check-in: one approved check-in cites several due follow-ups that are still active. `notify.py` and `memory_followups.py` merged with no marker.

The next step no longer says the check-in is still to build. A live JD pass remains a separate scoped session. Next merge at this point is #104.

### 8. #104 — clean, including the code overlap

No conflict markers. `app.py` and `runtime.py` auto-merged with #102/#103. Confirm `Runtime.tick` has mailbox, shopping, trips, offline calendar, then `memory_followups.tick`. `exchange.py` still exports the three bundles and nothing else was added there. `trip_routes` is registered after `offline_calendar_routes`. Trip quotes are an offline fixture on the existing task/notice path. They are not a fourth portable bundle.

### 9. #105 — clean

No conflict markers. Changes stay inside `travel_quotes`, the trip-quote UI/tests, `desk-companion/docs/offline-trip-quotes.md`, and the new reapproval QA. A changed quote needs a fresh owner approval. #104’s hold-on-one-task behavior stays. `Runtime.tick` is unchanged.

### 10. #108 — clean

No conflict markers. `app.py` and `runtime.py` auto-merged. `SavedSkillService` is constructed on `Runtime`. `saved_skill_routes` is registered after `digest_routes`. `SavedSkillsPanel` is mounted from `TaskPanel`. The nav id list is unchanged. No living-doc edit, no schema-version edit.

### 11. #109 — clean

No conflict markers. #108 is an ancestor of this tip, so the saved-skill files merge as a fast content update rather than a duplicate add. The only scheduler change is `saved_skills.release_due(conn)` inside `RoutineService.tick`, on the same local routine clock. It does not add a line to `Runtime.tick` and it does not add a route.

### 12. #110 — clean, including the Task panel overlap

No conflict markers. `runtime.py`, `app.py`, and `TaskPanel.tsx` auto-merged with #108/#109. Confirm both panels remain: `SavedSkillsPanel` and `PurchaseCardPanel`. `purchase_cards.release_quiet_notices()` is appended at the end of `Runtime.tick`, after `voice.work.cleanup()`. `purchase_card_routes` is registered after `google_routes` and before `mailbox_routes`. `tasks.py` changes come only from this pull request. The earlier quiet-release order is unchanged.

### 13. #111 — clean

No conflict markers. `runtime.py`, `app.py`, and `MemoryPanel.tsx` auto-merged. `SourceBriefService` is constructed on `Runtime`. `source_brief_routes` is registered after `sources_routes`. `SourceBriefPanel` is mounted from `MemoryPanel`. No living-doc edit.

### 14. #112 — one import conflict

Conflict markers:

- `desk-companion/backend/desk/runtime.py` (one hunk)

Cause: #108 and #112 both insert an import on the line after `from .goals import GoalService`.

```python
from .goals import GoalService
from .saved_skills import SavedSkillService
from .held_choices import HeldChoiceService
```

Keep both. The constructor lines auto-merged without a marker: `self.held_choices` after `self.goals`, and `self.saved_skills` after `self.personal_context`. `app.py` auto-merged `held_choice_routes` after `goal_routes`. `api.ts` auto-merged. `App.tsx` auto-merged `HeldChoicePanel` on the tasks page and did not change the nav ids. `desk-companion/docs/modules.md` gained the `held_choices` row with no marker.

No other file had a conflict marker on this step. `Runtime.tick` after the resolution is the block in “Code that must survive”.

## Combined tests

Run on the combined tree after step 14, before the #97 dry merge. No paid provider call. No fix was committed to any pull-request branch.

Backend, from `desk-companion/`:

```sh
export PYTHONPATH="$PWD:$PWD/backend"
uv run --no-sync pytest -q --tb=line
```

`PYTHONPATH` must include the `desk-companion` root. This environment’s pytest 9.1.1 does not import `scripts.*` when `tool.pytest.ini_options.pythonpath` is only `backend`. With that path set, collection succeeds. Interpreter: CPython 3.12.3.

Result: **2139 passed, 1 failed**, 519.18s. The only failure is the known `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]`. `test_restart_runs_only_the_approved_folder_job` is not in the failure list. Two warnings, both pre-existing in kind: Starlette/`httpx` deprecation in `TestClient`, and an empty `pytest.raises` match.

The 10 November combined tree, before #108–#112, was 2103 passed and 1 failed. This run is that tree plus the five later slices. No new failure appeared.

Frontend, from `desk-companion/frontend/`:

```sh
npm test
```

Result: **348 passed, 0 failed**, 0 skipped, about 10.3s. That is `node --experimental-strip-types --test tests/*.test.ts`, which is the package `test` script. The 10 November count was 338. The ten additional passes are the new saved-skill, purchase-card, source-brief, and held-choice cases.

Ruff, from `desk-companion/`:

```sh
uv run --no-sync ruff check
```

Result: all checks passed (ruff 0.16.9).

Typecheck, from `desk-companion/frontend/`:

```sh
npx tsc --noEmit
```

Result: exit 0, no diagnostics.

## Fixes pushed

None. The only failing test is the known Python 3.12 public-unicast case. It does not belong in #108–#112, and it was left unchanged.

## Dry merge of #97

After step 14, `git merge --no-commit --no-ff origin/codex/alice-home-wake-20261107` (`ebf6d917`) conflicted. The merge was aborted. #97’s branch was not updated and was not pushed.

No code file had a conflict marker. These code files auto-merged. Re-read them when #97 is actually merged; a marker-free merge can still drop a call. On this dry merge the required behavior was still present:

- `runtime.py` gained `MicrosoftApps` and `OutboundMail`, and still called mailbox, shopping, trips, offline calendar, `memory_followups.tick`, and `purchase_cards.release_quiet_notices`. `saved_skills`, `held_choices`, `source_briefs`, and `purchase_cards` were still constructed.
- `app.py` still registered memory follow-ups, held choices, saved skills, source briefs, purchase cards, mailbox, offline calendar, and trip routes, and added #97’s `weather_routes`, `outbound_mail_routes`, and `app_connections_routes`.
- `text_ai.py` still calls `conversation_work.turn` and also carries #97’s chat-attachment path.
- `test_folder_jobs.py` still passes `clock=app.state.store.clock` into the restarted app.
- `exchange.py` was not in the merge diff. The three bundle keys stayed.
- `TaskPanel.tsx` was not in the merge diff. `SavedSkillsPanel` and `PurchaseCardPanel` stayed.
- `MemoryPanel.tsx` still mounts `SourceBriefPanel`.
- `App.tsx` auto-merged `AliceHome` and still mounts `HeldChoicePanel` on the tasks page. The nav id list was unchanged.
- `routines.py` was not in the merge diff, so `saved_skills.release_due` stayed.

Conflict markers, all documentation:

| File | Kind | Hunks | What collided |
| --- | --- | --- | --- |
| `AGENTS.md` | living doc | 1 | Banner. Ours names the Grok slices through the morning check-in, the clock fix, offline takeover, and the unicast failure. Theirs is the 9 November composer / A3 banner. Keep one banner with both. |
| `START_HERE_NEXT_CHAT.md` | living doc | 1 | Ours is the combined 10–11 November continuation (clock, Work stack, takeover, memory follow-up, morning check-in, next trip-quote step). Theirs is the 9 November PR97 checkout note. Keep both status paragraphs. Do not revert takeover, Work, memory, trip quotes, skills, purchase cards, source briefs, or held choices to “not started”. |
| `decision-log.md` | living doc | 1 | Both sides append at the end. Keep every `##` from the Grok slices (#98 through #103) and every `##` from #97, including Shared Alice home, local wake, GPT Live, and the later voice/composer/mail entries. |
| `work-log.md` | living doc | 1 | Same append. Keep the Grok sections from #98 through #103 and #97’s sections from 7 November onward. |
| `handoff.md` | living doc | 2 | Ours is the combined Grok handoff, including the retained 7 November live-evaluation detail, takeover, Work, memory follow-up, and morning check-in. Theirs is the 9 November Alice/composer handoff. The marker covers the opening and the next-step paragraph. The live-evaluation `## Actual results` / `## Runtime and recovery` body is not safely outside the marker; restore it, do not accept its deletion. Keep #97’s current-software and runtime-availability sections. One next step must still say a live JD pass needs its own scoped session, and must also keep #97’s own next step (read the pinned Pi relay before the prepared safe-area follow-up; do not blindly restart). Trip quotes, saved skills, purchase cards, source briefs, and held choices are in the tree by this point even though the handoff’s older “next merge is #104” sentence was written at step 7. Do not treat them as future work. |
| `research/personal-agent-research-index.md` | living doc | 1 | Opening status only. Keep #97’s 9 November A3 paragraph and 8 November Gmail paragraph, and the 7 November live-update paragraph. The `工程更新` paragraphs, including the 2026-11-10 second-continue paragraph and the memory-follow-up `工程补充`, sit below the marker and were not inside the conflict. Do not delete them. |
| `product.md` | product contract | 2 | Opening status: keep #101’s takeover sentence and #97’s 9/8/7 November composer, A3, Gmail, and Alice-home paragraphs. The 7 November live-eval paragraph below the marker stays. Table: the 应用连接 row and the GPT Live AI会话 row auto-merged from #97 and should stay. The conflict is the 网页／手机 row and the 记忆／人格 row. Keep #97’s 网页／手机 text (三端深色 Alice 首页、月历／时间／天气、较矮屏幕独立滚动). Keep the combined 记忆／人格 text, which adds the 2026-11-10 follow-up and the morning check-in. #97’s side of that row is the older sentence and drops those two behaviors. |
| `desk-companion/docs/conversation-work.md` | feature contract | 1 | Keep #97’s `## Current interface boundary — 8 November 2026` (Voice input / Work conversion cards are gone from ordinary Conversation; the server steer APIs remain). Keep the combined 10 November paragraph that status asks re-show, one explicit continue advances once, and a later explicit ask takes one more step only while the run is open. #97’s 6 November paragraph is the older goal-change text and does not replace the later sentences. |

## After the fourteen Grok pulls are on main

Offline owner takeover, Work re-show and two explicit continues, the folder-job clock, one memory follow-up, one morning check-in, offline trip-quote hold plus reapproval, owner-saved skills, a skill schedule on the routine clock, an owner-confirmed staple purchase card, cited source briefs, and held choices are in the same tree. A live JD login, native unattended mail monitoring, payment, and a new paid round are not. #97 remains Codex’s separate pull request. Merge it after the fourteen, using the conflict list above, still with a normal merge and no force-push.

## Handoff for Codex

Grok Bot completed this check. The fourteen heads above merge in that order with one code conflict, the `runtime.py` import at #112, resolved by keeping both imports. Living-doc conflicts are append-or-restore, not pick-one-side. The combined local suites are 2139 passed / 1 failed (the known `::ffff:93.184.216.34` unicast test), 348 frontend passed, ruff clean, `tsc --noEmit` clean. Nothing was pushed to a Grok or Codex branch except this docs pull request. #97 dry-merges with documentation conflicts only; abort unless you are actually merging it, and re-read `Runtime.tick` after that merge so the quiet-release order and `saved_skills.release_due` are still there.
