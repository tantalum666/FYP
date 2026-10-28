# 对话质量验证

2026-10-27。Group 2。本片在有界计划分支之上。

## 更新的规范

- `handoff.md`、`work-log.md`、`decision-log.md`
- `desk-companion/docs/agent-loop.md`

## 检查

在 `desk-companion/`：

- `.venv/bin/pytest -q`：202 通过，1 条既有 Starlette／httpx 警告
- `.venv/bin/ruff check backend scripts tests`：通过
- `scripts/conversation_eval.py` 在去掉 `DESK_*` 的环境里退出码 2，标准错误为空

没有付费 API。没有把该脚本放进 CI。没有合并 PR。
