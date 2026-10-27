# Group 2 Current Handoff

更新：2026-10-27。当前是 Desk Companion 软件切片，均从 `main` `46ac167` 单独开出，尚未合并。硬件 PR #17 与整理 PR #18 仍是已合并事实。AliceChan／统一 Omni 仍只在未发布的本地工作区。

## 当前状态与证据

- 覆盖与回归：[#36](https://github.com/tantalum666/FYP/pull/36)。`main` 上读回遇到目录会抛 `IsADirectoryError`；修复只在该 PR。本地 `pytest` 193、前端测试 20。
- 日志、拥有者诊断、本地备份：[#42](https://github.com/tantalum666/FYP/pull/42)。本地 `pytest` 187、前端测试 19、构建通过；浏览器看过诊断页，未见 API key 和口令。
- 可安装外壳：[#49](https://github.com/tantalum666/FYP/pull/49)。服务工作者不缓存 `/api`。前端测试 20、构建通过；无头 Chrome 确认两份 manifest 链接。
- 报告软件章草稿：[software-chapter.md](desk-companion/docs/report/software-chapter.md)，在本交接所在 PR。只描述已提交代码和 decision-log，开放 PR 没有写成已合并。
- 更早仍开放且独立：[#21](https://github.com/tantalum666/FYP/pull/21)、[#22](https://github.com/tantalum666/FYP/pull/22)、[#24](https://github.com/tantalum666/FYP/pull/24)、[#25](https://github.com/tantalum666/FYP/pull/25)、[#27](https://github.com/tantalum666/FYP/pull/27)、[#28](https://github.com/tantalum666/FYP/pull/28)、[#30](https://github.com/tantalum666/FYP/pull/30)。GitHub Actions 仍因账户账单未真正跑测试。
- 若本交接与 #24 或 #30 的 `handoff.md` 冲突，保留这一份。

## 一个下一步

**按各 PR 说明的顺序审阅这些软件切片，不要合并旧 A1 栈。** 未发布的 AliceChan／Omni 仍单独整理。本轮没有硬件验收、付费模型调用或学校提交。
