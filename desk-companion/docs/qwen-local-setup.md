# Group 2：Qwen本机密钥与待接入配置

2026-10-16。用户已选择`qwen3.8-omni-flash-realtime`，并报告已创建国内站Key；提供千问AI平台兼容指南。本次完成本机安全保存，没有连接、计费、麦克风／屏幕采集或Omni协议适配。

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

文件保存`DASHSCOPE_API_KEY`及`FYP_QWEN_MODEL`、聊天base URL、Realtime URL等选择元数据；保留`DESK_VOICE_PROVIDER=none`、`DESK_TEXT_PROVIDER=none`及后台关闭。**这是待接入凭据，不由现有应用自动加载，不证明Key鉴权成功。**不要把它复制进前端、版本控制或聊天。Linux/Pi部署需在目标机单独安全配置；本次没有传输到Pi。

## 本次确认的千问AI平台入口

| 用途 | 官方入口 | 本组状态 |
|---|---|---|
| OpenAI兼容Chat客户端的base URL | `https://maas.qianwenaiapi.com/compatible-mode/v1` | 已记录；完整请求为`/chat/completions`，现有文字端点白名单尚未加入该域名 |
| 所选Omni实时模型 | `wss://maas.qianwenaiapi.com/api-ws/v1/realtime?model=qwen3.8-omni-flash-realtime` | 已记录；尚未实现Omni适配器 |

依据用户提供并实际核读的[Chat API](https://platform.qianwenai.com/docs/api-reference/chat/openai-chat)、[WebSocket概览](https://platform.qianwenai.com/docs/api-reference/realtime-api/websocket-overview)及[Omni接入](https://platform.qianwenai.com/docs/api-reference/real-time-multimodal/model-access)。阿里云官方页面导航至千问主页，主页再链接上述平台，来源关系已核对。这里只保存，不向新地址传送密钥。

“OpenAI兼容”指SDK／请求格式，不会把FYP的Qwen调用变成OpenAI服务，也不会更换当前Codex聊天的模型。Chat Completions地址不能直接当作Omni Realtime地址。此千问平台文档给出公共服务域名；旧[操作说明](operator-guide.md)中阿里百炼工作空间域名属于另一条有日期的配置路线，不将两套密钥／域名默认互换。以Key所属平台的实际开通与鉴权为准。

## 下一步与边界

所选提供商／型号已经由用户确定，取代此前“尚未选择型号”的当前状态。仍缺测试花费上限、音色、实际鉴权与模型权限、Omni消息／音视频／工具适配及目标Pi验证。旧`qwen_audio`只有Audio协议，不能仅换型号就称为Omni接入。下一步沿现有语音与JobService实现Omni适配、用模拟协议验证，然后在预算明确后做真实短测。

本轮7项专门检查覆盖私有权限、状态不泄密、原文件保留、上级／目标链接拒绝、环境注入拒绝、宽权限配置拒绝与取消；Ruff通过。[QA](../../output/qa/2026-10-16-qwen-key-setup/verification.md)记录本地元数据回执，不保存秘密或音视频。
