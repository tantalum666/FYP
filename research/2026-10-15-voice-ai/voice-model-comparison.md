# Group 2：语音模型全面复核（2026-10-15）

状态：公开资料、当前价格与独立评测复核完成；没有试听、麦克风采集、模型调用、账号开通或最终选型。适用对象是 Desk Companion 的自然交谈、普通话／英语／粤语与混说，以及日历和受限电脑作业。覆盖主要公开实时模型、托管组合平台、开放模型及 ASR／TTS 组件，不声称穷尽未公开系统。

**后续用户决定与实现，2026-10-16–17：**用户选择Qwen3.8 Omni Flash Realtime，提供国内千问平台指南并批准合成资料真实短测最多人民币5元。[本机设置](../../desk-companion/docs/qwen-local-setup.md)与独立[Omni适配](../../desk-companion/docs/qwen-omni.md)完成在草稿PR #15；两次虚构日历语音／一次生成图片问答通过。Mac收包3.176秒／2.619秒不是浏览器实际播音、p95或Pi验收。预留4.1元不是账单，已返回usage估算0.106608元有失败／取消缺口。下文“未选／未调用”指10月15日研究时点，旧排名不覆盖用户选择；自然度／多语言／GUI仍未验。详见[QA](../../output/qa/2026-10-16-qwen-omni-integration/verification.md)。

本稿取代 [9月29日自然度报告](../2026-09-29-voice-ai/naturalness-and-tools-review.md)、[价格报告](../2026-09-29-voice-ai/price-and-value-ranking.md)及 [10月14日架构建议](../../docs/tooling-and-review/companion-architecture.md)中的**当前候选顺序**。旧资料保留为 HISTORICAL。学校 Proposal、已选 A1 完整2D形象、软件功能和购买权限不因此改变。

**同日新增时效门槛：**用户要求“下周有什么会议”等查询约5秒给出有用答案、在10秒以内回答。当前[验收方案](../../planning/2026-10-15/voice-response-latency.md)把说完到实际播放有依据信息作为指标，首音／铺垫不能代替；本轮仅有本地工具离线测量，所有模型仍未通过端到端5秒验收。下述能力／费用优先级须同时受这一速度与正确性门槛约束。

**同日跨应用补充：**用户希望类似computer use的真实跨应用操作。[独立比较](computer-use-comparison.md)讨论Claude／GPT／Gemini规划模型及执行器，本报告的语音质量／工具排名不作为GUI排名。日常GUI建议先对照Sonnet5.5与6.1 Sol，复杂任务再看Opus5.5／Astra；这不是用户已选供应商，也不是已接入。

**同日Pi／一模型补充：**用户希望在Pi Linux运行，最终兼有本机与另一台电脑操作，并询问先Linux是否更简便。单模型听说、看截图和调用自定义动作可研究Realtime2.1、Gemini3.8 Live／Extended、Qwen3.8 Omni；这是能力组合，不是已验证的专用GUI Agent。按中文／Pi／学生原型约束，新增Qwen Omni新加坡SKU优先核验建议，未取代普通语音质量榜、冻结系统范围或选定提供商。地区与Wayland适配见[补充](computer-use-comparison.md#树莓派linux网络与单模型补充)。

## 1 这次实际更新了什么

| 项目 | 当前核对结果 | 对旧结论的影响 |
|---|---|---|
| Grok Voice 3.0 | 10月14日发布并开放 API；固定 ID 为 `grok-voice-3.0`；`grok-voice-latest` 已指向它，2.0 标为 deprecated；维持 $0.08／分钟 | 从第二轮工具备选升为首轮质量挑战者；不再拿2.0分数代替3.0。[发布](https://x.ai/news/grok-voice-3)、[API](https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech) |
| Gemini | 10月13日 GA 的是 `gemini-4-argon`，支持音频输入、文字输出，**不支持 Audio generation 或 Live API** | Argon 可作文字／任务后台，不是新的 Gemini 4 实时语音前台。[更新记录](https://ai.google.dev/gemini-api/docs/changelog)、[能力卡](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon) |
| Gemini 实时与合成 | 实时主线仍为9月15日的 `gemini-3.8-live`／`gemini-3.8-live-extended-thinking`；9月22日发布3.8 Flash TTS及Flash-Lite TTS | Live与TTS分开比较；不能把TTS换代或消费端声音变化当作Live换代。[Live](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live)、[发布记录](https://ai.google.dev/gemini-api/docs/changelog) |
| Amazon | 10月5日 GA `Nova 2.5 Sonic`，取代旧2.0作为当前候选；异步工具、分轮和推理改进 | 官方支持七种语言，仍未列中文；不把旧2.0榜单成绩给2.5。[发布](https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-nova-2.5-Sonic/)、[服务卡](https://docs.aws.amazon.com/ai/responsible-ai/nova-2-5-sonic/overview.html) |
| ElevenLabs | 9月28日发布 Eleven v4／v4 Turbo；10月5日文档将Agents默认语音模型改为v4 Turbo | A1角色声音路线应比较新版，而非只看v3；约100ms是厂商的TTS推理中位数，非整条语音Agent延迟。[发布记录](https://elevenlabs.io/docs/changelog/2026/9/28)、[Agents更新](https://elevenlabs.io/docs/changelog/2026/10/5) |
| Hume | 10月2日公告EVI与TTS API将在11月13日00:01 EST结束访问 | 从新项目接入候选移到历史／迁移观察；旧EVI推荐不再适用。[公告](https://dev.hume.ai/voice/changelog) |
| 其他组件 | MiniMax当前API列Speech2.8 HD／Turbo；Cartesia有Sonic3.6／Ink2；Deepgram有Flux STT／Flux TTS | 旧2.6／较早Sonic／只列Nova3与Aura2的组件清单不完整；这些仍须搭配LLM和会话控制。[MiniMax](https://platform.minimax.io/docs/guides/models-intro)、[Cartesia](https://www.cartesia.ai/pt/blog?category=news)、[Deepgram](https://deepgram.com/learn/introducing-flux-tts-conversation-native-text-to-speech-for-real-time-voice-agents) |

## 2 当前独立证据：能力、偏好和速度分别看

以下为10月15日打开的 [Artificial Analysis语音总表](https://artificialanalysis.ai/speech-to-speech/)的确切配置快照。Index由四项等权组成；Elo部分在发布时冻结，不能用后来变化的实时Elo重算。τ-Voice评价模拟服务任务的数据库最终状态；它与真人Arena成功率是不同指标。

| 确切配置 | 综合Index | τ-Voice（%） | 对话动态（%） | 推理题首音均值（秒） |
|---|---:|---:|---:|---:|
| Grok Voice 3.0 | 86.9 | 71.6 | 97.0 | 0.81 |
| GPT-Live-1，Astra medium | 83.2 | 74.5 | 94.9 | 1.34 |
| Gemini 3.8 Live Extended Thinking，High | 82.6 | 68.6 | 91.9 | 1.35 |
| GPT-Live-1，Sol low | 80.1 | 59.3 | 97.3 | 1.24 |
| Gemini 3.8 Live | 76.0 | 30.1 | 96.1 | 1.18 |
| GPT-Realtime-2.1，High | 75.2 | 45.7 | 95.7 | 1.21 |
| Qwen Audio 3.0 Realtime Flash | 67.7 | 35.9 | 96.9 | 1.55 |

Grok3.0目前综合领先，GPT-Live的Astra配置在该τ-Voice项更高。Gemini普通版的后台复杂推理项较弱，而接话／日常任务表现有价值；Extended Thinking并非所有场景都更自然。首音来自Big Bench Audio推理题，不是香港网络、Pi整机或同一套中文聊天测试。StepAudio3另有98.9%的对话动态及8.83秒推理题首音，但没有完整四项，不能补造综合分。

真人 [Speech Agent Arena](https://artificialanalysis.ai/speech-to-speech/arena)快照：

| 配置 | 整体偏好Elo及95%区间 | 工具任务成功率及95%区间 |
|---|---|---|
| Gemini 3.8 Live | 1088；1059–1117 | 93.2%；89.0–95.8 |
| Grok Voice 3.0 | 1070；1042–1099 | 94.8%；91.6–96.8 |
| GPT-Live-1，Astra medium | 1056；1029–1083 | 87.4%；82.9–90.8 |
| GPT-Realtime-2.1，High | 939；913–964 | 91.5%；87.7–94.3 |
| Qwen Audio 3.0 Realtime Flash | 852；814–891 | 81.7%；70.1–89.4 |

Grok与Gemini的两个区间均重叠，没有依据宣布二者在真人偏好或工具成功上显著分出胜负。旧Gemini3.1 Flash Live Minimal的偏好Elo仍为1100，但任务成功率为74.6%；旧型号不必然更难听，单看偏好也不能判断办事能力。此榜主要是给定场景中的整体偏好，不等于纯音色榜，也不是粤语榜。当前默认ElevenLabs／Deepgram／Cartesia／Inworld组合成绩属于榜单列出的组件配置；更新TTS或后台LLM后不能继承原成绩。

**没有新试听结论。**Jarvis页面本轮文本抓取为空，EVA页面也未返回可核读的榜单；9月29日Jarvis快照仅保留历史。Grok发布文中的EVA得分没有升级为本轮独立复核。没有找到这些最新版在同条件粤语完整Agent任务上的充分公开对照；缺数据不是零分。

## 3 原生实时语音／语音前台候选

“可接入”只表示公开文档存在，不表示本人的账号、所在地区、并发、音色或账单资格已通过。全双工音频传输、模型能否理解附和与改口、工具能否正确完成，须分别检验。

| 候选 | 本轮核对的能力与限制 | 本项目的位置 |
|---|---|---|
| [Grok Voice 3.0](https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech) | 实时听说、函数、MCP和搜索；默认reasoning high；明确列中文／英语，未单列粤语保证；官方称兼容OpenAI Realtime，但有事件差异 | **首轮质量挑战者**。复杂办事与低首音证据强；新版本需验证中文声音、粤语、会话费用和取消 |
| [Gemini 3.8 Live](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live) | 普通低延迟Live，默认异步工具；主动音频常开，旧affective参数已移除；中文／英语在官方语言表内，粤语需实测 | **日常会话与费用基线**。已有适配器；直接API地区资格需先核实 |
| [Gemini 3.8 Live Extended Thinking](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live-extended-thinking) | 持续交谈期间做后台思考／工具；turnComplete不代表后台idle，要处理interaction_status；仅异步非阻塞工具，额外思考会影响用量和体验 | 多步任务对照，不能用其High配置代替普通Live的成绩 |
| [GPT-Realtime-2.1](https://developers.openai.com/api/docs/models/gpt-realtime-2.1) | 语音、图像、直接函数调用，可调思考；官方强调字母数字、噪声、静默和打断改进 | 成熟协议与质量对照；本仓库尚无此适配器，不能仅填model字符串启用 |
| [GPT-Realtime-2.1 Mini](https://developers.openai.com/api/docs/pricing) | 更低音频费率；Mini需单独测理解和写入参数，不能继承完整版分数 | 后续降本对照，公开价不必然低于Gemini／QwenPlus |
| [GPT-Live-1＋任务后台](https://developers.openai.com/api/docs/models/gpt-live-1) | 全双工语音前台，推理／工具委派后台；后台版本和思考强度决定结果 | 长任务时继续聊最贴合Agent形态的候选之一；会话与后台分别计费 |
| [Qwen Audio 3.1 Realtime Plus](https://www.alibabacloud.com/help/en/model-studio/qwen-audio-3-1-realtime-plus) | smart_turn、音频输入输出、函数、声音复刻；[指南](https://www.alibabacloud.com/help/en/model-studio/qwen-audio-realtime-user-guides)明确含粤语等方言；内置搜索与函数不能同时启用 | **首轮中文／粤语候选**。已有协议适配；仍缺同版本独立真人工具比较 |
| [Qwen Audio 3.0 Realtime Flash](https://www.alibabacloud.com/help/en/model-studio/qwen-audio-3-0-realtime-flash) | 双工、smart_turn与函数，低价；本轮未核到3.1 Flash正式SKU | **低成本基线**；复杂任务须验证，不因低价推定质量相同 |
| [Qwen3.8 Omni Flash Realtime](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash-realtime) | 音视频、函数／远程MCP、多通道输入；输出文字与音频分别收费；当前报文有自身结构 | 需要视觉会话时再升优先；固定姿态算法仍独立。不能继承3.5 Omni榜单结果或当作Audio协议完全同款 |
| [StepAudio 3 Realtime](https://static.stepfun.com/blog/stepaudio3/realtime/) | 原生双工、边说边思考、工具方向；公开型号`stepaudio-3-realtime-preview`仍限时免费；首音风险见上表 | 中文第二轮／近期低费用试验候选；正式选型前核对完整工具事件与配额 |
| [豆包实时语音3.0／Seeduplex](https://docs.volcengine.com/docs/6561/2549732) | 官方索引已给出3.0标准Realtime JSON事件、取消、session和tools；直达编号本轮跳到接入页，完整协议／SKU映射仍需复核 | 中文第二轮；不用App体验证明本组API、工具或粤语已经通过 |
| [SeedRealtime](https://seed.bytedance.com/en/blog/seedrealtime-audio-visual-full-duplex-llm-released-toward-omni-modal-natural-interaction) | 音视频双工研究／发布方向；本轮未核定与Seeduplex等价的公开API契约 | 观察，不作为已经可采购的同一产品 |
| [Nova 2.5 Sonic](https://docs.aws.amazon.com/ai/responsible-ai/nova-2-5-sonic/overview.html) | 实时语音、异步工具；英语等七种正式支持语言，中文不在其中 | 英语／AWS路线备选；不作中英／粤语主线 |
| [Higgs Realtime](https://www.boson.ai/higgs-realtime) | 原生音频、函数、中文及多语言；厂商有低价与延迟说明，AA也有部分项目；[官方集成说明](https://www.boson.ai/blog/higgs-realtime-pipecat)承认兼容协议存在差异 | 新补进低成本观察组；厂商与旧代模型的自测不证明胜过Grok3／Gemini3.8 |
| [Deepslate Opal](https://github.com/deepslate-labs/deepslate-benchmarks) | AA有低首音数据；作者仓库说明语音生成处于闭测时公开API走音频入／文字出，当前输出权限需核对[文档](https://docs.deepslate.eu/websocket) | 不因440ms就列为现成完整语音工具主线；成熟接入与中文证据不足 |

旧Grok1／2、Gemini2.5／3.1 Live、Qwen3.0 Plus／3.5 Omni、Nova2.0和早期Realtime保留为历史或兼容对象；不占新项目首轮名额。AA还列FLM-Audio、Raon SpeechChat、Nemotron Voicechat／Freeze-Omni等；本轮未取得足够的当前中文、工具与公开服务契约，列为研究观察，不制造低分或已可接入结论。

## 4 托管组合平台：按完整配置比较

| 平台 | 现在值得比较什么 | 对Desk Companion的取舍 |
|---|---|---|
| [ElevenAgents](https://elevenlabs.io/docs/changelog/2026/10/5) | v4／v4 Turbo声音、Scribe v2 Realtime、可选后台LLM及工具 | **A1声音表现优先时的第二条路线**。音色、上下文和后台决定体验；v4的TTS优势不是完整Agent工具正确率 |
| [Deepgram Voice Agent](https://developers.deepgram.com/docs/voice-agent) | 听／想／说组件和函数统一会话；新增Flux家族 | 工程整合候选。[Flux STT Multilingual](https://deepgram.com/learn/introducing-flux-multilingual)当前十种语言未含中文，不能把Nova识别语种套给Flux |
| [Cartesia Line](https://docs.cartesia.ai/line/introduction) | Ink识别、Sonic合成、自选LLM、外部API和分轮 | 需要自己控制声音与Agent代码时有价值；Line和单独Sonic3.6分开计价／评价 |
| [Inworld](https://inworld.ai/) | Realtime TTS-2、STT-1、LLM推理与角色场景 | 角色／规模化路线候选；AA旧默认组合不等于新TTS-2整套成绩 |
| [Ultravox Realtime](https://docs.ultravox.ai/overview) | 托管低延迟语音、26语言含中文、异步工具与音色 | 开放音频理解权重与完整托管栈分开；9月30日被[Inworld收购](https://inworld.ai/blog/inworld-acquires-ultravox)，官方表示继续开发，不据此断言停服 |
| [Azure Voice Live](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live) | Realtime2.1／Mini、Azure Speech及其他LLM，多地区处理范围，回声／打断与Avatar | 可选择具体声音／地区；必须固定底层组合，不能把Azure的服务名当一个独立基础模型 |
| [Hume EVI](https://dev.hume.ai/voice/changelog) | 历史EVI3／4-mini表达与外接LLM | API即将结束访问，**不建议新接入** |

LiveKit、Pipecat、Vapi和Retell属于会话、部署或电话编排路线，不是又一个语音基础模型。可用于接模型；选框架并不能自动解决自然度、费用或工具成功。Muse／ChatGPT等消费产品的语音体验也不等于可嵌入API；本轮Meta公开入口列的是 [Muse Voice Transcribe](https://ai.meta.com/llama/)，属于ASR。

## 5 开放模型与本地路线

| 模型／框架 | 当前公开材料支持的定位 | 未进入首轮的原因 |
|---|---|---|
| [MiniCPM-o 4.5](https://github.com/OpenBMB/MiniCPM-V) | 9B，中英语音、连续音视频、原生双工与可控声音；同仓10月新发布的MiniCPM-V4.7是视觉系列 | **本地双工优先研究对象**，不是4.7语音升级；工具可靠性与目标硬件仍未验证 |
| [Fun-Audio-Chat 8B](https://github.com/QwenAudio/Fun-Audio-Chat) | 开放语音理解、生成及speech function calling，示例配CosyVoice3 | **开放工具语音候选**；不能把受控speech-function分数当完成双工设备集成 |
| [Qwen3-Omni](https://github.com/QwenLM/Qwen3-Omni) | 开放多模态流式听说；输入明确列粤语，输出语言清单未单列粤语 | 输入会听不等于输出同样自然；不等于商业Audio3.1／Omni3.8 |
| [Step-Audio2／mini](https://github.com/stepfun-ai/Step-Audio2)、[R1.1／R1.5材料](https://github.com/stepfun-ai/Step-Audio-R1) | R1.1有公开推理代码／权重；R1.5有报告与公开基准，另有商业API报价 | 不把R1.5报告、商业可调用与全部权重发布混同；也不等于StepAudio3商业实时型号 |
| [PersonaPlex](https://github.com/NVIDIA/personaplex)／Moshi | 原生双工与声音／角色控制，英语对话材料较多 | 中文／粤语及本组工具流程证据不足；代码与模型权重许可分别核对 |
| [GLM-4-Voice](https://github.com/zai-org/GLM-4-Voice) | 中英端到端对话、风格与语速，公开Demo | 较早基线；需补端点、播放、任务与工具工程 |
| [MiMo-Audio](https://github.com/XiaomiMiMo/MiMo-Audio) | 开放音频理解与对话研究 | 不把小爱产品或MiMo TTS的能力直接赋给公开Audio权重 |
| [Covo-Audio](https://github.com/Tencent/Covo-Audio) | 7B，当前下载示例为Chat，文章另述Chat-FD变体 | 不能把论文的FD描述当作下载目录已含同款全双工发布物 |
| [FireRedChat](https://github.com/FireRedTeam/FireRedChat) | 自托管完整双工语音交互方案 | 框架／级联工程对照，效果取决于具体组件和调优 |
| [MOSS-Speech](https://github.com/OpenMOSS/MOSS-Speech) | 端到端语音到语音研究 | 当前未核到充分的本组工具与目标机证据 |
| [SoulX-Duplug](https://github.com/Soul-AILab/SoulX-Duplug) | 流式语义VAD／状态预测，另有示例系统 | 分轮组件，不能单独替代知识、工具和语音生成模型 |

学校DGX-1／V100的显存、配额与权限仍未知；本轮没有下载、部署或测吞吐。本地模型没有按分钟的提供商音频费，不等于零成本；GPU、工程、网络、并发、维护和质量都需计算。Pi作为客户端与把完整模型直接跑在Pi是两回事。托管API仍是当前工程建议；开放路线保留研究价值。

## 6 单项ASR／TTS补全

单句声音好听、识别准确或翻译快，均不能直接证明完整Agent能接话和办事。若走级联路线，评估链为 ASR＋分轮／打断＋文字LLM／工具＋TTS＋播放／AEC。

| 家族 | 本轮核到的当前组件 | 适合比较的内容 |
|---|---|---|
| [Google](https://ai.google.dev/gemini-api/docs/changelog) | Gemini3.8 Flash TTS／Flash-Lite TTS；3.5 Transcribe／Transcribe Live；Live Translate另属翻译任务 | 原创角色音色、表达、快速合成／多语种识别；不能把Flash TTS写成Live |
| [OpenAI价格与组件表](https://developers.openai.com/api/docs/pricing) | GPT-Transcribe、4o／mini转写、live转写／翻译及TTS组件 | ASR／TTS或翻译路线，独立于Realtime／GPT-Live Agent |
| [Qwen识别](https://www.alibabacloud.com/help/zh/model-studio/asr-model/)、[合成](https://docs.modelstudio.console.alibabacloud.com/zh/model-studio/tts-model) | Qwen Audio3.1 ASR及streaming；Qwen Audio TTS、CosyVoice家族 | 中文／粤语识别、声音设计／复刻；不同SKU和音色支持分开核对 |
| [ElevenLabs模型表](https://elevenlabs.io/docs/overview/models) | Eleven v4／Turbo；Scribe v2／Realtime | A1发声与多语言ASR；不只比较已成旧代的v3／Scribe v1 |
| [MiniMax模型表](https://platform.minimax.io/docs/guides/models-intro) | Speech2.8 HD／Turbo；2.6在Legacy | 中文／方言及表达型TTS；它自己不承担日历工具决策 |
| [MiMo-V2.5-TTS](https://mimo.xiaomi.com/mimo-v2-5-tts) | Stock、VoiceDesign、VoiceClone三款 | 角色声音和文字／音频标签控制；开放Skills不是模型权重已开放 |
| [Cartesia](https://www.cartesia.ai/pt/blog?category=news) | Sonic3.6 TTS、Ink2 STT | 可控合成与识别／端点；15地区的厂商盲测不当作本组粤语测评 |
| [Deepgram](https://deepgram.com/learn/introducing-flux-tts-conversation-native-text-to-speech-for-real-time-voice-agents) | Flux STT／Multilingual与Flux TTS，Nova3／Aura2另存 | 对话上下文、分轮和打断；[Flux TTS免费期已于9月12日结束](https://deepgram.com/pricing)，不再按免费预算 |
| [Fish Audio](https://speech.fish.audio/inference/) | 推理文档列S2-Pro与Drama3；商业S2.1 Pro与开放权重分开 | 标签与表现型TTS。Drama3文档称V100的FP16路径未在实物验证，不能承诺可跑；限期免费消息不等于永久价 |
| [Soniox STT](https://soniox.com/docs/stt/models)、[TTS](https://soniox.com/docs/tts/rt/real-time-generation) | stt-rt-v5／async-v5；tts-rt-v2 | 多语种、数字实体、分离／端点与TTS；翻译S2S不能代替工具Agent |
| [Boson](https://www.boson.ai/pricing)、[Inworld](https://inworld.ai/) | Higgs TTS3／STT3；Inworld Realtime TTS-2／STT-1 | 声音及可组合后台；和各自Realtime完整栈分开 |
| [StepFun](https://platform.stepfun.ai/docs/en/guides/pricing/details)、[xAI](https://docs.x.ai/developers/pricing) | StepAudio3 TTS／ASR Max／Gen／Music；Grok TTS／STT | 对应单项生成／识别。音乐、配音、转写与实时办事分别计价 |

Whisper、FunASR／SenseVoice、Qwen3-ASR／TTS、CosyVoice和传统本地TTS继续作为组件／离线基线；不由“免费开放”直接升为整套体验首选。文字LLM如Qwen、Gemini Argon、GPT、Claude、DeepSeek或Kimi可放在级联后台，但不因此变成原生全双工语音模型。

## 7 同一用量下的基础费用

一台设备，30天，每天10分钟活跃会话，其中用户说5分钟、助理说5分钟：月会话300分钟，用户有声150分钟，助理输出150分钟。均用公开常规价、不扣赠额或首月优惠；Qwen绑定**新加坡**。计算脚本与精确结果在 [QA](../../output/qa/2026-10-15-voice-model-refresh/verification.md)。

**只算新增音频或会话基础项。不是完整月账单，也不是账单的上下界。**历史音频重算、文字／思考、转写、工具、后台、重试、税和网络另计。表中Qwen与Higgs斜线表示两种输入计量假设：150分钟有声输入／300分钟全流输入，不能当作已测的静默收费规则。

| 候选／固定套餐 | 该情景基础项，美元 | 当前价格依据 |
|---|---:|---|
| Qwen Audio3.0 Flash | 0.315／0.420 | 音频入0.93／出1.87美元每百万token，入出12.5 tokens/s |
| Qwen Omni3.8 Flash | 0.269／0.328 | 同单价，普通音频入7／出12.5 tokens/s；文字输出另计 |
| Qwen Audio3.1 Plus | 3.42／4.14 | 音频入6.4／出24美元每百万token，入出12.5 tokens/s |
| Gemini3.8 Live／Extended | 约4.20 | 官方近似入0.005／出0.018美元每分钟；输入按整段300分钟，Extended额外思考另计 |
| Higgs Realtime | 约2.45／2.79 | 厂商近似入0.0023／出0.014美元每分钟；实际按token；转写另列0.0025／分钟 |
| GPT-Realtime2.1 Mini | 4.50 | 音频入10／出20美元每百万token；VAD仅提交150分钟有声输入 |
| GPT-Realtime2.1 | 14.40 | 音频入32／出64美元每百万token；同一输入假设 |
| GPT-Live1 | 15.00＋后台 | 每活跃会话分钟0.05美元，包括静默和等待；后台单独算 |
| Grok Voice3.0 | 24.00＋文字事件／服务工具 | 默认server_vad按会话分钟0.08美元；不是只计用户说话 |
| ElevenAgents Creator | 24.00＋LLM等 | 常规22美元含275分钟，另外25分钟×0.08；不是所有用量下最低套餐 |
| Deepgram Voice Agent Standard | 22.50（固定套餐基础） | 9月13日起常规0.075美元／分钟；须固定套餐允许的LLM／声音，外接组件另核 |
| StepAudio3 Realtime Preview | 当前模型项限时免费 | 没有公开结束日／恢复价；账户配额和搜索等增值费仍单独核对 |

费率原文：[Qwen Audio](https://www.alibabacloud.com/help/en/model-studio/model-pricing)、[Omni价格](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash-realtime)／[计量](https://www.alibabacloud.com/help/en/model-studio/realtime)、[Google价格](https://ai.google.dev/gemini-api/docs/pricing)／[计量](https://ai.google.dev/gemini-api/docs/live-api/best-practices)、[OpenAI价格](https://developers.openai.com/api/docs/pricing)／[计量](https://developers.openai.com/api/docs/guides/voice-latency-cost)、[Grok价格与server_vad规则](https://docs.x.ai/developers/models/speech-to-speech)、[Higgs](https://www.boson.ai/pricing)、[ElevenAgents](https://elevenlabs.io/pricing/agents)、[Deepgram](https://deepgram.com/pricing)、[StepFun](https://platform.stepfun.ai/docs/en/guides/pricing/details)。

Grok的客户端`conversation.item.create`文字事件每条另收0.004美元，工具结果和音频item有豁免；不要把所有函数回包都算成付费文字。免按键server_vad与push-to-talk计量不同。OpenAI Realtime的缓存可降低历史输入费；GPT-Live不是Realtime的token计费替身。Gemini3.8主动音频常开且历史音频按轮重算，两种转写也可能增加文字费。Qwen Audio历史用户音频会重算，模型输出音频不重复作为音频历史计费；Omni有不同规则。

[豆包价表](https://docs.volcengine.com/docs/DoubaoVoice/Billinginstructions-21?lang=zh)仍可看到实时语音统一条目和音频入80／出300元每百万token的算例，但本轮未核定该SKU与3.0的完整映射，不把旧算例直接列为3.0报价。Nova2.5公告称与Nova2相同价格，本轮没有固定地区逐项费率，亦不编造月数。Azure、Line、Ultravox等需固定底层配置／地区后再报价；“未给统一月价”不表示免费。

费用选择应看**每个成功任务总费用**与失败率，而非只看每分钟或首包。短会话关闭后，任务、身份与记忆仍保存在本组后端；无需为了“常驻A1”维持整天收费音频连接。

## 8 地区、现有代码与建议

Google当前 [直接Gemini API地区页](https://ai.google.dev/gemini-api/docs/available-regions)仍未列香港；页面另指向企业平台路线，后者不能直接继承Developer API的价格与授权。Qwen当前Audio3.1及Omni3.8产品页列北京／新加坡SKU；有香港workspace不等于这些语音型号已有香港部署。Grok价目列us-east-1，这是处理集群，不是用户可申请地区清单。账号资格、部署地区、数据目的地和香港实测延迟是不同条件；本轮没有登录控制台验证个人权限。

10月15日代码只登记`qwen_audio`与`gemini`：前者smart_turn／10轮历史，后者音频／双向转写。10月17日[voice.py](../../desk-companion/backend/desk/voice.py)已新增独立`qwen_omni`，映射嵌套音频、semantic VAD、图像及函数生命周期；沿用工具／批准／JobService，默认none。真实合成短测见文首，不推为语言质量、GUI、AEC或机械臂验收。Grok／Realtime／GPT-Live仍需各自适配器，不能借用提供商名换URL冒称接入。

**当前工程建议，非用户决定：**

1. **质量首轮：Grok Voice3.0、Gemini3.8 Live、Qwen Audio3.1 Plus。**Grok看复杂任务与新语音能力；Gemini作日常自然交谈／费用基线；Qwen验证普通话、粤语和混说。实际账户不可用的对象记为不可测，不通过网络绕过代替资格。
2. **低价对照：Qwen Audio3.0 Flash与StepAudio3 Preview。**若它们达到相同任务与自然度要求，可升为实际使用方案；Omni3.8在需要视觉或极低价时加入，避免同时做多套完整客户端。
3. **长任务：GPT-Live＋固定后台**与Gemini Extended Thinking，验证工具慢时仍能接住取消和追加限制。GPT-Realtime2.1保留直接工具协议的质量对照，Mini在完整版达标后比较降本。
4. **A1声音优先：ElevenAgents v4 Turbo**；若采用自主级联，再对比Gemini3.8 TTS、MiniMax2.8、MiMo VoiceDesign、Sonic3.6／Fish等发声。原创声音设计与有授权的声音复刻分开；不能只试听配音就确定整套Agent。
5. **自托管研究：MiniCPM-o4.5与Fun-Audio-Chat先看**，再按实际资源评估Qwen3-Omni。当前不因可下载权重就改变托管API的工程路线。

如果不考虑费用，只选下一款值得验证的新增模型，**Grok3.0升到最前**。如果以一台学生原型的日常交谈、价格和已有代码为主，**Gemini3.8 Live仍是合理基线，但实际账户资格是前提**。如果粤语是硬要求，Qwen3.1应先做本地语言脚本，不能由英语榜代替。这三个判断回答不同问题，不能合成一个未经试听的“世界第一”。

## 9 下一步验证合同

本轮到公开比较为止。下一步先由拥有者选定实际可用的两至三款**确切型号、音色、后台／思考配置和总花费上限**，再接同一套工具做短测；没有新增付费或麦克风授权。

每款至少20个等量短场景，轮换顺序；普通话、英语、粤语及混说分别留结果。覆盖犹豫／改口、附和、明确插话、工具延迟与追加条件、确认前取消、失败与未知回执、字母数字／香港日期时区、旁人／键盘／扬声器回声。使用相同A1人格和简短回答要求；改变音色或思考配置记为新配置。

记录首个任意音频、首个有用回答、打断停止、任务完成的p50／p95；自然度用成对偏好及具体失败说明，工具以本地数据库／作业独立读回为准。另记重复写入、越权、错误确认、断音、取消后迟到工具、usage与实际账单。应用端继续保留独立确认、job_id、取消和未知写入只读对账；模型输出“完成”不构成证据。

通过短测后再扩到Proposal既有40条中英命令和10条歧义／禁止请求、真实wake／AEC、Pi扬声器与网络。坐姿闭环、A1动画和实体动作各自验收。来源覆盖及访问限制见 [source-register.md](source-register.md)，本轮交付与检查见 [QA](../../output/qa/2026-10-15-voice-model-refresh/verification.md)。
