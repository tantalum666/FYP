# Group 2 Current Handoff

更新：2026-10-27。当前任务是 Desk Companion 的软件健康与可复现。硬件研究、`archive/` 和未合并的 A1 草稿没有改动。

## 当前状态与证据

- README 的安装顺序已在本机走通：`uv sync --frozen`、`npm ci`、`npm run build`、`./scripts/dev.sh`。`/api/health` 返回 ok，5190 返回 HTTP 200。`uv` 不在 PATH 时，旧开发脚本以 127 退出；修复后同一环境可以启动。
- 当时的 `main`：后端 182 通过、前端 17 通过、Ruff 通过、前端构建通过。作业注册表分支再增加 2 项，为 184 通过。没有付费 API。记录见[本轮 QA](output/qa/2026-10-27-software-health/reading-record.md)。
- 待审查的软件健康 PR：[#21](https://github.com/tantalum666/FYP/pull/21) 是 CI 和开发脚本，[#22](https://github.com/tantalum666/FYP/pull/22) 是作业动作注册表，[#24](https://github.com/tantalum666/FYP/pull/24) 是模块说明。先合并 #21，#22 与 #24 互不依赖。后两支没有 workflow 文件，#21 进入 `main` 之前它们不会自动获得这套检查。
- #21 的 Actions 作业没有启动。GitHub 的注解是账户近期付款失败或支出上限需要提高，不是测试失败。本地命令已经通过。恢复额度后需要重跑 #21。
- PR #4、#5、#15、#16 仍不合并。AliceChan／统一 Omni 的本地未发布增量仍不在 `main`。

## 一个下一步

**拥有者恢复 GitHub Actions 额度后重跑 #21，再由 Codex 按 #21、然后 #22 与 #24 的顺序审查合并。** 不要并入 A1 草稿。
