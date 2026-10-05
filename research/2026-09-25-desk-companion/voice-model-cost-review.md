# Group 2 桌面助理语音方案：成本、模型与本地训练

核对日期：2026-09-25。状态：**公开资料比较，未建立 API 账号、付费、下载安装模型或在 Pi／Mac 上跑音频基准**。本页修正[总体可行性研究](feasibility-review.md)中把 GPT-Live 当成直接可用候选的印象。Group 2 原型面向香港，提供商的地区及账号可用性必须先于报价比较。

**后续筛选条件更新：**用户要求暂不考虑地区与按键说话，优先比较免按键实时语音和设备工具调用。对应的[新比选](realtime-voice-model-comparison.md)取代本页“按键说话为首选”的建议；本页地区与分段式成本研究作为当时条件下的记录保留。

## 最重要的新发现：地区可用性

[OpenAI API 官方支持地区](https://developers.openai.com/api/docs/supported-countries)与[Google AI Studio／Gemini Developer API 官方地区](https://ai.google.dev/gemini-api/docs/available-regions)截至本次查询均**没有列香港**。这不是声称用户的 ChatGPT App 不可用，也不是对所有经合法企业渠道提供的模型服务作否定；它表示不能把两家**直连 Developer API**写成香港 FYP 的确定依赖，更不能为降低成本自行绕过地区限制。实际账号、学校安排与目标部署地区仍需分别核对。

[阿里云 Model Studio 的官方区域表](https://www.alibabacloud.com/help/en/model-studio/regions)则列有 `cn-hongkong` 工作空间、端点和实时推理能力。[官方价表](https://www.alibabacloud.com/help/en/model-studio/model-pricing)明确列出香港区域 `qwen3.8-flash` 文字模型的 Global 部署价：输入 **US$0.113／百万 token**、输出 **US$0.382／百万 token**。这是文字处理的公开单价，非整套语音通话价格；账户能否开通、该工作空间的具体模型和费用应以实际控制台再次核对。香港区域的**语音实时模型可用性及对应定价**没有从这张公开价表得到同等明确的逐型号确认，不能把新加坡 `qwen3.8-omni-flash-realtime` 标价直接当香港报价。

另一个已核的**香港云端语音备选**是[阿里云 `qwen3.8-omni-flash`](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash)：官方型号页明确列香港区域，接受音频输入、输出文本并支持工具调用；它适合“一段语音指令→文本答案／日历操作”，**并非直接生成语音的实时型号**。香港[价表](https://www.alibabacloud.com/help/en/model-studio/model-pricing)列其 Global 部署输入US$0.113、输出US$0.382／百万 token，但实际音频 token 数要由代表性录音实测，不能把该价格误写成每分钟价格。需要较自然的云端播报时，[Azure Speech 官方区域表](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions)列 East Asia (`eastasia`) 支持基础语音服务；[微软地区表](https://learn.microsoft.com/en-us/azure/reliability/regions-list)将 East Asia 列在香港。账户、所选声音、具体计费和学校访问权限仍待核实，未建立资源。

## 能选哪些架构

| 路线 | 实际结构 | 已核价格／成本口径 | 适合本项目的取舍 |
|---|---|---|---|
| A. [GPT-Live 1](https://developers.openai.com/api/docs/guides/live) | 云端语音会话＋另一个后端负责日历工具 | [US$0.05／活跃会话分钟](https://developers.openai.com/api/docs/pricing)，静默与工具等待也计时，后端另计；10分钟／天×30天约US$15语音费 | 自然打断与边说边查最贴近演示，但常开昂贵，且香港直连 API 不应预设可用。 |
| B. [GPT-Realtime-2.1 Mini](https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini) | 单个实时模型收音、说话、调用工具 | 音频输入**US$10／百万 token**、输出**US$20／百万 token**；文字输入0.60／百万、输出2.40／百万；不是固定每分钟收费 | [官方](https://developers.openai.com/api/docs/guides/voice-latency-cost)指出较便宜，但小模型的指令遵循／工具调用可能较弱，需测成功率；同样有香港直连可用性问题。 |
| C. [Gemini 3.8 Live](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live) | Google 实时音频模型 | [公开价](https://ai.google.dev/gemini-api/docs/pricing)：输入音频约US$0.005／分钟、输出音频约US$0.018／分钟，另有文本及反复处理会话上下文的费用 | 价格形式看起来低，但官方 Developer API 地区列表未列香港；[长对话会重计上下文](https://ai.google.dev/gemini-api/docs/live-api/best-practices)。不能作为当前香港原型的必需服务。 |
| D. **语音转文字 → 便宜文字模型 → 文字转语音** | 按键录音，用本地或按段 ASR 得到文本；日历工具由程序校验；短句 TTS 输出 | 若地区适用，[OpenAI Mini 转写](https://developers.openai.com/api/docs/pricing)约US$0.003／输入音频分钟；[Mini TTS](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts)按文字输入及音频输出 token 收费。香港可选本地ASR，或让`qwen3.8-omni-flash`处理音频输入；文字中段用香港Qwen，TTS本地或另选合适的香港语音服务 | **首选 FYP 主线。**成本按真正处理的语音和文字产生，不必维持昂贵会话；中间文本可审查，日历修改更容易确认。代价是轮流说话，打断体验和响应时延须实测。 |
| E. 尽量本地 | Pi 上用[whisper.cpp](https://github.com/ggml-org/whisper.cpp)作多语言 ASR，受限意图／日程规则或经[llama.cpp](https://github.com/ggml-org/llama.cpp)加载量化小模型，使用本地 TTS | 无逐次云端语音 API 费，但有设备、供电、性能调校和维护成本 | 隐私及离线演示有价值；Pi5 8GB能否同时达到所需中文／英文准确率、首音延迟和散热尚未测。先在 Mac 验证正确性，再在 Pi 测整机。 |

[OpenAI Docs 的语音代理指南](https://developers.openai.com/api/docs/guides/voice-agents)也把实时会话和三段式语音链列为不同架构，后者的优势是每阶段可单独换模型、检查文字及控制工具。**模型选择不改变提醒策略的主目标**：本地固定提醒和按钮操作即使断网也应继续；自然聊天可降级。

### 同口径的算术示例

这只是说明计费结构，不是我们的实际账单。假设每天有一段总共10分钟的语音交互，其中用户说5分钟、助理说5分钟，连用30天：

- GPT-Live 1：活跃会话10×30×US$0.05＝**US$15**，仍要另计后端模型与工具。
- GPT-Realtime-2.1 Mini：按[官方计量说明](https://developers.openai.com/api/docs/guides/voice-latency-cost)，用户音频约10 token／秒、输出音频约20 token／秒。只算**新产生的一次音频量**：5×60×10×10／1,000,000＋5×60×20×20／1,000,000＝**US$0.15／天，30天US$4.50**。真实账单还会重计会话历史、文字 token，可能另有转写费；不能把4.50当总价。
- Gemini 3.8 Live：仅新音频输入5×0.005＋输出5×0.018＝**US$0.115／天，30天US$3.45**；会话上下文及额外文字费用另算，而且当前直连地区限制使其不成为香港首版承诺。
- OpenAI Mini 按段转写：只算5分钟用户语音，5×30×0.003＝**US$0.45／月**；文字模型、TTS、请求失败及重试另算。此报价仍以 OpenAI API 在适用地区可用为前提，不能在香港直接照抄部署。
- 香港 Qwen 文字中段：假设每月1000次、每次1000个输入与300个输出 token，文字费为1,000,000／1,000,000×0.113＋300,000／1,000,000×0.382＝**约US$0.23／月**；ASR、TTS、网络和更长上下文另计。1000次和 token 数完全是假设，不代表已获得真实使用量。

三段式要报真实成本时，保留每次的输入音频秒数、转写调用、文字输入／输出 token、TTS 输出 token 或字符数、失败重试和月总次数；拿相同20–30句英语／普通话指令测试，比较首个有用语音的时延、中断能力和日历操作成功率，而不只看宣传单价。

## “我们自己训练”应怎样理解

**从零训练语音大模型不合适。**三人半年、M2 Pro／16GB及未确定的 Pi5 资源，不具备从零建立高质量多语言 ASR＋对话＋自然 TTS 所需的数据、计算、标注和全面评估。省下小额 API 费，可能换来几个月的训练与兼容性工作，而且更难达到现成模型的自然交互。这里的“不可取”是当前项目资源与目标的工程判断，不是数学上任何人都不可能训练。

更合理的三个层次：

1. **先复用预训练模型并直接运行。**[whisper.cpp 官方仓库](https://github.com/ggml-org/whisper.cpp)列 Raspberry Pi、CPU 推理和量化支持；一定要选多语言模型，不能用 `base.en` 仅英文模型来测试普通话。文字生成可先用受控规则或香港可用的云端小模型；如果要全离线，再以 `llama.cpp` 的小型量化模型做有界对照。模型“能加载”不等于声学噪声和整机延迟合格。
2. **有数据后训练真正属于本项目的部分。**例如从用户主动反馈学习“这个提醒现在适不适合”，用日程紧迫度、是否在桌前、明确专注模式、近期延后次数等特征训练一个小分类／排序模型；与固定规则和无学习基线比较，按人和日期分离测试集。这比微调聊天模型更对应 FYP 痛点，且可在现有 Mac 上完成。
3. **只有明确失败原因才微调语音。**[Qwen3-ASR 0.6B](https://github.com/QwenLM/Qwen3-ASR)和[Qwen3-TTS 0.6B](https://github.com/QwenLM/Qwen3-TTS)提供公开权重与中文／英文能力，但其桌面或服务器示例不能证明可在 Pi5 8GB 上低延迟并行运行。要针对真实口音、环境噪声和设备麦克风积累有权使用的录音，先做错误分析；无这些数据时微调不可能凭空提高准确率。

本地 TTS 的轻量候选是 Piper。[原作者仓库](https://github.com/rhasspy/piper)已归档，列有[简体中文 huayan 声音](https://github.com/rhasspy/piper/blob/master/VOICES.md)；[后续维护仓库](https://github.com/OHF-Voice/piper1-gpl)为 GPL-3.0。用于原型时应先听声音、实测 Pi 速度，并逐项核对引擎与语音文件许可；不要把“开源”理解成所有素材自动可随意商用或分发。

## 建议的决定

当前不要锁死 GPT-Live 或承诺全天候云端陪伴。**首个实机验证：Pi 按键说话＋本地多语言 ASR＋程序化日历权限／提醒策略＋本地 TTS；并用同一批指令比较香港区域 `qwen3.8-omni-flash` 的音频输入→文本能力。**需要开放式对话时可接香港区域Qwen文字模型；若本地声音不够好，再核对 Azure East Asia 等语音服务的实际账单与许可。这能在没有云语音时完成核心闭环，也让语音服务可替换。实时双工体验可作为进阶实验，而非 Proposal 的唯一实现路线。

此处“建议”尚未由用户／Marco选定；没有新的训练结果或供应商报价。下一版正式 Proposal 应写成可替换的语音架构，不以不受香港直连支持的 API 作为唯一交付前提。
