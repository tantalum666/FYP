# Group 2 Current Handoff

更新：2026-10-06。状态：**本轮个人 AI Agent 讨论已整理；现有软件可继续，电脑执行层与新硬件待验证**。

## 当前任务与结论

用户要求先把这轮讨论结果推到GitHub。完整交接见[个人Agent讨论与下一阶段方案](planning/2026-10-06/personal-agent-discussion-and-next-steps.md)。真实、受限的电脑／软件操作是核心；统一身份、持久任务、语音、屏幕与现有日历。固定摄像头的标定→持续判断→反馈→复测仍是必做，不因Agent定位而取消。

用户主责软件／AI，另两人主责硬件，具体硬件工作包尚未对应姓名。实体概念是LUWU RIG-Arm＋Pi＋屏幕＋可拆卸迷你桌面清洁模块；ESP32为候选，尺寸／BOM／接口、采购、自动回座和无线充电未确认。

## 分支与本轮交付

从main `5b8ce5b81dd075cae3cef6787c964bf0406591e2` 建立独立 `codex/personal-agent-plan-20261006`。只更新Markdown与QA记录，应用代码、学校文件和身份资料不变。已有[RIG研究PR #1](https://github.com/tantalum666/FYP/pull/1)仍为未合并Draft；本轮核对head为 `085dc01e3ea360d4d1555189f542c435cd5e40e3`。两分支入口文件可能重叠，后续整合需审阅差异，不自动覆盖。

已整理：确认要求与待定项、当前实现边界、单一助理与可选多模型、异步任务／版本授权／未知写入、LCU许可及平台权限边界、最小证明矩阵、语音费用／质量测试、硬件安全和三人分阶段工作包。[本轮验证](output/qa/2026-10-06-personal-agent-plan/verification.md)。

## 已有软件与未验证项

[软件README](desk-companion/README.md)／[架构](desk-companion/docs/architecture.md)／[事务契约](desk-companion/docs/task-tracking.md)：React／FastAPI／SQLite日历、配对、持久任务、草稿确认、姿态软件、Qwen／Gemini适配及命名输出已实现。101项后端、11项前端等是[10月3日历史QA](output/qa/task-enhancement-ux-2026-10-03/verification.md)，本轮没有重跑。

模型默认关闭。没有通用PC执行器、LCU接入、RIG总线舵机或清洁模块实现。现有语音600秒／45秒限制、接收循环等待工具、无provider会话恢复，不等于全天在线Agent。实际云语音／粤语／AEC／费用、Pi负载、真实姿态标签、机械／停机与目标账号授权仍待验证。

仓库保持私人。[成员协作方法](CONTRIBUTING.md)继续适用，本轮未邀请成员。主机预览运行状态没有重新核实。学校Proposal／日志及计划贡献比例不因本次文档自动修订或批准。

## 唯一下一步

**按本轮方案P0／P1定义2至3个最小电脑任务与权限契约，准备Mac上可独立读回的受限执行验证，再决定LCU或替代执行器。** 需要安装第三方runtime、系统／浏览器权限、凭据／持久访问或付费服务时先取得对应授权；本轮没有安装、执行模型、动硬件、采购、合并或部署。
