# Desk Companion · Group 2

本仓库是个人AI Agent的桌面软件基础，已包含日历、坐姿反馈与语音适配。开发名称暂为 **Desk Companion**，英文默认，可切换简体中文。旧 Senplate 项目与学校原件保留在上层目录，本工程不使用旧食品业务或品牌。

10月2–3日已接起原定S1–S10软件；10月6日继续补齐新增个人Agent的受限笔记作业与语音调度基础。功能、安装、验证与尚需外部条件的部分分别记录，不能把回放、模拟器或协议测试当成实机准确率。

**2026-10-09整合更新：**已实现持久作业、拥有者逐项批准、专用目录真实笔记保存／独立读回、取消／重启对账和非阻塞语音工具。默认关闭，不具备任意目录、第三方应用、浏览器或LCU控制；不能把此受限闭环当成通用Agent完成。[讨论与下一阶段方案](../planning/2026-10-06/personal-agent-discussion-and-next-steps.md)记录LCU候选、异步执行／授权／恢复、实体模块与验收；固定姿态闭环继续保留。

**2026-10-09角色更新：**加入可替换的全身女性二次元VRM角色、骨骼动作、眨眼、输出音量驱动开口、本地动作预览和纯黑／镜像出口。示范角色来自pixiv官方，非最终角色美术；Pi与物理显示效果待实测。详见[3D角色契约](docs/avatar.md)。

**2026-10-10美术状态：**用户同意A1方向后的[简明角色简报](../design/desk-companion/characters/a1-character-brief.md)、[表情／表演规则](../design/desk-companion/characters/a1-expression-rules.md)与[六表情E1](../design/desk-companion/characters/2026-10-10-expression-study/README.md)已完成。E1待图像反馈；原A1 V1–V4及B1／五提示词保持，许可样本与程序没有替换。新增[近期主流动画研究](../research/2026-10-10-avatar-art/mainstream-anime-c1-study.md)与独立[C1紫暮全身首稿](../design/desk-companion/characters/2026-10-10-c1-concept/README.md)供当时对照；A1／B1／E1保持，10月12日后续用户已选择A1，当前服装步骤见下段。

**2026-10-12已保存美术资料：**用户已确定A1，要求先保存服装再做全方位和细节。[九套原图包](../output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)已核对，原素材与提示词保留；[六个全身视角与四张细节](../design/desk-companion/characters/2026-10-12-a1-turnaround-details/README.md)完成并逐张查看，原V4服装只是统一工作参考。斜视角度偏浅、未见背部结构为新设计提案，具体默认服装仍待选。[视图规范](../design/desk-companion/characters/a1-turnaround-spec.md)与[A1九套总索引](../design/desk-companion/characters/a1-wardrobe-index.md)供后续；二维图不表示原创VRM／衣物绑定完成。

**2026-10-12软件盘点：**[17模块功能／完成与待办清单](../planning/2026-10-12/software-function-inventory.md)核对现有代码和历史验证。近期日志／角色成果已推送现有分支`e45afd2`，PR #4保持开放；软件基础已具备，真实电脑应用执行、完整记忆管理／作业归档、A1原创VRM与真实服务／目标机验收仍待。下表是已实现功能，不能仅据“已实现”推定真实设备效果。

**2026-10-12本机试用：**已启动独立测试工作区，[Web管理页](http://localhost:8832/)与[Linux常亮屏布局](http://localhost:8832/?surface=device)共用虚构数据。服务仅监听本机，使用`.runtime/user-preview-20261012`；原主工作区保持。已实际保存日程并核对两页显示、触摸管理／返回、桌面／窄屏；修复侧栏小月历最右列裁切。[本轮QA](../output/qa/2026-10-12-web-linux-preview/verification.md)记录证据。当前是Mac浏览器中的设备界面预览，Pi安装／触控／性能仍待；真实AI未配置，专用笔记须每项本人批准。

**2026-10-12当前页面角色：**用户最终要求换回2D、去掉分割感。[A1常驻层](docs/page-companion.md)使用一张完整睁眼原图，轻微整体反馈；不拆关节、不做深度／局部变形。滚轮／拖角／滑条连续缩放，左右／下边缘半身／露头／隐藏与召回、偏好保存、弹窗暂避和减少动态已实现。[本轮QA](../output/qa/2026-10-12-a1-page-companion/verification.md)记录28项前端测试、构建和实际浏览器检查。分块／2.5D／3D尝试已被否决，新3D运行资产已移除；旧许可VRM入口独立保留。

## 2026-10-12 个人 Agent 内核增量

本轮在独立 [PR #5](https://github.com/tantalum666/FYP/pull/5) 实施，叠加 PR #4，不自动合并或部署。上面美术／盘点段落是相应阶段记录；其中“记忆／指定应用／CI尚未开发”由本节取代。

- [可审阅个人上下文](docs/personal-context.md)：事实／偏好／决定的查看、更正与忘记；默认临时对话，可明确选择保存连续文字线程。保存、模型使用、私人展示是独立开关；模型不能自行批准记忆或动作
- [持续职责](docs/routines.md)：一次／每日／每周的本地日程简报与事务检查，持久调度、暂停／恢复／取消、重启合并补查和显式领取结果；无需模型轮询，本机服务须运行
- [独立应用执行器](docs/computer-jobs.md)：除专用笔记外，可在另一个回环测试应用真实创建记录并独立读回；审批绑定目标实例、适配器、版本和正文。它不是通用桌面／浏览器控制
- [提供商策略](docs/provider-policy.md)：精确官方端点、无自动重定向或环境代理；额外保存的记忆、历史和业务内容分别获同意，并绑定实际提供商目的地。隐藏／撤销后停止继续投影、丢弃迟到回答
- [可复现软件检查](docs/software-checks.md)：锁文件安装、资产hash、后端／前端／构建和 GitHub Actions；本轮真实浏览器、远端CI、实际语音及硬件证据分别记录，不能互相代替

当前英文和简体中文入口均在 Assistant。新私人写入的重试信息只放内存，不把对话／记忆正文持久化到浏览器重试缓存。内容删除不宣称法证擦除；部分无正文操作去重元数据仍无限期保留，限制详见个人上下文契约。

## 2026-10-12 持久工作与文件增量（整合验收中）

新增[持续工作任务](docs/agent-runs.md)与[选定来源／真实成果文件](docs/sources-and-artifacts.md)。在 Assistant → Work tasks 中选择本地来源和应用记录、明确保留工作，再查看计划、证据、问题、草稿审阅与结果文件。模型模式沿用已同意的文字提供商，文件另需本次传输同意；没有配置时只能做明确标注的确定性证据整理。

模型协调器可基于累计观察进行计划、分段／批量读取、提问、生成引用报告和申请本地事务／日历修改；批准后独立读回结果再继续。它不是普通聊天的自动升级，也不把文件写出或结构检查通过当作广泛目标已经完成。当前不接任意搜索、外部消息、通用桌面、并行子代理或自动硬件动作。

另有默认关闭的 [Browser workflow 实验入口](docs/browser-workflow.md)：固定官方公开资料 → 审阅公开／虚构笔记 → StackEdit 实际编辑／导出适配器。10月12日初版与模型工具分开；10月13日已接入有界模型工具链，真实目标机验收尚待。请求过滤不是系统网络沙箱，不得导入私人文档、账号、记忆或日历。代码与本地定向测试不等于真实浏览器已通过；远端提交与完整检查以当轮 QA 为准。

## 当前功能

| 模块 | 已实现的行为 |
|---|---|
| 电脑作业 | 专用目录UTF-8笔记和独立回环测试应用记录／再次核验；精确意图、实例及事务版本审批、持久队列／历史、取消／未知结果只读对账；模型无批准工具 |
| 个人上下文 | 拥有者可审阅／更正／忘记事实；临时或明确保存的文字线程；提供商目的地同意、隐私与迟到结果隔离 |
| 持续职责 | 一次／每日／每周本地简报和事务检查；持久调度、暂停／恢复／取消、结果历史与显式领取 |
| 日历 | 日／周／月、批量日期、公历重复与单次例外、编辑／删除／完成、冲突、提前提醒／延后、记录与CSV |
| 主动事务 | 状态／截止／下一步／步骤、持久进展与来源、一次待处理检查、暂停／延后／完成／恢复；Tasks、Today和常亮入口 |
| 常亮设备屏 | 独立大时钟／日期／月历／近期安排，日／夜／自动外观，触摸展开，60秒闲置返回，编辑保护；可切角色场景 |
| 坐姿 | 本地关键点采集适配、三步个人标定、可见性门槛、前倾／侧歪的持续判断、具体提示、复测、离桌／活动提醒、暂停／冷却／延后 |
| 配对 | 单次短码、拥有者核对批准、可撤销终端身份、常驻屏长期会话；iPhone令牌留在Keychain |
| 助理 | 事务／日历查询、进展草稿、简报、确认／取消／过期、版本冲突；可选Qwen／Gemini文字模型，默认本地规则；模型只获得受限工具，停止输出可立即请求，其他动作先审阅 |
| 语音 | Qwen Audio和Gemini Live适配、流式PCM、打断取消、时限、用量记录；本地中英唤醒工作进程；默认没有配置供应商 |
| 反馈 | 完整2D A1常驻伙伴、连续缩放／拖动／贴边收起与整体回应；原全身3D VRM角色、状态动作／眨眼、浏览器实际播放驱动开口、本地预览、独立黑底／镜像出口；灯光／机械臂命名预设、去重／过期／停机／驱动回执；模拟与实物分开 |
| 日历辅助 | 选择地区后读取香港天气、缓存和过期状态、农历显示、香港2025–2027公众假期、日期占用摘要、安静时段与本地简报 |
| 数据交换 | ICS预览／去重／导入／导出；只读忙闲或可展示标题分享／撤销；业务备份与保留现有数据的合并恢复 |
| 外部日历 | Google主要日历的只读连接、刷新和预览应用；不写回Google、不自动删除本地副本。Outlook／Apple日历可通过ICS文件交换 |
| iPhone | Capacitor原生工程、Keychain配对、原生导出、WidgetKit小组件、系统快捷入口、可选择启用的缓存本地通知 |
| Linux | 同源生产服务、kiosk启动、用户级systemd文件生成／安装、诊断、可独立启动的相机／唤醒／输出工作进程 |

文字离线入口是明确标注的日期规则，例如 `Tomorrow 15:00–16:00 Project discussion` 或 `明天15:00到16:00 项目讨论`。缺少结束时间时会要求补充，不冒充语言模型。主动事务可使用 `Track: finish the report`／`跟进：完成报告`或表单；已有事务的讨论会保留进展。可选文字AI与语音独立配置，详见[事务契约](docs/task-tracking.md)。自然交谈需要配置语音服务并完成实际试听。

## 先运行软件

需要Node 22.12+、Python 3.12+、SQLite 3.38+（Python sqlite3 所链接版本）和uv。首次安装：

```sh
cd desk-companion  # 从克隆后的 FYP 仓库根目录开始
uv sync --frozen
cd frontend
npm ci
npm run build
cd ..
./scripts/dev.sh
```

开发脚本运行8831后端与5190前端，Ctrl+C只停止该脚本启动的进程；端口占用时不会结束其他程序。

- [电脑／手机管理界面](http://127.0.0.1:5190/)
- [独立常亮屏](http://127.0.0.1:5190/?surface=device)
- [独立角色输出](http://127.0.0.1:5190/?surface=avatar)；纯黑无界面用`&clean=1`，反射像再加`&mirror=1`

构建前端后，也可以只运行同源服务，不依赖Vite：

```sh
.venv/bin/uvicorn desk.app:create_app --factory --app-dir backend --host 127.0.0.1 --port 8831 --workers 1 --no-access-log
```

此时在`http://127.0.0.1:8831/`打开同样的界面。**必须保持单个API工作进程**：姿态、输出停机和语音会话在该进程中协调。

账号是`owner`。首次运行随机生成密码，保存在[本机凭据](.runtime/credentials.json)，权限0600。数据库、配对令牌、配置密钥与姿态／唤醒模型在`.runtime/`，不进入版本控制。不要删除整个目录来重置页面。真实手机访问需要可到达的HTTPS地址；手机自身的`127.0.0.1`不是桌面主机。

## 操作入口

- **页面A1**：拖动换位置、靠边收起，滚轮或拖角连续缩放；右键／省略号控制，双击打开助理。
- **Assistant → Personal context / Routines**：管理记忆、保留会话与模型上下文同意；设置本地持续职责并查看结果。
- **Assistant → Work tasks / Browser workflow**：持续工作、源文件／成果检查与公开浏览器实验；各自限制见上节。Work tasks → Find saved work 可按名称、当前目标、ID及关联来源名称检索本地记录，并明确选择确切记录。
- **Assistant → Computer jobs**：拥有者核对全文及目标后批准笔记或独立测试应用记录；默认关闭，按[隔离试运行](docs/computer-jobs.md)启用。
- **Assistant → Open 3D companion**：全身角色、双语、本地预览、模型替换和黑底镜像；自然语音仍需单独配置。
- **Tasks**：创建事务、记录进展、查看／暂停跟进、安排日历时段、确认完成或恢复。
- **Today／Calendar**：查看与编辑日程；右上角助理可查询、生成草稿并确认。
- **Device → Posture & feedback**：允许观察、个人标定、提示时间、暂停及复测状态。
- **Device → Pairing & outputs**：生成配对码、核对两端号码、批准／撤销；查看输出回执和停机状态。
- **Device → Calendar & companion**：天气、双历、假期、提醒／安静时段、唤醒进程开关与常亮画面。
- **Device → Import & share**：文件、Google只读连接、分享和备份。
- **Records**：按类别、来源和日期筛选，导出CSV；回放会单独标记。
- **iPhone → Device → On this iPhone**：用户主动启用通知、刷新小组件摘要。没有自动授予系统权限。

[完整操作与安装说明](docs/operator-guide.md)包括Pi、iPhone、语音配置、模型、相机和输出控制。[架构与限制](docs/architecture.md)说明数据及权限边界。[评价流程](docs/evaluation.md)用于以后获同意的真人测试。

## 2026-10-13 个人Agent续作

模型规划可经[持久工具链](docs/agent-runs.md)调用限定公开浏览器与[精确审阅MCP连接器](docs/application-connectors.md)，观察结果进入后续规划；[选定个人上下文](docs/agent-personal-context.md)与来源证据、工具权限分开。普通聊天可显式移交目标，隐藏私人内容仍保留元数据停止控制。提供商和连接器默认不配置，没有因本轮代码而自动获得外部账号、真实模型或桌面权限。

[持续计划](../planning/2026-10-13/continuous-agent-capability-plan.md)及[整合验证](../output/qa/2026-10-13-agent-continuation/verification.md)区分软件、协议、真实界面与远端发布；该检查点不是整体开发结束或商业产品等同。

## 2026-10-13 已保存工作检索

[检索契约](docs/work-search.md)新增拥有者专用的本地元数据查询。支持中英及Unicode规范化、相关性排序、快照绑定的前后分页，分别显示工作／来源／成果和确切ID。只搜索名称、当前目标及关联来源名称，不读取文件正文或调用模型；搜索结果是上次记录状态，打开详情／预览／下载另行核验实际字节。旧成果关联的是当前目标，不伪造原始目标；未知关系保持未知。

查询只在明确提交时运行，不写浏览器缓存、URL或数据库索引。隐藏／退出／断线／过期响应受身份与隐私围栏约束，选择不会自动开始或授予模型／工具权限。本地完整软件验证与真实界面验收分开记录于[检索QA](../output/qa/2026-10-13-work-search/verification.md)。

## 验证与交付边界

本轮角色验证见[3D角色QA](../output/qa/2026-10-09-3d-avatar/verification.md)；整合基线149项后端、15项前端及实际浏览器证据见[本地整合核验](../output/qa/2026-10-09-dot-integration/verification.md)；[10月6日云端软件核验](../output/qa/software-completion-2026-10-06/verification.md)保留当时结果。启用与复现实验见[电脑作业操作](docs/computer-jobs.md)。旧阶段证据在[事务增强与UI／UX审查](../output/qa/task-enhancement-ux-2026-10-03/verification.md)：101项后端、11项前端检查、生产／iPhone构建及实际三端交互。此前[S1–S10记录](../output/qa/software-completion-2026-10-02/verification.md)保留。测试数据库与主数据分开，10月9日交互使用独立`.runtime/dot-integration-qa/`；旧轮使用`.runtime/completion-qa/`。截图中的安排和回放是演示数据。正式主库原有示例保留，不自动移动到今天。

已经执行本地业务／API／协议测试、模型运行冒烟检查、浏览器交互，以及iPhone模拟器构建安装。仍需在取得条件后验证：真实摄像头视角和人工标签、实际唤醒／回声／自然语音、Pi并行性能、机械角度／电源／物理停机、显示光学、Google本人授权及Apple真机签名。没有调用付费语音API或采集真人音视频，也没有提交学校文件。

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
frontend/src/workspace/ 姿态、助理、连接、数据交换与角色入口
frontend/src/companion/ 完整2D A1常驻层、连续缩放和位置／显示偏好
frontend/src/avatar/    按需加载的3D场景、模型校验与播放音量桥
frontend/ios/           iPhone、WidgetKit、App Intents与Keychain桥
scripts/                安装、诊断、模型校验、回放、标注和评价
config/                 未启用的设备／服务示例配置
.runtime/               本机私有运行数据、模型和构建缓存
```

依赖与来源见[THIRD_PARTY.md](THIRD_PARTY.md)。框架与角色源稿可替换；常驻A1为AI辅助二维原稿，独立3D入口仍为pixiv官方授权示范VRM，许可与嵌入设置单独保留；不是本组原创美术、Razer角色或已定稿品牌。
