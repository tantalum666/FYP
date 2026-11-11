> HISTORICAL contributor integration rehearsal. The reviewed combined implementation, repairs and actual validation are recorded in [11 November QA](../../output/qa/2026-11-11-grok-review/verification.md). Historical instructions to keep failures or avoid #97 do not govern the current owner-authorized integration.

# Merge guide for open Grok Bot pull requests — 11 November 2026, conversation intents

Completed by Grok Bot via a Cursor cloud agent on 11 November 2026, for Codex. This is a merge plan, not a merge. Codex merges. Do not modify PR #97 or any Codex branch. Do not force-push. Do not rebase these branches. No paid model call was made while checking this plan.

This pull request only adds this guide. It does not edit [the 11 November guide](https://github.com/tantalum666/FYP/pull/113) (`desk-companion/docs/merge-guide-2026-11-11.md`, which is not on `main` yet), `handoff.md`, `work-log.md`, `decision-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `product.md`, or the research index. Merge this guide whenever; it does not change those conflicts against current `main`.

`origin/main` at the check was `855e60ee9f413de84474e3e0b9975b9b9a3d5fbc`. The fourteen heads in [PR #113](https://github.com/tantalum666/FYP/pull/113) had not moved. The three new heads are the conversation intents opened on that same `main` after that guide.

The check used a local throwaway branch, `cursor/merge-integration-throwaway-24ac`, created from that `main`. Each head below was brought in with ordinary `git merge --no-ff` (no rebase, no squash). That branch was not pushed and is not a pull request. None of #98, #95, #96, #99, #101, #102, #103, #104, #105, #108, #109, #110, #111, #112, #114, #115, or #116 were modified. No fix was pushed. #97 was dry-merged and the merge was aborted. Nothing was pushed to `codex/alice-home-wake-20261107`.

## Do not merge from this file until Codex is merging

- **#97** `codex/alice-home-wake-20261107` at `ebf6d91751ff69f6acec0813f7eb69a1ed53dc5d` stays a Codex pull request. The dry merge is listed at the end. It was aborted.
- Drafts #73, #87, and #88 stay untouched. #94 stays merged.
- Do not reopen a paid round. The USD1 live ledger stays closed.
- `test_public_unicast[::ffff:93.184.216.34]` still fails on this Python 3.12. Leave it.
- #98 still fixes `test_restart_runs_only_the_approved_folder_job`. On this combined tree that test passed.

## Order

Merge each **head** into `main` with a merge commit, top to bottom. Do not use “Rebase and merge”. Stack children contain their parents, so merge the parent head into `main` first, then merge the child head into `main`.

Steps 1–14 are the order already checked in PR #113, re-run here at the same tips. Steps 15–17 are the new conversation intents, in the order they were opened: next step, then open time, then meeting prep.

| Step | PR | Head | Tip | At this step |
| --- | --- | --- | --- | --- |
| 1 | [#98](https://github.com/tantalum666/FYP/pull/98) | `cursor/folder-job-restart-clock-fc55` | `c37d194b97f8cf7974730dba2f73dafc58398479` | clean |
| 2 | [#95](https://github.com/tantalum666/FYP/pull/95) | `cursor/conversation-work-reshow-verified-b9a2` | `19745987f62d2a044ec6c0be690e11268532524a` | living docs |
| 3 | [#96](https://github.com/tantalum666/FYP/pull/96) | `cursor/conversation-work-continue-once-51ee` | `195ccc7c0d2fd088fce117f8275b921f516444cc` | living docs |
| 4 | [#99](https://github.com/tantalum666/FYP/pull/99) | `cursor/conversation-work-second-continue-3b11` | `53f22fffc964ee11291d5675f12c16adc3d0646c` | living docs |
| 5 | [#101](https://github.com/tantalum666/FYP/pull/101) | `cursor/owner-browser-takeover-c60c` | `259a30469dd57dc880ebd668d9c9cda3f854afe6` | living docs |
| 6 | [#102](https://github.com/tantalum666/FYP/pull/102) | `cursor/memory-followup-112e` | `fa66d4b003326149804a365aefaaebede29c0534` | living docs |
| 7 | [#103](https://github.com/tantalum666/FYP/pull/103) | `cursor/memory-morning-checkin-c3a3` | `a23c09d135b66e44e250596249288d657cc58c38` | living docs |
| 8 | [#104](https://github.com/tantalum666/FYP/pull/104) | `cursor/offline-trip-quotes-1593` | `eb7f6c05a00586cac3d99ad5c8f7ef3326a29c08` | clean |
| 9 | [#105](https://github.com/tantalum666/FYP/pull/105) | `cursor/trip-quote-reapproval-2cfb` | `baf3032d85b6c224eddd7db5af8065910525a6a2` | clean |
| 10 | [#108](https://github.com/tantalum666/FYP/pull/108) | `cursor/saved-skills-d761` | `02779034f81f44575ee3d55728ba62fd84b7673b` | clean |
| 11 | [#109](https://github.com/tantalum666/FYP/pull/109) | `cursor/skill-schedule-be49` | `531426bb13868d85db211ef8df2fe1a25498a538` | clean |
| 12 | [#110](https://github.com/tantalum666/FYP/pull/110) | `cursor/staple-purchase-card-ffeb` | `3313dc2d2c3ac8e9c6668326dee4c63678d65f54` | clean |
| 13 | [#111](https://github.com/tantalum666/FYP/pull/111) | `cursor/source-briefs-fa6c` | `9dec212fb5fc004aa6ff2b2336786cce36f644a2` | clean |
| 14 | [#112](https://github.com/tantalum666/FYP/pull/112) | `cursor/held-choices-2645` | `1e32628e706e5a6a901f4c11fc4714646f42de8a` | one import in `runtime.py` |
| 15 | [#114](https://github.com/tantalum666/FYP/pull/114) | `cursor/conversation-next-step-159d` | `7622ed7e0c50a15d64e8fdb096cf7d24063e8fe8` | one hunk in `text_ai.py` |
| 16 | [#115](https://github.com/tantalum666/FYP/pull/115) | `cursor/open-time-conversation-e110` | `022082c4931ffda842fb368d9d573667a0e60158` | clean |
| 17 | [#116](https://github.com/tantalum666/FYP/pull/116) | `cursor/meeting-prep-f16d` | `0a8d4975bb2ace699bdb1ce9061bb4e129673054` | clean |

Stacks, unchanged: #95 is an ancestor of #96, #96 of #99, #102 of #103, #104 of #105, #108 of #109. #114, #115, and #116 each sit directly on `855e60ee`. They do not edit `handoff.md`, `AGENTS.md`, `decision-log.md`, `work-log.md`, `START_HERE_NEXT_CHAT.md`, `product.md`, or `runtime.py`.

## Living-doc rule

Use the rule in the 11 November guide. `decision-log.md` and `work-log.md` append: keep every new `##` section from both sides, the section already on the branch first. `handoff.md` and `START_HERE_NEXT_CHAT.md` are rewritten by several slices. Keep the folder-job clock paragraph, the 7 November live-evaluation body (Actual results, Runtime and recovery, closed USD1 ledger, Pi source `d40457fe`, PR94), and each incoming slice. Do not accept a deletion of that live-evaluation body when a rewrite only conflicts at the opening.

This replay’s marker counts, after that keep-both resolution:

| Step | Files (hunks) |
| --- | --- |
| 2 #95 | `START_HERE_NEXT_CHAT.md` (1), `decision-log.md` (1), `handoff.md` (1; the 7 November `## Actual results` body was restored from the branch side), `work-log.md` (1) |
| 3 #96 | `START_HERE_NEXT_CHAT.md` (1), `handoff.md` (2). `decision-log.md` and `work-log.md` auto-merged |
| 4 #99 | `START_HERE_NEXT_CHAT.md` (1), `handoff.md` (2). `decision-log.md` and `work-log.md` auto-merged |
| 5 #101 | `AGENTS.md` (1), `START_HERE_NEXT_CHAT.md` (1), `decision-log.md` (1), `handoff.md` (3), `work-log.md` (1) |
| 6 #102 | `START_HERE_NEXT_CHAT.md` (1), `decision-log.md` (1), `handoff.md` (2), `work-log.md` (1). `product.md` and the research index auto-merged |
| 7 #103 | `handoff.md` (1) |
| 8–13 | no markers |
| 14 #112 | `desk-companion/backend/desk/runtime.py` (1), below |

`AGENTS.md` after step 5 is one HTML comment. #102 and #103 do not edit that banner, so it was not replaced. It names the second continue (stacked on #96 and #95) and offline owner takeover, and it still says a live JD login is not done. The clock, memory follow-up, and morning check-in stay in the handoff and decision log from their own slices.

## Code that must survive the fourteen

Unchanged from the 11 November guide, and still true after steps 15–17 because those three pulls do not edit `runtime.py`, `app.py`, or `exchange.py`.

`Runtime.tick`:

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

`saved_skills.release_due(conn)` stays inside `RoutineService.tick`. Constructors still include `memory_followups`, `trips`, `saved_skills`, `purchase_cards`, `source_briefs`, and `held_choices`. Route order is unchanged: memory follow-ups after memory, held choices after goals, saved skills after digest, source briefs after sources, purchase cards after Google and before mailbox, trip routes after offline calendar. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` stay. `SCHEMA_VERSION` stays 3.

### 14. #112 — one import

```python
from .goals import GoalService
from .saved_skills import SavedSkillService
from .held_choices import HeldChoiceService
```

Keep both imports. The constructors and `app.py` auto-merged.

## Conversation intents

There is no separate intent registry. The router is the call order in `AssistantService._local_message` and `TextAssistant`. After steps 15–17 all three new kinds are present, plus the existing local parsers (memory, goals, recall, file commands, task note, calendar list, Work).

| Kind | Module | Whole-message matcher |
| --- | --- | --- |
| `next_step` | `desk/next_step.py` | `asks_next_step` |
| `open_time` | `desk/open_time.py` | `parse_ask` |
| `meeting_prep` | `desk/meeting_prep.py` | `asks_meeting_prep` → `"tomorrow"` or `"next"` |
| calendar list | `assistant.py` | keyword search, then `query_period` |
| Work | `conversation_work.py` | closed follow-up, continue, and goal-change lists |

### Where each call sits

Local path, `AssistantService._local_message`, top to bottom:

1. `next_step_turn` — before a selected task becomes a progress note.
2. Memory, goals, recall.
3. Save-to-folder, editor preview, save note.
4. `meeting_prep.answer_meeting_prep` — before the word “meeting” is a calendar list.
5. `open_time_turn` — before `task_message` and before that same calendar list.
6. `task_message`, posture, then the calendar list.

Provider path:

- `TextAssistant._scoped_message`: `conversation_work.turn(payload, key, principal, conversation=conversation)` first. If that returns None, `next_step_turn`. The `conversation=` argument is the one already on the combined tree from #95/#96. Do not drop it when taking #114’s call.
- `TextAssistant._message`: memory, goals, recall, then `open_time_turn`, then `maybe_extract`, then `meeting_prep.answer_meeting_prep`, then the model.
- `maybe_extract` returns None immediately when `asks_meeting_prep` matches, so a meeting question is not sent for extraction.

Imports: `from .open_time import answer_open_time` sits before `owner_lookup` in `assistant.py`. `from .next_step import answer_next_step` sits next to the recall import. Meeting prep is a local import inside the two functions. None of the three inserts a line after `from .goals import GoalService` in `runtime.py`.

### These phrases do not shadow each other

Checked by calling the real matchers on the combined tree. A phrase is in at most one of `next_step`, `open_time`, and `meeting_prep`. The calendar keyword search also matches the free/prep sentences, so those two calls have to stay before the calendar list. “What should I do next?” does not contain a calendar keyword; it has to stay before the final clarify, which it does, at the start of `_local_message` and in `_scoped_message`.

| Phrase | Who answers |
| --- | --- |
| What is on tomorrow? / 明天的行程 / 今天的行程 / 下周的日程 | calendar list |
| When am I free tomorrow? / Am I free tomorrow? / 我明天什么时候有空？ / 明天有空吗 / 明天下午有空吗 | `open_time` |
| When am I free next week? | calendar list. #115 leaves this sentence out of `parse_ask` on purpose |
| Prep me for tomorrow's meeting / 明天的会要准备什么 / 明天的会议要准备什么？ | `meeting_prep` tomorrow |
| Prep me for my next meeting / 下一场会要准备什么 / 下一场会议要准备什么 / 开会前我要准备什么 | `meeting_prep` next |
| What should I do next? / what's next / next step / 接下来做什么？ / 我该做什么 / 我现在该做什么 / 下一步是什么 / 下一步做什么 / 现在做什么 | `next_step` |
| What should I know before my next meeting? / Please brief me before my next meeting. | `meeting_prep` next, not `next_step` |

Work follow-up, Work continue, goal-change, and recall do not match any row above. “What should I do tomorrow at 15:00?” is not a next step; the existing calendar keyword still sees “tomorrow”.

The local path runs meeting prep before open time. The provider path runs open time before meeting prep. The sets are disjoint, so both orders answer the rows above the same way. Do not reorder them in front of the calendar list.

### Starters and copy keys

There is no shared i18n dictionary. Each chip is a `t(english, chinese)` pair. The English strings are the React keys and they do not repeat:

- `What is on today?` / 今天的行程
- `What should I do next?` / 接下来做什么？
- `What is on next week?` / 下周的日程
- `When am I free tomorrow?` / 我明天什么时候有空？
- `Prep me for my next meeting` / 下一场会要准备什么 (its own button, not inside that array)

Reply labels, also unique pairs, and unique CSS classes:

- kind `next_step`: “Next step” / 下一步, `.assistant-next-step-label`, before the reply paragraph
- kind `open_time`: “Open on the saved calendar” / 日历上的空档, `.assistant-open-time`, after the paragraph. The turn stores `openTime` from `result.open_time`
- kind `meeting_prep`: “Next meeting” / 下一场会议, `.assistant-meeting-prep-label`, after the job card

The help list has the same three questions and does not reuse an English string for a different Chinese line.

### 15. #114 — one hunk in `text_ai.py`

`assistant.py` and `AssistantPanel.tsx` auto-merged. The only marker was in `_scoped_message`, where both sides edit the line after “An explicit goal change is owner authority.”

Keep the combined call, then #114’s question:

```python
admitted = self.runtime.conversation_work.turn(
    payload, key, principal, conversation=conversation
)
stepped = None
if cached is None and admitted is None:
    stepped = self.runtime.assistant.next_step_turn(
        payload, owner=principal is None or principal.get("kind") == "owner"
    )
```

The `elif stepped is not None` branch that stores the reply auto-merged and must stay. `next_step_turn` at the start of `_local_message` auto-merged and must stay.

### 16. #115 — clean

No markers. Confirmed on the combined tree: `open_time_turn` is after the file commands and before `task_message`; in `_message` it is after `recall_turn` and before `maybe_extract`. The starter is appended after “What is on next week?”. The open-time label is after the reply paragraph. `assistantTypes.ts` gained `open_time` with no marker.

### 17. #116 — clean

No markers. Confirmed: `answer_meeting_prep` in `_local_message` is after the save-note command and before `open_time_turn` and the calendar list. In `_message` it is after `maybe_extract` and before the model. `maybe_extract` still returns None when `asks_meeting_prep` matches. The prep button is a sibling of the starter array. The “Next meeting” label is after the job card.

## Combined tests

Run on the combined tree after step 17, before the #97 dry merge. No paid provider call. No fix was committed to any pull-request branch. Interpreter: CPython 3.12.3. Pytest 9.1.1. Ruff 0.16.9.

Backend, from `desk-companion/`:

```sh
export PYTHONPATH="$PWD:$PWD/backend"
uv run --no-sync pytest -q --tb=line
```

Result: **2168 passed, 1 failed**, 529.81s. The only failure is `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]`. `test_restart_runs_only_the_approved_folder_job` is not in the failure list. Two warnings, both the same kind as the 11 November run: Starlette/`httpx` deprecation in `TestClient`, and an empty `pytest.raises` match. The 11 November count before these three pulls was 2139 passed and 1 failed. The extra 29 passes are the next-step, open-time, and meeting-prep tests. No new failure appeared.

Frontend, from `desk-companion/frontend/`:

```sh
npm test
```

Result: **351 passed, 0 failed**, 0 skipped, about 8.1s. The 11 November count was 348. The three additional passes are `conversation-next-step.test.ts`, `open-time.test.ts`, and `meeting-prep.test.ts`.

Ruff, from `desk-companion/`:

```sh
uv run --no-sync ruff check
```

Result: all checks passed.

Typecheck, from `desk-companion/frontend/`:

```sh
npx tsc --noEmit
```

Result: exit 0, no diagnostics.

## Fixes pushed

None. The only failing test is the known public-unicast case. The three new intents do not shadow the phrases above, and the combined tree did not add a failure that belongs in #114, #115, or #116.

## Dry merge of #97

After step 17, `git merge --no-commit --no-ff origin/codex/alice-home-wake-20261107` (`ebf6d917`) conflicted. The merge was aborted. #97’s branch was not updated and was not pushed.

`assistant.py`, `runtime.py`, `app.py`, and `assistant-minimal.css` auto-merged with no markers. On that dry merge the required calls were still present: `next_step_turn` at the start of `_local_message`, `answer_meeting_prep` before `open_time_turn`, both before the calendar list, and the three CSS classes. `Runtime.tick` still had the quiet-release order above, and it also constructed `MicrosoftApps` and `OutboundMail`. Re-read those files when #97 is actually merged.

### Code conflicts

`desk-companion/backend/desk/text_ai.py`, one hunk, in `_message` between recall and `maybe_extract`.

Ours inserts `open_time_turn` under `if turn is None`. Theirs changes the following condition from `if turn is None` to `if turn is None and not has_files`, so a message that carries attachments is not parsed as a local question. `meeting_prep` auto-merged after the marker and still runs when `turn is None`. `next_step_turn` in `_scoped_message` auto-merged and still runs only when Work returned None. #97’s `attachments.select` and the `attachment_ids` fingerprint pop auto-merged.

Resolve the hunk as:

```python
if turn is None and not has_files:
    turn = self.runtime.assistant.open_time_turn(payload, owner=allow_memory)
if turn is None and not has_files:
    turn = self.maybe_extract(payload, key, allow_memory=allow_memory)
if turn is None and not has_files:
    from . import meeting_prep

    turn = meeting_prep.answer_meeting_prep(
        self.runtime, payload, owner=allow_memory
    )
```

The third `not has_files` is the same guard #97 already uses for memory, goals, recall, and extraction. Without it, “Prep me for my next meeting” plus an attachment would skip the files. `asks_meeting_prep` inside `maybe_extract` stays.

`desk-companion/frontend/src/workspace/AssistantPanel.tsx`, four hunks:

| Hunk | Ours | Theirs | Keep |
| --- | --- | --- | --- |
| Turn state | inline array with `openTime?` | `useState<ConversationTurn[]>([])` | `ConversationTurn[]`. Add `openTime?: Reply["open_time"]` on `ConversationTurn` in `conversationTranscript.ts` |
| `showHttpReply` | stores `openTime: result.open_time` | stores `files` and calls `chatFiles.sent` | #97’s file handling, and also `openTime: result.open_time` on the assistant turn |
| Welcome | starter chips, including the three new questions | deletes the welcome block | Do not restore the welcome. The typed phrases still work. The help list auto-merged and already lists all three questions |
| Turn body | next-step label, open-time block, meeting label, older immersive slice | file chips, #97’s immersive latest line | #97’s file chips and immersive line. Put the next-step label before the paragraph, the open-time block after the paragraph, and the meeting label after the job card |

The three `t()` pairs and the three CSS classes do not collide with #97’s strings. The help-list `<li>` items were outside the markers.

### Documentation conflicts

Same files as the 11 November dry merge, with the same keep-both rule. Hunk counts on this tree:

| File | Hunks | What collided |
| --- | --- | --- |
| `AGENTS.md` | 1 | Banner. Keep one comment that still names the Grok slices through takeover and the unicast failure, and #97’s 9 November composer / A3 line |
| `START_HERE_NEXT_CHAT.md` | 1 | Keep the combined continuation and #97’s checkout note. Do not revert takeover, Work, memory, trip quotes, skills, purchase cards, source briefs, held choices, next step, open time, or meeting prep to “not started” |
| `decision-log.md` | 1 | Append. Keep every Grok `##` and every #97 `##` |
| `work-log.md` | 1 | Same append |
| `handoff.md` | 2 | Keep the 7 November live-evaluation body. Do not accept its deletion. Keep #97’s current-software sections. One next step must still say a live JD pass needs its own scoped session, and must keep #97’s own next step |
| `product.md` | 2 | Opening: keep the takeover sentence and #97’s composer / Alice-home paragraphs. Table: keep #97’s 网页／手机 text and the combined 记忆／人格 text |
| `research/personal-agent-research-index.md` | 1 | Opening status only. Keep #97’s 9 November and 8 November paragraphs and the 7 November live-update paragraph |
| `desk-companion/docs/conversation-work.md` | 1 | Keep #97’s `## Current interface boundary — 8 November 2026`. Keep the 10 November paragraph that status asks re-show, one explicit continue advances once, and a later explicit ask takes one more step only while the run is open. #97’s 6 November paragraph does not replace those later sentences |

## Handoff for Codex

Grok Bot completed this check. Merge the seventeen heads in the order above with a normal merge and no rebase. Steps 1–14 are the 11 November order, including the one `runtime.py` import at #112 (keep both `SavedSkillService` and `HeldChoiceService`). #114’s only code conflict is the `conversation_work.turn` call in `text_ai.py`: keep `conversation=conversation` and keep `next_step_turn` when Work returns None. #115 and #116 auto-merge; do not drop `open_time_turn` or `answer_meeting_prep`, and do not move either of them below the calendar list.

The four questions stay on different parsers, in English and in Chinese: “what is on tomorrow” is the calendar list, “when am I free tomorrow” is open time, “prep me for tomorrow's meeting” is meeting prep, “what should I do next” is next step. “When am I free next week?” stays the calendar list. Starter strings, reply labels, and CSS classes do not collide.

Combined local suites after the seventeen, before #97: **2168 passed / 1 failed** (the known `::ffff:93.184.216.34` unicast test), **351 frontend passed**, ruff clean, `tsc --noEmit` clean. Nothing was pushed to a Grok or Codex branch except this docs pull request. The throwaway integration branch was not pushed.

#97 dry-merges with the documentation conflicts above plus two code files: `text_ai.py` (keep open time and meeting prep behind `not has_files`) and `AssistantPanel.tsx` (keep #97’s turn type, files, and deleted welcome; keep the three labels and `openTime`). Abort unless you are actually merging it.
