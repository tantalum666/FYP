# 拥有者语音提示里的记忆命中

日期：2026-10-27。接代理循环交接。改的是 `voice_context_note`、语音会话如何附上这段提示，以及交接说明。没有重读整库。

## 更新的规范

- `desk-companion/docs/agent-loop-handoff.md`
- `desk-companion/docs/agent-loop.md`
- `handoff.md`、`decision-log.md`、`work-log.md`

## 检查

在 `desk-companion/`：

- `.venv/bin/pytest -q`：231 通过。Starlette／httpx 弃用警告仍在，没有为此升级。
- `.venv/bin/ruff check backend tests`：通过。
- 没有付费 API。没有新的语音供应商调用。

测试覆盖：上一句「灯笼」让红灯笼留在预算内、更长的无关事实被丢掉、待批准草稿仍在且标 `saved=false`、删除后的事实不出现、`allow_memory=False` 得到空字符串。
