# 2026-10-27 软件健康阅读记录

完成时间：2026-10-27。方法：下列文件用工具分段读到 EOF。`work-log.md` 只读了开头和 10 月 14 日之后的条目。SHA 或目录清单不能代替阅读。本轮用户指定先读入口和 Desk Companion 操作文档，并禁止修改硬件研究与 `archive/`。

## 已完整阅读

| 文件 | 行数 | 范围 |
| --- | ---: | --- |
| `AGENTS.md` | 50 | 1–50 |
| `product.md` | 56 | 1–56 |
| `handoff.md`（改写前） | 15 | 1–15 |
| `decision-log.md`（追加前） | 305 | 1–305 |
| `README.md` | 42 | 1–42 |
| `CONTRIBUTING.md` | 96 | 1–96 |
| `desk-companion/README.md` | 106 | 1–106 |
| `desk-companion/THIRD_PARTY.md` | 23 | 1–23 |
| `desk-companion/docs/operator-guide.md` | 171 | 1–171 |
| `desk-companion/docs/architecture.md` | 95 | 1–95 |
| `desk-companion/docs/computer-jobs.md` | 69 | 1–69 |
| `desk-companion/docs/memory.md` | 32 | 1–32 |
| `desk-companion/docs/task-tracking.md` | 61 | 1–61 |
| `desk-companion/docs/evaluation.md` | 60 | 1–60 |
| `desk-companion/frontend/ios/App/CapApp-SPM/README.md` | 5 | 1–5 |
| `docs/tooling-and-review/companion-architecture.md` | 129 | 1–129 |
| `docs/tooling-and-review/fyp-repo-review.md` | 86 | 1–86 |
| `planning/2026-10-06/software-architecture-audit.md` | 69 | 1–69 |
| `output/qa/2026-10-14-text-adapters/reading-record.md` | 11 | 1–11 |

`desk-companion/docs/modules.md` 是本轮新写的，写完后又通读了一遍。

## 部分阅读

- `work-log.md`：1–80，以及当时文件末尾约 300–348。中间 9 月历史没有逐行重读。
- `output/qa/2026-10-26-repo-cleanup/reading-record.json`：只看了前 40 行的记录格式。

## 盘点但未读正文

`rg --files --hidden -g '*.md'` 当时为 174 个文件。未读、也未修改：

- `archive/`，包括退役 Senplate
- `research/`，包括硬件研究
- 其余 `planning/`、`design/`、`inputs/`、`docs/tooling-and-review/companion-product-teardown.md`
- `output/qa/` 里除上表以外的历史快照

## 本轮更新的规范

`handoff.md`、`decision-log.md`、`work-log.md`、`desk-companion/README.md`（模块链接；CI 分支另改了开发脚本说明）、`desk-companion/docs/architecture.md`、`desk-companion/docs/modules.md`。

## 检查

在 `desk-companion/`：

- `uv sync --frozen`
- `npm ci`；`npm run build`
- `uv run --no-sync ruff check backend scripts tests`
- `uv run --no-sync pytest -q`：改代码前 182 通过；作业注册表分支 184 通过
- `npm test`：17 通过
- `./scripts/dev.sh`：健康检查 ok，5190 HTTP 200；无 `uv` 的 PATH 下修复前后对照见工作日志

没有付费模型调用。文档分支没有再跑一遍测试。

#21 的 GitHub Actions 运行 `40538751215` 没有启动 runner。注解原文是账户近期付款失败或需要提高支出上限。这不是 Ruff、pytest 或前端构建失败。
