# 2026-10-27 软件切片阅读记录

这是上下文压缩后的继续，不是新的全库开工。没有重新通读全部项目 Markdown。

## 本轮实际阅读

| 文件 | 范围 |
| --- | --- |
| `AGENTS.md` | 全文，50 行 |
| `product.md` | 全文，57 行 |
| `handoff.md` | 全文，压缩前的 15 行归档交接 |
| `decision-log.md` | 标题清单，以及 2026-10-14 审查起至 2026-10-26 归档一节 |
| `desk-companion/README.md` | 全文，107 行 |
| `desk-companion/docs/architecture.md` | 全文，96 行 |
| `work-log.md` | 开头与 2026-10-26 末节，用于追加，不是全文 |

代码阅读覆盖本轮要测或要改的路径：`app.py`、`store.py`、`jobs.py`、`calendar.py`、`tasks.py`、`exchange.py`、`computer.py` 的读回、`text_ai.py` 的额度查询、`runtime.py`、`dates.ts`、`index.html`，以及诊断页和 PWA 新增文件。常量核对包括记忆 200／40、人格 4000、跟进 3、语音 600／45、工具信号量 2／8／32。

## 排除

`.git`、`node_modules`、`.venv`、`frontend/dist`、`archive/`、`output/qa/` 里的旧证据快照、planning 与 research 全文。没有因为压缩而重跑已通过的整库测试。

## 本轮更新的规范

- `handoff.md`
- `decision-log.md` 2026-10-27 一节
- `work-log.md` 2026-10-27 一节
- `desk-companion/docs/report/software-chapter.md`

## 检查

各 PR 的命令和结果写在该 PR 正文和软件章节第 3 节。报告分支本身不改 Python 或前端，因此没有在这个分支上重跑 pytest。链接目标 `architecture.md`、`product.md`、`decision-log.md` 均在仓库内。

完成时间：2026-10-27。
