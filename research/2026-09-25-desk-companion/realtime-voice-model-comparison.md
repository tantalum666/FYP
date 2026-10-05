# Group 2 免按键实时语音模型同口径比较（HISTORICAL）

**2026-09-29取代说明：**用户要求不按本地／API筛选，重新比较自然交谈与工具调用，并纳入第三方测评。当前推荐与下一步以[全面复核](../2026-09-29-voice-ai/naturalness-and-tools-review.md)为准。本页所有“首选”“当前顺序”均指9月25日的价格条件及历史偏好，不再定义现行验证顺序；包括旧豆包版本及未点名的Grok型号亦不能代表新版本。价格未在本轮全面刷新，不套给Qwen3.1或其他新型号。没有试听、账单、部署或模型测试。

核对日期：2026-09-25。状态：**公开规格与价格评估，未开通或实测任何语音 API**。按用户最新要求，本轮**不以服务地区筛选，不考虑按键说话**；研究免按键连续对话、能打断并通过函数调用控制 Group 2 桌面设备的方案。[上一份语音专项](voice-model-cost-review.md)的香港地区／按键首版结论仍保留为历史比较，本页的评选条件取代其“按键说话是首选”建议。这里的“所有”限定为截至本日可找到公开技术与计费依据、与实时语音和设备函数调用直接相关的主流方案；不能声称穷尽全部厂商或未公开型号。

## HISTORICAL：9月25日结论

**纸面功能／费用首选：`qwen3.8-omni-flash-realtime`。**官方列明流式音频输入、文字＋语音输出、自定义 Function Calling／MCP、WebSocket／WebRTC、服务端 VAD；新加坡价为输入音频 **US$0.93／百万 token**、输出音频 **US$1.87／百万 token**，而该型号的音频换算为输入 **7 token／秒**、输出 **12.5 token／秒**。[型号](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash-realtime)、[价格](https://www.alibabacloud.com/help/en/model-studio/model-pricing)、[计量](https://www.alibabacloud.com/help/en/model-studio/realtime)。这使它成为本次同口径**新增音频用量**算例中最低价、又具备设备工具调用的单模型。它于2026-09-21才进入官方发布清单，缺少本组真实口音、噪声、工具选择和长时稳定性实验；**不能把最低标价直接写成已验证的最高性价比或实际月费**。[发布清单](https://www.alibabacloud.com/help/en/model-studio/newly-released-models)。

**用户后续指定的考虑顺序：Qwen第一、Gemini第二、OpenAI Realtime第三、GPT-Live第四。**此处将“Realtime”按前一轮最常比较的低成本型号暂记为 `gpt-realtime-2.1-mini`，若后来指定完整版再调整。它有函数调用和官方可读取的每轮音频计量，VAD可过滤空输入；Mini 在指令／工具能力上可能弱于大模型，必须测具体任务。[OpenAI 型号](https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini)、[计费机制](https://developers.openai.com/api/docs/guides/voice-latency-cost)。第二位 `gemini-3.8-live` 支持异步函数调用和实时音频，但持续监听按输入音频计费，多轮又会重算上下文。[Google 型号](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live)、[成本与上下文](https://ai.google.dev/gemini-api/docs/live-api/best-practices)。这是先后验证顺序，**不是四款都必须接入成品**。

## 比较对象与自动操纵能力

| 方案 | 免按键语音和设备工具 | 当前公开费率 | 适用判断 |
|---|---|---|---|
| [Qwen3.8 Omni Flash Realtime](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash-realtime) | 服务端 VAD、流式语音、可中断；自定义函数及远端 MCP。Pi 收到工具请求后执行。 | 新加坡价：音频入0.93／出1.87、文字入0.23／出0.70美元／百万 token；**播报时音频和相应文字均计费**。[价表](https://www.alibabacloud.com/help/en/model-studio/model-pricing) | **首选实测。**纸面音频成本最低且工具齐全；新型号的实际工具正确率和机上稳定性未知。 |
| [OpenAI GPT-Realtime-2.1 Mini](https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini) | 语音到语音、打断、函数调用；VAD可自动分轮。 | 音频入10／出20美元／百万 token，文字入0.60／出2.40。[价格](https://developers.openai.com/api/docs/pricing) | **用户第三顺位／对照。**成本高于Qwen新增音频价，但空白输入可由VAD过滤；须测Mini的日历和设备工具正确率。 |
| [OpenAI GPT-Realtime-2.1](https://developers.openai.com/api/docs/pricing) | 同类实时接口与工具。 | 音频入32／出64美元／百万 token | 能作能力上限对照；比Mini明显贵，不能在未测任务成功率时说其总体更划算。 |
| [Google Gemini 3.8 Live](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live) | 流式双向语音、打断、异步函数调用；工具执行可不阻塞整段会话。 | 输入音频约0.005美元／分钟、输出约0.018美元／分钟，文本与历史上下文另计。[价表](https://ai.google.dev/gemini-api/docs/pricing) | **用户第二顺位。**功能完整；该型号的主动监听一直开启，长时输入和多轮重算需纳入预算。 |
| [OpenAI GPT-Live 1](https://developers.openai.com/api/docs/guides/live) | 全双工语音，复杂工作委派到独立后端；后端调用设备工具。 | 0.05美元／活跃会话分钟，双方静默或等工具也计，后端另计。[计费](https://developers.openai.com/api/docs/guides/voice-latency-cost) | **用户第四顺位。**自然对话参照，不适合整天保持活跃会话的低成本原型。 |
| [Amazon Nova 2 Sonic](https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-tool-configuration.html) | 实时语音及**异步工具调用**，AWS示例有真正双向与打断实现。 | [AWS官方应用算例](https://aws.amazon.com/blogs/machine-learning/live-meeting-assistant-with-amazon-transcribe-amazon-bedrock-and-strands-agents/)给约0.30–0.60美元／30分钟活跃语音，另有应用基础设施；具体账单依音频token和部署。 | 有能力但Bedrock流协议／部署工作更重，公开算例不足以断言比Qwen低价。 |
| [Grok Voice](https://docs.x.ai/developers/models/speech-to-speech) | 实时WebSocket，函数、MCP、搜索等工具。 | 开发者型号页为**0.08美元／送入或输出的音频分钟**，文字输入另0.004美元／条；营销页出现过0.05分钟价，比较以本次开发者价为准。 | 有工具，但按本次价格没有成本优势。 |
| [ElevenAgents](https://elevenlabs.io/pricing/agents) | 语音代理平台，可接LLM与外部工具，主打声音和托管。 | 额外语音通话约0.08美元／分钟，LLM另计；[长于10秒静默时有折扣](https://elevenlabs.io/docs/help-center/product/eleven-agents/how-much-does-eleven-agents-cost)。 | 产品平台而非单一语音模型；可作高质声音参照，不是低价硬件控制首选。 |
| [Hume EVI 4 mini](https://www.hume.ai/pricing) | 情感表达语音界面，工具依赖补充LLM。 | 价格页实际切到“EVI 4 MINI”后，Starter／Creator列约0.035美元／分钟，Pro额外用量0.03、Scale 0.025；补充LLM另计。 | [官方仅列英、日、韩、西、法、葡、意、德、俄、印地、阿语](https://dev.hume.ai/docs/speech-to-speech-evi/configuration/evi-version)，**暂未列中文**；不适合本组中英文主演示。 |
| [Deepgram Voice Agent API](https://developers.deepgram.com/docs/voice-agent) | 托管ASR＋LLM＋TTS流水线，支持中断与[客户端／服务端函数调用](https://developers.deepgram.com/docs/voice-agents-function-calling)。 | [标准Pay-As-You-Go为0.075美元／分钟](https://deepgram.com/pricing)，自带LLM/TTS与自备组件有不同价档。 | 平台可减少工程集成，但不是单个端到端模型；按标准价10活跃分钟／天约22.5美元／月。 |
| [Azure Voice Live](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live) | 托管语音层可选GPT/Phi等后端，支持降噪、回声消除、打断、Avatar与函数调用。 | 由所选Pro／Basic／Lite模型、音频／文本token和可选Speech／Avatar组成，[官方没有一个通用每分钟价](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live)。 | 适合要集成品牌声音与视觉角色的团队，但不是比Qwen更低价的单模型证据；须指定型号和配置才可同口径算。 |
| [豆包端到端实时语音](https://docs.volcengine.com/docs/DoubaoVoice/ProductOverview-5?lang=zh) | 中文拟人语音和打断较符合陪伴效果；[RTC方案](https://www.volcengine.com/docs/6348/1544162?lang=zh)在识别到函数意图时可交给另配LLM处理。 | RTC、语音模型、LLM／ASR／TTS可分项计，[官方RTC示例](https://www.volcengine.com/docs/6348/1392584?lang=zh)不能直接当独立端到端型号每分钟单价。 | 值得做中文声音质感对照；未查到与Qwen3.8相同配置、可直接换算的完整官方费率，**本次不排价格名次**。 |
| 本地组合：ASR＋小文字模型＋TTS | 本地唤醒词或VAD，Pi允许名单控制屏幕／灯／云台；可离线 | 无逐次云端费用，另有主机、散热、训练／维护工时 | 不应与上述端到端模型称为同一种“语音模型”。Pi5 8GB尚无本项目实时双工性能证据；作为离线与隐私基线。 |

DeepSeek、Kimi等**文字模型**可以替换工具决策的后端，但通常不能单独承担这一表里的实时收音与自然语音输出；需要额外 ASR/TTS或一个语音前端。[MiniMax当前公开语音价表](https://platform.minimax.io/subscribe/token-plan?tab=api-enterprise)列的是TTS字符计价，也不能直接当一套实时听说＋工具模型的价格。把文字模型或单独TTS的每百万token／每万字符价格和完整语音会话价格直接比较会漏掉最贵或最慢的环节。

## 同口径成本：短时对话与全天待命

下表用同一个假设演算，方便看数量级，**不是任何厂商已向本组开出的账单**。短时场景：每天用户说5分钟、助手说5分钟、30天；全天场景：每天向服务端送入8小时音频，并让助手每天说10分钟、30天。只计算可直接由公开费率换算的**新增音频**，排除历史上下文重算、系统提示词、工具／网页调用、输出文字、失败重试、税和设备成本。对不按新音频token计费的型号注明自身口径。

| 模型 | 5分钟用户＋5分钟助理／天，30天 | 每天送入8小时＋输出10分钟，30天 | 为什么实际账单会不同 |
|---|---:|---:|---|
| Qwen3.8 Omni Flash Realtime | **约US$0.27** | **约US$6.05** | 输入7 token／秒、输出12.5 token／秒；输出文字另计；多轮历史音频和指令反复计入。[官方计量](https://www.alibabacloud.com/help/en/model-studio/realtime) |
| GPT-Realtime-2.1 Mini | **至少约US$4.50** | 不把8小时直接乘音频价；VAD过滤的空输入目前不计模型输入token | 旧会话内容与输出会进入下一轮、文本另计；若客户端手工提交静音音频则可能计费。[官方说明](https://developers.openai.com/api/docs/guides/voice-latency-cost) |
| Gemini 3.8 Live | **音频基础约US$3.45** | **音频基础约US$77.40** | 主动监听永久开启，输入持续计费；历史上下文每轮重算、转写与文本另计。[官方说明](https://ai.google.dev/gemini-api/docs/live-api/best-practices) |
| GPT-Live 1 | **活跃10分钟／天约US$15** | **活跃8小时／天约US$720** | 语音前端计整段会话；后端模型／工具另计。[官方说明](https://developers.openai.com/api/docs/guides/voice-latency-cost) |

Qwen的算式可复核：短时每月为`30×[(300×7×0.93＋300×12.5×1.87)÷1,000,000]≈0.269美元`；全天为`30×[(28,800×7×0.93＋600×12.5×1.87)÷1,000,000]≈6.045美元`。这不是“长时间开着肯定只要6美元”：模型每轮仍会再次处理留在上下文中的历史音频，实际账单需要用代表性会话的usage字段核对。官方亦规定单个WebSocket会话最长120分钟；全天运行要有重连和短历史摘要。[连接限制](https://www.alibabacloud.com/help/en/model-studio/realtime)。

**免按键不等于要把全天室内声音都传到云。**本地唤醒词／本地VAD自动触发后，打开短的实时会话、无声一段时间后关闭，用户全程不按按钮。它能减少传输、误触发与计费；与真正“全天云端收音”是两个需要分别测试的用户体验。若用户要求连唤醒词也不要，Qwen在纸面**单位音频**价格仍低，但全天总价尚无可靠冠军：OpenAI官方说服务端VAD会过滤未被手动提交的空输入，而Qwen连续送音的静默计费细节需用usage实测。8小时噪声、多人说话和误调用也会改变真正的性价比。

## “模型自动操纵设备”应如何实现

模型不能直接连Pi GPIO或任意执行shell。可由Pi提供短的、带类型校验的工具，例如：`get_today_schedule`、`create_reminder_draft`、`set_focus_mode`、`set_display_scene`、`set_indicator_color`、`move_avatar_head`。用户说“把屏幕变暗并显示下一场会议”，模型返回两个函数调用；Pi验证参数、权限和当前状态后执行，回传真实结果，模型再口头说明。灯光／动画这类可逆动作可直接执行；新增／更改日历事项先读回、明确复述并确认，不把识别错的时间静默写入。[Qwen函数调用流程](https://www.alibabacloud.com/help/en/model-studio/realtime)、[Google异步工具](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live)、[AWS工具流程](https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-tool-configuration.html)均是“模型提出、应用执行、结果回传”的模式。

Qwen3.8的官方限制包括**内置网页搜索与自定义工具调用不能在同一个会话同时启用**、单WebSocket最长120分钟，以及上下文会丢弃超过上限的旧音频；我们优先使用设备工具，把日历和必要外部资料交给自己的受限后端。[官方限制](https://www.alibabacloud.com/help/en/model-studio/realtime)。

## HISTORICAL：9月25日实验安排

这是一份**按公开资料筛出的短名单**，不是语音质量或中文工具调用排行榜。新Qwen型号发布不久，不能凭厂商支持列表认定其在本桌面麦克风、房间噪声、普通话／英文切换及连续运行中好用。按用户指定顺序先测Qwen、再测Gemini；若需要第三个对照，再测OpenAI Realtime Mini；GPT-Live排第四。对进入测试的型号使用同一硬件、同一工具schema、同一日历数据，至少做：

1. 30个普通话／英语日程查询与提醒命令，含时间歧义、取消和改口；统计正确工具、参数、真正成功的设备动作，不能只统计模型口头说“已完成”。
2. 20个设备动作（屏幕、灯、头像小云台）与10个**不应执行**的含糊或背景语音；错误实体动作必须单列，不能被总体回答正确率掩盖。
3. 10个说话中打断、10个噪声／多人声场景；记录端到端第一句有效回答的p50／p95、误触发、错误打断、掉线／重连和10分钟及连续2小时账单。
4. 成功任务成本＝该模型实际账单÷正确完成且用户确认的任务数。若便宜模型误动作多、需重复三次，最终性价比可能反转。

**当前执行顺序：先用Qwen3.8 Omni Flash Realtime做免按键＋函数控制的首个原型；需要能力对照或Qwen不稳时，第二测Gemini3.8 Live；第三是OpenAI Realtime Mini，第四才考虑GPT-Live。**顺序来自用户最新选择，是否切换仍应看同任务实测，不能为了最低token价降低重要提醒或实体设备动作的可靠性。此前“必须按键说话”是上一轮为降低费用提出的工程建议，本轮不再把它作为模型选型的前提。新学校Proposal仍待定稿、无实机API证据。
