# Group 2｜首次真实模型小验收（待批准，未执行）

核对日期：2026-10-13。这里只提出一次小实验，不确定最终模型。保持同一个助理／任务核心；实时语音直接使用受限工具，文字推理按需单独验证，不要求每次说话都串联第二个模型。

## 1. 条件候选，不是最终选型

最低准备成本的分阶段建议：仅当用户已有合法合资格的 Alibaba Cloud Singapore 账户／工作空间，先只执行下文的一次 `qwen3.6-flash` 文字规划测试。语音候选为 `qwen-audio-3.1-realtime-plus`，但付费语音必须另过输出／费用控制门槛，不能和文字测试捆绑成已获准调用。若已有合资格 Gemini 项目，则可少开一个供应商账户，使用以下同样受限的备选：

- 语音：`gemini-3.8-live`，`wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`，现有 `gemini` 语音适配器
- 文字：`gemini-3.5-flash-lite`，`https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent`，现有 `gemini` 文字适配器；配置的 ENDPOINT 只填到 `/v1beta`，代码会添加模型路径

Google 官方确认前者在 2026-09-15 GA，后者是稳定型号；Live API 的通用协议参考页仍标 preview，不能把模型 GA 当作整个传输协议永不改变。当前官方可用地区列表没有香港，必须先核对用户实际使用地区与账户资格；不能假定香港账户可用，也不建议绕过地区限制。[发布记录](https://ai.google.dev/gemini-api/docs/changelog)、[语音型号](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live)、[文字型号](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)、[传输协议](https://ai.google.dev/api/live)、[地区要求](https://ai.google.dev/gemini-api/docs/available-regions)

Qwen 的确切配置如下；先核对 Singapore 工作空间与模型是否可用：

- 语音：`qwen-audio-3.1-realtime-plus`，`wss://{实际WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/api-ws/v1/realtime`，配置 provider=`qwen_audio`；代码会添加 `?model=...`，配置本身不带 query
- 文字：`qwen3.6-flash`，`https://{实际WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions`，provider=`qwen`；沿用 `enable_thinking:false`、JSON object 与本地 schema 校验

这两个工作空间域名形状已经被 `provider_policy.py` 接受，不需要放宽端点白名单。工作空间 ID 必须来自用户实际控制台，不能照抄占位符。Alibaba 当前文档列有上述模型和 Singapore 服务，语音也列 Beijing；这不证明用户自己的账号已获访问。[语音型号与报价](https://www.alibabacloud.com/help/en/model-studio/qwen-audio-3-1-realtime-plus)、[文字型号与报价](https://www.alibabacloud.com/help/en/model-studio/qwen3-6-flash)、[OpenAI 兼容入口](https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope)、[JSON 支持](https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output)

本次没有发现这些重点型号／日期缺乏当前官方公开支持；没有重新验证历史报告中的所有其他厂商与排行榜。

## 2. 已支持与仍需补的小门槛

- 当前 Qwen 的 `smart_turn`、嵌套 function 定义、`input_audio_buffer.append`、函数结果加 `response.create`，与官方事件契约吻合；两家输入 16 kHz／16-bit／单声道 PCM，输出 24 kHz 路径已有适配。Qwen 搜索保持关闭，不能与 function calling 同时启用。[Qwen 指南](https://www.alibabacloud.com/help/en/model-studio/qwen-audio-realtime-user-guides)、[客户端事件](https://www.alibabacloud.com/help/en/model-studio/fun-audiochat-client-events)、[Gemini 能力](https://ai.google.dev/gemini-api/docs/live-api/capabilities)
- Gemini 当前配置正确省略普通 3.8 Live 不支持的 `thinkingLevel`。现有转写保守标为未最终确认；必须让本人选定／编辑快照，不能把 assistant `turnComplete` 当用户已经明确授权。
- 文字适配器发送 JSON MIME／JSON object 和 schema 提示，再由本地 Pydantic 验证；它没有请求供应商端严格 JSON schema。这不是严格 schema 成功保证，错误 JSON 应算验收失败，不能自动再收费修复。
- 当前语音上限是 600 秒／闲置 45 秒，并无请求总数、输出 token／美元硬上限。下一步需要单独审阅的测试夹具：60 秒外部 watchdog、单次连接、禁止重连、最多一次工具请求与一次结果回复，只开放 `task_create_draft`；在连接前审查完整 payload 和隔离数据库。
- Gemini 可用已记录的 `generationConfig.maxOutputTokens` 加低输出上限，例如每次生成 512。当前代码没有发这个字段。Qwen 本轮读取的客户端参考未列对应输出上限，不应套用其他 Realtime API 的 `max_response_output_tokens`。Qwen 需以断开／回复次数／接收音频大小约束，并保留账单延迟风险；不能宣称同等服务端 token 硬限。
- 以上在线夹具／小配置增量仅为研究提案，本文件不声称实现或通过。当前异步工具 dispatcher 已存在；10 月 6 日历史文档所述“接收路径等待工具”不能继续当成当前源码事实。会话恢复和真机回声消除仍不在这次小验收范围。

## 3. 首次提案：仅合成文字，不包含语音

本次建议只申请一次文字规划调用；用户没有批准该调用或任何支出。账户／区域／模型未核实，不能默认可用，也不为了试验自动开通账户。

使用全新空白隔离数据库。个人记忆／历史为空，不导入现有任务、日历、个人文件或学校资料。后台 AI、语音服务、浏览器执行器、硬件与自动职责关闭。

**唯一拟议外传内容：**应用的文字规划系统说明、必要 JSON schema、下面这条虚构任务命令及必要的虚构 UTC 测试时间／时区。提交前列出并审查最终 JSON 正文，合计不超过 16 KiB。不发送音频、麦克风、图片、文件、个人记忆、既有任务、工具执行结果或后续对话；不进行第二次模型请求。服务会正常获得网络连接元数据。认证只使用另行批准且安全配置的服务端机制；秘密不进聊天、日志、前端或仓库。

合成命令：请只提出一个待审阅的本地任务草稿，标题为“FYP synthetic test A”，不要保存任务或安排提醒。

- 方法：仅一次非流式 HTTPS POST，`qwen3.6-flash`，`enable_thinking:false`、JSON object，现有 `max_tokens:1600`
- 拟议夹具限制：一次请求、无重试／自动格式修复、16 KiB 正文、外部进程 45 秒 wall-clock watchdog。现有 HTTPX 5 秒 timeout／30 秒分块检查不是硬 wall-clock 保证；watchdog 也不是账单硬限
- 结果：仅本地验证一次 `TextPlan`，检查工具为 `task_create_draft` 且虚构标题准确；若需展示，只保存隔离本地待审阅提案，不批准、不建立提醒、不执行 computer job、不向供应商回复工具结果
- 停止：401／403／429、无效 JSON／schema、越界意图、超时、收费条件变化、任一上限或不可核算用量即结束。不重试，不换模型，不转语音
- 证据：最终配置摘要与虚构 payload、实际模型、一次请求计数、schema 验证／本地读回、usage 与实际控制台费用；全部隐藏认证信息

文字成功只证明这一次规划／格式路径；不证明真实语音识别、麦克风、声音自然度、长任务或一般电脑操作。

### 独立后续提案：语音协议／合成语音验收

以下不是上述文字测试的一部分，需要另行决定、准备和批准。不得因文字测试通过而自动运行。

未来语音拟议发送内容包括：语音系统说明、虚构 UTC 时间／时区、一个草稿工具定义、事先审查的合成语音命令，以及一次虚构本地草稿工具结果（标题／测试 ID）。不发送真人环境音、个人资料或真实业务数据。若仅以虚构文字输入实时端点验证音频输出，必须明确记为“文字入／声音出协议测试”，不能声称验证了 ASR。

- 一次 WSS 连接；外部 watchdog 从连接开始计 60 秒；禁止重连
- 合成 PCM 输入至多 10 秒／320,000 原始字节，按实时速度分块；不能另调云 TTS 制作夹具。无合成音频时保留 ASR 未测
- 最多一轮输入、一次本地 `task_create_draft`、一次结果回复与简短播报；只开放这一个工具
- 接收至多 20 秒 PCM／960,000 字节，超限断开；停止后不新增请求
- Gemini 可提案增加服务端 `maxOutputTokens:512`；Qwen 不宣称具有对应服务端输出上限。声音可以快于播放速度生成／到达，断开也不能撤回已产生的费用；这些本地限制不是账单硬限
- Qwen 语音先过第 4 节费用控制门槛；未通过则不运行付费语音

## 4. 费用与用户准备

Google 当前标准美元价（每百万 token）：Live 文字入／出 0.75／4.50、音频入／出 3／12；Flash-Lite 入／出 0.30／2.50。其免费档受项目实际配额限制，免费档内容可用于改进产品；付费档价表标为不用于改进产品。[价目](https://ai.google.dev/gemini-api/docs/pricing)、[实际配额](https://ai.google.dev/gemini-api/docs/rate-limits)

Qwen Singapore：Audio 3.1 Plus 文字入／出 0.8／6.4、音频入／出 6.4／24；3.6 Flash 短上下文入／出 0.25／1.5 美元／百万 token。价格必须绑定区域，不能用 Beijing 报价替代 Singapore。

先只批准一次文字调用更稳妥：以约 6,000 输入 token 加最多 1,600 输出 token 的 Qwen 短请求估算，模型费约 US$0.0039；6,000 是估算，并非由 16 KiB 自动证明的精确 token 数。可请求该一次调用 US$0.10 总支出上限，非订阅，并在实际控制台确认费用／税与适用保护。不能将预算余额自动用于第二次请求。

语音短场景通常只涉及美分级模型费，但没有当前 Qwen 服务端输出 token cap 的证据，因此不提供伪精确的付费硬上界。只设 60 秒 watchdog、20 秒接收量和两次生成，仍无法约束断开前供应商已生成但未收取的内容。需先验证该模型有效的 Free Quota Only 保护，或取得官方支持的输出限额并加到夹具；否则暂缓付费语音。Gemini 分支可使用服务端 maxOutputTokens，再结合调用次数与 watchdog，但仍需实际账户费用保护／预算批准。上述预算都只是提案，没有取得用户批准。

Gemini 3.8 永久启用主动监听，整段监听及多轮历史重算、转写文字都可能收费；不能只用十秒命令估算全部费用。[计量细节](https://ai.google.dev/gemini-api/docs/live-api/best-practices)

Alibaba 免费额度仅适用于符合条件的 Singapore International 模型；新额度通常有 90 天有效期，按模型分别计，继续使用可能转按量收费。Free Quota Only 默认关闭、并非所有模型都有，设置生效也可能延迟；必须在实际控制台核对，不能承诺这次免费。[免费额度条件](https://www.alibabacloud.com/help/en/model-studio/new-free-quota)

用户先决定供应商／合法区域，并自行完成需要的账户与凭据安全配置；开新账号、接受新服务条款、生成／配置长期凭据、增加计费或传输真实个人资料均需各自适当批准。不要在聊天中提供 API key。仅有“继续开发”不代表同意这些动作。

## 5. 首次文字验收勾选表

- [ ] 用户确认供应商、具体数据、一次试验范围与预算；账户／区域／配额可用
- [ ] 无秘密出现在代码／聊天／日志；隔离数据库为空；语音及执行器关闭；已审查限额夹具
- [ ] 最终 HTTP 正文仅含已审查的虚构文字与 schema，无音频／工具结果／个人资料
- [ ] 恰好一次模型请求；工具名／参数通过本地验证，至多一个隔离待审阅草稿，没有提醒或外部写入
- [ ] 回复准确说“待审阅”，未谎称已完成；停止后没有新 provider 请求
- [ ] 记录实际型号、日期、事件／时延、请求数、usage、草稿独立读回及控制台费用；隐藏凭据
- [ ] 401／403／429、收费条件变化、协议错误、越界工具、额外生成、超时或任一大小上限触发即停止；无自动重试
- [ ] 分开标注通过／失败／未测。一次成功只证明这条链路，不能宣称粤语自然度、Pi AEC、长会话、一般自主电脑操作已验收

本文件本身不授予任何调用、账户、费用或数据分享权限；没有执行模型调用、账户操作、安装或代码修改。

## 6. 阅读与验证边界

沿用本轮已完成的项目 intake，仅补读模型历史讨论与相关实现；没有重新开展全库审查。聚焦来源：

- [10 月 6 日讨论](../2026-10-06/personal-agent-discussion-and-next-steps.md)
- [9 月 29 日语音研究](../../research/2026-09-29-voice-ai/naturalness-and-tools-review.md)与[价格研究](../../research/2026-09-29-voice-ai/price-and-value-ranking.md)
- [voice.py](../../desk-companion/backend/desk/voice.py)、[text_ai.py](../../desk-companion/backend/desk/text_ai.py)、[provider_policy.py](../../desk-companion/backend/desk/provider_policy.py)
- [本次研究 QA 与公开来源清单](../../output/qa/2026-10-13-live-model-trial-gates/verification.md)

公开页面访问日期均为 2026-10-13 UTC；账户实时配额、实际账单、模型响应和真机性能均未检查。独立离线 preflight 工作不由本研究证明；本文件编写时未引用尚不存在的完成证据。
