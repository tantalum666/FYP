# Group 2：自然语音与工具调用的重新比较

核对日期：2026-09-29。状态：**公开研究完成；未试听、调用模型或实测设备；最终型号未定**。

**同日价格补充：**用户随后要求加入价格，见[价格与性价比排名](price-and-value-ranking.md)。本页保留自然度／工具的证据和能力对照；加入价格后，低价Qwen Flash与限时免费的StepAudio3优先级上升，不能继续将本页三候选安排视为唯一成本测试顺序。

## 1 本轮结论与取代关系

用户要求不按本地／API筛选，以自然交谈和工具调用为主要条件，同时检查第三方测评。本稿取代9月25日价格优先、9月28日只重点比较两款Qwen的**工程推荐**；此前用户Qwen→Gemini→Realtime→Live的偏好保留历史，本轮重新比较不把这个顺序当成质量排名。学校Proposal、日志和设备功能范围不变。

**工程建议：首轮并排比较Gemini 3.8 Live、GPT-Realtime-2.1和Qwen-Audio-3.1-Realtime-Plus。**如果现在必须挑一个接入起点，选Gemini 3.8 Live：它在两个较新的真人对话评估中均有较好证据，且公开工具接口明确。这是针对当前证据覆盖和本项目任务的判断，不是证明其中文绝对第一。GPT-Realtime-2.1作自然交谈／工具基准；Qwen 3.1作中文与方言重点挑战者，不能套用上一代的第三方成绩。

Grok Voice Think Fast 2.0作为工具任务的强对照；StepAudio 3 Realtime、豆包实时语音3.0／Seeduplex应补进第二轮。GPT-Live-1适合连续聊天与后台复杂工作并行；ElevenAgents Expressive mode适合重视角色声音且接受组合平台的路线。不要同时开发八套完整产品：共享工具与评估接口，每次比较二至三套。

研究覆盖主要公开实时服务、语音代理平台、开放语音模型及相关组件；未声称穷尽全球未公开模型。对没有可比实测的候选，写明“证据不足”，不把缺席排行榜当低分。

## 2 把“自然”落实成可观察行为

| 维度 | 我们希望设备做到的事 | 不足以证明的东西 |
|---|---|---|
| 说话质感 | 语调、重音、停顿、语速和角色声音协调，中英混说可听懂 | 单句配音好听不证明多轮聊天自然 |
| 接话时机 | “明天下午……嗯，四点”说完再回答；句子确实结束就及时接话 | 最短静默阈值不等于最佳体验 |
| 插话与附和 | 区分“嗯，继续”和“等等，改成五点”，及时停止或接续 | WebSocket双向传输不证明模型会合理分配说话时机 |
| 内容与连续性 | 记住当前事项、改口和约束，避免每轮重问，语句简短合宜 | 长上下文标称容量不等于长期可靠记忆 |
| 工具执行 | 查日历、提议改期、确认后写入、读取实际结果再播报 | 输出函数名或口头说“完成”不等于成功 |
| 同时聊天与办事 | 工具慢时能解释等待，听懂期间的新限制和取消 | 填充语音快速出现不等于实质答案已生成 |

评价时同时记录“首个任何音频”“首个有用回答”和“最终任务完成”的时间。只比较厂商最小首包，容易奖励没有信息的“好的”。模型、音色、提示词、思考强度、音频链、网络和工具后端都影响结果。

## 3 第三方证据：各自回答什么问题

### 3.1 Jarvis Bench v0.5：真人觉得像不像自然交谈

2026-09-29已通过浏览器读取[Jarvis Bench](https://voicearena.com/jarvis-bench)可见榜单与方法。它采用真人多轮对话和盲选；当前页面列90名来电者、569通完成对话。以下摘取少量当前结果，Elo不是百分制。

| 确切配置 | 自然度Elo及95%区间半宽 |
|---|---:|
| Gemini 3.8 Live，Kore | 991 ±13 |
| GPT-Realtime-2.1，Low，Marin | 986 ±17 |
| GPT-Live-1＋GPT 6 Astra Medium，Marin | 949 ±21 |

前两项区间重叠，不宣布显著胜负。公开航班任务明确只讲英语，不能当普通话榜。每款只测一个声音／配置；v0.5尚未发布工具日志的客观成功率，Task effectiveness也是人的评价。页面方法仍有“8月采集”的旧说明而榜单已加入9月型号，故记录为当前页面快照，不能替作者补出准确采集日期。只查看了公开转写、指标及方法，没有实际听音频。

### 3.2 Artificial Analysis：完成任务与用户偏好分开看

[Speech Agent Arena](https://artificialanalysis.ai/speech-to-speech/arena)让用户与匿名系统完成同场景任务。下面只摘取与短名单相关的成功率；取页面打开时数据，搜索缓存中Grok曾显示94.7%，本稿使用直达页面的94.6%。

| 测试配置 | 最终工具任务成功率 | 95%区间 |
|---|---:|---:|
| Grok Voice Think Fast 2.0 High | 94.6% | 91.4–96.7% |
| Gemini 3.8 Live | 93.2% | 89.0–95.8% |
| GPT-Realtime-2.1 High | 91.5% | 87.7–94.3% |
| GPT-Live-1＋Sol Low | 90.9% | 87.2–93.7% |
| Qwen Audio 3.0 Realtime Plus | 77.8% | 66.9–85.8% |

前三项区间重叠。最后一项是3.0，不能推算3.1。AA的用户整体偏好对GPT-Live较有利，与Jarvis自然度次序不同；提示我们不要把不同场景和配置混成一个“世界第一”。

[方法说明](https://artificialanalysis.ai/methodology/speech-to-speech-benchmarking)显示：Arena成功率由LLM评审转写和完整工具轨迹，先过滤用户偏离／无法核实的会话，再检查最终调用及参数；它不是我们数据库的实测正确率。另一项τ-Voice通过用户模拟器及数据库最终状态评价，多卡／真实中文设备并非该测试对象。当前综合Index已是四项等权，不能把6月发布时的三项指数与9月直接混排。

### 3.3 标准化插话测试与真实等待时间

[AA语音总表](https://artificialanalysis.ai/speech-to-speech/)的Conversational Dynamics检查停顿、接话、打断和附和。StepAudio 3为98.9%、Qwen Audio 3.0 Plus为98.4%，很值得关注；但其Big Bench Audio首音均值分别为8.83秒、1.54秒。前者是推理题设置，不证明日常聊天每句都要等8.83秒，也不能忽略这个风险。首音速度和接话得分来自不同测试，不能组合成未经测量的“整机自然度”。

### 3.4 其他测评怎样使用

- [Scale Voice Showdown](https://labs.scale.com/api/pdf/blog/voice-showdown)：真人场景覆盖多语言，区分听懂、内容和发声；已读发布文章对应2026年3月的型号。用于提醒中英切换、短语和噪声会暴露错误，**不拿旧GPT-Realtime-1.5／Gemini2.5结果给9月新型号排名**。
- [Full-Duplex-Bench-v3论文](https://arxiv.org/abs/2604.04847)：真人不流利语音配合多步工具任务；4月配置说明改口与连环任务是难点。用于补设计我们的测试，不把旧配置成绩移植到2.1／3.8。
- [AA Controlled Voice方法](https://artificialanalysis.ai/methodology/text-to-speech)：同一段文字、同一克隆声音比较发声质量。即使某家TTS领先，也不证明它的Realtime会正确等待、理解改口或执行日历工具。

本轮检索了Qwen3.1独立实测及StepAudio3评测报道。可找到大量新品介绍或复述技术报告的文章，未找到足够的同条件中文、多轮、工具日志三者齐全的3.1第三方比较。因此不把媒体转载升级为独立验证，也不补造“中文最自然”的分数。

## 4 当前重点实时语音候选

| 候选与官方来源 | 语音及工具的实际路径 | 本项目取舍与证据不足 |
|---|---|---|
| [Gemini 3.8 Live](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live) | 实时音频交互；自定义函数，默认异步工具调用 | **首个接入起点建议**。普通日历、设备查询更符合其定位；中文、房间噪声与Pi播放仍需验证。 |
| [Gemini 3.8 Live Extended Thinking](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live-extended-thinking) | 后台思考与异步工具，期间可语音说明进度 | 连续多步任务候选；[官方区分](https://ai.google.dev/gemini-api/docs/live-api/thinking)不是“凡事用最高思考更自然”。先保留普通Live作日常基准。 |
| [GPT-Realtime-2.1](https://developers.openai.com/api/docs/models/gpt-realtime-2.1) | 实时语音与直接函数请求，可调思考强度 | **首轮基准**。官方改进字母数字、噪声与打断；Jarvis测Low、AA表测High，不能说这是同一配置复测。Mini可作为之后的成本对照，不用Mini代表完整版。 |
| [GPT-Live-1](https://developers.openai.com/api/docs/models/gpt-live-1) | 语音前台持续交谈；任务委派给独立后台Agent | **长任务并行候选**。自然度没有跨测评一致胜出。[官方委派](https://developers.openai.com/api/docs/guides/live)允许独立选择后台，不等于多模型架构天然更好。声音会话与后台费用分别计算。 |
| [Qwen-Audio-3.1-Realtime-Plus](https://help.aliyun.com/en/model-studio/qwen-audio-3-1-realtime-plus) | 流式听说、函数请求；[smart_turn](https://help.aliyun.com/en/model-studio/qwen-audio-realtime-user-guides)利用声学与语义判断，支持中英及多种中文方言 | **首轮中文重点**。有具体能力资料，尚缺完整独立真人工具榜；不可继承3.0或同系列TTS排名。内置搜索与Function Calling不能同时启用，需设计自己的外部工具路径。 |
| [Qwen3.8-Omni-Flash-Realtime](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash-realtime) | 流式音视频、音频输出、自定义函数与远程MCP | 保留，尤其需要语音同时理解视频时；本项目坐姿由本地独立算法判断，所以不因Omni模态更多而优先。未找到同型号充分独立自然度数据。 |
| [Grok Voice Think Fast 2.0](https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech) | 双向音频、函数／MCP、思考设置；官方列中文 | **工具任务强对照**。AA任务结果较强，Jarvis自然感相对靠后；不再因旧价格比较而提前排除。固定版本，避免latest切换污染实验。 |
| [StepAudio 3 Realtime](https://static.stepfun.com/blog/stepaudio3/realtime/) | 全双工、Think-While-Speaking；[技术报告](https://arxiv.org/html/2609.14005v1)说明异步工具执行 | **补入第二轮**。很贴合目标，第三方接话成绩强，但推理题首音慢；官方τ-Voice56.0是作者报告，AA当前该项仍空白。本轮未取得足够清楚的完整公开工具事件契约，不编造接入代码。 |
| [豆包实时语音3.0／Seeduplex](https://docs.volcengine.com/docs/DoubaoVoice/Productdynamics?lang=zh) | 官方产品动态明确原生全双工及工具执行；[Seed发布说明](https://seed.bytedance.com/zh/blog/introducing-seed-full-duplex-speech-llm-attentive-listening-robust-interference-suppression-enabling-more-natural-interaction)强调抗干扰与动态等待 | **补入中文第二轮**。不要沿用旧O／SC端到端版本的能力描述；具体3.0接口、权限和工具契约在接入前核定。本轮缺可直接比较的独立中文自然度及工具成功数据。 |
| [SeedRealtime](https://seed.bytedance.com/en/blog/seedrealtime-audio-visual-full-duplex-llm-released-toward-omni-modal-natural-interaction) | 研究／产品发布强调原生音视频、主动互动及工具 | 观察候选，**不与可采购的Seeduplex混同**。官方发布页没有给出足够清楚的公开开发者接入契约，本轮不把同名第三方网站当字节官方API。 |
| [Amazon Nova 2 Sonic](https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-tool-configuration.html) | 实时语音、异步工具 | 英语方案可比较；[官方服务卡](https://docs.aws.amazon.com/pdfs/ai/responsible-ai/nova-2-sonic/nova-2-sonic.pdf)支持语言清单未列中文，故不作当前中英主线。服务卡在本轮读到官方索引内容，未声称完成整PDF逐页审阅。 |

Qwen3.1还必须区分**发布页演示、论文配置、完整服务**。其[技术报告v2](https://arxiv.org/html/2609.25176v2)明确τ-Voice工具结果使用半双工语音输入／文字输出的改编协议，不能和AA全双工语音进出的分数直接相减。另一个长期任务Voice Harness原型以前台3.0为基础，不能写成3.1下载后自带的可靠长期记忆。本文读了架构、评估协议、工具表和局限段，没有复现论文。

## 5 组合平台也能满足条件，不必只选单个模型

| 平台 | 为什么值得看 | 当前取舍 |
|---|---|---|
| [ElevenAgents Expressive mode](https://elevenlabs.io/docs/eleven-agents/customization/voice/expressive-mode) | Eleven v3 Conversational与新的分轮系统，语气、停顿和表达可控；[工具](https://elevenlabs.io/docs/eleven-agents/customization/tools)含客户端、Webhook和MCP | 角色声音优先时值得比较。AA的默认组合使用较早Flash声音，不可把其成绩当v3新版实测；更换后台LLM也会改变正确率与延迟。 |
| [Hume EVI 4-mini](https://dev.hume.ai/docs/speech-to-speech-evi/overview) | 面向声音表达、可打断；[工具依赖补充LLM](https://dev.hume.ai/docs/speech-to-speech-evi/configuration/tools) | [当前语言清单](https://dev.hume.ai/docs/speech-to-speech-evi/faq)未列中文。英语对照可以，暂不作中英主线；“empathic”不是医疗准确性指标。 |
| [Deepgram Voice Agent](https://developers.deepgram.com/docs/voice-agent) | 自选听、想、说组件，经统一会话连接；[函数调用](https://developers.deepgram.com/docs/voice-agents-function-calling)说明轮次未确认前请求可能提前发出 | 工程整合候选。必须把最终确认与写入控制放在应用端；中文支持要核对整个ASR／TTS组合，不能拿识别语种数代表完整对话能力。 |
| [Cartesia Line](https://docs.cartesia.ai/line/sdk/tips) | 语音代理／对话编排平台，可连接工具；它的Sonic是语音合成组件 | AA有默认组合的真人偏好数据；更适合需要定制声音和后台的团队，不把单独Sonic音质当整个Agent质量。 |
| [Azure Voice Live](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-faq) | 多模型、异步函数、语音与Avatar整合；[文档](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-how-to)包括中文语义VAD配置 | 可行整合选项，但必须固定底层模型及语音配置才有可比较对象；它不是一个可以独立宣称胜过Gemini的基础模型。 |
| [Ultravox Realtime](https://docs.ultravox.ai/overview) | 托管完整语音代理，中文、多语言及[HTTP／客户端工具](https://docs.ultravox.ai/tools/custom/http-vs-client-tools) | 可行备选。托管服务和开放音频理解权重不是同一整套产品；不能以下载文字输出模型代表已完成语音生成链。 |
| Inworld | 两个第三方榜都纳入其组合系统，可承担角色语音 | Jarvis与AA使用的识别、LLM、TTS版本不同，不合并分数；没有证据应为本项目优先于首轮三款。 |

Vapi、Retell、LiveKit和Pipecat属于部署／会话编排路线，可帮助把各组件接起来；它们不是与Qwen3.1同层的一个语音基础模型。不因为选了框架就认为自然度或工具准确率已经得到保证。

## 6 开放模型及组件查漏

本轮不因必须本地而加分，也不因需要开发适配就说完全不能用。以下保留作研究或后续路线；“未核到工具契约”不等于理论上无法连接工具。

| 候选／组件 | 核对到的定位 | 未进入首轮的主要原因 |
|---|---|---|
| [MiniCPM-o 4.5](https://github.com/OpenBMB/MiniCPM-V) | 开放中英多模态全双工，官方有持续音视频Demo | 自然体验值得研究，但未核到与商业实时服务等价的成熟工具契约及可比独立真实任务数据。 |
| [Qwen3-Omni](https://github.com/QwenLM/Qwen3-Omni) | 开放音视频理解和语音输出 | 不等于3.1Audio／3.8Omni实时商业型号；服务端模拟双工与模型原生行为分别判断。 |
| [Fun-Audio-Chat](https://github.com/QwenAudio/Fun-Audio-Chat) | 开放语音对话与speech function calling研究 | 比先前清单更值得保留的工具语音候选；公开演示与受控分数不足以证明连续自然会话已胜首轮服务。 |
| [Step-Audio 2／mini](https://github.com/stepfun-ai/Step-Audio2)、[Step-Audio R1](https://github.com/stepfun-ai/Step-Audio-R1) | 语音理解／推理与工具方向 | 不能漏掉新StepAudio3却只推荐旧mini；也不把Realtime商品名当开放权重同款。 |
| [NVIDIA PersonaPlex](https://github.com/NVIDIA/personaplex)、Moshi | 可控角色与同时听说的研究路线 | 英语材料较多；当前未核到本项目所需中文＋可靠工具的完整证据，不能由像真人聊天推导会办事。 |
| [GLM-4-Voice](https://github.com/zai-org/GLM-4-Voice) | 中英语音生成、风格和语速控制 | 较早开放方案，当前工具工作流与独立多轮体验证据不足。 |
| [MiMo-Audio](https://github.com/XiaomiMiMo/MiMo-Audio) | 开放音频理解、对话与生成 | “小爱同学”的产品体验不能直接当这份公开权重的能力；需另做端点、播放和工具整合。 |
| [Tencent Covo-Audio](https://github.com/Tencent/Covo-Audio) | 语音对话及全双工变体研究 | 必须逐个核对Chat与Chat-FD实际发布物，不由论文描述推导下载目录含所有能力；本轮工具证据不足。 |
| [FireRedChat](https://github.com/FireRedTeam/FireRedChat) | 自托管级联／半级联语音系统，含端点、识别、合成与对话管理 | 更适合作工程框架对照；“组合”不必然不自然，但需要团队调优与同条件评价。 |
| [SoulX-Duplug](https://github.com/Soul-AILab/SoulX-Duplug) | 流式语义VAD／说话状态预测模块及示例系统 | 可改善何时说话，不是单独具备完整知识、工具与声音的万能模型。 |
| [MOSS-Speech](https://github.com/OpenMOSS/MOSS-Speech)、MOSS-Audio | 语音生成或音频理解研究 | 没有充分证据证明现成满足本组自然多轮＋日历工具，需要分清生成与理解型号。 |

另外检查了MiniMax、MiMo语音、Qwen TTS、CosyVoice、Fish Audio、Cartesia Sonic等语音合成路线以及Whisper／各家ASR。TTS负责发声、ASR负责转写；能作为组件但不能单独完成本请求。DeepSeek、Kimi或其他文字LLM可以处理工具，配好听的TTS仍须补齐分轮、插话与音频处理。以[MiniMax Speech 2.6](https://www.minimax.io/news/minimax-speech-26)和[MiMo TTS](https://mimo.xiaomi.com/mimo-v2-5-tts)为例，Voice Agent应用描述或“Agent tool-call support”字样不等于该TTS自己理解并执行设备工具。

## 7 对本组设备的建议与短测办法

先保持一套本地日历和设备工具。Gemini／Realtime／Qwen只更换语音适配器，日历记录、确认流程、角色状态与机械臂预设一致。没有必要为每家重做一次UI，更无需从零训练一个大语音模型。学校V100资源可供开放模型对照，暂不拿兼容性作为本轮质量筛选条件。

建议第一轮每个候选20个短场景，至少覆盖普通话、英语及混说，轮换顺序以减少先听哪款的影响。同一参与者比较同一任务，尽量隐藏型号；这属于功能／体验验证，不新增学校不要求的市场问卷。

| 场景 | 具体输入／变化 | 记录什么 |
|---|---|---|
| 犹豫和改口 | “明天下午三点……不，四点提醒我交报告” | 是否等完、最终时间、实际写入次数 |
| 附和 | 它解释时说“嗯，你继续” | 是否不必要停下或重启整段 |
| 明确插话 | “等等，只讲下一件事” | 声音停止延迟、是否理解新范围 |
| 长工具任务 | 查询日历有意延迟几秒，期间补“只看明天下午” | 是否接住补充、等待说明与最终结果一致 |
| 取消 | 拟议写入确认前说“取消” | 是否未提交；已提交情况是否准确说明 |
| 中英混说 | “把Project meeting改到next Friday，四点” | 事项、日期、时区及发音 |
| 背景干扰 | 键盘声、旁人聊天、设备自己播音 | 误触发、误打断、错误确认 |
| 真实工具失败 | 请求合法但日历写入失败／机械臂未启用 | 是否如实说明、不谎报完成、不重复动作 |

自然度采用简单成对偏好与具体失败记录，工具采用本地状态读回，不用模型自评。除首音与打断延迟，还记录p50／p95、失败重试、整段断音、实际使用量。旧文档的时延数值只是待定目标；本稿没有生成新的实测成绩。

通过前述小测的候选再扩到Proposal已有40条中英命令、10条歧义／禁止请求和持续运行。角色的idle／listening／thinking／speaking／confirm由真实会话事件驱动；语音自然、动画同步和机械动作成功分别验收。

## 8 交付状态

这是一次候选覆盖、官方能力和第三方证据的补全。已经核对公开网页、论文相关章节及浏览器中的Jarvis榜单／方法／转写；未试听其音频，不把读转写说成音色评测。没有购买、开通、使用收费API、获取麦克风、下载模型、登录学校服务器或修改学校交付文件。

后续只需建立同一工具后端的三候选短测，再按实际中文自然度与正确执行决定。当前推荐是可解释的验证顺序，不是最终合同、部署决定或导师批准。
