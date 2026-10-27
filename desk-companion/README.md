# Desk Companion · Group 2

本仓库是个人AI Agent的桌面软件基础，已包含日历、坐姿反馈与语音适配。开发名称暂为 **Desk Companion**，英文默认，可切换简体中文。旧 Senplate 项目与学校原件保留在上层目录，本工程不使用旧食品业务或品牌。

10月2–3日已接起原定S1–S10软件；10月6日继续补齐新增个人Agent的受限笔记作业与语音调度基础。功能、安装、验证与尚需外部条件的部分分别记录，不能把回放、模拟器或协议测试当成实机准确率。

**2026-10-09整合更新：**已实现持久作业、拥有者逐项批准、专用目录真实笔记保存／独立读回、取消／重启对账和非阻塞语音工具。默认关闭，不具备任意目录、第三方应用、浏览器或LCU控制；不能把此受限闭环当成通用Agent完成。[讨论与下一阶段方案](../planning/2026-10-06/personal-agent-discussion-and-next-steps.md)记录LCU候选、异步执行／授权／恢复、实体模块与验收；固定姿态闭环继续保留。

## 当前功能

| 模块 | 已实现的行为 |
|---|---|
| 电脑作业 | 专用笔记目录，或拥有者指定的一个真实文件夹；新建 UTF-8 文件／再次核验、意图及事务版本审批、同一持久队列、取消／未知结果读回；模型无批准工具，也不能提交路径 |
| 记忆 | 拥有者保存／更正／删除事实；模型只能读活动事实并准备草稿；删除后不再进入模型上下文；配对屏不可读。见[记忆契约](docs/memory.md) |
| 人格 | 拥有者编辑一段文字，文字助理和语音共用；程序仍附加工具规则。模型不能改这段文字 |
| 日历 | 日／周／月、批量日期、公历重复与单次例外、编辑／删除／完成、冲突、提前提醒／延后、记录与CSV |
| 主动事务 | 状态／截止／下一步／步骤、持久进展与来源、一次待处理检查、暂停／延后／完成／恢复；Tasks、Today和常亮入口 |
| 常亮设备屏 | 独立大时钟／日期／月历／近期安排，日／夜／自动外观，触摸展开，60秒闲置返回，编辑保护；可切角色场景 |
| 坐姿 | 本地关键点采集适配、三步个人标定、可见性门槛、前倾／侧歪的持续判断、具体提示、复测、离桌／活动提醒、暂停／冷却／延后 |
| 配对 | 单次短码、拥有者核对批准、可撤销终端身份、常驻屏长期会话；iPhone令牌留在Keychain |
| 助理 | 事务／日历查询、进展草稿、简报、确认／取消／过期、版本冲突；可选Qwen／Gemini文字模型，默认本地规则；模型只获得受限工具，停止输出可立即请求，其他动作先审阅 |
| 语音 | Qwen Audio和Gemini Live适配、流式PCM、打断取消、时限、用量记录；本地中英唤醒工作进程；默认没有配置供应商 |
| 反馈 | 角色状态、独立黑底／镜像出口；灯光／机械臂命名预设、去重／过期／停机／驱动回执；模拟与实物分开 |
| 日历辅助 | 选择地区后读取香港天气、缓存和过期状态、农历显示、香港2025–2027公众假期、日期占用摘要、安静时段与本地简报 |
| 数据交换 | ICS预览／去重／导入／导出；只读忙闲或可展示标题分享／撤销；业务备份与保留现有数据的合并恢复 |
| 外部日历 | Google主要日历的只读连接、刷新和预览应用；不写回Google、不自动删除本地副本。Outlook／Apple日历可通过ICS文件交换 |
| iPhone | Capacitor原生工程、Keychain配对、原生导出、WidgetKit小组件、系统快捷入口、可选择启用的缓存本地通知 |
| Linux | 同源生产服务、kiosk启动、用户级systemd文件生成／安装、诊断、可独立启动的相机／唤醒／输出工作进程 |

文字离线入口是明确标注的日期规则，例如 `Tomorrow 15:00–16:00 Project discussion` 或 `明天15:00到16:00 项目讨论`。缺少结束时间时会要求补充，不冒充语言模型。主动事务可使用 `Track: finish the report`／`跟进：完成报告`或表单；已有事务的讨论会保留进展。可选文字AI与语音独立配置，详见[事务契约](docs/task-tracking.md)。自然交谈需要配置语音服务并完成实际试听。

## 先运行软件

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

- [电脑／手机管理界面](http://127.0.0.1:5190/)
- [独立常亮屏](http://127.0.0.1:5190/?surface=device)
- [独立角色输出](http://127.0.0.1:5190/?surface=avatar)；反射像可加`&mirror=1`

构建前端后，也可以只运行同源服务，不依赖Vite：

```sh
.venv/bin/uvicorn desk.app:create_app --factory --app-dir backend --host 127.0.0.1 --port 8831 --workers 1 --no-access-log
```

此时在`http://127.0.0.1:8831/`打开同样的界面。**必须保持单个API工作进程**：姿态、输出停机和语音会话在该进程中协调。

账号是`owner`。首次运行随机生成密码，保存在本机文件`.runtime/credentials.json`，权限0600。数据库、配对令牌、配置密钥与模型在`.runtime/`，不进入版本控制。不要删除整个目录来重置页面。真实手机访问需要可到达的HTTPS地址；手机自身的`127.0.0.1`不是桌面主机。

## 操作入口

- **Assistant → Computer jobs**：拥有者核对全文及目标后批准。专用笔记默认关闭；指定文件夹要先填写一个运行目录之外的真实路径。见[隔离试运行](docs/computer-jobs.md)。
- **Tasks**：创建事务、记录进展、查看／暂停跟进、安排日历时段、确认完成或恢复。
- **Today／Calendar**：查看与编辑日程；右上角助理可查询、生成草稿并确认。
- **Device → Posture & feedback**：允许观察、个人标定、提示时间、暂停及复测状态。
- **Device → Pairing & outputs**：生成配对码、核对两端号码、批准／撤销；查看输出回执和停机状态。
- **Device → Calendar & companion**：天气、双历、假期、提醒／安静时段、唤醒进程开关与常亮画面。
- **Device → Import & share**：文件、Google只读连接、分享和备份。
- **Records**：按类别、来源和日期筛选，导出CSV；回放会单独标记。
- **iPhone → Device → On this iPhone**：用户主动启用通知、刷新小组件摘要。没有自动授予系统权限。

[完整操作与安装说明](docs/operator-guide.md)包括Pi、iPhone、语音配置、模型、相机和输出控制。[架构与限制](docs/architecture.md)说明数据及权限边界。[评价流程](docs/evaluation.md)用于以后获同意的真人测试。

## 验证与交付边界

最新10月15日[审查与合并QA](../output/qa/2026-10-15-grok-review-merge/verification.md)为182项后端、17项前端，Ruff／类型／构建和npm审计零发现，含记忆／人格／目录的真实浏览器检查。历史149项后端、15项前端及实际浏览器证据见[本地整合核验](../output/qa/2026-10-09-dot-integration/verification.md)；[10月6日云端软件核验](../output/qa/software-completion-2026-10-06/verification.md)保留当时结果。启用与复现实验见[电脑作业操作](docs/computer-jobs.md)。旧阶段证据在[事务增强与UI／UX审查](../output/qa/task-enhancement-ux-2026-10-03/verification.md)：101项后端、11项前端检查、生产／iPhone构建及实际三端交互。此前[S1–S10记录](../output/qa/software-completion-2026-10-02/verification.md)保留。测试数据库与主数据分开，10月9日交互使用独立`.runtime/dot-integration-qa/`；旧轮使用`.runtime/completion-qa/`。截图中的安排和回放是演示数据。正式主库原有示例保留，不自动移动到今天。

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
frontend/src/workspace/ 姿态、助理、连接、数据交换与角色
frontend/ios/           iPhone、WidgetKit、App Intents与Keychain桥
scripts/                安装、诊断、模型校验、回放、标注和评价
config/                 未启用的设备／服务示例配置
.runtime/               本机私有运行数据、模型和构建缓存
```

依赖与来源见[THIRD_PARTY.md](THIRD_PARTY.md)。框架与角色源稿可替换；当前小角色为本组软件中的原创占位图形，不是Razer角色或已定稿品牌。
