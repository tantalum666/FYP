# Group 2 Current Handoff

更新：2026-10-14。状态：**main 仍是 10 月 9 日已合并的 Desk Companion；本轮只新增 tooling 文档。**

## 当前结果

`main` 软件基线未改。新增 [docs/tooling-and-review](docs/tooling-and-review/fyp-repo-review.md)：仓库结构与缺口、[托管 API 架构与供应商建议](docs/tooling-and-review/companion-architecture.md)、[REA 构建记录](docs/tooling-and-review/rea-setup.md)。REA 在仓库外的 scratch 目录用 Rust 1.99 编过，`rea --help` 与自编译 ELF 的 one-shot 已跑通。没有把二进制、报告或密钥提交进来。

供应商仍未由用户选定。文档里的 Qwen 优先、Gemini 对照是工程建议，不是购买或锁定。Muse／Dot 的公开拆解仍在未合并的 [PR #5](https://github.com/tantalum666/FYP/pull/5)，本轮没有重写。GitHub 打开项是 [PR #4](https://github.com/tantalum666/FYP/pull/4) 与 PR #5，没有单独的 open issue。

## 证据

REA 验证命令与 JSON 字段见 [rea-setup.md](docs/tooling-and-review/rea-setup.md)。阅读范围见 [本轮 QA](output/qa/2026-10-14-tooling-and-review/reading-record.md)。未跑 Desk Companion 测试，未调用付费模型，未对商业客户端做逆向。

## 未完成

通用电脑执行、真实语音与费用、Pi、真人姿态标签、RIG／清洁模块、PR #4／#5 合并，以及学校提交，都还开着。

## 唯一下一步

**在 owner 指定的一个测试应用或目录上，沿现有作业契约做批准、独立读回和取消；不要新开一套任务系统，也不要在没有花费上限时开通模型账号。**
