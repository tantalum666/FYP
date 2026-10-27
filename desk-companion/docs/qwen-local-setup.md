# Group 2：Qwen本机密钥与Omni启用

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**现行规范／入口**。已按本轮保存状态核对；最新软件、GitHub main 和 Pi 部署分开，Pi 暂停、旧 API 预算关闭。 [新聊天入口](../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

2026-10-17。用户已选择`qwen3.8-omni-flash-realtime`并提供国内千问AI平台指南。Key已私有保存；独立Omni适配器、主动图像分享和有5元上限的合成资料真实短测已完成在草稿PR #15，普通服务仍关闭。[Omni契约](qwen-omni.md)说明协议、数据范围、预算与未验部分。

## 密钥输入与保存

从`desk-companion/`运行：

```sh
# macOS本机隐藏输入窗口；不要把Key粘贴到聊天或命令参数。
python3 scripts/configure_qwen.py --native-dialog
# Linux在真实终端中隐藏输入。
python3 scripts/configure_qwen.py
# 只输出存在性、权限、所选型号及关闭状态，不显示Key。
python3 scripts/configure_qwen.py --status
```

仅依赖Python标准库，支持系统Python3.9及项目环境。默认保存到`~/.config/desk-companion/qwen.env`，目录0700、文件0600，位于Git仓库外。逐级拒绝符号链接，原子新建；已有文件不会覆盖。取消不会创建配置，格式错误不会回显输入。需要轮换时由拥有者明确处理已有私有配置，不使用脚本自动覆盖。

文件保存`DASHSCOPE_API_KEY`及`FYP_QWEN_MODEL`、聊天base URL、Realtime URL等选择元数据；保留`DESK_VOICE_PROVIDER=none`、`DESK_TEXT_PROVIDER=none`及后台关闭。**普通启动不加载；仅显式选择Omni并给出该文件路径时，后端读取Key。**不要把它复制进前端、版本控制或聊天。Linux/Pi部署需在目标机单独安全配置；本次没有传输到Pi。

## 本次确认的千问AI平台入口

| 用途 | 官方入口 | 本组状态 |
|---|---|---|
| OpenAI兼容Chat客户端的base URL | `https://maas.qianwenaiapi.com/compatible-mode/v1` | 已记录；完整请求为`/chat/completions`，现有文字端点白名单尚未加入该域名 |
| 所选Omni实时模型 | `wss://maas.qianwenaiapi.com/api-ws/v1/realtime?model=qwen3.8-omni-flash-realtime` | 已实现独立Omni适配，真实握手／虚构日历语音／单图短测通过 |

依据用户提供并实际核读的[Chat API](https://platform.qianwenai.com/docs/api-reference/chat/openai-chat)、[WebSocket概览](https://platform.qianwenai.com/docs/api-reference/realtime-api/websocket-overview)及[Omni接入](https://platform.qianwenai.com/docs/api-reference/real-time-multimodal/model-access)。阿里云官方页面导航至千问主页，主页再链接上述平台，来源关系已核对。10月16日先只保存；10月16–17日经5元授权，使用上述Realtime网关完成受限真实短测。Chat文字服务仍未接入这个新域名。

“OpenAI兼容”指SDK／请求格式，不会把FYP的Qwen调用变成OpenAI服务，也不会更换当前Codex聊天的模型。Chat Completions地址不能直接当作Omni Realtime地址。此千问平台文档给出公共服务域名；旧[操作说明](operator-guide.md)中阿里百炼工作空间域名属于另一条有日期的配置路线，不将两套密钥／域名默认互换。以Key所属平台的实际开通与鉴权为准。

## 显式启用Omni

前端构建后，从`desk-companion/`在拥有者自己的终端启动：

```sh
DESK_VOICE_PROVIDER=qwen_omni \
DESK_QWEN_CREDENTIAL_FILE="$HOME/.config/desk-companion/qwen.env" \
.venv/bin/uvicorn desk.app:create_app --factory --app-dir backend --host 127.0.0.1 --port 8831 --workers 1 --no-access-log
```

不用`source qwen.env`，不用把Key放进命令参数。后端只读取Key，不执行文件，不使用该文件里的端点元数据；型号与公共WSS默认值由代码固定。也可给`DESK_VOICE_API_KEY`，但不要将真实值写入聊天、Git或命令历史。已有环境中的型号／端点需与[Omni契约](qwen-omni.md)匹配。

systemd用户可在私有`.runtime/service.env`设置`DESK_VOICE_PROVIDER=qwen_omni`和`DESK_QWEN_CREDENTIAL_FILE`的**目标机绝对路径**，其余语音型号／端点可留空用默认值；EnvironmentFile不替换`$HOME`。普通示例继续为none。每台目标机分别安全配置，不自动复制本机Key到Pi。

在Assistant点击“Start conversation／开始交谈”才申请麦克风并连接。图片／屏幕另需主动选择，停止分享不会删除提供商已收到的会话内容。启动普通服务不会自动发起语音，但用户开始真实会话后会产生新的服务用量；本轮5元试验授权不是日常运行预算，当前没有人民币自动停费开关。

## 当前证据与剩余

10月16日的隐藏输入和7项私有文件检查见Key设置QA (local historical material: `output/qa/2026-10-16-qwen-key-setup/verification.md`; not included in this checkpoint)。10月16–17日的真实短测和215后端／21前端检查见Omni QA (local historical material: `output/qa/2026-10-16-qwen-omni-integration/verification.md`; not included in this checkpoint)。Key／所选模型在公共网关已鉴权成功，两次虚构日历回复与合成蓝色图片问答通过。

测试只用合成音频／图片和虚构日历；没有采集真实麦克风或屏幕，没有目标Pi结果。Tina是工程默认音色，真人语言／AEC、实际播放5秒统计、逐轮10秒时限、Pi和通用GUI仍待验。预算预留4.1元、已返回usage的保守估算0.106608元，两者均不是实际完整账单，失败／取消的usage缺口保留。
