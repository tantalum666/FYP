# 代理循环交接

日期：2026-10-27。接离线评估表那一支。依据是当前的 `agent-loop.md`、`capabilities.py`、上下文预算和语音轮次代码。没有重读整库。

## 更新的规范

- `desk-companion/docs/agent-loop-handoff.md`（新）
- `desk-companion/docs/agent-loop.md` 的提供方一句，与 `generate`／`generate_live` 对齐
- `handoff.md`、`decision-log.md`、`work-log.md`

## 检查

在 `desk-companion/`：

- `.venv/bin/pytest -q`：230 通过。Starlette／httpx 弃用警告仍在，没有为此升级。
- `.venv/bin/ruff check backend tests scripts/tool_eval.py`：通过。
- 交接里的相对链接指向 `agent-loop.md`、`assistant-stream.md`、`memory.md`，三个文件都在 `desk-companion/docs/`。
- 没有付费 API。没有新的运行时行为。
