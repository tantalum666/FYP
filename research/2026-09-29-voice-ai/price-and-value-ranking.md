# Group 2：加入价格后的语音AI选择

核对：2026-09-29。状态：**公开价目与算例；没有API账单、试听或最终选型**。

## 1 排名的含义

本稿补充[自然度与工具报告](naturalness-and-tools-review.md)。用户现在要求把价格纳入；仍保留自然交谈和工具执行要求，不重新设定必须本地或必须API。下表是针对一台FYP设备的**工程优先级**，不是测评机构的综合排行榜，更不是已经通过本组验收的型号。自然度／工具证据沿用刚完成的同日研究；价格本轮刷新。

| 综合优先级 | 候选 | 理由与条件 |
|---|---|---|
| 1 | Gemini 3.8 Live | 自然交谈与任务的第三方证据较完整，常规付费音频价仍低；作为质量与费用的平衡起点。 |
| 2 | Qwen Audio 3.0 Realtime Flash | 低价纯语音候选，有上一报告所述同型号部分第三方数据；加入价格后值得升到首轮，不表示自然度已胜过Plus。 |
| 3 | Qwen3.8 Omni Flash Realtime | 新增音频费用很低且有设备工具；同型号独立自然度证据较少。若真实体验达标且预算更重，可升为第一。 |
| 4 | Qwen Audio 3.1 Realtime Plus | 中文自然交谈重点；价格与Gemini接近，不能沿用Flash的极低成本结论。若其中文明显更适合用户，可升到前二。 |
| 5 | GPT-Realtime-2.1 Mini | 比完整版便宜，但价格未明显低于Gemini，且Mini与完整版能力分开评价。 |
| 6 | GPT-Realtime-2.1 | 成熟能力基准；在一台学生原型中，额外费用需要实际体验／任务收益支持。 |
| 7 | GPT-Live-1＋后台 | 连续聊天与后台任务并行有价值；计整段活跃会话，后台另算。长上下文场景实际总价可能与Realtime倒转，不固定宣称更贵。 |
| 8 | Grok Voice Think Fast 2.0 | 工具证据强，但免按键server_vad按整段会话收费；当前未显示出足够符合本项目的成本优势。 |
| 9 | ElevenAgents | 声音／托管工具有价值；主要成本是整个平台及另选LLM。不同音色喜好可能改变选择，不由价钱证明声音较差。 |

**StepAudio 3 Realtime Preview单列为当前低成本试验优先项。**官方本轮可见价格表将`stepaudio-3-realtime-preview`标为“限时免费”，未列结束日期或恢复后的费率。可在近期试用顺序排前，不当作未来半年永久免费。模型访问、限速、真实延迟和工具集成仍须验证。[阶跃官方价目](https://platform.stepfun.com/docs/zh/guides/pricing/details)

豆包3.0不硬插入精确名次：本轮找到统一“豆包实时语音大模型”价表，但页面未明确逐版本映射到3.0／1.2.6.1。先列价格依据和映射缺口，避免拿旧SKU价格冒充新型号已确认报价。本地模型也不因学校资源可能免费而自动第一；自然度、维护和配额仍未知。

## 2 同一使用情景的费用数量级

假设一台设备，每天10分钟活跃语音会话，其中用户说5分钟、AI说5分钟，30天：月会话300分钟、用户有声150分钟、输出150分钟。不把设备待机时间当交谈时间。

**以下只算新增音频／会话基础费用，排除历史上下文重复处理、文本／思考、工具服务、失败重试、税和后台模型。它不是完整月账单，也不是完整账单上下界。**使用常规按量价，不扣赠送额度或首次优惠。Qwen取新加坡美元价格以便比较；地区不作为淘汰条件，但价格必须绑定地区。

| 候选 | 该情景的基础费用（美元） | 计量说明 |
|---|---:|---|
| Gemini 3.8 Live | 约4.20 | 输入按整段300分钟，输出150分钟；使用官方近似每分钟费率。 |
| Qwen Audio 3.0 Realtime Flash | 0.315／0.420 | 前者假设仅150分钟用户音频成为计费输入；后者假设300分钟流全部成为计费输入。 |
| Qwen3.8 Omni Flash Realtime | 0.269／0.328 | 同上两种输入假设；普通单声道，不含视频，输出文字还会计费。 |
| Qwen Audio 3.1 Realtime Plus | 3.42／4.14 | 同上两种输入假设；不能将3.8的7 tokens/s输入换算套给Audio3.1。 |
| GPT-Realtime-2.1 Mini | 4.50 | 假设VAD过滤空白，只计150分钟用户有声输入；输出150分钟。 |
| GPT-Realtime-2.1 | 14.40 | 相同音频量，完整版价。 |
| GPT-Live-1 | 15.00＋后台 | 300分钟活跃会话；期间双方静默和等待后台仍计时。 |
| Grok Voice Think Fast 2.0 | 24.00＋部分文字事件／服务工具费 | 本项目免按键server_vad按300分钟会话；不能套按键模式的计量规则。 |
| ElevenAgents | 24.00＋LLM等 | 采用Creator常规22美元／275分钟，加25分钟×0.08；不是最低可能套餐，也未减免费／首月优惠。 |
| StepAudio3 Realtime Preview | 当前模型价目为限时免费 | 不保证账户获准无限量使用，也不排除另用收费搜索等增值能力。 |

计算记录：[calculations.json](../../output/qa/voice-price-followup-2026-09-29/calculations.json)。约1美元＝7.8港元仅可作为预算换算假设，不是本轮实时汇率报价。月300分钟的Gemini新增音频约33港元、Realtime完整约112港元、Live前台约117港元；均须再加各自未计部分。

## 3 本轮核对的官方费率与计量

- **Google：**Gemini3.8 Live音频输入约0.005美元／分钟、输出0.018美元／分钟，文本／思考另按价表。3.8主动监听常开，因此算例按整段10分钟输入，不只按用户讲话5分钟。多轮仍会重算保留的音频历史，转写开关会有额外文本费用。[官方价格](https://ai.google.dev/gemini-api/docs/pricing)、[计量说明](https://ai.google.dev/gemini-api/docs/live-api/best-practices)。
- **Qwen Audio：**新加坡Audio3.0 Flash音频入0.93／出1.87美元每百万token；Audio3.1 Plus入6.4／出24；两者输入输出均按12.5 tokens/s。Plus文字入0.8／出6.4，Flash文字入0.23／出0.7。用户音频历史重算，模型输出音频只在输出时计一次、后续按对应文字进入上下文。[官方美元表与计量](https://www.alibabacloud.com/help/en/model-studio/model-pricing)。北京Plus音频入40／出150元每百万token，另有文本费用；不混用地区或直接用货币符号比较。[官方人民币表](https://help.aliyun.com/zh/model-studio/model-pricing)。
- **Qwen Omni3.8 Realtime：**新加坡音频入0.93／出1.87美元每百万token；普通音频输入7、输出12.5 tokens/s；音频与对应输出文字分别计费。持续历史、空间音频和视频不能遗漏。[型号与价格](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash-realtime)、[具体计量](https://www.alibabacloud.com/help/en/model-studio/realtime)。
- **OpenAI：**Realtime2.1音频入32／出64、Mini入10／出20美元每百万token；输入600、输出1200 tokens/min。历史输入和文本另计，缓存可改变实际费用。Live每分钟0.05美元，后台另算。[官方价表](https://developers.openai.com/api/docs/pricing)、[计量与上下文](https://developers.openai.com/api/docs/guides/voice-latency-cost)。
- **Grok：**当前2.0为0.08美元／分钟，默认server_vad按会话时长；push-to-talk才按发送和接收音频计。客户端部分文字事件每条0.004美元，函数执行结果有豁免；不得把旧0.05标价或按键模式套给免按键设备。[确切型号计费](https://docs.x.ai/developers/models/speech-to-speech)。
- **ElevenAgents：**Creator常规22美元／月含275分钟，额外0.08美元／分钟；LLM另计。Free／Pay-as-you-go和其他套餐、长静默优惠可能影响账单，算例使用明确的Creator标准月，不声称为所有用量的最便宜套餐。[官方价格](https://elevenlabs.io/pricing/agents)。
- **豆包统一实时语音条目：**浏览器读取[官方计费说明](https://docs.volcengine.com/docs/DoubaoVoice/Billinginstructions-21?lang=zh)：音频入80／出300元每百万token，输入约6.25、输出25 tokens/s；文本、缓存、音色等独立。按150／300分钟输入与150分钟输出仅可推得72／76.5元的条件算例；页面未逐型号写明3.0，故不把它写成已确认3.0报价，且其正文算例文本输出费率与表格不一致，实际集成要按控制台SKU复核。

## 4 为什么基础费不等于月账单

例如按Qwen3.1规则作一个**条件算例**：每天一段20轮对话，每轮15秒用户音频、15秒输出；所有旧用户音频在后续轮次重算，输出音频不重复计费，忽略文字等。输入从20份新增音频变成1＋2＋…＋20＝210份处理量；每月音频项从3.42美元变成约10.26美元。这个例子不模拟噪声、缓存、实际压缩或账户账单，只解释历史长度为何会改变价格。

因此不能由表格相差几角钱判断Gemini一定比QwenPlus便宜，也不能保证Live必定比Realtime完整更贵。短会话、合理保留上下文、及时关闭空闲收费会话，再观察实际usage，才能得出可靠成本。不要靠删掉必要信息让模型反复误操作来“省token”。

对当前一台FYP，建议以Gemini建立基准，再用Qwen Audio3.0 Flash／Omni3.8 Flash检验能否用更低费用达到同样要求；StepAudio3可趁限时免费先作短测。Qwen3.1与Realtime完整保留质量对照。若较贵方案每月只多几十港元却少很多错误或等待，值得为演示质量支付；若之后扩为多设备，再重点评估规模成本。

## 5 状态

没有新增付费授权或最终模型选择。未登录服务、开通试用、接受条款、收集麦克风、调用API或改学校Proposal／日志。官方费率和条件算例已核，体验和真实账单仍待测；当前价格建议与之前能力研究并存，不回写旧测评数据。
