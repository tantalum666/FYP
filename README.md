# Desk Companion · FYP Group 2

**2026 年 11 月 24 日**　常用 Web、iPhone 17 Pro 模拟器和原装 Pi 最近一次核验的应用版本为 `92acac8e`。普通文字和托管浏览使用 GPT-6.2 Sol，实时语音使用 GPT-Live-1.1 和 A3 v9。GitHub `main` 的源码、已安装的版本和供应商实际回执分别记录。[三端验收](output/qa/2026-11-23-owner-flow-hotfix/verification.md) · [当前交接](handoff.md)。

**11 月 18 日软件进度**　开发分支已将普通 OpenAI 文字接入官方 Sessions 和 Functions，并将静音期积累的主动发现合并提醒。[迁移契约](desk-companion/docs/official-text-sessions.md) · [Claude 文章与 FYP 对照](research/2026-11-18-always-on-personal-agent.md) · [本地验收](output/qa/2026-11-18-official-text-sessions/verification.md)。 [GPT‑6.2 Sol 真实时区查询、同会话追问与删除回执](output/qa/2026-11-18-live-text-clock/verification.md)。

个人 Agent 方向与旧研究统一从[研究总入口](research/personal-agent-research-index.md)恢复：含六份原 PR #5 报告、Grok／Muse／Your dot 当前公开机制，以及邮件／购物／旅行目标与已实现范围的对应。

面向家庭／办公室桌面的个人 AI 助理：日历与事务、可更正的记忆、受限电脑作业，以及固定摄像头的坐姿判断、反馈和复测。当前开发名称为 **Desk Companion**；仓库用于三人协作。

**2026-10-26 仓库整理：**组员的 [硬件 PR #17](https://github.com/tantalum666/FYP/pull/17) 已完成审查、修订并合入 `main`。退役食品项目的代码、设计、采购、学校版本和验证资料统一放在 [archive/senplate](archive/senplate/README.md)。

**2026-10-28 软件整合：**Grok #20–#59 与 #60 已通过 [PR #61](https://github.com/tantalum666/FYP/pull/61) 合入 main；41个原PR均已读回为merged。当前软件主线、修复及450／89项本地验证见[整合QA](output/qa/2026-10-28-grok-review-merge/verification.md)。Pi仍暂停，软件按用户要求只做本地验证。

**2026-10-29 继续开发：**在PR64记忆修复之上完成事务／文件／手机接续，统一网页与App的对话内操作卡片及Ask first／Full access权限；489／89项本地检查、实际恢复／文件读回及当前原生构建见[本轮QA](output/qa/2026-10-29-assistant-permissions/verification.md)。完整产品尚未通过的流程按[交付门槛](desk-companion/docs/delivery-readiness.md)推进，原生触控／软键盘仍待。分支发布状态见交接。

**2026-10-31 PR5已合并：**持久 Work、来源／产物、事务变化跟踪、定期检查和显式保存会话接入当前核心；旧事实仍能读取，Alice和既有权限／应用执行保持。[兼容与迁移步骤](desk-companion/docs/pr5-integration.md)／[本轮QA](output/qa/2026-10-31-pr5-repair/verification.md)。[合并回执](output/qa/2026-10-31-pr5-repair/publication.json)确认代码合并9b655e1与已测候选完全一致。旧数据库须按明确步骤升级；本轮没有迁移真实运行数据、开启付费模型或恢复Pi。

## 从哪里开始

| 内容 | 入口 |
| --- | --- |
| 当前要求、完成边界和下一步 | [product.md](product.md) · [handoff.md](handoff.md) |
| 软件代码与运行说明 | [desk-companion](desk-companion/README.md) · [操作指南](desk-companion/docs/operator-guide.md) |
| 硬件成员最新进度 | [ArUco 定位台、纸质牌与相机验证](research/2026-11-24-aruco-localisation/README.md) · [采购与 V3 外壳](research/2026-11-17-hardware-progress/README.md) |
| 机械臂技术依据 | [RIG-Arm二次开发研究](research/2026-10-05-rig-arm/secondary-development-review.md) |
| 当前学校提案与团队日志 | [2026-09-28交付目录](output/submission/2026-09-28/) · [制作与审阅记录](planning/2026-09-28/logsheet-and-proposal-review.md) |
| 学校原件、成员与协作 | [inputs](inputs/README.md) · [Group 2资料](planning/2026-09-14/group-2-details.json) · [CONTRIBUTING](CONTRIBUTING.md) |
| 决定与工作历史 | [decision-log](decision-log.md) · [work-log](work-log.md) |
| 已退役的Senplate | [统一归档入口](archive/senplate/README.md) · [原路径与校验清单](archive/senplate/archive-manifest.json) |

## 运行 GitHub 中的当前版本

需要 Python 3.12+、uv、Node 22.12+。已有运行目录先按[兼容迁移说明](desk-companion/docs/pr5-integration.md#store-migration)核对版本、停服务与备份，再启动新版。全新目录从仓库根目录执行：

```sh
cd desk-companion
uv sync --frozen
cd frontend
npm ci
npm run build
cd ..
./scripts/dev.sh
```

网页为 `http://127.0.0.1:5190/`，设备布局为 `http://127.0.0.1:5190/?surface=device`。可信回环默认使用自动本机身份，界面无登录密码表单；恢复凭据仅在各自本机，不随仓库分发。真实相机、麦克风、模型服务和机械输出按操作指南另行配置。

## 历史软件检查点（2026 年 10 月）

本分支基于归档后的main，整合**AliceChan、统一Omni文字／语音、有界上下文、逐轮时限、Linux固定双应用、网页与全屏手机**；同时整合Grok #20–#59：有界工具循环、流式回复、记忆／目标／通知、备份与诊断；保留手机职责拆分，并修复权限、恢复、数据保留和跨栈兼容问题。实现见[维护契约](desk-companion/docs/software-maintenance.md)，整合历史验证见[整合QA](output/qa/2026-10-28-grok-review-merge/verification.md)，最新权限／跨端接续验证见[本轮QA](output/qa/2026-10-29-assistant-permissions/verification.md)。

Qwen为已测基线，其他AI候选仍开放。本轮使用模拟提供商及虚构本地数据，没有新收费调用。Pi暂停；原生触控／键盘、真机和硬件另验。旧PR与作者工程留作历史，不把独立软件分支推送称为合并或部署。

现行版本默认以`DESK_AUTO_OWNER=1`连接可信回环工作区；外部访问仍受原身份／配对边界约束，见[本机连接](desk-companion/docs/passwordless-device.md)。手机浏览器调试入口为`?surface=phone`，原生iPhone使用同一独立PhoneApp。本地运行后端Lint／测试和前端测试／构建，不连接模型或硬件；不使用GitHub CI。

硬件目录是采购前研究，仍缺完整免焊转接、电源／Qi／风机及实物验证；学校文件完成不等于已签署或提交。进入本仓库的代理先遵守 [AGENTS.md](AGENTS.md)。本次整理和验证见 [QA](output/qa/2026-10-26-repo-cleanup/verification.md)。

## 2026-10-29 OpenAI实时语音试验

完成Realtime2.1与GPT-Live1＋Luna两条路线的真实短测，并加入Mini英文费用参照。16次会话包含11次最终控制条件检查，费用按返回usage保守估算约0.304美元；本轮5美元额度已关闭。英／普／粤日历、待确认记忆及合成插话结果、初次失败和可试听录音见[QA](output/qa/2026-10-29-openai-realtime/verification.md)。504后端／15专项检查通过，无CI。这是独立评测工具，日常App尚未新增OpenAI提供商入口；[接入边界](desk-companion/docs/openai-voice-evaluation.md)。

## 2026-10-30 复杂应用任务

按用户要求，将主验收提高为浏览器＋电子表格＋文档／PDF＋日历／事务的[演示准备包](planning/2026-10-30/complex-application-acceptance.md)，包含中途改预算／数量／日期、不可行条件澄清、丢回执和重启恢复。[固定材料](desk-companion/evals/app_workflow_v1/README.md)与受限应用适配器已完成，真实 Chromium／Calc／Writer／PDF 的脚本任务、原日程更新及重启恢复通过；[本轮 QA](output/qa/2026-10-30-application-execution/verification.md)记录 524 后端／89 前端与实际网页／手机操作。完整语音自主执行仍待，未产生新模型费用。


本轮未合并 PR 的审查与整合见[2026-10-30 QA](output/qa/2026-10-30-all-pr-review/verification.md)。硬件组最新[采购 Excel、外壳 V3 和定位资料](research/2026-11-17-hardware-progress/README.md)见 11 月 17 日进度。[10 月 26 日教师审核稿](research/2026-10-26-hardware-procurement-review/README.md)保留历史。硬件实物采购和台架验收另行确认。
