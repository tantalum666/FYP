# 检索排序验证

2026-10-27。Group 2。本片在真实文本片段分支之上。排序不依赖片段流，叠在其上是为了让后面的上下文预算使用同一套排序。

## 更新的规范

- `handoff.md`、`work-log.md`、`decision-log.md`
- `desk-companion/docs/agent-loop.md`
- `desk-companion/docs/memory.md`

## 检查

在 `desk-companion/`：

- `.venv/bin/pytest -q`：213 通过，1 条既有 Starlette／httpx 警告
- `.venv/bin/ruff check backend scripts tests`：通过

没有付费 API。没有新依赖。没有合并 PR。
