# Group 2 Current Handoff

更新：2026-10-27。当前任务是 Desk Companion 的软件健康与可复现。硬件研究、`archive/` 和未合并的 A1 草稿没有改动。

## 当前状态与证据

- README 的安装顺序已在本机走通：`uv sync --frozen`、`npm ci`、`npm run build`、`./scripts/dev.sh`。`/api/health` 返回 ok，5190 返回 HTTP 200。`uv` 不在 PATH 时，旧开发脚本以 127 退出；修复后同一环境可以启动。
- 当时的 `main`：后端 182 通过、前端 17 通过、Ruff 通过、前端构建通过。作业注册表分支再增加 2 项，为 184 通过。没有付费 API。记录见[本轮 QA](output/qa/2026-10-27-software-health/reading-record.md)。
- 待审查的软件健康 PR：[#21](https://github.com/tantalum666/FYP/pull/21) 是 CI 和开发脚本，[#22](https://github.com/tantalum666/FYP/pull/22) 是作业动作注册表，模块说明是本交接所在的分支。先合并 #21，#22 与模块说明互不依赖。#22 和模块说明的分支里没有 workflow 文件，#21 进入 `main` 之前，它们的远端检查不会自动出现。
- PR #4、#5、#15、#16 仍不合并。AliceChan／统一 Omni 的本地未发布增量仍不在 `main`。

## 一个下一步

**Codex 审查并合并这三支软件健康 PR，顺序为 #21，然后 #22 与模块说明。** 不要并入 A1 草稿。
