# Group 2：Qwen Omni实时语音、图像与工具契约

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**现行规范／入口**。已按本轮保存状态核对；最新软件、GitHub main 和 Pi 部署分开，Pi 暂停、旧 API 预算关闭。 [新聊天入口](../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

更新：2026-10-24（同轮跨日收尾）。所选qwen3.8-omni-flash-realtime充值后已恢复，最新补测 (local historical material: `output/qa/2026-10-23-ai-acceptance/resumed/verification.md`; not included in this checkpoint)完成40条有效实际播音计时、合成停顿／插话和模型负面用例。41次尝试保留1次测试保护计时缺口，不混入早期长会话；首有用词／真人自然度与Pi另验。用户累计授权提高至15元，本次执行已结束。后端279项重跑通过、前端56项沿用；初始接入仍在草稿[PR #15](https://github.com/tantalum666/FYP/pull/15)，本地改动未推送。

## 配置与目的地

- `DESK_VOICE_PROVIDER=qwen_omni`启用独立Omni适配器。型号默认且当前限于`qwen3.8-omni-flash-realtime`，音色默认Tina；音色是工程默认，尚未由用户最终选定。
- 默认WSS入口`wss://maas.qianwenaiapi.com/api-ws/v1/realtime`；后端追加model query并在握手头发送Bearer Key。仅接受该公共域名或官方工作空间`*.maas.aliyuncs.com`的同一路径，不接受端口、用户信息、自带query或fragment。工作空间路线需要自己的账号／Key匹配，未借本次公共网关试验验证。
- `DESK_QWEN_CREDENTIAL_FILE`是显式私有文件路径；仅当选择Omni且未给`DESK_VOICE_API_KEY`时加载。逐级无符号链接，父目录仅本人权限，文件必须本人所有、0600、常规文件且不超过8KiB。只取一条合法`DASHSCOPE_API_KEY`，不执行shell，也不采纳文件中的端点元数据。错误只显示安全错误码，应用本地日历仍能启动。
- Key不进入前端、状态JSON、业务备份、异常文本或Git；`VoiceConfig`的repr隐藏Key。存在性不等于真实鉴权，`configured`也不是质量／费用验收。
- [本机设置](qwen-local-setup.md)提供启用命令。Chat兼容base URL和Realtime入口分别使用；此次没有改当前Codex聊天模型或启用另一个文字模型。

## 音频和响应生命周期

输入为PCM16、16kHz、单声道，输出PCM、24kHz。`session.update`使用嵌套`audio.input/output`，ASR为`qwen3-asr-flash-realtime`，`semantic_vad_ec`阈值0.5／静默700ms，最多1024输出tokens。保留流式40ms输入、短票据、单会话、600秒总时长／45秒空闲限制，不自动重连。另由VoiceTurns执行逐轮5秒提示／10秒截止，工具往返不重置计时。

2026-10-23续轮：原semantic_vad在同一合成粤语中两次未发出speech/ASR事件；semantic_vad_ec在ready与冷连接测试成功，统一用于初始化和切回语音。[官方Realtime指南](https://www.alibabacloud.com/help/en/model-studio/realtime)列出该模式；真人回声／噪声质量另验。生成参数temperature=0.2、presence_penalty=0，事实正确性仍依赖当前数据与程序批准，不能只靠温度保证。

连接尚未ready时，浏览器仅在内存保留最多5秒PCM及原始采集端点；就绪后按顺序发送，超限明确失败，取消／关麦／断连立即清除。后端在消费票据前验证prebuffer_ms为0–5000的整数，只给相应一次性上传余量。用户点击语音之前不会采集。

当前日历查询要求当轮工具结果，包含连续重复／只问数量；没有结果的答案不送往客户端，在原10秒内最多补查一次。相同无效参数连续两次后停止。图片中的日历问题不误要求本地日历查询。输出戳若与单调时钟相差超过5秒，使用明确标记的audio_context_estimate，负时差不能当0ms达标。

函数用本组现有TOOLS，保持网页批准、JobService及ToolDispatcher；web search关闭，不接任意远程MCP或shell。配对客户端仍不能调用拥有者记忆工具。模型无确认、指定路径或直接执行界面的权限。

`output_item.added`关联函数item、call_id、name和response_id；参数完成、item完成或最终response可补足元数据。相同调用只分发一次。结果等待本次response结束后送回，不占住提供商发送锁；同一response的全部函数返回后仅恢复一次生成，避免生成仍活跃时重复`response.create`。

插话／停止播报会清空客户端音频、取消未批准草稿并发原生`response.cancel`。若本地已请求生成但`response.created`尚未到达，等准入回执后取消。已取消响应的迟到音频／工具不能污染新轮次，未送出的旧函数结果被丢弃，不再发送失效call_id或重启生成。已经由拥有者批准的作业沿原作业契约继续；语音结束不撤销已写入内容。

语音模式使用音频转写作为显示文本，纯文字模式处理text delta／done，避免两者重复。usage仅保存白名单数值及模态token数，每个response_id只计一次；响应取消／失败可能缺usage，缺失不是零账单。函数缓存／响应数受限，异常结束会释放会话及采集。

公共网关可能发送没有type的REST式错误；AccessDenied.Unpurchased映射为VOICE_MODEL_ACCESS_DENIED，界面提示检查千问模型权限／开通状态并停止连接。未发送文本保留，不误显示成未知写入；不回显服务商原文或敏感请求，也不据此认定余额不足。

用户表示充值后，已用同Key／同型号成功重连并调用日历。后续41次数量查询尝试有40条完整计时，1条测试保护缺口保留；4种合成输入各有10条有效结果。句中停顿保留前段日期，插话切换到新轮且未接收旧轮音频。产品语音／输出参数未变；最后针对创建时长增加明确追问规则。详细失败、预算边界与后端再验均在最新QA，不把合成材料等同真人声学。

## HISTORICAL：2026-10-23同模型文字／语音首次验收

拥有者输入框已接同一Omni实时会话：文字模式`modalities=[text]`且VAD关闭，不申请麦克风或创建AudioContext；显式开启语音再切`[text,audio]`。模式确认前不恢复输入，关闭／迟到资源释放。已有ToolDispatcher／JobService／页面审批保持，切换不取消已经完成、待本人核对的草稿。[统一对话契约](omni-conversation.md)定义RAM上下文上限／到期／拥有者隔离和新对话。长期记忆共用原服务，修订后清旧连接与重放，不能声称远端留存删除。

本轮249后端／48前端与实际模拟页面通过。新授权最多5元的两条真实连接验证纯文字Cedar记忆、同连接切语音正确查三场会议再回文字，以及重连后的中文指代。工具后实际播音3.1861秒，切换主动打断剩余播放，不计完整播放验收。预留4.8元、已返usage估算0.348144元，非账单；测试已停止。详见本轮QA (local historical material: `output/qa/2026-10-23-omni-unified/verification.md`; not included in this checkpoint)，不混用此前预算或声学统计。

## 2026-10-22 浏览器生命周期修复

所有语音适配器共用的VoiceAudio现在在AudioContext恢复、麦克风权限、worklet加载和票据获取后检查取消；停止后不再申请下一资源，迟到麦克风轨道立即释放。关闭时拆除socket回调和worklet端口，旧连接不能把新面板切回ready。面板的语音资源只在真实卸载时清理；语言变化导致的轮询重建不会误关活动连接。

麦克风许可成功后，音频初始化／票据／WebSocket／ready合计最多等待10秒，超时关闭本机采集与连接并提示可重试／文字输入。首次授权等待不计入此10秒。**这是连接保护，不是说完后10秒有效回答时限。**不自动重连或自动重试收费请求。

无效JSON、空／奇数字节PCM、错误采样率、超大帧和播放队列超限进入错误收尾；服务器turn_complete等到本机队列播完才更新前端“聆听”，插话清理待播和未送达的完成通知。后台服务状态与实际本机扬声器状态仍各有来源。7项新增合成音频生命周期回归在本轮QA (local historical material: `output/qa/2026-10-22-alice-software/verification.md`; not included in this checkpoint)，没有开启真人采集或收费连接。

## 主动图片／屏幕分享

只有拥有者在活动语音会话中能看到“分享一张图片／分享所选屏幕／停止屏幕分享”。图片与所选屏幕将经过**当前已配置的语音提供商**，供本次问答使用。它不读取姿态摄像头，也不自动取得桌面操作权限。

1. 单图由用户选择JPEG／PNG／WebP，输入文件最多4MiB；浏览器解码后等比缩至1280×720以内并重新编码JPEG，按需降低质量。
2. 屏幕由浏览器`getDisplayMedia`选择界面授予，`audio:false`，每秒最多一帧。同样缩放／重编码，连接背压时停止分享。
3. 后端逐消息检查当前拥有者会话、会话内`vision_start`及此前至少一个音频块。后端最短帧间隔900ms以容忍网络抖动；JPEG base64最多256KiB、解码最多192KiB；解析头部尺寸，最长边≤1920、短边≤1080，拒绝格式／尺寸／速率越界。头部校验不是完整像素解码器。
4. 发送计数由后端确认，图片不进数据库或应用文件。视觉帧随语音VAD提交供模型使用，选择图片本身不会额外触发一次回复；分享后可直接提问。
5. 停止分享、结束对话、关闭面板／断连会清定时器、停止所有屏幕轨道、释放隐藏video；选择器或解码晚于关闭才完成也会释放，不发新帧。停止阻止未来上传，已发内容仍在当前提供商会话中；不承诺提供商删除或保留期限。

浏览器原生屏幕选择器依赖实际平台支持；iPhone不支持时按钮禁用，其他语音／图片能力需真机检查。Pi Wayland／ARM64、窗口选择、录屏门户及真实敏感信息遮蔽尚未验收。固定摄像头坐姿闭环仍独立在本地。

## HISTORICAL：2026-10-16首次检查与预算

完整QA (local historical material: `output/qa/2026-10-16-qwen-omni-integration/verification.md`; not included in this checkpoint)保留源码测试、合成媒体界面及真实服务记录。215后端／21前端、Ruff／类型／生产构建通过；桌面1440×1000和窄屏390×844界面在模拟提供商下检查，无真人音视频。

用户批准本轮最多人民币5元，只用合成音频、虚构日历和生成图片。完成一次握手／设置、三次日历尝试（第一次失败、后两次成功）及一次图片问答，共五次连接；预算脚本预留4.1元后停止。真实日历工具返回三项虚构会议，成功两次都读出名称和时间；合成语音结束至首段有依据音频**收包**为3.176秒／2.619秒。蓝色矩形问答正确。

最早失败发生在两段合成语音的改口／打断附近，服务拒绝call_id，保留失败而未写成成功。新增元数据关联、取消前后生成及未送结果回归；重跑原两段输入通过。成功包本身带有name/call_id，因此不把“提供商一定漏字段”当作已证明根因。

本次核读的[平台模型价目](https://www.qianwenai.com/models/qwen3.8-omni-flash-realtime)列音频输入6／输出12元每百万token、文字／图像／视频输入1.5、文字输出4.5。平台和[Alibaba型号页](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash-realtime)对音频对应文字输出计费的说明有差异，故试验按全部已返回token×12元／百万作保守估算，不扣免费额度。三次成功响应估算合计0.106608元，失败／取消缺usage、握手及实际账单未确认。**4.1元是预留，不是消费额；0.106608元不是完整账单。**5元授权不扩为常驻使用或其他模型预算，产品尚无按人民币自动停费功能。

这些结果只证明当前Key／公共网关、英文合成日历工具闭环和单图理解。该计时取工具结果回传后的音频首包，没有标注首个有用词的声学位置；Mac收包不是浏览器实际播音或Pi成绩，两次成功没有统计p50／p95。真人普通话／英语／粤语、混说、唤醒／AEC、用户试听选声、冷启动、Pi硬件播音、通用GUI和实体硬件仍需独立验证；逐轮时限已在10月22日续轮补齐。

## 协议来源

本轮实际核读：[WebSocket概览](https://platform.qianwenai.com/docs/api-reference/realtime-api/websocket-overview)、[客户端事件](https://platform.qianwenai.com/docs/api-reference/real-time-multimodal/client-events)、[服务端事件](https://platform.qianwenai.com/docs/api-reference/real-time-multimodal/server-events)与[Realtime文字输入指南](https://www.alibabacloud.com/help/en/model-studio/realtime)。来源是接入契约，真实trial另列为本组证据，不能把厂商支持清单当本组全部验收。

## 2026-10-22 续轮：输出时钟、逐轮截止与新预算

新增逐轮ID、工具完成门槛、5秒等待状态／10秒取消、迟到草稿围栏；Web Audio输出时钟和原生PortAudio DAC时钟区分收包与实际播音。客户端缺VAD也有临时截止，暂停的AudioContext不算回应。Assistant → More → Response timing显示最近20轮数值，不存录音。首个工具后声学样本不是自动证明语义正确，semantic_verified=false。

本轮发现并修复系统SOCKS代理所需python-socks依赖、400ms断句过早附近的失败，以及模型生成快于播放时正常回答超过旧8秒队列的问题；Python／浏览器队列上限统一30秒。保留连接10秒与会话600秒边界。最后一次真实合成英文／虚构日历短测2.9252秒开始实际播放，完整三项回答正确、outcome=played、无客户端错误。前两次真实连接失败仍记录，不能只留成功率分子。

本轮单独授权最多5元；3次真实连接各预留1.6元，总4.8元，另一次本机未联网失败释放预留且保留记录。已返回usage的保守估算共0.240540元，不是实际账单／完整费用。测试服务已停止；常驻生产服务没有人民币硬限额。普通软件默认none；用户这张Pi专用镜像显式配置现有Omni Key，只有点击语音才请求服务。QA (local historical material: `output/qa/2026-10-22-voice-linux-sd/verification.md`; not included in this checkpoint)。
