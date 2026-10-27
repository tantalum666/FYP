# 代理循环交接

2026-10-27，Group 2。这份说明从当前代码整理，不是供应商决定，也不是导师批准或已经合并到 `main`。契约细节仍以 [agent-loop.md](agent-loop.md) 为准。手机流字段见 [assistant-stream.md](assistant-stream.md)。记忆边界见 [memory.md](memory.md)。

## 已经有的

托管模型只提出一个 `ModelStep`。执行、拒绝、超时和审计在 `execute_tool()`。文字和语音共用这一处。模型没有确认工具。草稿和电脑笔记停在待审，拥有者在屏幕上确认后才写入。

- **文字循环。** `AgentLoop` 最多 3 步、45 秒。提供方失败或无法使用的步骤在调用工具前最多试 3 次。读工具可以把普通错误交回下一步。草稿、取消、停止和读超时结束本轮。`propose_plan` 出错也结束本轮；成功不结束，所以后面还可以再准备一个草稿。
- **注册表。** `CAPABILITIES` 与 `assistant.TOOLS` 的名字集合相同。风险是 `read`、`draft`、`cancel`、`stop`。参数用原来的 Pydantic 模型校验。未知工具名直接拒绝。
- **同一结果只保留一份。** 文字的范围是用户操作 id。语音的范围是会话 id 加提供方 call id。超时后晚到的未批准草稿或待审作业会被丢掉。
- **检索。** `desk/rank.py` 用英文词、中文单字和相邻两字，再加上更新时间。`owner_search` 排序全部活动记忆。带 `query` 的 `memory_query` 只排序 `for_model()` 的最新 40 条。空查询仍返回那 40 条。
- **回复流。** Qwen／Gemini 的 `deltas()` 抽出 JSON 里的 `message`，用 `preview` 替换可见文字。没有任何文本时，同一条用量记录改走一次 `complete()`，再按最多 24 字发 `delta`。工具事件没有参数。网页和 iPhone 都请求 `POST /api/assistant/messages/stream`。手机桥可以一次交回整个正文。JSON `POST /messages` 仍在。
- **上下文。** `pack_conversation` 按字符预算组装，默认约 12000，工具名单不计入。短人格、当前这句话、选中事务、全部待批准草稿和最近一次工具结果始终保留。放不下时先去掉日历，再去掉事务、较旧轮次和排序靠后的记忆。拥有者文字、拥有者语音和本机语音工作进程把文本轮次写入同一张表。配对会话不写、不读。音频不入库。拥有者语音提示在会话开始时附上预算留下的记忆命中（用上一句用户转写或调用方给出的文字，经 `rank.py` 排序）和全部待批准草稿。配对会话的提示不包含这些。这一通新说的话要到下一通会话才参与排序。
- **离线表。** `scripts/tool_eval.py` 跑代理循环、脚本化对话质量和检索排序，打印通过／失败。不联网。可选的真实对话脚本另有三个环境条件，不由这张表触发。
- **审计。** 拥有者看 `GET /api/assistant/tool-calls` 和助理面板。配对屏 403。

## 扩展点

加能力时停在这些入口，不要另开一套批准或第二套工具执行。

1. **新工具。** 同时改 `assistant.TOOLS`、`CAPABILITIES` 和 `TextPlan` 里的工具名字面量。名字集合必须相等。风险只能是现有四种。有副作用的工具只准备草稿或待审作业。
2. **新文字适配器。** 在 `text_providers.py` 实现 `complete()` 和 `deltas()`。`complete()` 保持一次 JSON。流式失败且还没有文本时才可以退回 `complete()`。不要把密钥写进仓库。
3. **新离线场景。** 代理循环加 `scenario_<名字>` 并放进 `agent_eval.run_all`。对话质量加 `ConversationCase`。检索加进 `retrieval_eval.run_all`。`scripts/tool_eval.py` 会跟着这三份名单走。不要把场景并进另一份 `run_all` 而让原来的顺序断言失效。
4. **上下文取舍。** 改 `fit_context` 的丢弃顺序。待批准草稿、选中事务、当前这句话和最近一次工具结果不要放进可丢列表。语音提示只应调用 `voice_context_note`，不要在配对会话上调用它。
5. **语音协议。** 新的供应商事件先映射成现有的 `transcript`、`tool`、`turn_complete`、`interrupted`。转写用 `apply_voice_event`。不要在协议对象里直接写数据库。

## 已知缺口（按价值）

这些是代码里还没做完的事，不是已经测得的产品效果。

1. **语音不跑有界多步循环。** 实时模型给出一次调用，`ToolDispatcher` 执行一次。读完再决定要不要草稿，发生在供应商那一侧，不受文字这边的 3 步和 45 秒约束。做法写在下面的设计里，本文件不实现它。
2. **字符预算没有罩住真正送出的提示。** 工具名单在预算之外。当前 `TOOLS` 的 JSON 大约 17000 字，长过默认的 12000 字预算。模型仍可能先看到名单，后看到被裁过的日历。
3. **流在第一段文字之后失败不会退回。** 退回只发生在还没有任何文本的时候。手机桥不是逐 token 回调，75 秒计时器也不会取消已经发出的原生请求。
4. **`memory_query` 的查询只看见最新 40 条。** 更早的活动事实可以出现在 `owner_search`、文字包和拥有者语音提示里，但不能出现在这条工具的查询结果里。
5. **语音提示不随这一句重排。** 记忆命中在会话开始时排好。新的一句要到下一通拥有者语音才变成排序查询。
6. **没有真实模型的任务成功率。** 离线表和假提供方不代替自然度、延迟或正确动作率。真实对话脚本有硬上限，而且不进入 CI。
7. **轮次是短文本。** 表里最多留 24 行，打包最多看 16 行，每行裁到 500 字。被打断的半句会留下。没有音频，也没有说话人分离。

## 接下来做什么

按上面的顺序做。每一项都应单独开分支，并继续走 `execute_tool()` 和现有草稿。

1. 按下面的设计实现拥有者语音的有界后续步骤。这一份只写设计和测试，不改调度代码。
2. 把工具名单算进预算，或按这一轮可能用到的名字缩短名单，使 12000 字的限制真的限制送出的提示。
3. 流在已经发出第一段之后失败时，给出不重复文字的收尾，而不是再拼一段 `delta`。
4. 让带查询的 `memory_query` 排序全部活动事实，再按原上限截断。
5. 只有在明确的花费上限下，才用 `scripts/conversation_eval.py` 跑一次真实提供方。不要把它放进 CI，也不要用那一次结果宣称商业收益。

不要做的事：任意 shell、浏览器或 GUI；绕过拥有者批准的新写入；合并 PR #4、#5、#15、#16；把离线场景写成真实准确率或减损效果。

## 语音走文字循环的设计（未实现）

这次不改 `ToolDispatcher` 或 `voice.py`。把 `AgentLoop.run` 直接放进 `ToolDispatcher._invoke` 或 `receive_provider` 不安全：那条线程在等实时套接字，`AgentLoop` 会再调文字提供方，可能计入 `DESK_TEXT_DAILY_CAP` 并发起付费请求；Qwen 的 `protocol.result` 在工具结果之后还会发 `response.create`，实时模型会自己续写下一步，和文字循环抢同一次草稿。Gemini 只回 `toolResponse`，两条协议不能用同一处补丁蒙混。

以后单独实现时遵守这些边界。

- 只有 `allow_memory` 为真的拥有者会话和本机语音工作进程进入后续循环。配对会话保持今天的 `ToolDispatcher`，不调用 `AgentLoop`。
- 实时模型给出的那一次调用仍由 `execute_tool()` 执行一次。语音幂等范围仍是会话 id 加 call id。文字循环里随后的步骤用新的 `voice-loop/` 前缀加会话 id 和步号，不能复用已经执行过的 call id，也不能把同一次读取再执行一遍。
- 后续步骤调用现有 `AgentLoop`，`max_steps` 用剩余步数，上限仍是 `MAX_STEPS`（3），`max_seconds` 用剩余时间，上限仍是 `MAX_SECONDS`（45）。结束条件用现在的 `_ends_turn`：草稿、取消、停止、读超时、`propose_plan` 失败，以及 `OWNER_SIGN_IN_REQUIRED` 和 `TOOL_NOT_ALLOWED` 都结束。`propose_plan` 成功不结束。`stop_physical_outputs` 即使本轮已结束也必须还能执行。
- 读工具没有结束本轮、并且文字提供方已配置时，不要再发 Qwen 的 `response.create`，也不要再发会让 Gemini 继续生成的用户内容。`AgentLoop` 的回复只作为客户端转写文本。上下文用 `pack_conversation` 加上这次的 `last_tool_result`，系统提示用现有的 `voice_instructions` 和 `voice_context_note`。
- 文字提供方未配置时，保持今天的路径：结果仍经 `protocol.result` 交回实时模型，现有的草稿套接字测试继续成立。
- 不新增工具，不给模型确认工具。草稿的 `saved` 仍是 false。

测试必须离线，用 `ScriptedProvider` 或假套接字，不访问网络。实现时按这些名字写，断言如下。

1. `test_owner_voice_read_then_stops_at_three_steps`：连续读取只执行 3 次。第 4 次不调用 `execute_tool`，审计里没有第 4 条成功行，回复的 `saved` 不是 true。
2. `test_owner_voice_draft_ends_the_turn`：合法的 `calendar_create_draft` 产生提案且 `saved` 为 false，日历表不加行。紧接着的 `memory_query` 不执行。`stop_physical_outputs` 仍然执行。
3. `test_owner_voice_time_bound_uses_injected_clock`：注入时钟从 0 跳到 46 秒后，第二个工具不开始。说明句与文字循环的超时句相同。
4. `test_paired_voice_does_not_enter_the_text_loop`：`allow_memory` 为 false 时 `ScriptedProvider.calls` 保持 0，上下文里没有拥有者记忆。
5. `test_realtime_response_create_is_not_sent_after_an_owner_read`：假的 Qwen 连接在拥有者读取之后不再发出 `response.create`。客户端看到的是循环给出的那句文本。没有真实 HTTP。
6. `test_unconfigured_text_keeps_the_current_voice_result_path`：文字提供方无效时，一次读取仍走 `protocol.result`，其中包含今天的 `response.create`。`test_realtime_transport_creates_only_a_draft_and_interrupt_cancels_it` 仍然通过。
7. `scenario_voice_same_policy` 保持不变：文字和语音对 `shell_exec` 的拒绝仍各写一行，结果都是 `TOOL_NOT_ALLOWED`，`saved` 为 false。
8. 第 4 次若是草稿，提案数不增加。已执行的第一次读取不会因为进入 `AgentLoop` 再执行一次。
