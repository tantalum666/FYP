# 2026-10-14 指定文件夹作业

压缩后的延续，不是新的全库开工。上一轮记忆实现的全文阅读记录仍是 [owner-memory](../2026-10-14-owner-memory/reading-record.md)。本轮只补读要改的作业契约和调用处，没有把目录或搜索命中当成已读。

完成时间：2026-10-14。

## 本轮读过的正文

- `handoff.md`、`AGENTS.md`（流程）、`product.md` 全文
- `desk-companion/backend/desk/jobs.py`、`computer.py` 全文
- `desk-companion/docs/computer-jobs.md` 全文
- `desk-companion/tests/test_computer_jobs.py` 全文
- `desk-companion/frontend/src/workspace/ComputerJobsPanel.tsx`、`jobTypes.ts` 全文
- `desk-companion/frontend/tests/computer-jobs.test.ts` 全文
- `assistant.py`、`text_ai.py`、`voice.py`、`memory.md`、`architecture.md`、`operator-guide.md`、`api.ts` 中与作业、人格字符串和错误文案有关的部分
- `decision-log.md`、`work-log.md` 的当前末尾

排除：`.git`、`.venv`、`node_modules`、`output/qa/` 里更早的自动证据快照。没有重读整套研究或学校原件。

## 已更新的规范

`computer-jobs.md`、`memory.md`、`architecture.md`、`operator-guide.md`、软件 README、`product.md`、`handoff.md`、`decision-log.md`、`work-log.md`。

## 检查

- `uv run --no-sync pytest -q`：162 通过
- `uv run --no-sync ruff check backend scripts tests`：通过
- `npm test`：16 通过
- `npm run typecheck`：通过

没有浏览器点击 Computer jobs 的新文件夹表单。没有付费模型，没有对商业客户端做逆向。
