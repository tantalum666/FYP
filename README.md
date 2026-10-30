# Desk Companion · FYP Group 2

个人 Agent 方向与旧研究统一从[研究总入口](research/personal-agent-research-index.md)恢复：含六份原 PR #5 报告、Grok／Muse／Your dot 当前公开机制，以及邮件／购物／旅行目标与已实现范围的对应。

面向家庭／办公室桌面的个人 AI 助理：日历与事务、可更正的记忆、受限电脑作业，以及固定摄像头的坐姿判断、反馈和复测。当前开发名称为 **Desk Companion**；仓库为三人私人协作空间。

**2026-10-26 仓库整理：**组员的 [硬件 PR #17](https://github.com/tantalum666/FYP/pull/17) 已完成审查、修订并合入 `main`。退役食品项目的代码、设计、采购、学校版本和验证资料统一放在 [archive/senplate](archive/senplate/README.md)。

**2026-10-28 软件整合：**Grok #20–#59 与 #60 已通过 [PR #61](https://github.com/tantalum666/FYP/pull/61) 合入 main；41个原PR均已读回为merged。当前软件主线、修复及450／89项本地验证见[整合QA](output/qa/2026-10-28-grok-review-merge/verification.md)。Pi仍暂停，软件按用户要求只做本地验证。

**2026-10-29 继续开发：**在PR64记忆修复之上完成事务／文件／手机接续，统一网页与App的对话内操作卡片及Ask first／Full access权限；489／89项本地检查、实际恢复／文件读回及当前原生构建见[本轮QA](output/qa/2026-10-29-assistant-permissions/verification.md)。完整产品尚未通过的流程按[交付门槛](desk-companion/docs/delivery-readiness.md)推进，原生触控／软键盘仍待。分支发布状态见交接。

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

## 当前软件检查点

本分支基于归档后的main，整合**AliceChan、统一Omni文字／语音、有界上下文、逐轮时限、Linux固定双应用、网页与全屏手机**；同时整合Grok #20–#59：有界工具循环、流式回复、记忆／目标／通知、备份与诊断；保留手机职责拆分，并修复权限、恢复、数据保留和跨栈兼容问题。实现见[维护契约](desk-companion/docs/software-maintenance.md)，整合历史验证见[整合QA](output/qa/2026-10-28-grok-review-merge/verification.md)，最新权限／跨端接续验证见[本轮QA](output/qa/2026-10-29-assistant-permissions/verification.md)。

Qwen为已测基线，其他AI候选仍开放。本轮使用模拟提供商及虚构本地数据，没有新收费调用。Pi暂停；原生触控／键盘、真机和硬件另验。旧PR与作者工程留作历史，不把独立软件分支推送称为合并或部署。

仅本机开发预览可用`DESK_LOCAL_PREVIEW=1 ./scripts/dev.sh`免输入账号密码；正式默认认证和外部访问保护保留。手机浏览器调试入口为`?surface=phone`，原生iPhone使用同一独立PhoneApp。本地运行后端Lint／测试和前端测试／构建，不连接模型或硬件；不使用GitHub CI。

硬件目录是采购前研究，仍缺完整免焊转接、电源／Qi／风机及实物验证；学校文件完成不等于已签署或提交。进入本仓库的代理先遵守 [AGENTS.md](AGENTS.md)。本次整理和验证见 [QA](output/qa/2026-10-26-repo-cleanup/verification.md)。

## 2026-10-29 OpenAI实时语音试验

完成Realtime2.1与GPT-Live1＋Luna两条路线的真实短测，并加入Mini英文费用参照。16次会话包含11次最终控制条件检查，费用按返回usage保守估算约0.304美元；本轮5美元额度已关闭。英／普／粤日历、待确认记忆及合成插话结果、初次失败和可试听录音见[QA](output/qa/2026-10-29-openai-realtime/verification.md)。504后端／15专项检查通过，无CI。这是独立评测工具，日常App尚未新增OpenAI提供商入口；[接入边界](desk-companion/docs/openai-voice-evaluation.md)。

## 2026-10-30 复杂应用任务

按用户要求，将主验收提高为浏览器＋电子表格＋文档／PDF＋日历／事务的[演示准备包](planning/2026-10-30/complex-application-acceptance.md)，包含中途改预算／数量／日期、不可行条件澄清、丢回执和重启恢复。[固定材料](desk-companion/evals/app_workflow_v1/README.md)与受限应用适配器已完成，真实 Chromium／Calc／Writer／PDF 的脚本任务、原日程更新及重启恢复通过；[本轮 QA](output/qa/2026-10-30-application-execution/verification.md)记录 524 后端／89 前端与实际网页／手机操作。完整语音自主执行仍待，未产生新模型费用。
