# 手机回复流契约

日期：2026-10-27。压缩后的继续，没有重读整库 Markdown。本轮补读 AGENTS.md、product.md、handoff.md、decision-log.md 里 2026-10-27 的代理循环条目、agent-loop.md 回复流、architecture.md 身份段、operator-guide.md 第 9 节，以及要改的前端和上下文文件。排除 `.git`、依赖、`archive/` 和硬件研究。

## 更新的规范

- `desk-companion/docs/assistant-stream.md`（新）
- `desk-companion/docs/agent-loop.md`
- `desk-companion/docs/architecture.md`
- `desk-companion/docs/operator-guide.md`
- `handoff.md`、`decision-log.md`、`work-log.md`

## 检查

在 `desk-companion/`：

- `.venv/bin/pytest -q`：215 通过。已有的 Starlette／httpx 弃用警告仍在，没有为此升级。
- `.venv/bin/ruff check backend tests`：通过。
- `npm test`：25 通过。
- `npm run build`：通过。
- 本机 Chrome：登录后发送 “Remember: the stream code is lantern”，看到 `memory_save_draft`、Not saved、核对句，取消后显示 Draft cancelled。运行目录已删除。没有付费 API。

## 样例

`desk-companion/contracts/assistant-stream.sse` 含 `tool`、`preview`、`delta`、`done`、`error`。Python `parse_sse` 和前端 `readBody`／`consumeChunk` 都读这份文件。
