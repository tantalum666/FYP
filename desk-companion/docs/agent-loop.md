# 文字代理循环与工具审计

2026-10-27，Group 2。这是工程实现，不是供应商决定，也不是任意电脑或应用控制。

托管模型只负责提出一个结构化调用。执行、拒绝、批准和记录都在本组代码里。Qwen 与 Gemini 仍是仅有的文字适配器，入口仍是 `text_providers.py`。

## 一轮里发生什么

`desk/agent_loop.py` 的 `AgentLoop` 向提供方要一个 `ModelStep`：给拥有者看的一句话，加上 `none` 或一个工具名和参数。

- 最多 3 步。某步开始前若已经超过 45 秒，不再调用工具，也不再要下一步。正在进行的单次 HTTP 仍受适配器 20 秒超时限制；这个时限不会中途杀掉请求。
- 提供方返回 `TEXT_AI_UNAVAILABLE` 时，该步在执行工具之前最多共试 3 次。失败的完成不会重放已经执行过的工具。
- `read` 工具可以把错误交回下一步，让模型改参数或改口答复。
- `draft`、`cancel`、`stop` 只执行一次，然后结束本轮。
- 未知工具名直接拒绝，不进入执行器。可见回复是固定的拒绝句，不用模型那句“已经做完”的话。

有副作用的调用仍进 `assistant.tool`。草稿和作业准备不写入。作业取消和软件停止沿用原来的作业契约和输出急停，没有第二套批准，也没有绕过批准的新写入。模型没有确认工具。

## 注册表

`desk/capabilities.py` 给每个现有工具一个风险，并用原来的 Pydantic 模型校验参数。名称集合与 `assistant.TOOLS` 相同，避免语音工具表和文字循环各写一份名单后走样。

| 风险 | 工具 | 执行后 |
|---|---|---|
| read | `memory_query`、`task_query`、`task_details`、`calendar_query`、`computer_job_status`、`device_status`、`posture_status` | 只返回数据 |
| draft | 记忆、事务、日历、设备预设和电脑作业的准备工具 | 提案或待审作业，拥有者另确认后才写入 |
| cancel | `computer_job_cancel` | 原作业取消路径。未开始的作业不产生文件；已写入的文件不假装回滚 |
| stop | `stop_physical_outputs` | 原软件停止闩。不表示物理断电已经确认 |

## 提供方

`HostedTextProvider` 只调用 `TextAssistant.generate`。因此密钥、端点白名单和 JSON 解析仍在原适配器。`DESK_TEXT_DAILY_CAP` 默认 40，只接受 1 到 500 的整数，否则仍用 40。它按 UTC 日统计 `purpose=conversation` 的调用，失败和重试都计数。达到上限后不再发请求，并告诉拥有者没有修改。跟进建议仍单独每天最多 20 次，这段循环不会把失败的建议自动重试。

`ScriptedProvider` 按给定步骤返回，不打开网络。离线场景在 `desk/agent_eval.py`，由 `tests/test_agent_loop.py` 调用：准备一条提醒草稿且不写入日历、按记忆查询回答、拒绝 `shell_exec`、提供方第一次失败后重试成功。

## 审计

每次进入 `assistant.tool` 的调用，以及文字／语音在执行前就拒绝的调用，写入 `tool_calls`。记录通道（`text`、`voice`、`local`）、工具、风险、参数、结果代码、是否保存、提案或作业 id。参数最长约 12000 字符，更长则只留截断预览。不记录 API 密钥。

`GET /api/assistant/tool-calls` 只接受拥有者会话。助理面板在拥有者登录时列出这些记录。配对屏得到 403，响应里没有参数。

## 还没有做

没有新增任意目录、shell、浏览器或 GUI 工具。没有付费模型调用，也没有用离线场景代替真实自然度或任务成功率。语音实时协议仍由原适配器接收工具调用，执行和审计与文字共用 `assistant.tool`。主动跟进的调度不在这一片。
