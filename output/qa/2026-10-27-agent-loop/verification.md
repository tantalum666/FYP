# 2026-10-27 文字代理循环验证

Group 2。本片只改代理循环、工具注册、审计和离线场景。没有付费模型、硬件动作或合并 PR #4／#5／#15／#16。

## 命令与结果

在 `desk-companion/`：

```sh
.venv/bin/pytest -q
.venv/bin/ruff check backend scripts tests
```

结果：190 通过，1 条既有 Starlette／httpx 弃用警告。Ruff 通过。此前 main 的后端计数是 182；新增 8 项在 `tests/test_agent_loop.py`。

在 `desk-companion/frontend/`：

```sh
npm test
npm run build
```

结果：17 通过。`tsc --noEmit` 与 Vite 生产构建通过。npm audit 报告 0 vulnerabilities。

离线场景由 pytest 调用 `desk.agent_eval.run_all`，不打开网络。当时覆盖：日历提醒草稿不写入、记忆查询后才回答、拒绝 `shell_exec`、提供方第一次 `TEXT_AI_UNAVAILABLE` 后重试成功。

## 同日补充

继续同一分支。没有重读全库 Markdown。补读并修改了代理循环、工具策略、语音调度、审计、离线场景、助理面板和上面列出的规范。

```sh
.venv/bin/pytest -q
.venv/bin/ruff check backend scripts tests
```

结果：193 通过，仍是那条既有 Starlette／httpx 弃用警告。Ruff 通过。

`frontend` 下 `npm test` 19 通过，`npm run build` 通过，`npm audit` 0。

离线场景现为八个：提醒、记忆回忆、拒绝 `shell_exec`、待批准电脑笔记、三步上限、注入时钟的时间上限、提供方重试、文字与语音同一次拒绝。

本机 Chrome 打开 `http://127.0.0.1:5190/`，以拥有者登录后打开助理。面板显示 `memory_save_draft`、Needs approval、ok、Not saved、local，以及 “Prepared for review. Nothing was saved.”。展开参数后可见该草稿正文。没有批准，没有付费 API。

## 本轮更新的规范

- `desk-companion/docs/agent-loop.md`（新）
- `desk-companion/docs/architecture.md`
- `desk-companion/docs/task-tracking.md`
- `desk-companion/docs/operator-guide.md`
- `desk-companion/README.md`
- `product.md`
- `handoff.md`（只加本片，保留 2026-10-26 归档交接）
- `decision-log.md`
- `work-log.md`

## 阅读

本轮完整阅读了开工要求的 `AGENTS.md`、`product.md`、`handoff.md`、`decision-log.md`、`desk-companion/README.md`，以及要改的软件契约和实现：架构、电脑作业、记忆、事务、操作指南、个人代理讨论、架构审查、工具文档和当前代码。历史研究与学校提案未逐篇重读；它们不改变本片的批准边界。排除 `.git`、依赖、构建产物、`archive/` 和 `output/qa/` 里的旧证据快照。硬件研究目录没有修改。

## 未验证

没有真实 Qwen／Gemini 调用，也没有浏览器里点击助理面板。前端只做了类型检查和生产构建。配对屏 403 由 API 测试覆盖。
