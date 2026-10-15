# 2026-10-14 共用人格文本

压缩后的延续。文件夹作业的阅读记录在 [folder-job](../2026-10-14-folder-job/reading-record.md)。本轮只读人格会改到的文字通道、语音指令、运行时装配和记忆页导航。

完成时间：2026-10-14。

## 本轮读过的相关代码

- `desk/text_ai.py` 的系统提示与后台建议
- `desk/voice.py` 的会话指令
- `desk/runtime.py` 的服务装配
- `desk/app.py` 的路由注册
- `desk/tasks.py` 里 `follow_up_enabled` 如何跳过新的本地检查
- 前端 `App.tsx` 导航、`types.ts` 的页面联合、`MemoryPanel.tsx` 的拥有者表单模式

排除：`.git`、`.venv`、`node_modules`，以及更早的 QA 快照。没有重读整套研究。

## 已更新的规范

`memory.md`、`architecture.md`、软件 README、`product.md`、`handoff.md`、`decision-log.md`、`work-log.md`。

## 检查

- `uv run --no-sync pytest -q`：165 通过
- `uv run --no-sync ruff check backend scripts tests`：通过
- `npm test`：16 通过
- `npm run typecheck`：通过

没有浏览器点击人格页。没有付费模型。
