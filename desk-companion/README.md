# Desk Companion - Group 2

6 November 2026. The shared Alice app now includes persistent Work, passwordless
local entry, existing office executors and general public-browser preparation.
The owner selected general browser capability first, without fixed merchants.
[Current handoff](../handoff.md), [product](../product.md),
[browser contract](docs/computer-use.md), [current QA](../output/qa/2026-11-06-openai-agent-merge/verification.md).

OpenAI is the default: Realtime2.1 for realtime conversation, GPT6.1Sol Responses
for independent text/Work and computer calls. Mac configuration is ready. Pi runs
the new release but its current OpenAI access returns an unsupported-region error;
the UI states that limitation rather than silently using Qwen. The local Alice
wake model loads on Pi; this is not proof of successful human wake/voice use.

PR93 merged the seven previously open PRs. The browser milestone is in independent
[PR94](https://github.com/tantalum666/FYP/pull/94). Local checks and actual browser
rehearsals are separate from paid-model planning or real purchase/ticket results.
No CI and no new paid inference. Pi software continues; only the red-LED
investigation is deferred. Keep private runtime data and original school files.

AliceChan remains the attributed CC BY-SA4.0 character.
[Character source](../design/desk-companion/characters/2026-10-22-alice/README.md).

## 当前功能

| 模块 | 已实现的行为 |
|---|---|
| 电脑作业 | 新增受限Linux编辑器→浏览器及双应用／SHA读回；专用笔记目录，或拥有者指定的一个真实文件夹；新建 UTF-8 文件／再次核验、意图及事务版本审批、同一持久队列、取消／未知结果读回；模型无批准工具，也不能提交路径 |
| 记忆 | 拥有者在「我了解的关于你的事」里更正、忘掉、设到期，并查看「为什么提醒我」。相同文字、填充词、同一姓名或同一偏好主题经既有草稿确认后停用。未删除事实进入业务备份。见[记忆契约](docs/memory.md) |
| 人格 | 拥有者编辑一段文字，文字助理和语音共用；程序仍附加工具规则。模型不能改这段文字 |
| 日历 | 日／周／月、批量日期、公历重复与单次例外、编辑／删除／完成、冲突、提前提醒／延后、记录与CSV |
| 主动事务 | 状态／截止／下一步／步骤、持久进展与来源、一次待处理检查、暂停／延后／完成／恢复；跟进写明触发原因；早晨简报与可选晚间检查沿用安静时段。Tasks、Today和常亮入口 |
| 常亮设备屏 | 独立大时钟／日期／月历／近期安排，日／夜／自动外观，触摸展开，60秒闲置返回，编辑保护；可切角色场景 |
| 坐姿 | 本地关键点采集适配、三步个人标定、可见性门槛、前倾／侧歪的持续判断、具体提示、复测、离桌／活动提醒、暂停／冷却／延后 |
| 配对 | 单次短码、拥有者核对批准、可撤销终端身份、常驻屏长期会话；iPhone令牌留在Keychain |
| 助理权限 | 默认Ask first；输入框旁／Settings可选Full access，独立服务验证新拥有者请求、撤回与版本；不扩大实体／媒体／账号／执行器范围。见[权限契约](docs/assistant-permissions.md) |
| 助理 | Omni 配置下文字／语音同一模型、上下文和记忆；未配置时明确本地规则。事务／日历／记忆草稿、确认／取消／过期、版本冲突与独立读回；模型不能确认，软件停止可直接请求 |
| Voice | OpenAI Realtime2.1 by default; Qwen Audio/Omni and Gemini adapters retained. Shared tool/permission state, explicit media sharing and local Alice wake. Human acoustics and live browser autonomy remain separate acceptance steps. |
| 反馈 | AliceChan（CC BY-SA4.0）的原生VRM／MToon／表情与发骨、注意／短回应、常驻拖动／缩放／贴边收起、完整2D回退和黑底／镜像；新成品本地VRM预览／缓存恢复已实现；原生v1已否决，AliceChan已作为当前常驻。灯光／机械臂命名预设及回执与模拟／实物分开 |
| 日历辅助 | 选择地区后读取香港天气、缓存和过期状态、农历显示、香港2025–2027公众假期、日期占用摘要、安静时段与本地简报 |
| 数据交换 | ICS预览／去重／导入／导出；只读忙闲或可展示标题分享／撤销；业务备份与保留现有数据的合并恢复 |
| 外部日历 | Google主要日历的只读连接、刷新和预览应用；不写回Google、不自动删除本地副本。Outlook／Apple日历可通过ICS文件交换 |
| iPhone | 全屏Alice、Plan／More和共享业务／草稿保护；Capacitor工程、Keychain、导出、Widget／快捷入口及可选缓存通知。模拟器视觉已验，完整原生触控仍待 |
| Linux | Pi5离线启动镜像／首次设置窗口、受限双应用；同源生产服务、kiosk启动、用户级systemd文件生成／安装、诊断、可独立启动的相机／唤醒／输出工作进程 |

文字离线入口是明确标注的日期规则，例如 `Tomorrow 15:00–16:00 Project discussion` 或 `明天15:00到16:00 项目讨论`。缺少结束时间时会要求补充，不冒充语言模型。主动事务可使用 `Track: finish the report`／`跟进：完成报告`或表单；已有事务的讨论会保留进展。Omni 配置下输入框和语音共用同一模型；独立文字适配器用于未配置Omni时的显式HTTP文字入口及后台建议，见[事务契约](docs/task-tracking.md)。真人语音自然度仍需实际试听。

## 先运行软件

OpenAI is selected by default; without a valid key it remains unavailable. Explicit owner requests start model use. Historical Qwen results remain comparison evidence, not the runtime default. All agent-paid trial budgets remain closed.

需要Node 22.12+、Python 3.12+、uv。首次安装：

```sh
cd desk-companion  # 从克隆后的 FYP 仓库根目录开始
uv sync --frozen
cd frontend
npm ci
npm run build
cd ..
./scripts/dev.sh
```

开发脚本运行8831后端与5190前端，Ctrl+C只停止该脚本启动的进程；端口占用时不会结束其他程序。端口检查使用已经装好的 `.venv/bin/python`，所以依赖安装完成后，即使新的 shell 没有把 `uv` 放进 PATH，也可以运行这个脚本。

Trusted direct loopback sessions connect automatically with `DESK_AUTO_OWNER=1` (default). The app no longer shows Sign in forms. Remote/paired authority still needs its existing trusted transport; restoring a session does not retry writes.

- [电脑／手机管理界面](http://127.0.0.1:5190/)
- [独立常亮屏](http://127.0.0.1:5190/?surface=device)
- [已否决A1 v1归档](http://127.0.0.1:5190/?surface=a1-history&lang=zh)，停止精修，完整源保留
- [现成角色／本地VRM预览](http://127.0.0.1:5190/?surface=models)；独立黑底镜像为`?surface=avatar&clean=1&mirror=1`
- [已否决头部历史](http://127.0.0.1:5190/?surface=head-history&lang=zh)；源与失败证据保留，不再继续制作

构建前端后，也可以只运行同源服务，不依赖Vite：

```sh
.venv/bin/uvicorn desk.app:create_app --factory --app-dir backend --host 127.0.0.1 --port 8831 --workers 1 --no-access-log
```

此时在`http://127.0.0.1:8831/`打开同样的界面。**必须保持单个API工作进程**：姿态、输出停机和语音会话在该进程中协调。

Private data, pairing tokens and credentials stay in `.runtime/` and out of Git. Preserve this directory. The old password API is retained only for compatibility/recovery; it is not the normal app entry. A physical phone needs reachable trusted HTTPS; its own `127.0.0.1` is not the desk.

## OpenAI and browser configuration

Install the locked audio/browser extras with `uv sync --frozen --extra audio --extra browser`.
Use an existing private FYP key file; do not put credentials in frontend variables.
`scripts/configure_openai.py` can update the selected Linux runtime's `service.env`
without calling a model or starting a service. The generated systemd unit reads
that file. A manual `dev.sh` session instead needs the selected settings in its
environment, including `DESK_OPENAI_CREDENTIAL_FILE`, `DESK_COMPUTER_USE_ENABLED=1`
and the installed `DESK_BROWSER_EXECUTABLE`. It does not automatically load
`service.env`. See [browser setup and scope](docs/computer-use.md).

## 操作入口

- **Assistant 对话卡片**：默认Allow once／Not now；输入框旁或Settings可显式保存Full access，让受支持的新软件请求按策略执行。**More → File activity**保留历史、手动草稿及目录设置。专用笔记默认关闭；指定文件夹要先填写一个运行目录之外的真实路径。见[隔离试运行](docs/computer-jobs.md)。
- **Assistant → Start conversation**：启用Omni后可自然交谈；拥有者可主动分享图片或所选屏幕，停止分享／结束对话释放采集。见[语音与图像契约](docs/qwen-omni.md)。
- **Tasks**：创建事务、记录进展、查看／暂停跟进、安排日历时段、确认完成或恢复。
- **Today／Calendar**：查看与编辑日程；右上角助理可查询、生成草稿并确认。
- **Device → Posture & feedback**：允许观察、个人标定、提示时间、暂停及复测状态。
- **Device → Pairing & outputs**：生成配对码、核对两端号码、批准／撤销；查看输出回执和停机状态。
- **Device → Calendar & companion**：天气、双历、假期、提醒／安静时段、唤醒进程开关与常亮画面。
- **Device → Import & share**：文件、Google只读连接、分享和备份。
- **Records**：按类别、来源和日期筛选，导出CSV；回放会单独标记。
- **iPhone → Device → On this iPhone**：用户主动启用通知、刷新小组件摘要。没有自动授予系统权限。

[完整操作与安装说明](docs/operator-guide.md)包括Pi、iPhone、语音配置、模型、相机和输出控制。[架构与限制](docs/architecture.md)说明数据及权限边界。[模块与扩展点](docs/modules.md)对照当前代码列出供应商、工具和作业的接入位置。[评价流程](docs/evaluation.md)用于以后获同意的真人测试。

## 验证与交付边界

已合入main的10月15日[审查与合并QA](../output/qa/2026-10-15-grok-review-merge/verification.md)为182项后端、17项前端，Ruff／类型／构建和npm审计零发现，含记忆／人格／目录的真实浏览器检查。历史149项后端、15项前端及实际浏览器证据见[本地整合核验](../output/qa/2026-10-09-dot-integration/verification.md)；[10月6日云端软件核验](../output/qa/software-completion-2026-10-06/verification.md)保留当时结果。启用与复现实验见[电脑作业操作](docs/computer-jobs.md)。旧阶段证据在[事务增强与UI／UX审查](../output/qa/task-enhancement-ux-2026-10-03/verification.md)：101项后端、11项前端检查、生产／iPhone构建及实际三端交互。此前[S1–S10记录](../output/qa/software-completion-2026-10-02/verification.md)保留。测试数据库与主数据分开，10月9日交互使用独立`.runtime/dot-integration-qa/`；旧轮使用`.runtime/completion-qa/`。截图中的安排和回放是演示数据。正式主库原有示例保留，不自动移动到今天。

10月16–17日Omni QA (local historical material: `output/qa/2026-10-16-qwen-omni-integration/verification.md`; not included in this checkpoint)新增215项后端、21项前端、Ruff／类型／构建与桌面／窄屏合成媒体交互。两次真实API虚构日历回复、一次生成图片问答通过；Mac音频收包3.176秒／2.619秒不是浏览器播放或Pi的5秒验收。预算预留4.1元，已返回usage保守估算0.106608元，均非完整账单。

已经执行本地业务／API／协议测试、模型运行冒烟检查、浏览器交互，以及iPhone模拟器构建安装。仍需在取得条件后验证：真实摄像头视角和人工标签、实际唤醒／回声／自然语音、Pi并行性能、机械角度／电源／物理停机、显示光学、Google本人授权及Apple真机签名。Omni已调用付费API做受限合成短测，该次没有采集真人音视频或提交学校文件；10月26日已实际运行Pi并通过网页／桌面入口验证。

```sh
uv run --no-sync pytest -q
uv run --no-sync ruff check backend scripts tests
cd frontend
npm run build
npm test
```

模型可选依赖用`uv sync --frozen --extra vision --extra audio`安装；普通`uv sync`可能移除未指定的可选包。检查时使用`--no-sync`保留当前安装。

## 代码结构

```text
backend/desk/            日历、持久化、配对、姿态、助理、语音、交换与API
backend/desk/agents/     明确启动的相机、唤醒／声音、命名输出工作进程
frontend/src/           手机／网页管理界面与共享业务组件
frontend/src/device/    独立常亮屏与触摸面板
frontend/src/workspace/ 姿态、助理、连接、数据交换与角色
frontend/ios/           iPhone、WidgetKit、App Intents与Keychain桥
scripts/                安装、诊断、模型校验、回放、标注和评价
config/                 未启用的设备／服务示例配置
.runtime/               本机私有运行数据、模型和构建缓存
```

依赖与来源见[THIRD_PARTY.md](THIRD_PARTY.md)。当前默认AliceChan来自yuna0x0／edisonlee55，CC BY-SA4.0；Shino／Victoria旧版CC0样本作为可选基线保留；旧pixiv许可全身改作、自制Anna头部和原生ImageGen完整2D各自保留来源与否决／回退状态，不混称全部学生原创、Razer角色或已定稿品牌。

## OpenAI实时语音评测（2026-10-29）

[评测工具与费用保护](docs/openai-voice-evaluation.md)在隔离虚构数据上实际测试了gpt-realtime-2.1和gpt-live-1＋gpt-6-luna，另测Mini英文参照。16次会话／11次最终控制条件检查，总保守usage估算USD0.3035168833。当前轮账本已关闭，不允许继续预留费用。504后端／15专项检查通过；[JSON、CSV及录音](../output/qa/2026-10-29-openai-realtime/verification.md)区分实际结果、初次失败和真人未验项。正常App提供商选择没有新增OpenAI；该脚本不是生产实时音频适配器。

## Bounded application workspace (30 October 2026)

The optional application executor now supports scoped Chromium source reads, real Calc workbook edits/formulas, Writer documents/PDF export and versioned local text artifacts. It reuses the existing task/job/permission services. [Setup and boundaries](docs/application-execution.md) / [actual execution QA](../output/qa/2026-10-30-application-execution/verification.md). The complex scenario passed a scripted execution/recovery run with 524 backend and 89 frontend checks; autonomous voice completion and production OpenAI integration remain open. No CI or new model spending.
