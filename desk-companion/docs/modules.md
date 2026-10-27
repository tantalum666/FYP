# 模块、数据流与扩展点

2026-10-27，Group 2。本文对照 `desk-companion/` 里已经在 `main` 上的代码。未合并的 PR #4／#5／#15／#16，以及本地尚未提交的 AliceChan／统一 Omni 工作区，都不在这里。更早的边界叙述仍在[架构说明](architecture.md)。

## 模块

一个 FastAPI 进程（`desk.app:create_app`）和一份 SQLite（`desk/store.py`）。姿态时间窗、输出停机和语音会话都在这个进程的内存里，所以 API 只使用一个 worker。

| 代码 | 当前职责 |
| --- | --- |
| `app.py` | 装配路由、拥有者 Cookie、配对和本机工作进程身份；启动四个后台循环 |
| `calendar.py`、`exchange.py`、`google_calendar.py` | 本地日历、ICS、Google 只读预览 |
| `tasks.py` | 事务、进展和跟进；安静推迟记在 `task_quiet_holds` |
| `workspace_data.py` | 偏好、`is_quiet`／`quiet_until`、天气和屏内提示音 |
| `memory.py`、`context.py` | 拥有者事实；`pack_conversation` 组装一次发给模型的内容 |
| `persona.py` | 一份正文。文字、语音和跟进再附加各自写在代码里的协议 |
| `text_providers.py`、`text_ai.py` | Qwen／Gemini 文字适配器和草稿循环 |
| `voice.py` | Qwen Audio／Gemini Live 的报文和会话时限 |
| `assistant.py` | 按工具名执行。确认不在工具表里 |
| `tool_dispatch.py` | 语音工具的队列、取消和停止槽 |
| `jobs.py`、`computer.py` | 同一条作业队列；笔记目录和一个拥有者指定文件夹 |
| `posture.py`、`posture_service.py`、`outputs.py`、`agents/` | 姿态判断、命名输出，以及相机／唤醒／输出进程 |
| `frontend/src` | 管理界面。`device/` 是常亮屏。`workspace/jobTypes.ts` 是作业恢复文案 |

## 数据流

浏览器、常亮屏和 iPhone 调用同一个 API，布局分开。日历和事务写入 SQLite。

可选文字模型只在 `TextConfig.valid()` 通过时，由 `TextAssistant.generate` 调用 `text_providers.ADAPTERS` 里的适配器。语音由 `VoiceService.run` 按配置选择协议；工具事件进入 `ToolDispatcher`，再进入 `AssistantService.tool`。会改日历、事务、记忆或文件的工具只准备草稿，或调用 `jobs.prepare`。`stop_physical_outputs` 是例外，它直接请求软件停止。拥有者用另外的确认或批准路由提交。笔记和文件夹文件由 `computer_jobs` 循环执行，写完后独立读回。姿态判断不调用模型。

`create_app` 里的四个循环是：`rules` 每 1 秒（包含 `tasks.tick` 和作业到期）、`public_data` 每 10 秒、`task_advice` 每 30 秒、`computer_jobs` 每 0.5 秒。

`pack_conversation` 放入活动记忆、最多 30 条事务、选中事务，以及从当前时刻起 7 日内最多 80 条日历发生项。密钥、相机帧和文件夹路径不是这个包的字段。

## 扩展点

**文字供应商。** 新适配器提供 `complete(client, config, prompt, content)`，用 `name` 登记到 `text_providers.ADAPTERS`。`TextConfig.valid()` 还要接受这个供应商和它的端点。调用方仍走 `TextAssistant.generate`。未登记的 provider 抛出 `TEXT_AI_NOT_CONFIGURED`。

**语音供应商。** 没有文字那份注册表。`VoiceConfig.valid()` 只接受 `qwen_audio` 和 `gemini`。`VoiceService.run` 选择 `GeminiProtocol` 或 `QwenAudioProtocol`，并使用不同的 header 和 endpoint。再加一家要改这些位置，只改 `ADAPTERS` 不会接到语音。

**工具。** 模型能看见的名字在 `assistant.TOOLS`。`AssistantService.tool` 按名字执行。文字模型若要调用它，`TextPlan.tool` 的字面量也要包含这个名字。没有确认工具。`stop_physical_outputs` 直接请求软件停止，不先做草稿。`allow_memory` 为假时，以 `memory_` 开头的工具被拒绝。

**作业。** 仍用 `JobService` 这一条队列。`JobInput` 只接受 `save_note`、`verify_note`、`save_folder_file`、`verify_folder_file`。笔记还要 `DESK_COMPUTER_ENABLED=1`，目录固定为运行目录下的 `computer-notes/`。文件夹不看这个开关；路径来自拥有者已经保存的一条目录记录，`JobInput` 没有 path 字段。`prepare` 写下 executor 和 scope。`_bindings` 在批准和执行时按同样的两组动作选择执行器。两个执行器都只新建 `<作业ID>.txt`，不覆盖已有文件。增加动作时要同时改字面量、动作集合、`prepare` 和 `_bindings`，并实现执行器的 `execute`／`verify`。不要再开一条队列。

## 安全不变量

下面是代码里的现限制，不是提案里的目标。

- **拥有者批准。** 登录会话 8 小时。作业批准、人格、记忆写入和文件夹命名要求拥有者 Cookie。模型不能调用确认接口。助理草稿和待批准作业 5 分钟过期。批准后再有 60 秒执行期限，并核对版本与 `intent_hash`。
- **上限。** 活动记忆最多 200 条，发给模型最多 40 条，每条最多 500 字。人格正文最多 4000 字。作业最多 1000 条，待审加排队最多 20 条，列表最多 200 条。一次 `tasks.tick` 最多新建 3 条跟进。文字后台建议默认关闭；只有配置有效且 `DESK_TEXT_BACKGROUND=1` 时才会调用，每个 UTC 日最多 20 条 `purpose='followup'` 用量记录，失败也计入。一次文字请求最多 3 轮。语音会话在 600 秒或 45 秒无活动后结束，不自动重连。语音工具有 2 个并发槽，普通调用最多 8 个未完成，调用表为 32 再加一个可回收的停止槽，结果队列 64。
- **安静时段。** 默认 22:00–07:00，使用工作空间时区，可以关闭。安静期内 `tasks.tick` 把到期检查推到 `quiet_until`，并写入 `task_quiet_holds`。开始和结束相同的时候，推到下一个本地午夜。`enrich_one` 在安静期内直接返回。跟进关闭的事务离开到期队列；已经排队的文字建议在 `follow_up_enabled` 为假时标成 skipped，不发给模型。屏内提醒保留。桌面提示音在安静期内不播放。
- **结果。** 写入后的核验失败，或进程在运行中重启，作业变为 `unknown`，不会自动再写一次。取消不删除已经写成的文件。作业成功不把关联事务标成完成。姿态结果不解释成健康或情绪诊断。

还没有通用 GUI／shell、作业归档，也没有把记忆、人格和作业放进业务 JSON 备份。RIG 驱动没有接入。提供商没有锁定，默认不调用付费模型。
