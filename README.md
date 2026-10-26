# Desk Companion · FYP Group 2

面向家庭／办公室桌面的个人 AI 助理：日历与事务、可更正的记忆、受限电脑作业，以及固定摄像头的坐姿判断、反馈和复测。当前开发名称为 **Desk Companion**；仓库为三人私人协作空间。

**2026-10-26 仓库整理：**组员的 [硬件 PR #17](https://github.com/tantalum666/FYP/pull/17) 已完成审查、修订并合入 `main`。退役食品项目的代码、设计、采购、学校版本和验证资料统一放在 [archive/senplate](archive/senplate/README.md)。

## 从哪里开始

| 内容 | 入口 |
| --- | --- |
| 当前要求、完成边界和下一步 | [product.md](product.md) · [handoff.md](handoff.md) |
| 软件代码与运行说明 | [desk-companion](desk-companion/README.md) · [操作指南](desk-companion/docs/operator-guide.md) |
| 硬件成员最新进度 | [Mini图册、元件与采购前待办](research/2026-10-23-mini-robot-hardware/README.md) |
| 机械臂技术依据 | [RIG-Arm二次开发研究](research/2026-10-05-rig-arm/secondary-development-review.md) |
| 当前学校提案与团队日志 | [2026-09-28交付目录](output/submission/2026-09-28/) · [制作与审阅记录](planning/2026-09-28/logsheet-and-proposal-review.md) |
| 学校原件、成员与协作 | [inputs](inputs/README.md) · [Group 2资料](planning/2026-09-14/group-2-details.json) · [CONTRIBUTING](CONTRIBUTING.md) |
| 决定与工作历史 | [decision-log](decision-log.md) · [work-log](work-log.md) |
| 已退役的Senplate | [统一归档入口](archive/senplate/README.md) · [原路径与校验清单](archive/senplate/archive-manifest.json) |

## 运行 GitHub 中的当前版本

需要 Python 3.12+、uv、Node 22.12+。从仓库根目录执行：

```sh
cd desk-companion
uv sync --frozen
cd frontend
npm ci
npm run build
cd ..
./scripts/dev.sh
```

网页为 `http://127.0.0.1:5190/`，设备布局为 `http://127.0.0.1:5190/?surface=device`。账号 `owner` 的密码在各成员本机首次生成的 `desk-companion/.runtime/credentials.json`，不随仓库分发。真实相机、麦克风、模型服务和机械输出按操作指南另行配置。

## GitHub与本地工作区的状态

`main`包含已审查的日历／事务／记忆／人格／受限文件作业基础，以及本次硬件研究。最新的 **AliceChan常驻形象、同一Qwen Omni文字与语音、每轮超时／实际播音计时、Linux双应用流程**仍保存在软件负责人的本地工作区，尚未全部提交到 `main`。因此新克隆不能被描述为已包含这些最新功能。

当前产品方向采用AliceChan和同一Omni会话；旧A1造型／独立内核草稿见PR #4／#5，早期Omni和A1研究草稿见PR #15／#16。它们保留待单独梳理，不能按编号直接把已否决的人物实现合回去。下一步见交接中的唯一任务。

硬件目录是采购前研究，仍缺完整免焊转接、电源／Qi／风机及实物验证；学校文件完成不等于已签署或提交。进入本仓库的代理先遵守 [AGENTS.md](AGENTS.md)。本次整理和验证见 [QA](output/qa/2026-10-26-repo-cleanup/verification.md)。
