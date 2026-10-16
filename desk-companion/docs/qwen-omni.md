# Group 2：Qwen Omni实时语音、图像与工具契约

更新：2026-10-17。所选`qwen3.8-omni-flash-realtime`已在草稿[PR #15](https://github.com/tantalum666/FYP/pull/15)实现并通过受限真实短测；普通服务仍默认关闭。本文描述本组实现和实际证据，不代表通用GUI、Pi或多语言自然度验收完成。

## 配置与目的地

- `DESK_VOICE_PROVIDER=qwen_omni`启用独立Omni适配器。型号默认且当前限于`qwen3.8-omni-flash-realtime`，音色默认Tina；音色是工程默认，尚未由用户最终选定。
- 默认WSS入口`wss://maas.qianwenaiapi.com/api-ws/v1/realtime`；后端追加model query并在握手头发送Bearer Key。仅接受该公共域名或官方工作空间`*.maas.aliyuncs.com`的同一路径，不接受端口、用户信息、自带query或fragment。工作空间路线需要自己的账号／Key匹配，未借本次公共网关试验验证。
- `DESK_QWEN_CREDENTIAL_FILE`是显式私有文件路径；仅当选择Omni且未给`DESK_VOICE_API_KEY`时加载。逐级无符号链接，父目录仅本人权限，文件必须本人所有、0600、常规文件且不超过8KiB。只取一条合法`DASHSCOPE_API_KEY`，不执行shell，也不采纳文件中的端点元数据。错误只显示安全错误码，应用本地日历仍能启动。
- Key不进入前端、状态JSON、业务备份、异常文本或Git；`VoiceConfig`的repr隐藏Key。存在性不等于真实鉴权，`configured`也不是质量／费用验收。
- [本机设置](qwen-local-setup.md)提供启用命令。Chat兼容base URL和Realtime入口分别使用；此次没有改当前Codex聊天模型或启用另一个文字模型。

## 音频和响应生命周期

输入为PCM16、16kHz、单声道，输出PCM、24kHz。`session.update`使用嵌套`audio.input/output`，ASR为`qwen3-asr-flash-realtime`，`semantic_vad`阈值0.5／静默400ms，最多1024输出tokens。保留流式40ms输入、短票据、单会话、600秒总时长／45秒空闲限制，不自动重连。这里的上限不是逐轮10秒超时。

函数用本组现有TOOLS，保持网页批准、JobService及ToolDispatcher；web search关闭，不接任意远程MCP或shell。配对客户端仍不能调用拥有者记忆工具。模型无确认、指定路径或直接执行界面的权限。

`output_item.added`关联函数item、call_id、name和response_id；参数完成、item完成或最终response可补足元数据。相同调用只分发一次。结果等待本次response结束后送回，不占住提供商发送锁；同一response的全部函数返回后仅恢复一次生成，避免生成仍活跃时重复`response.create`。

插话／停止播报会清空客户端音频、取消未批准草稿并发原生`response.cancel`。若本地已请求生成但`response.created`尚未到达，等准入回执后取消。已取消响应的迟到音频／工具不能污染新轮次，未送出的旧函数结果被丢弃，不再发送失效call_id或重启生成。已经由拥有者批准的作业沿原作业契约继续；语音结束不撤销已写入内容。

使用音频转写作为显示文本，避免与文本delta重复。usage仅保存白名单数值及模态token数，每个response_id只计一次；响应取消／失败可能缺usage，缺失不是零账单。函数缓存／响应数受限，异常结束会释放会话及采集。

## 主动图片／屏幕分享

只有拥有者在活动语音会话中能看到“分享一张图片／分享所选屏幕／停止屏幕分享”。图片与所选屏幕将经过**当前已配置的语音提供商**，供本次问答使用。它不读取姿态摄像头，也不自动取得桌面操作权限。

1. 单图由用户选择JPEG／PNG／WebP，输入文件最多4MiB；浏览器解码后等比缩至1280×720以内并重新编码JPEG，按需降低质量。
2. 屏幕由浏览器`getDisplayMedia`选择界面授予，`audio:false`，每秒最多一帧。同样缩放／重编码，连接背压时停止分享。
3. 后端逐消息检查当前拥有者会话、会话内`vision_start`及此前至少一个音频块。后端最短帧间隔900ms以容忍网络抖动；JPEG base64最多256KiB、解码最多192KiB；解析头部尺寸，最长边≤1920、短边≤1080，拒绝格式／尺寸／速率越界。头部校验不是完整像素解码器。
4. 发送计数由后端确认，图片不进数据库或应用文件。视觉帧随语音VAD提交供模型使用，选择图片本身不会额外触发一次回复；分享后可直接提问。
5. 停止分享、结束对话、关闭面板／断连会清定时器、停止所有屏幕轨道、释放隐藏video；选择器或解码晚于关闭才完成也会释放，不发新帧。停止阻止未来上传，已发内容仍在当前提供商会话中；不承诺提供商删除或保留期限。

浏览器原生屏幕选择器依赖实际平台支持；iPhone不支持时按钮禁用，其他语音／图片能力需真机检查。Pi Wayland／ARM64、窗口选择、录屏门户及真实敏感信息遮蔽尚未验收。固定摄像头坐姿闭环仍独立在本地。

## 本轮检查与预算

[完整QA](../../output/qa/2026-10-16-qwen-omni-integration/verification.md)保留源码测试、合成媒体界面及真实服务记录。215后端／21前端、Ruff／类型／生产构建通过；桌面1440×1000和窄屏390×844界面在模拟提供商下检查，无真人音视频。

用户批准本轮最多人民币5元，只用合成音频、虚构日历和生成图片。完成一次握手／设置、三次日历尝试（第一次失败、后两次成功）及一次图片问答，共五次连接；预算脚本预留4.1元后停止。真实日历工具返回三项虚构会议，成功两次都读出名称和时间；合成语音结束至首段有依据音频**收包**为3.176秒／2.619秒。蓝色矩形问答正确。

最早失败发生在两段合成语音的改口／打断附近，服务拒绝call_id，保留失败而未写成成功。新增元数据关联、取消前后生成及未送结果回归；重跑原两段输入通过。成功包本身带有name/call_id，因此不把“提供商一定漏字段”当作已证明根因。

本次核读的[平台模型价目](https://www.qianwenai.com/models/qwen3.8-omni-flash-realtime)列音频输入6／输出12元每百万token、文字／图像／视频输入1.5、文字输出4.5。平台和[Alibaba型号页](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash-realtime)对音频对应文字输出计费的说明有差异，故试验按全部已返回token×12元／百万作保守估算，不扣免费额度。三次成功响应估算合计0.106608元，失败／取消缺usage、握手及实际账单未确认。**4.1元是预留，不是消费额；0.106608元不是完整账单。**5元授权不扩为常驻使用或其他模型预算，产品尚无按人民币自动停费功能。

这些结果只证明当前Key／公共网关、英文合成日历工具闭环和单图理解。该计时取工具结果回传后的音频首包，没有标注首个有用词的声学位置；Mac收包不是浏览器实际播音或Pi成绩，两次成功没有统计p50／p95。真人普通话／英语／粤语、混说、唤醒／AEC、用户试听选声、冷启动、10秒逐轮时限、通用GUI和实体硬件仍需独立验证。

## 协议来源

本轮实际核读：[WebSocket概览](https://platform.qianwenai.com/docs/api-reference/realtime-api/websocket-overview)、[客户端事件](https://platform.qianwenai.com/docs/api-reference/real-time-multimodal/client-events)、[服务端事件](https://platform.qianwenai.com/docs/api-reference/real-time-multimodal/server-events)与[Realtime文字输入指南](https://www.alibabacloud.com/help/en/model-studio/realtime)。来源是接入契约，真实trial另列为本组证据，不能把厂商支持清单当本组全部验收。
