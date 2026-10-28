# 助理回复流契约

2026-10-28，Group 2。未走统一 Omni 实时连接的网页和 iPhone 文字入口使用同一个回复流。JSON 接口仍然存在。

## 请求

`POST /api/assistant/messages/stream`

请求体与 `POST /api/assistant/messages` 相同：`message`、`language`，以及可选的 `task_id`、`conversation_id`。需要 `X-Desk-Request: 1` 和 `X-Operation-Id`。操作回执绑定已认证 principal 和精确请求；同一操作 id 重试不再调用提供方或创建第二份草稿。会话重放另按登录和事务隔离。已知拥有者回执可在重新登录后恢复，旧聊天不会因此重放。

响应是 `text/event-stream`。每个事件一行 `data: ` 加 JSON，然后空行。事件之间可以一次到达，也可以分成任意字节块。客户端不能假设块的边界。

## 事件

| type | 字段 | 客户端 |
| --- | --- | --- |
| `tool` | `phase` 为 `started` 或 `finished`，`tool`。结束时另有 `outcome` 和 `saved` | 显示进度。没有 `arguments` |
| `preview` | `text` | 用整段文字替换当前可见回复 |
| `delta` | `text` | 接到当前可见回复后面。这是没有真实片段时的退路 |
| `done` | `reply`，其中 `message` 是完整回复，拥有者另获 `conversation_id` | 用这份回复结束本回合 |
| `error` | `code`，可选 `status` | 结束本回合 |

`preview` 只显示已经抽出的 `message`。读取工具下一步之前会把预览清成空字符串。草稿仍要拥有者在屏幕上批准。参数留在拥有者审计里，不进入这条流。

固定样例在 [assistant-stream.sse](../contracts/assistant-stream.sse)。它把五种事件放在同一段正文里，用来锁定字段，不是一次真实模型回合的记录。

## 手机

iPhone 的 `DeskNative.request` 把整个响应体作为 base64 交回。应用把它还原成一个 `Response`，再用和网页相同的解析器读完。因此手机看到同一套事件，但不声称插件会逐 token 回调。未配置文字模型时，本地规则也走这条流。原来的 JSON `POST /messages` 保留给不读事件流的调用方。

网页在浏览器里按块读取。75 秒后中止。原生桥不接收这个中止信号；计时器到期后应用不再等待结果，桥上的请求可能仍在进行。

## 中断与身份变化

EOF 不等于完成。只有完整 `done` 才清除待确认操作；`error` 按状态处理，未知结果保留原操作 id。Check save status 用同一 SSE 接口恢复，成功后清理匹配的输入／错误／预览，并明确草稿仍需确认，不显示成已经写入记忆。迟到回复受组件与提交代次保护。

共享工作空间在 principal 类型／ID 改变时重建界面并清掉旧待处理请求，防止拥有者内容残留到配对身份；同身份本机预览续期保留未发送文字，丢弃旧会话恢复句柄，不自动重试写入。
