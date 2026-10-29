# 文字代理循环与工具审计

2026-10-29，Group 2。这是工程实现，不是供应商决定，也不是任意电脑或应用控制。交接清单见 [agent-loop-handoff.md](agent-loop-handoff.md)。

托管模型只负责提出一个结构化调用。执行、拒绝、批准和记录都在本组代码里。Qwen 与 Gemini 是当前托管文字适配器；另有明确离线的 fake 演示适配器，其他候选未被排除，入口仍是 `text_providers.py`。

## 一轮里发生什么

`desk/agent_loop.py` 的 `AgentLoop` 向提供方要一个 `ModelStep`：给拥有者看的一句话，加上 `none` 或一个工具名和参数。语音实时协议仍由原适配器接收下一步；它不跑这段多步循环。两边真正执行工具时都调用 `desk/tool_policy.py` 的 `execute_tool()`。

- 最多 3 步。某步开始前若已经超过 45 秒，不再调用工具，也不再要下一步。正在进行的单次 HTTP 仍受适配器 20 秒超时限制；这个时限不会中途杀掉请求。
- 提供方返回 `TEXT_AI_UNAVAILABLE`，或返回无法使用的步骤时，该步在执行工具之前最多共试 3 次。三次之后给拥有者一句可读说明，不声称已经完成，也不执行工具。失败的完成不会重放已经执行过的工具。
- 每个工具有自己的等待上限：读取 5 秒，草稿 8 秒，取消 5 秒，停止 3 秒。超时后不再重试这次调用。线程如果稍后才准备好草稿或待审作业，策略会把它取消。这不会杀掉已经进入数据库事务的线程。
- `read` 工具可以把普通错误交回下一步，让模型改参数或改口答复。读取超时则结束本轮。
- `draft`、`cancel`、`stop` 只执行一次，然后结束本轮。
- 未知工具名直接拒绝，不进入执行器。可见回复是固定的拒绝句，不用模型那句“已经做完”的话。

有副作用的调用按同一用户操作、工具和参数只接受一个持久结果；只读工具每次重新查询当前数据，不从持久工具结果缓存重放旧事实。文字用这条消息的操作 id 做范围，语音用会话 id 加提供方的 call id。因此同一次请求的重试不会准备出第二份草稿。新的消息或新的语音 call id 可以再准备一次。

有副作用的调用仍进 `assistant.tool`。草稿和待审作业记录会持久保存，但准备阶段不修改目标日历／事实，也不创建目标文件。作业取消和软件停止沿用原来的作业契约和输出急停，没有第二套批准，也没有绕过批准的新写入。模型没有确认工具。

## 注册表

`desk/capabilities.py` 给每个现有工具一个风险，并用原来的 Pydantic 模型校验参数。名称集合与 `assistant.TOOLS` 相同，避免语音工具表和文字循环各写一份名单后走样。

`owner_search` 在拥有者的笔记、事务、日历和记忆里做有限检索。笔记只包括已经交给电脑作业的 `save_note` 正文，不读任意目录。排序是确定性的：英文词和中文单字及相邻两字，重合多的在前，相同重合时更新的在前。`plate_summary` 用拥有者时区列出今天或本周（周一到周日）的未完成事务和日历项。`owner_clock` 返回同一时区的当前时间、今天和这一周的日期。配对会话看不到这三个工具，调用也会被拒绝。

| 风险 | 工具 | 执行后 |
|---|---|---|
| read | `memory_query`、`task_query`、`task_details`、`calendar_query`、`computer_job_status`、`device_status`、`posture_status`、`owner_search`、`plate_summary`、`owner_clock`、`propose_plan` | 只返回数据。`propose_plan` 最多五个步骤，不写入 |
| draft | 记忆、事务、日历、设备预设和电脑作业的准备工具 | 提案或待审作业；默认单次确认，适用的新拥有者请求可由独立Full access策略应用 |
| cancel | `computer_job_cancel` | 原作业取消路径。未开始的作业不产生文件；已写入的文件不假装回滚 |
| stop | `stop_physical_outputs` | 原软件停止闩。不表示物理断电已经确认 |

## 提供方

`HostedTextProvider` 在没有流式回调时调用 `TextAssistant.generate`。网页流走 `generate_live`；流失败且还没有文本时，先原子预留另一次用量记录，再调用适配器的 `complete()`；无剩余额度时不发起回退请求。密钥、端点白名单和 JSON 解析仍在原适配器。`DESK_TEXT_DAILY_CAP` 默认 40，只接受 1 到 500 的整数，否则仍用 40。它按 UTC 日统计 `purpose=conversation` 的调用，失败和重试都计数。达到上限后不再发请求，并告诉拥有者没有修改。跟进建议仍单独每天最多 20 次，这段循环不会把失败的建议自动重试。

`ScriptedProvider` 按给定步骤返回，不打开网络。离线场景在 `desk/agent_eval.py`，由 `pytest` 调用，不需要网络：

- 准备一条提醒草稿，且不写入日历
- 先查记忆再回答，事实不会提前放进提示
- 拒绝 `shell_exec`
- 电脑笔记草稿停在待审，不写文件
- 连续读取达到 3 步后停止
- 注入时钟后，超时不再开始下一个工具
- 提供方第一次失败后重试成功
- 同一拒绝从文字循环和语音调度各走一遍，审计结果一致

### 如何加一个场景

1. 在 `agent_eval.py` 写 `scenario_<名字>(new_runtime)`。`new_runtime()` 每次返回一套新的本地运行时。
2. 用 `ScriptedProvider` 给出 `ModelStep` 或一个 `DomainError`。不要打开套接字，也不要调用托管模型。
3. 用 `raise AssertionError` 表示失败。检查草稿没有落库、拒绝没有副作用、审计的工具、风险、结果和 `saved`。
4. 把函数名加进 `run_all` 的元组。`tests/test_agent_loop.py` 会按这个顺序检查。
5. 语音只比较调度结果时，用 `ToolDispatcher.submit` 发一条调用，并和文字循环的审计行对照。不要另写一套参数校验。

## 对话质量

`desk/conversation_eval.py` 另有一组场景，不放进上面的 `run_all`，所以原来的名单保持不变。离线检查人格是否进入系统提示并且回复仍自称 Desk Companion、越界或危险请求被拒绝、含糊请求只问一个问题且不调用工具。中英文都有。`pytest` 用 `ScriptedProvider`，不联网。

### 如何加一个对话场景

1. 在 `cases()` 里加一条 `ConversationCase`。`expect` 只能是 `persona`、`refuse` 或 `clarify`。
2. `scripted_message` 和 `scripted_tool` 是离线模型的那一步。拒绝场景要给出注册表里没有的工具名。含糊场景的工具是 `none`，回复里只能有一个 `?` 或 `？`。
3. 检查函数是 `check_persona`、`check_refuse`、`check_clarify`。真实提供方脚本用同一套函数。
4. 把名字加进 `tests/test_conversation_eval.py` 的顺序断言。

可选的真实提供方只在 `scripts/conversation_eval.py`。它在这三个条件同时成立时才发请求：`DESK_CONVERSATION_EVAL=1`、文字提供方已按现有规则配置、`DESK_CONVERSATION_EVAL_CAP` 是 1 到 24 的整数。上限在每次调用前检查，用完就停。每个场景用一套新的临时运行时，不打开拥有者的数据库。不要把这个脚本放进 CI。

## 回复流

`POST /api/assistant/messages` 仍然一次返回整段 JSON。未使用统一 Omni 的网页文字入口走 `POST /api/assistant/messages/stream`，用 `text/event-stream`。Qwen 与 Gemini 的 `deltas()` 按提供方的流式接口交出文本片段。程序从尚未写完的 JSON 里抽出 `message`，用 `preview` 事件替换当前可见文字。读取工具在下一步之前会清空这段预览。草稿或最终回复如果已经按真实片段出现，就不再切成 24 字。流失败且还没有任何文本时，单独计数后改走原来的 `complete()`，再按最多 24 字分段。工具事件仍只有名字和阶段。未配置文字模型时走本地规则的分段。同一操作 id 的缓存回复不会再调用提供方。网页和 iPhone 都请求这条流；手机桥可能一次交回整个正文，解析规则相同。字段见 [assistant-stream.md](assistant-stream.md)。原来的 JSON 接口仍保留。

## 上下文预算

`pack_conversation` 用字符数而不是分词器。默认约 12000 字，不含工具名单；工具名不能为了缩短上下文被删掉。短人格摘要、当前这句话、选中的事务、待批准草稿和最近一次工具结果始终保留。待批准行带 `saved: false`。放不下时先去掉日历，再去掉事务、较旧的对话轮次，最后去掉排序靠后的记忆。配对会话不写入、也不读取这些轮次，也不打包记忆草稿。

近期文字复用 `conversation.py` 的有界 RAM 对象，绑定拥有者登录和所选事务；不建立全局 `assistant_turns` 数据库表。HTTP 预算最多取该对象最近 16 条、每条 500 字的视图。配对和本机语音工作进程没有可恢复的拥有者聊天缓存。Omni 保留自己的有界重放／当前事实机制，其他已配置语音适配器可在启动时使用同一拥有者对象的预算视图。音频不入库。超长的工具结果会留下是否保存、错误、提案或作业标识，并截断其余正文。

## 离线评估表

在 `desk-companion/` 运行 `.venv/bin/python scripts/tool_eval.py`。它依次跑代理循环、对话质量和检索排序的全部离线场景，打印一张 `suite`、`name`、`result` 表。全部通过时退出码 0，否则 1。不联网，不读取 `DESK_CONVERSATION_EVAL`，也不进入 CI。可选的真实对话脚本仍是 `scripts/conversation_eval.py`，条件不变。

## 审计

模型路径上的每次调用只写一行 `tool_calls`：文字循环、语音调度，以及两者在执行前就拒绝的调用。本地规则直接调用 `assistant.tool` 时仍会写一行。记录通道（`text`、`voice`、`local`）、工具、风险、参数、结果代码、是否保存、提案或作业 id，以及给拥有者看的短句。参数最长约 12000 字符，更长则只留截断预览。不记录 API 密钥。

`GET /api/assistant/tool-calls` 只接受拥有者会话。助理 More → Tool activity 在拥有者登录时列出这些记录。配对屏得到 403，响应里没有参数。

## 还没有做

没有新增任意目录、shell、浏览器或 GUI 工具。没有付费模型调用，也没有用离线场景代替真实自然度或任务成功率。语音实时协议仍接收模型给出的调用，执行、拒绝、超时和审计与文字共用 `execute_tool()`。主动跟进的调度不在这一片。

## 2026-10-28 整合约束

参数校验保留未提供字段的状态，不能把默认值补进改期请求而清空备注、地点、提醒或重复规则。记忆删除会清理关联回复、草稿、历史操作／审计副本，并把旧工具结果变成失效回执；不删除操作键后重新执行。目标标记的草稿在列出和决定时都要求拥有者。完整证据见[整合QA](../../output/qa/2026-10-28-grok-review-merge/verification.md).

## 2026-10-29：独立的持续授权

Full access不修改这个循环的三步／一次effect限制。HTTP在得到新回复后、实时调度在新draft结果后，通过PermissionService核验拥有者会话／策略版本／请求边界，再使用原业务服务应用。模型不获得确认或改权限工具；read状态查询及旧缓存不会借此批准旧待审动作。自动效果与单次确认记录不同来源。详见[权限契约](assistant-permissions.md)；多效果串行编排与部分成功恢复尚未因此实现。
