# 上下文预算

日期：2026-10-27。接手机回复流那一支，没有重读整库。补读本轮要改的 `context.py`、`agent_loop.py`、`text_ai.py`、`memory.md`、`agent-loop.md`，以及记忆与代理循环测试。

## 更新的规范

- `desk-companion/docs/agent-loop.md` 新增「上下文预算」
- `desk-companion/docs/memory.md`
- `handoff.md`、`decision-log.md`、`work-log.md`

## 检查

在 `desk-companion/`：

- `.venv/bin/pytest -q`：222 通过。Starlette／httpx 弃用警告仍在，没有为此升级。
- `.venv/bin/ruff check backend tests`：通过。
- 前端未改，没有重跑 `npm test` 或浏览器。
- 没有付费 API。

长对话测试覆盖：中文记忆命中留在无关长事实之前、待批准草稿在预算为 1 时仍在、较旧轮次先去掉、选中事务和工具结果的 `saved`／提案 id 留下、循环在工具之后重新装配、配对会话看不到拥有者轮次。
