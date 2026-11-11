> HISTORICAL contributor integration rehearsal. The reviewed combined implementation, repairs and actual validation are recorded in [11 November QA](../../output/qa/2026-11-11-grok-review/verification.md). Historical instructions to keep failures or avoid #97 do not govern the current owner-authorized integration.

# Merge guide for open Grok Bot pull requests — 11 November 2026, waiting and reply

Completed by Grok Bot via a Cursor cloud agent on 11 November 2026, for Codex. This is a merge plan, not a merge. Codex merges. Do not modify PR #97 or any Codex branch. Do not force-push. Do not rebase these branches. No paid model call was made while checking this plan.

This pull request only adds this guide. It does not edit [the conversation-intent guide](https://github.com/tantalum666/FYP/pull/117) (`desk-companion/docs/merge-guide-2026-11-11b.md`, which is not on `main` yet), `handoff.md`, `work-log.md`, `decision-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `product.md`, or the research index. Merge this guide whenever; it does not change those conflicts against current `main`.

`origin/main` at the check was `855e60ee9f413de84474e3e0b9975b9b9a3d5fbc`. The seventeen heads in [PR #117](https://github.com/tantalum666/FYP/pull/117) had not moved. The two new heads are the conversation intents opened on that same `main` after that guide.

The check used a local throwaway branch, `cursor/merge-integration-throwaway-7853`, created from that `main`. Each head below was brought in with ordinary `git merge --no-ff` (no rebase, no squash). That branch was not pushed and is not a pull request. None of #98, #95, #96, #99, #101, #102, #103, #104, #105, #108, #109, #110, #111, #112, #114, #115, #116, #118, or #119 were modified. No fix was pushed. #97 was dry-merged and the merge was aborted. Nothing was pushed to `codex/alice-home-wake-20261107`.

## Do not merge from this file until Codex is merging

- **#97** `codex/alice-home-wake-20261107` at `ebf6d91751ff69f6acec0813f7eb69a1ed53dc5d` stays a Codex pull request. The dry merge is listed at the end. It was aborted.
- Drafts #73, #87, and #88 stay untouched. #94 stays merged.
- Do not reopen a paid round. The USD1 live ledger stays closed.
- `test_public_unicast[::ffff:93.184.216.34]` still fails on this Python 3.12. Leave it.
- #98 still fixes `test_restart_runs_only_the_approved_folder_job`. On this combined tree that test passed.

## Order

Merge each **head** into `main` with a merge commit, top to bottom. Do not use “Rebase and merge”. Stack children contain their parents, so merge the parent head into `main` first, then merge the child head into `main`.

Steps 1–17 are the order already checked in PR #117, re-run here at the same tips, with that guide’s resolutions. Steps 18–19 are the new conversation intents, in the order they were opened: waiting on, then reply owed.

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
| 18 | [#118](https://github.com/tantalum666/FYP/pull/118) | `cursor/waiting-on-conversation-eae3` | `11ed2f5e3ee7e15ce7e96050abbe7b32c768ed6b` | one help-list hunk |
| 19 | [#119](https://github.com/tantalum666/FYP/pull/119) | `cursor/reply-owed-conversation-6a62` | `40fcb6a0debf51fe222e4f173e9d9a718ea2afc1` | two CSS hunks |

Stacks, unchanged: #95 is an ancestor of #96, #96 of #99, #102 of #103, #104 of #105, #108 of #109. #114, #115, #116, #118, and #119 each sit directly on `855e60ee`. #118 and #119 do not edit `handoff.md`, `AGENTS.md`, `decision-log.md`, `work-log.md`, `START_HERE_NEXT_CHAT.md`, `product.md`, or `runtime.py`.

Steps 1–17 reused the resolutions in the 11 November b guide. Living-doc conflicts stayed append-or-restore. The only code markers in those steps were the same two: keep both `SavedSkillService` and `HeldChoiceService` in `runtime.py` at #112, and keep `conversation=conversation` plus `next_step_turn` in `text_ai.py` at #114. #115 and #116 auto-merged. `open_time_turn` stays before the calendar list. `answer_meeting_prep` stays before `open_time_turn`.

## Where the two new calls sit

There is still no separate intent registry. The router is the call order.

Local path, `AssistantService._local_message`, after step 19:

1. `next_step_turn`
2. Memory, goals, recall.
3. `answer_waiting` — after recall, before the save-to-folder command.
4. Save-to-folder, then editor preview.
5. `answer_reply_owed` — after the editor-preview return, before the save-note command.
6. `answer_meeting_prep`, then `open_time_turn`, then `task_message`, then the calendar list.

Provider path, `TextAssistant._message`, after the scoped Work and next-step calls:

1. `answer_reply_owed` first, before `memory_turn`. The existing `if turn is not None` return stores it.
2. Memory, goals, recall, `open_time_turn`, `maybe_extract`, `answer_meeting_prep`.
3. If any of those returned a turn, store it and return.
4. `answer_waiting`, then `from .assistant import TOOLS`.

`maybe_extract` still returns None for `asks_meeting_prep` and for `is_waiting_message`. Both new answers return None when the message carries `attachment_ids`. `我要…` stays a goal: `parse_reply_owed` does not match it, and `goals.turn` does.

## Phrases do not shadow

Checked on the combined tree by calling the parsers, not by a model. A calendar keyword on a sentence does not mean the calendar list wins. `answer_meeting_prep` and `open_time_turn` run before that list.

| Phrase | Parser |
| --- | --- |
| What am I waiting on? / 我在等什么 | waiting ask |
| Who do I need to reply to? / 我该回复谁 | reply ask |
| What should I do next? / 接下来做什么？ | next step |
| What is on tomorrow? / 明天的行程 | calendar list only |
| I'm waiting on Sam for the budget / 我在等 Sam 的预算 | waiting record |
| I need to reply to Sam about the venue / 我该回复 Sam，关于场地 | reply record |
| 我要回复 Sam，关于场地 | goal, not a reply |
| When am I free tomorrow? / 我明天什么时候有空？ | open time |
| When am I free next week? | calendar list |
| Prep me for my next meeting / 下一场会要准备什么 | meeting prep |
| Prep me for tomorrow's meeting / 明天的会要准备什么 | meeting prep |

No asked phrase matched a second intent parser. There is no shared i18n catalog. `t(english, chinese)` is the pair at the call site. The four questions use different English strings and different Chinese strings. Welcome chips stay the next-step, open-time, and meeting-prep questions. “What am I waiting on?” is the button above the composer (`WaitingAskButton`), plus one help-list item. “Who do I need to reply to?” is the help-page button (`ReplyOwedAsk`) and the list item between “What is on next week?” and “Track: …”. The “Reply owed” / “待回复” label is after the turn list, not inside the turn body.

## 18. #118 — one help-list hunk

`assistant.py` and `text_ai.py` auto-merged. `answer_waiting` landed after `recall_turn` and before the save-to-folder command. In `_message` it landed after the memory/goal/recall/open-time/extract/meeting-prep return and before `from .assistant import TOOLS`. `is_waiting_message` landed inside `maybe_extract`. `WaitingAskButton` landed above the composer, outside the welcome chips.

The only marker was the last help-list item in `AssistantPanel.tsx`. Keep both:

```tsx
<li>{t("When am I free tomorrow?", "我明天什么时候有空？")}</li>
<li>{t("What am I waiting on?", "我在等什么")}</li>
```

## 19. #119 — two CSS hunks

`assistant.py`, `text_ai.py`, and `AssistantPanel.tsx` auto-merged. `answer_reply_owed` landed after the editor-preview return and before the save-note command. In `_message` it landed before `memory_turn`. The help button and the “Who do I need to reply to?” / “我该回复谁” list item landed between “What is on next week?” and “Track: …”. The waiting list item stayed. The “Reply owed” / “待回复” label landed after the turn list.

`assistant-minimal.css` had two markers because both sides added a rule in the same place and git shared the font lines. Keep both complete rules. Do not leave the font-size on only one of them.

```css
.assistant-open-time {
  margin: 4px 0 0;
}
.assistant-open-time-label {
  margin: 0 0 2px;
  font-size: 12px;
  letter-spacing: 0.04em;
  color: #5c6578;
}
.assistant-open-time ul {
  margin: 0;
  padding-left: 18px;
}
.assistant-reply-owed-label {
  margin: 4px 6px 0;
  font-size: 12px;
  letter-spacing: 0.04em;
  color: #5c6578;
}
.assistant-reply-owed-ask {
  margin: 0 0 12px;
}
```

`.assistant-waiting-ask` auto-merged and stays.

## Combined tests

Run on the combined tree after step 19, before the #97 dry merge. No paid provider call. No fix was committed to any pull-request branch. Interpreter: CPython 3.12.3. Pytest 9.1.1. Ruff 0.16.9.

Backend, from `desk-companion/`:

```sh
export PYTHONPATH="$PWD:$PWD/backend"
uv run --no-sync pytest -q --tb=line
```

Result: **2235 passed, 3 failed**, 540.11s. Failures:

- `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]` — the known failure. Leave it.
- `tests/test_waiting_on.py::test_older_phrases_still_reach_their_own_parsers`
- `tests/test_reply_owed.py::test_older_phrases_still_reach_their_own_parsers`

Both new failures stop on `assert free["kind"] == "brief"` for “When am I free tomorrow?”. The combined tree returns `open_time`. That is #115’s phrase, and #117 already required it to stay open time. Those tests were written on `main` before #114–#116, so they still use the old fallback: `brief` for that sentence, and `clarify` for “Prep me for my next meeting”, “What should I do next?”, and, in #119, “What am I waiting on?”. Those later lines were not reached. On this tree those kinds are `meeting_prep`, `next_step`, and `waiting`.

This is not a router defect. Do not send “When am I free tomorrow?” back to the calendar list to make the old assertion pass. Do not change the assertions on #118 or #119 by themselves: those branches do not contain open time, meeting prep, or next step, and the same tests pass there. When Codex merges #118 and #119 after steps 15–17, update those two tests so each phrase expects its own kind. “What is on today?” stays `brief`. “我要回复 Sam，关于场地” stays a goal.

`test_restart_runs_only_the_approved_folder_job` is not in the failure list. Two warnings, the same pair as the 11 November b run: Starlette/`httpx` deprecation in `TestClient`, and an empty `pytest.raises` match. The count before these two pulls was 2168 passed and 1 failed.

Frontend, from `desk-companion/frontend/`:

```sh
npm test
```

Result: **354 passed, 0 failed**, 0 skipped, about 8.5s. The 11 November b count was 351. The three additional passes are the two tests in `waiting-ask.test.ts` and the one test in `reply-owed.test.ts`.

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

None. The product routers do not shadow the phrases above. The two new pytest failures are stale assertions in #118 and #119, not a combined-tree behavior bug. Nothing was committed to those branches.

## Dry merge of #97

After step 19, `git merge --no-commit --no-ff origin/codex/alice-home-wake-20261107` (`ebf6d917`) conflicted. The merge was aborted. #97’s branch was not updated and was not pushed.

#118 and #119 do not edit the living docs, so they do not add a documentation file to the #117 dry-merge list. The same files conflicted: `AGENTS.md` (1), `START_HERE_NEXT_CHAT.md` (1), `decision-log.md` (1), `work-log.md` (1), `handoff.md` (3 on this replay’s handoff text; #117 recorded 2), `product.md` (2), `research/personal-agent-research-index.md` (1), `desk-companion/docs/conversation-work.md` (1). Use the keep-both rule already written in #117. The extra handoff marker is this replay’s handoff wording, not a new edit from #118 or #119.

`assistant.py`, `runtime.py`, `app.py`, and `assistant-minimal.css` auto-merged, as they did in #117. `tasks.py` also auto-merged, with no marker. `.assistant-waiting-ask` and `.assistant-reply-owed-label` were still present after that auto-merge.

### New code conflicts relative to #117

#117 recorded one hunk in `text_ai.py` and four hunks in `AssistantPanel.tsx`. This dry merge had two and five.

`desk-companion/backend/desk/text_ai.py`:

| Hunk | What is new |
| --- | --- |
| 1 | New. #119 inserts `answer_reply_owed` on the line #97 changes to `has_files` plus `memory_turn`. |
| 2 | The same open-time hunk as #117: ours uses `if turn is None`, theirs uses `if turn is None and not has_files`. |

`answer_waiting` and #97’s `attachments.context` auto-merged. `answer_waiting` stays after the early return and before `TOOLS`. The `if turn is None` in front of `answer_meeting_prep` is still outside the marker. Give it `not has_files` by hand, as #117 already says.

Resolve the new hunk by leaving the reply call where #119 put it, then applying #97’s guard to the older chain:

```python
from .reply_owed import answer_reply_owed

has_files = bool(conversation and conversation.attachment_ids)
turn = answer_reply_owed(
    self.runtime, payload, key, owner=allow_memory, conversation=conversation
)
if turn is None and not has_files:
    turn = self.runtime.assistant.memory_turn(payload, key, allow_memory=allow_memory)
if turn is None and not has_files:
    turn = self.runtime.goals.turn(payload, key, allow=allow_memory)
if turn is None and not has_files:
    turn = self.runtime.assistant.recall_turn(
        payload, key, allow_memory=allow_memory, conversation=conversation
    )
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

`answer_reply_owed` and `answer_waiting` already return None when `attachment_ids` is non-empty. Do not move either call below the calendar list.

`desk-companion/frontend/src/workspace/AssistantPanel.tsx`:

| Hunk | Compared with #117 |
| --- | --- |
| Turn state | Same. Keep `ConversationTurn[]` and `openTime` on that type. |
| `showHttpReply` | Same. Keep #97’s files and also `openTime: result.open_time`. |
| Welcome | Same. Do not restore the welcome. Typed phrases still work. |
| Turn body | Same conflict, plus the reply-owed label that now sits after the turn list on our side. Keep #97’s file chips and immersive line. Put the next-step label before the paragraph, the open-time block after the paragraph, and the meeting label after the job card. Put “Reply owed” / “待回复” after the mapped turns, not inside each turn. |
| Composer | New. Ours wraps the form in a fragment and renders `WaitingAskButton` above it. Theirs replaces the form with the file-drag form, `ComposerFiles`, and paste handling. Keep the waiting button above the composer, and keep #97’s form. |

The help-list items for waiting and reply were outside the markers. Their `t()` pairs do not collide with #97’s strings.

## Handoff for Codex

Grok Bot completed this check. Merge the nineteen heads in the order above with a normal merge and no rebase. Steps 1–17 are the 11 November b order, including the `runtime.py` import at #112 and the `text_ai.py` call at #114. #118 auto-merges the Python calls. Keep both help-list items: “When am I free tomorrow?” and “What am I waiting on?”. #119 auto-merges the Python calls and the panel. Keep both CSS blocks: open time and reply owed. Do not drop `answer_waiting` or `answer_reply_owed`, and do not move either of them below the calendar list.

“What am I waiting on?” is only waiting. “Who do I need to reply to?” is only reply owed. “What should I do next?” is only next step. “What is on tomorrow?” is only the calendar list. “I'm waiting on Sam for the budget” records a waiting reason. “I need to reply to Sam about the venue” records a reply. `我要…` stays a goal. The same split holds for the Chinese sentences in the table above.

Combined local suites after the nineteen, before #97: **2235 passed / 3 failed**. One failure is the known `::ffff:93.184.216.34` unicast test. The other two are `test_older_phrases_still_reach_their_own_parsers` in #118 and #119, which still expect the pre-#115 calendar kind for “When am I free tomorrow?”. Update those assertions at merge time. Do not change the routers to satisfy them. **354 frontend passed**, ruff clean, `tsc --noEmit` clean. Nothing was pushed to a Grok or Codex branch except this docs pull request. The throwaway integration branch was not pushed.

#97 dry-merges with the documentation conflicts from #117, plus one new `text_ai.py` hunk (keep `answer_reply_owed`, then `not has_files`) and one new `AssistantPanel.tsx` hunk (keep the waiting button and #97’s file form). Abort unless you are actually merging it.
