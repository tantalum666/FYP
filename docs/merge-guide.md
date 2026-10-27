# Merge guide for open Grok Bot pull requests

Completed by Grok Bot via a Cursor cloud agent on 2026-10-27. This is a merge plan, not a merge. Codex merges. Do not merge PR #4, #5, #15, #16, or #19. Those are outside this set (#19 is the hardware procurement review; #4/#5/#15/#16 stay unmerged).

Tips below were the branch tips used for `git merge-tree --write-tree --name-only`. A later push to the same branch can change a conflict. Re-run merge-tree if a tip moved.

`origin/main` at the check was `46ac167`.

## How this order was checked

The order below was simulated with `git merge-tree` from `origin/main`, one PR at a time, parent before child. A step marked **clean** produced no conflict against the tree of the earlier steps. A step marked **conflict** names the files that conflicted at that step.

Do not resolve code conflicts by keeping both sides blindly. That duplicates the model loop in `text_ai.py`, the `Notifier` assignment in `runtime.py`, the reconnect button in `App.tsx`, and the product-table rows. Use the resolutions in this file.

This pull request only adds `docs/merge-guide.md`. It does not edit `handoff.md`, `work-log.md`, `decision-log.md`, or `context.py`. Merge it whenever; it does not change the conflicts below.

## Log files: one rule for every step

`handoff.md`, `work-log.md`, and `decision-log.md` conflict because each pull request appends its own section at the same end of the file. Keep every section. Do not drop one branch's section because another branch's "剩余" still talks about it as future work.

1. Remove the conflict markers.
2. Keep every `##` and `###` heading that appears on either side. If the same heading appears twice, keep the longer copy once.
3. Do not accept a deletion of an earlier section. PR #44's handoff diff deletes `## 回复流`. Restore that section from `origin/cursor/assistant-streaming-c6a1`. The text is quoted in step 15.
4. Keep a single opening `更新：` line. Use the incoming pull request's line. Leave older status as its own `##` sections, not as extra opening lines.
5. PR #24 and PR #30 both replace `## 当前状态与证据`. Keep PR #30's bullets. They already name #21, #22, #24, #25, #27, #28, and #30. Keep the 2026-10-26 archive facts under `## 2026-10-26 仓库归档交接` from PR #20. Do not leave two `## 当前状态与证据` headings.

Sections that must exist when the set is fully merged:

- Handoff: `## 代理循环那一片`, `## 只读查询`, `## 有界计划`, `## 对话质量`, `## 回复流`, `## 真实片段`, `## 检索排序`, `## 2026-10-26 仓库归档交接`, `## 2026-10-27 记忆与主动检查切片`, `## 2026-10-27 通知通道`, `## 2026-10-27 目标`, `## 2026-10-27 档案摘要`, `## 2026-10-27 备份`, `## 2026-10-27 反省`, `## 2026-10-27 空隙建议`, `## 2026-10-27 未完成事项`, `## 2026-10-27 记忆引用`, `## 2026-10-27 别名`, `## 2026-10-27 语气与主动程度`, `## 2026-10-27 对话风格`, `## 2026-10-27 Web Push`.
- Decision log: `## 2026-10-27 软件健康：可复现、CI 与作业动作边界`, `## 2026-10-27 离线演示与安全卫生`, `## 2026-10-27 文字代理循环与工具审计` plus the `### 同日补充` blocks for 工具策略, 只读查询, 有界计划, 对话质量, 网页回复流, 真实文本片段, 检索排序, then `## 2026-10-27 记忆核对与主动检查`, `## 2026-10-27 记忆备份、本机会话清理与确定性核对`, `## 2026-10-27 反省、建议、引用和语气`, `## 2026-10-27 对话里引用已保存事实`, `## 2026-10-27 引用用别名表而不是模型`, `## 2026-10-27 语气、详略和主动程度`, `## 2026-10-27 对话遵守已保存的风格`, `## 2026-10-27 没有空隙时的未完成事项`, `## 2026-10-27 Web Push 默认关闭`.
- Work log: the matching `## 2026-10-27` sections, including `## 2026-10-27｜通知通道`, `## 2026-10-27｜目标与承诺`, `## 2026-10-27｜关系档案`, `## 2026-10-27｜人格与作业备份`, `## 2026-10-27｜每日与每周反省`, `## 2026-10-27｜空隙建议`, `## 2026-10-27｜未完成事项`, `## 2026-10-27｜记忆引用`, `## 2026-10-27｜别名`, `## 2026-10-27｜语气与主动程度`, `## 2026-10-27｜对话风格`, `## 2026-10-27｜Web Push`.

## `context.py`: required result

In this order `desk-companion/backend/desk/context.py` auto-merges. PR #31 adds `profile`, PR #39 adds `memory_citation`, PR #40 adds the `owner_style` import and the `style` key. PR #43 does not edit this file. If a different order produces a conflict, the function must end as:

```python
from .calendar import iso
from .workspace_data import owner_style


def pack_conversation(runtime, task_id=None, *, include_memory=True):
    now = runtime.store.clock()
    tasks = runtime.tasks.listing(include_closed=bool(task_id))
    selected = runtime.tasks.detail(task_id) if task_id else None
    window = runtime.store.snapshot(now, now + timedelta(days=7))
    return {
        "now": iso(now),
        "timezone": tasks["timezone"],
        "memory": runtime.memory.for_model() if include_memory else [],
        "memory_citation": (
            "When an answer uses one saved fact, name the day from that fact's created_at. "
            "Do not invent a day."
            if include_memory
            else ""
        ),
        "profile": runtime.profile.text() if include_memory else "",
        "tasks": tasks["tasks"][:30],
        "more_tasks": len(tasks["tasks"]) > 30,
        "selected_task": selected,
        "calendar": window["occurrences"][:80],
        "style": owner_style(runtime.data.preferences()),
    }
```

## Order

Merge top to bottom. The base column is the pull request's GitHub base. Stack children are merged only after that base is already in `main`, so the GitHub diff stays the child slice while the merge into `main` is what the conflict notes describe.

### 1. Hygiene, still close to `main`

| Step | PR | Tip | Base | Head | At this step |
| --- | --- | --- | --- | --- | --- |
| 1 | [#21](https://github.com/tantalum666/FYP/pull/21) | `a6f6c9d` | `main` | `cursor/desk-ci-repro-2d6c` | clean |
| 2 | [#22](https://github.com/tantalum666/FYP/pull/22) | `4864395` | `main` | `cursor/job-action-registry-2d6c` | clean |
| 3 | [#36](https://github.com/tantalum666/FYP/pull/36) | `a51d86d` | `main` | `cursor/desk-coverage-gaps-2d6c` | clean |
| 4 | [#24](https://github.com/tantalum666/FYP/pull/24) | `49cc5ea` | `main` | `cursor/desk-module-map-2d6c` | clean |
| 5 | [#25](https://github.com/tantalum666/FYP/pull/25) | `a175205` | `main` | `cursor/desk-offline-demo-2d6c` | clean |
| 6 | [#27](https://github.com/tantalum666/FYP/pull/27) | `96a82b3` | `main` | `cursor/desk-frontend-resilience-2d6c` | clean |
| 7 | [#28](https://github.com/tantalum666/FYP/pull/28) | `2902373` | `main` | `cursor/desk-security-hygiene-2d6c` | clean |
| 8 | [#30](https://github.com/tantalum666/FYP/pull/30) | `aca6e4c` | `main` | `cursor/desk-provider-smoke-2d6c` | logs only |
| 9 | [#42](https://github.com/tantalum666/FYP/pull/42) | `b4c2e90` | `main` | `cursor/desk-ops-diagnostics-2d6c` | clean |

What each one is:

1. CI workflow and `scripts/dev.sh` port check via `.venv/bin/python`.
2. Computer-job actions must be in the executor registry.
3. Extra tests around jobs, backup, session, and calendar. Same `computer.py` as #22; it auto-merged after #22. If it conflicts, keep #22's registry rejection and #36's added guards.
4. Module map. Rewrites the top of `handoff.md`. Superseded by #30's status bullets in step 8.
5. Offline demo seed and `DESK_TEXT_PROVIDER=fake`.
6. Owner and device UI distinguish offline, server error, and expired session.
7. Credential files, proxied cookies, uvicorn `--no-access-log`.
8. Skipped-by-default Qwen/Gemini smoke script. No network in CI.
9. Redacted logs, owner diagnostics, local backup trigger.

`scripts/dev.sh` is edited by #21, #25, and #28 and auto-merged. If it conflicts, keep all three edits: `.venv/bin/python` for the port check (#21), `${DESK_RUNTIME_DIR:-.runtime}/credentials.json` (#25), and `--no-access-log` (#28).

Step 8 conflicts only in `handoff.md`, `work-log.md`, and `decision-log.md`. Use the log rule. For the handoff status block, keep #30's bullets rather than #24's shorter copy.

### 2. Agent loop, bottom up

| Step | PR | Tip | Base | Head | At this step |
| --- | --- | --- | --- | --- | --- |
| 10 | [#20](https://github.com/tantalum666/FYP/pull/20) | `f18b218` | `main` | `cursor/agent-loop-tools-c6a1` | logs, and `product.md` is still clean here |
| 11 | [#32](https://github.com/tantalum666/FYP/pull/32) | `f0a29a9` | `cursor/agent-loop-tools-c6a1` | `cursor/read-only-tools-c6a1` | `handoff.md` |
| 12 | [#34](https://github.com/tantalum666/FYP/pull/34) | `ea64a8a` | `cursor/read-only-tools-c6a1` | `cursor/owner-planning-c6a1` | `handoff.md` |
| 13 | [#37](https://github.com/tantalum666/FYP/pull/37) | `941c8ba` | `cursor/owner-planning-c6a1` | `cursor/conversation-harness-c6a1` | `handoff.md` |
| 14 | [#41](https://github.com/tantalum666/FYP/pull/41) | `56abeab` | `cursor/conversation-harness-c6a1` | `cursor/assistant-streaming-c6a1` | `handoff.md` |
| 15 | [#44](https://github.com/tantalum666/FYP/pull/44) | `be5c3f5` | `cursor/assistant-streaming-c6a1` | `cursor/token-streaming-c6a1` | `text_providers.py`, `handoff.md` |
| 16 | [#47](https://github.com/tantalum666/FYP/pull/47) | `1622f56` | `cursor/token-streaming-c6a1` | `cursor/ranked-retrieval-c6a1` | `handoff.md` |

What each one is:

10. Bounded agent loop and one tool policy for text and voice.
11. Owner-scoped search, plate summary, and clock.
12. Bounded owner plan before any draft.
13. Offline conversation harness. Live script stays capped and out of CI.
14. Web reply stream with tool progress. JSON `POST /messages` stays.
15. Real provider text deltas, with a one-shot fallback.
16. Deterministic rank for owner search and `memory_query`. No new dependency.

Step 15, `desk-companion/backend/desk/text_providers.py`: the module docstring gained one sentence on each side. Keep both:

```text
The fake adapter is an offline demonstration. It never opens a network connection.
`deltas` yields text pieces. `complete` remains the one-shot fallback.
```

Step 15, handoff: #44 deletes `## 回复流` and adds `## 真实片段`. Keep both. Restore this section from #41 above `## 真实片段`:

```markdown
## 回复流

- 网页助理发送使用 `POST /api/assistant/messages/stream`。工具开始和结束先到，最终回复再按短段出现。原来的 JSON `POST /messages` 仍在。
- 草稿仍要拥有者批准。工具参数不进流事件。手机原生请求仍走 JSON。
- 契约见 [agent-loop.md](desk-companion/docs/agent-loop.md)。
```

### 3. Memory stack, then its siblings

Spine first. These four after #23 were clean in this order, including `app.py` and `runtime.py`.

| Step | PR | Tip | Base | Head | At this step |
| --- | --- | --- | --- | --- | --- |
| 17 | [#23](https://github.com/tantalum666/FYP/pull/23) | `602c634` | `main` | `cursor/memory-proactivity-b6e4` | logs, `product.md`, `text_ai.py`, `memory.md` |
| 18 | [#26](https://github.com/tantalum666/FYP/pull/26) | `1228d2a` | `cursor/memory-proactivity-b6e4` | `cursor/notification-channels-b6e4` | `App.tsx` |
| 19 | [#29](https://github.com/tantalum666/FYP/pull/29) | `05fd93b` | `cursor/notification-channels-b6e4` | `cursor/goals-commitments-b6e4` | clean |
| 20 | [#31](https://github.com/tantalum666/FYP/pull/31) | `11b24a3` | `cursor/goals-commitments-b6e4` | `cursor/profile-summary-b6e4` | clean |
| 21 | [#33](https://github.com/tantalum666/FYP/pull/33) | `312db65` | `cursor/profile-summary-b6e4` | `cursor/backup-persona-jobs-b6e4` | clean |

What each one is:

17. Owner-reviewed memory consolidation and explained check-ins.
18. Check-ins go through notification channels. No push network yet.
19. Stated goals stay open until the owner confirms they are done.
20. Bounded profile from confirmed memory, injected by `pack_conversation`.
21. Persona text and computer jobs in the business backup.

Step 17, `text_ai.py` imports. Keep both lines:

```python
from .model_provider import HostedTextProvider
from .memory_extract import EXTRACT_INSTRUCTIONS, accept_stated_fact
```

Step 17, `product.md`. Keep one pair of rows, not two:

```markdown
| 事务与助理 | 持久进展、暂停／延后／结束、安静时段、草稿审阅／确认／取消／到期、版本与操作ID；文字与语音共用工具策略、风险级别和拥有者可查看的工具记录 | 模型不能调用确认接口，完成需要真实依据。离线场景不是真实模型效果 |
| 记忆与人格 | 拥有者事实查看／更正／忘掉、重复与同一主题偏好的停用、到期；对话只产生待确认草稿；事实进入业务备份；共用人格；配对显示身份受限 | [记忆契约](desk-companion/docs/memory.md)；不是聊天全文或无限上下文。提供商侧日志无法从本机擦除 |
```

Step 17, `desk-companion/docs/memory.md`. Keep #23's bullets (dedupe, correction history, expiry, extract caps). In the `memory_query` bullet, also keep #47's clause: a query ranks by English words and Chinese character bigrams and does not write. Do not paste the bullet list twice.

Step 18, `desk-companion/frontend/src/App.tsx`. Keep #27's `offlineNotice(...)` call, including `aria-hidden`. Delete the older reconnect `<button>` fragment from #26. Immediately after `offlineNotice`, add the inbox from #26, and keep `import { NoticeInbox } from "./workspace/NoticeInbox"`:

```tsx
        {connection === "offline" &&
          offlineNotice(
            t(
              "Offline. Showing your last loaded calendar.",
              "已离线，当前显示上次读取的日历。",
            ),
            t("Reconnect", "重新连接"),
            refresh,
            <RefreshCw size={14} aria-hidden="true" />,
          )}
        <NoticeInbox t={t} language={language === "zh" ? "zh" : "en"} />
```

`jobs.py` from #33 auto-merged on top of #22. If it conflicts, keep #22's registry check and #33's backup bundle.

### 4. Siblings of the backup branch

None of these depend on each other except where the table says so. The order is the one that was simulated.

| Step | PR | Tip | Base | Head | At this step |
| --- | --- | --- | --- | --- | --- |
| 22 | [#40](https://github.com/tantalum666/FYP/pull/40) | `9586379` | `cursor/backup-persona-jobs-b6e4` | `cursor/owner-style-b6e4` | clean, including `context.py` |
| 23 | [#43](https://github.com/tantalum666/FYP/pull/43) | `c815813` | `cursor/owner-style-b6e4` | `cursor/prompt-style-b6e4` | `text_ai.py`, `voice.py` |
| 24 | [#39](https://github.com/tantalum666/FYP/pull/39) | `adba5e3` | `cursor/backup-persona-jobs-b6e4` | `cursor/memory-recall-b6e4` | logs, `assistant.py` |
| 25 | [#45](https://github.com/tantalum666/FYP/pull/45) | `1d353f6` | `cursor/memory-recall-b6e4` | `cursor/recall-aliases-b6e4` | clean |
| 26 | [#38](https://github.com/tantalum666/FYP/pull/38) | `a395b6b` | `cursor/backup-persona-jobs-b6e4` | `cursor/free-moment-b6e4` | logs |
| 27 | [#48](https://github.com/tantalum666/FYP/pull/48) | `ad9a449` | `cursor/free-moment-b6e4` | `cursor/open-loops-b6e4` | `decision-log.md` |
| 28 | [#35](https://github.com/tantalum666/FYP/pull/35) | `6a24fc4` | `cursor/backup-persona-jobs-b6e4` | `cursor/daily-digest-b6e4` | logs, `runtime.py`, `MemoryPanel.tsx` |
| 29 | [#46](https://github.com/tantalum666/FYP/pull/46) | `24a5cc3` | `cursor/backup-persona-jobs-b6e4` | `cursor/web-push-b6e4` | logs, `runtime.py`, `operator-guide.md`, `knowledge.test.ts` |

What each one is:

22. Settings page for tone, verbosity, and proactivity. Chat does not write them.
23. Chat honors those three settings. Prompt layer plus offline Chinese and English checks.
24. Recall cites the day the fact was saved. "Forget that" is a delete draft.
25. Owner-extendable alias table so 茶 and tea match. No model call.
26. One suggestion when a timed event leaves a 30–180 minute gap.
27. One open loop when no timed event is in that window. Same dismiss and pause rules, counted per kind.
28. Daily and weekly counts from saved records. Spoken text is counts only.
29. Web Push behind `DESK_WEB_PUSH`. Default off. Tests use a fake sender.

Step 23, `text_ai.py`. #20 already replaced the old generate loop with `AgentLoop`. #43 still contains that old loop because it branched before the agent loop. Keep one path:

- Imports: `AgentLoop`, `HostedTextProvider`, `EXTRACT_INSTRUCTIONS` / `accept_stated_fact`, `reply_stream`, `token_stream`, `present` / `render_prompt`, `tool_visible`. Drop `text_system` and `followup_system` once both call sites use `render_prompt`.
- `message` keeps `on_event=None`.
- Early turns stay in this order: `memory_turn`, `goals.turn`, `recall_turn`, `maybe_extract`. #39 inserts `recall_turn`; that hunk auto-merged when #39 came after #43. Wrap each of those replies with `present(...)`.
- The model path is `render_prompt` (default channel), then `AgentLoop(...).run(..., on_event=on_event)`, then `present`. Delete the `for index in range(3): plan = self.generate(...)` loop from #43.
- Follow-up advice uses `render_prompt(..., channel="followup")` instead of `followup_system(...)`.

```python
            system = render_prompt(
                self.runtime.persona.current()["body"],
                self.runtime.data.preferences(),
                payload.language,
            )
            reply = AgentLoop(
                self.runtime, HostedTextProvider(self.generate, self.generate_live)
            ).run(
                system=system,
                context=context,
                key=key,
                language=payload.language,
                allow_memory=allow_memory,
                on_event=on_event,
            )
            reply = present(reply, self.runtime.data.preferences(), payload.language)
```

Step 23, `voice.py`. Keep `from .tool_policy import tool_visible`. Delete `from .persona import voice_instructions`. Keep the `render_prompt(..., channel="voice")` block from #43.

Step 24, `assistant.py`. Keep one import block, not two `memory` imports:

```python
from .memory import MemoryDeleteDraft, MemoryQuery, MemoryReplaceDraft, MemorySaveDraft
from .rank import rank_rows
from .tool_audit import ToolAudit, channel_for
from .owner_lookup import OwnerClockArgs, OwnerSearch, PlateQuery, owner_clock, owner_search, plate_summary
from .owner_plan import ProposePlan, propose_plan
from .tool_policy import audit_suppressed, memory_blocked, outcome_message
from .recall import cited_id, classify, matching, render, set_focus, zone_of
from .recall import ensure as ensure_recall
```

In `__init__`, keep both lines:

```python
        self.audit = ToolAudit(self.store)
        ensure_recall(self.store)
```

Also keep #43's `local_message` wrapper that calls `present`, and #39's `recall_turn`. Those did not conflict with each other in this order.

Step 25 is clean on top of that `assistant.py` / `memory.py` / `recall.py`. Alias matching is inside `recall.py`. Ranking from #47 stays. Built-in pairs cannot be deleted.

Step 28, `runtime.py` import. Keep both:

```python
from .moments import MomentService
from .digest import DigestService
```

`MemoryPanel.tsx`: import and render both `<AliasList t={t} />` and `<DigestPanel t={t} />`.

Step 29, `runtime.py`. One `self.notify` assignment, the one that passes `push`. Keep moments and digests:

```python
        self.moments = MomentService(self)
        self.notify = Notifier(
            self.store,
            push=PushService(
                self.store, HttpPushSender(), self.store.directory / "vapid-private.pem"
            )
            if push_enabled()
            else None,
        )
        self.digests = DigestService(self)
```

Keep the imports `HttpPushSender`, `PushService`, and `push_enabled`. Do not leave the earlier `self.notify = Notifier(self.store)` in place.

`notify.py` auto-merged. #46 sends only after the in-app write commits, and only when the browser channel delivered. Quiet hours and the dedupe row from #26 stay. If it conflicts, keep that order: quiet return, dedupe, commit, then `push.dispatch`.

`app.py` auto-merged. The router list after step 29 must include `nudge_routes`, `notice_routes`, `goal_routes`, `profile_routes`, `moment_routes`, `digest_routes`, and `push_routes`, plus #42's diagnostics routes and #28's cookie change. If a later conflict appears, keep every `include_router` from both sides.

`operator-guide.md`: one quiet-hours paragraph. Keep the tone / verbosity / proactivity sentences from #40 and #43, and add #46's Web Push sentence (`DESK_WEB_PUSH=1`, mode `0600`, link to `web-push.md`). Do not paste the quiet-hours opening twice.

`knowledge.test.ts`: keep the `form.tone` / `form.verbosity` / `form.proactivity` asserts and `assert.match(extras, /Web Push stays off until DESK_WEB_PUSH=1/)`.

`moments.py` auto-merged at step 27. If it conflicts, keep #38's free-time card when a timed event falls in 30–180 minutes, and #48's open loop only when `free_gap` is missing. Pause counts are per `kind`.

## After the last merge

Search the tree for `<<<<<<<`. There should be none.

Then from `desk-companion/`:

```bash
uv run --no-sync ruff check backend scripts tests
uv run --no-sync pytest -q
```

From `desk-companion/frontend/`:

```bash
npm test
npm run build
```

Do not set `DESK_WEB_PUSH` in that run. Web Push stays off unless the operator sets it later. Do not call a paid model. Counts will be higher than any single pull request's count because the suites add up; a failure needs a look at the resolution above before changing a feature.

`desk-companion/docs/companion-gaps.md` on #35 still describes digest, moments, recall, and style as next work. Leave that file as #35 wrote it. This guide is the newer order.
