# Group 2 Current Handoff

更新：2026-10-12。当前：**首批5467342已发布、远端CI通过；持久多步骤Agent与真实浏览器执行继续实现**。用户最新要求读取现有工作、深入研究Grok Bot／Muse／dot、自主实现并将已验证工作推到GitHub；此任务取代前一轮单纯等待A1视觉反馈的当前下一步。

## 基线与保留

- PR #4仍为既有角色分支，不自动合并；本轮起点`50e174f50a4130b3c666f836f666f6aa4cde4b32`，main仍为`ccfac48ce8c68e6f9c8796911bbe5f35728d7807`
- 独立分支`codex/personal-agent-kernel-20261012`／[PR #5](https://github.com/tantalum666/FYP/pull/5)，首批提交`546734273c9c8305cf6226e96a8e07854ba5c0b1`；137项发布候选blob逐一读回匹配。叠加完整基树，未下载二进制不是删除项
- A1保持单张完整2D、连续缩放／拖动／贴边召回；被否决的分块／2.5D／3D不恢复。学校、全部美术／实际prompt、旧许可VRM和用户Mac已有预览运行数据保留
- 既有Mac预览localhost:8832是上一轮服务，不是本轮云端实例；没有据此声称Pi／Linux实机已验收

## 已完成并重新验证

- 186份自有Markdown全文阅读，固定提交hash与行范围／EOF记录见[本轮QA](output/qa/2026-10-12-agent-kernel/reading-union-status.json)
- 起点149后端／28前端通过；首批新增后361后端／50前端、Ruff、TypeScript、Vite构建通过；A1与VRM来源hash核对通过，详见[首批核验](output/qa/2026-10-12-agent-kernel/checkpoint-verification.md)
- [三家公开研究与实施入口](planning/2026-10-12/personal-agent-implementation.md)，明确消费级产品和可用开发API的区别，没有取得或使用私有内部实现

## 进行中与未验证

首批提供商端点规则、可审阅个人记忆、选择保留的文字线程、独立测试应用执行器、持久本地职责、英中界面及CI配置已实现并通过软件检查。独立审查发现的隐私／并发／旧来源问题已修复。远端push／PR两次[CI](https://github.com/tantalum666/FYP/actions/runs/38265191556)已通过，真实浏览器仍在隔离Mac任务验收，不把软件检查当作全链路已验收。用户质疑能力广度后，后续优先级调整为持久多步骤Agent、真实来源／成果文件和现有应用操作，不先堆供应商开关。

A1原PNG已从必要的Mac验证任务补齐，原字节hash一致；该任务准备了隔离checkout，未改已有8832预览，正在按准确提交5467342进行真实浏览器验收。真实模型自然度／费用、音频／摄像头、Pi／iPhone／RIG／清洁模块、一般PC／LCU及账号授权仍需真实条件，协议替身与软件测试不能冒充这些成果。

## 唯一下一步

按[持久Agent设计](planning/2026-10-12/durable-agent-run-design.md)完成并验收真正的目标→计划／工具→审阅→结果→恢复工作链，同时修复现有Mac验收发现；只有通过检查的批次推到PR #5。必要的新Codex会话按用户指定6.1 Sol Max，优先继续云端。

三家产品能力／差距、LCU边界与真实应用验收路线见[能力总览](planning/2026-10-12/agent-capability-roadmap.md)。真实模型质量、通用桌面及实物仍不得称为完成。
