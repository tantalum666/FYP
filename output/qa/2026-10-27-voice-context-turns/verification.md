# 语音轮次进入上下文预算

日期：2026-10-27。接上下文预算那一支。补读 `voice.py` 的会话循环、`turns.py`、`context.py` 和 `agent-loop.md` 的预算段。没有重读整库。

## 更新的规范

- `desk-companion/docs/agent-loop.md`
- `handoff.md`、`decision-log.md`、`work-log.md`

## 检查

在 `desk-companion/`：

- `.venv/bin/pytest -q`：226 通过。Starlette／httpx 弃用警告仍在，没有为此升级。
- `.venv/bin/ruff check backend tests`：通过。
- 前端未改。没有付费 API，语音测试使用假连接。

覆盖：最终转写替换增量、配对和关闭的日志不写、本机语音工作进程写入、待批准草稿在预算为 1 时仍在、语音提示不含记忆正文、套接字回合写入文本且不写入音频字节。
