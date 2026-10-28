# 离线工具评估表

日期：2026-10-27。接语音轮次那一支。补读三组 `run_all`／`run_scripted` 和 `scripts/conversation_eval.py` 的门槛。没有重读整库。

## 更新的规范

- `desk-companion/docs/agent-loop.md` 新增「离线评估表」
- `handoff.md`、`decision-log.md`、`work-log.md`

## 检查

在 `desk-companion/`：

- `.venv/bin/pytest -q`：229 通过。Starlette／httpx 弃用警告仍在，没有为此升级。
- `.venv/bin/ruff check backend tests scripts/tool_eval.py`：通过。
- `.venv/bin/python scripts/tool_eval.py`：退出码 0，末行 `29 passed, 0 failed`。
- 前端未改。没有付费 API。脚本没有读取 `DESK_CONVERSATION_EVAL`。
