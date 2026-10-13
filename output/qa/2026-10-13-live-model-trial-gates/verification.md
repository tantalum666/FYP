# Group 2｜真实模型小试验门槛研究 QA

日期：2026-10-13 UTC。状态：仅公开文档与源码研究完成；在线试验未执行，无模型选定、费用批准或账户可用性结论。

## 范围与产物

- 主产物：`planning/2026-10-13/live-model-trial-gates.md`
- 本工作只新增该研究文档和本 QA 目录；未修改应用代码、共享入口规范或学校文件
- 沿用同一工作轮由父任务管理的 intake，本研究不是新一轮全库审查
- 聚焦阅读：`planning/2026-10-06/personal-agent-discussion-and-next-steps.md`（架构／模型讨论）；`research/2026-09-29-voice-ai/naturalness-and-tools-review.md` 与 `price-and-value-ranking.md`；`desk-companion/backend/desk/voice.py`、`text_ai.py`、`provider_policy.py`（协议、配置、限制）；`desk-companion/docs/voice-work.md`（转写／草稿边界）；`desk-companion/backend/desk/agents/voice.py`（音频格式／AEC 声明）
- 不复制账户标识或密钥；端点中的 WorkspaceId 是明确占位符

## 已实施事实与提案分开

源码事实：Qwen 非思考 JSON 请求已有 1,600 输出 token 字段；端点白名单接受指定 workspace 域名；语音现有 600 秒／闲置 45 秒限制；当前异步工具 dispatcher 已存在；Gemini 语音没有输出 token 字段；本地 schema 验证不等于供应商严格 schema 保证。

仅为提案：一次在线 POST、16 KiB 发送正文限制、外部 45 秒文字／60 秒语音 watchdog、在线测试工具白名单、Gemini 512 token 上限、账户侧费用保护、任何预算、在线验收及真实账单。独立离线 preflight 实现未由本研究测试或背书。

所有付费调用、账户开通、持久凭据配置和数据分享均未批准。没有 API 推理调用、安装、Git 操作、凭据操作、账户查询或真实数据上传。公开开发者文档读取不代表调用模型。

## 关键核对结果

1. 当前官方文档确实支持 gemini-3.8-live、其 2026-09-15 GA 日期和 qwen-audio-3.1-realtime-plus；没有理由把这些重点历史记录标成不存在。其他历史厂商／排行榜未重验
2. Google 可用地区列表未列 Hong Kong；实际账户／运行地区资格未知，不能绕过
3. Qwen Singapore 候选只能在用户已有合资格账户时作为低准备成本建议，不是强制选型；没有就先等待账户选择与授权
4. 首次只提案文字：外传系统文字、JSON schema 和虚构命令／必要虚构测试时区；明确排除音频、工具结果和真实资料。语音另列后续提案
5. Qwen realtime 客户端事件参考未找到 max_response_output_tokens 或 max_output_tokens；不虚构服务端 cap。断开／watchdog／收取字节数不能保证供应商账单上界
6. 两家免费条件、数据使用／额度期限、按量回退与账户侧保护必须在实际控制台核对；没有承诺免费
7. 文字费用算例：6,000 × 0.25 / 1,000,000 + 1,600 × 1.5 / 1,000,000 = USD 0.0039。输入 token 数是估算，不是 16 KiB 的精确 token 转换；USD 0.10 是未批准的提议上限，不是实测账单

## 公开来源（全部于 2026-10-13 UTC 读取）

- https://ai.google.dev/gemini-api/docs/changelog
- https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live
- https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite
- https://ai.google.dev/api/live
- https://ai.google.dev/gemini-api/docs/available-regions
- https://www.alibabacloud.com/help/en/model-studio/qwen-audio-3-1-realtime-plus
- https://www.alibabacloud.com/help/en/model-studio/qwen3-6-flash
- https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope
- https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output
- https://www.alibabacloud.com/help/en/model-studio/qwen-audio-realtime-user-guides
- https://www.alibabacloud.com/help/en/model-studio/fun-audiochat-client-events
- https://ai.google.dev/gemini-api/docs/live-api/capabilities
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://ai.google.dev/gemini-api/docs/live-api/best-practices
- https://www.alibabacloud.com/help/en/model-studio/new-free-quota

补充参数核对：
- https://help.aliyun.com/en/model-studio/qwen-api-via-openai-chat-completions ：HTTP 顶层 enable_thinking 与非思考设置

使用公开官方开发者原始资料；无社交媒体推断，没有读取用户控制台或模型列表账户 API。价格／型号仅是访问日期快照。

## 本地文档检查

- 检查本产物全部本地相对链接目标存在
- 检查所有公开来源均为 Google／Alibaba 官方域名
- 检查主产物明确“没有批准”、text-only 排除音频／工具结果、Qwen realtime 无 cap 证据，以及 watchdog 非账单硬限
- 未跑单元测试／UI／音频测试；仅文档研究，不冒充实现验收
