# Desk Companion 操作与安装说明

2026-10-28接续：手机已按职责拆分，网页／手机共用会话恢复和日程编辑。[维护契约](software-maintenance.md)／[本轮QA](../../output/qa/2026-10-28-maintainable-ai/verification.md)。本机免登录会话失效后重新建立会话并保留输入，不自动重试未确认写入。

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**现行规范／入口**。已按本轮保存状态核对；最新软件、GitHub main 和 Pi 部署分开，Pi 暂停、旧 API 预算关闭。 [新聊天入口](../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

适用：Group 2单拥有者原型。先使用本地日历，再按实际条件连接设备与服务。以下命令在`desk-companion/`执行。配置中没有真实账号密钥。

## 本机免登录预览（2026-10-28）

当前开发预览显式使用`DESK_LOCAL_PREVIEW=1`，打开网页或已连接的模拟器即可进入，无需设置用户名／密码。仅接受直接回环请求；公网、远端、转发和外部Origin不能使用。正常API权限、8小时会话和写入批准保留；关闭该标志恢复下节登录方式。真实设备／Pi／公网不自动采用此模式。隔离数据、启动命令及当前模拟器入口见[实现说明](../../planning/2026-10-28/phone-simulator-implementation.md)。

## 1. 日常操作与配对

拥有者登录有效8小时；配对屏幕使用独立身份，可在连接页撤销。长期常亮屏先登录，在设备界面的Connections选择“Keep this display paired”。退出登录会清理该终端凭据，不能用退出按钮保留同一配对身份。

手机／另一浏览器选“Pair with an existing desk”，输入拥有者生成的8位单次码。码有效2分钟；申请有效5分钟。拥有者核对两端4位号码后批准。iPhone的长期令牌由原生桥保存到Keychain，不放入localStorage。拥有者管理、导出、分享和第三方授权要求重新进行拥有者登录。

当前所有配对屏幕属于同一个人的工作空间，不是学校多人租户系统。私人／可展示是展示政策：普通已授权控制界面可编辑本人内容，常亮屏可在离桌或无法判断时隐藏私人标题。分享是单独生成的只读授权。

## 2. Linux／Pi主机

2026-10-27：用户已暂停实机。以下教室成功是历史结果，不能直接在宿舍复用旧 IP。当前 Student 接入但远程超时，Halls 冷启动 v2 已写好但未运行；恢复入口见[当前交接](../../handoff.md)。

Pi5 8GB已实际启动并于10月26日通过NETGEAR02接通Mac网页与桌面。按[无屏幕连接说明](pi5-usb-mac.md)使用Wi-Fi连接脚本；USB数据仍未接通。当前卡含systemd路径／8891来源／VNC认证热修复，新的统一Omni代码仍待同步。外接屏幕与离线镜像说明保留在[首次启动说明](pi5-first-boot.md)。下列手动安装流程用于其他主机，Pi现场性能仍需实测。安装Node、uv和Python依赖后，执行README中的前端构建。系统需具备Chromium、摄像头权限、音频系统和中文字体；Debian系可按实际镜像安装`chromium`、`libgl1`、PortAudio和`fonts-noto-cjk`。不要把Mac安装结果当成Pi已安装。

```sh
uv sync --frozen --extra vision --extra audio
.venv/bin/python scripts/fetch_models.py
.venv/bin/python scripts/fetch_wake_model.py
.venv/bin/python scripts/diagnose.py
.venv/bin/python scripts/install_linux.py
```

最后一条默认只在`.runtime/linux-preview/`生成可审阅单元。目标Linux确认路径后：

```sh
.venv/bin/python scripts/install_linux.py --install --enable
systemctl --user status desk-companion.service
./scripts/kiosk.sh
```

它只启用API；相机、语音和输出单元保持关闭。10月26日修复WorkingDirectory／EnvironmentFile的路径引用；四个生成单元经Pi systemd解析通过，实际运行也验证了含空格／百分号路径及环境文件读取。可将kiosk启动器加入目标桌面会话的自动启动。X11启动器只调整当前显示会话的屏保／DPMS；Wayland的空闲抑制、触摸键盘、旋转和背光要在所用桌面环境上配置验证。Chromium保持默认沙箱。代码没有修改当前Mac的全局休眠。

网络访问使用[示例Caddy配置](../config/Caddyfile.example)及`DESK_PUBLIC_ORIGIN`。先确定主机名／局域网地址、安装可信证书，再配对手机；不会自动开放公网或跳过证书验证。API继续绑定回环，由TLS代理转发。

## 3. 摄像头与个人标定

```sh
PYTHONPATH=backend .venv/bin/python -m desk.agents.camera --camera 0
```

进程先查询“允许观察”，未允许／已暂停／控制连接失效时不会持续打开相机。允许后在界面依次记录平时姿势、轻微前倾、轻微侧移。每项需至少20个有效观察且持续至少5秒；无法分开的姿势会要求调整机位。移动相机、换输入或改变分辨率后应重新标定。设备编号相同的物理移动不一定能自动检测。

模型只提供可见关键点。亮度、可见性、多人数、时序和标定匹配由程序检查；缺帧／遮挡等显示“无法判断”。不会用不可靠髋点算角度，也不把低置信度当作正确姿势。默认不保存或上传图像。

macOS使用MediaPipe0.10.35，已实际运行空帧；1.0.1的macOS CPU图存在已复现的问题。Linux使用1.0.1，因为该发行版有官方aarch64轮子；Linux分支已在ARM64容器安装／导入，并装入离线镜像；没有在Pi实跑。模型内容使用SHA256固定。

## 4. 回放演示

回放只能在明确设置`DESK_ALLOW_REPLAY=1`的隔离运行目录使用。主服务默认关闭。

```sh
DESK_RUNTIME_DIR="$PWD/.runtime/demo" DESK_ALLOW_REPLAY=1 .venv/bin/uvicorn desk.app:create_app --factory --app-dir backend --host 127.0.0.1 --port 8832 --no-access-log
```

在第二个终端启动：

```sh
.venv/bin/python scripts/replay_posture.py --runtime .runtime/demo --api http://127.0.0.1:8832 --seconds 600 --pose reference
```

界面标定时，回放会提供对应的合成姿势。可用`--pose forward`／`side`／`away`／`dark`演示，或使用`--control`指定仅包含姿势名称的本地文件。画面和记录始终显示Replay。回放产生的姿态提醒不会驱动已连接的真实输出。

## 5. 自然语音

**2026-10-27 当前选择：**Qwen3.8 Omni 同时承接拥有者输入框与语音，使用同一上下文／记忆／工具。完整合成操作链和实际播放采样已有最终 QA (local historical material: `output/qa/2026-10-23-ai-acceptance/resumed/verification.md`; not included in this checkpoint)；真人声学与 Pi 尚未验收。早期 PR #15 不包含全部最新本地功能。所有已执行预算均关闭；普通示例不自动读取私有 Key。

后端从环境读取配置。复制[service.env.example](../config/service.env.example)到`.runtime/service.env`并设权限0600；systemd会读取该文件。手动启动时由本机安全加载环境后再启动服务，不把密钥粘贴到前端或Git。

| 字段 | Qwen Omni | Qwen Audio | Gemini Live |
|---|---|---|---|
| `DESK_VOICE_PROVIDER` | `qwen_omni` | `qwen_audio` | `gemini` |
| `DESK_VOICE_MODEL` | 留空默认`qwen3.8-omni-flash-realtime` | 实际获准型号，如`qwen-audio-3.1-realtime-plus` | 实际获准型号，如`gemini-3.8-live` |
| `DESK_VOICE_ENDPOINT` | 留空默认`wss://maas.qianwenaiapi.com/api-ws/v1/realtime`，不带query | 对应工作空间`wss://…maas.aliyuncs.com/api-ws/v1/realtime`，不带query | 可留空使用官方端点 |
| `DESK_VOICE_API_KEY` | 可留空，显式`DESK_QWEN_CREDENTIAL_FILE`绝对路径读私有Key | 对应工作空间密钥 | Gemini密钥 |
| `DESK_VOICE_VOICE` | 留空默认Tina，尚非最终选声 | 可选官方音色名 | 可选官方音色名 |

配置重启后，“Configured”仅表示字段可用；真实连接、语言效果、费用和自然度要另外测试。没有凭据时不会自动调用服务。用户选择Omni，其余适配器仍保留；Omni本次短测不替代真实麦克风、语言自然度或Pi验收。

浏览器／iPhone在助理里“Start conversation”后申请麦克风并持续交谈，不必按住按钮。浏览器请求AEC／降噪，结果取决于设备。输入PCM16、16kHz、单声道；输出24kHz。每轮5秒仍等待给提示、10秒仍无合格播音结束并围栏迟到结果。More → Response timing显示首包／首音／工具后首音来源；后者不是自动语义正确评分。每次会话最多10分钟，45秒无活动会结束；不会自动重连造成重复费用。打断清空播放，取消未确认草稿；已保存日程不会被打断撤销。

日历和命名动作由后端工具执行。创建／修改／删除／设备预设先在屏幕确认；模型没有确认接口。命名动作排队与驱动回执分开。软件停止可直接请求，不受另一个待保存日程阻挡。

Omni活动语音会话中，拥有者可主动选择一张图片或浏览器屏幕来源。图像会送至已配置语音提供商，不打开摄像头；最多1280×720 JPEG、1fps，后端检查身份、分享状态、大小与速率。停止屏幕分享或结束对话会释放采集，已发内容仍在当前提供商上下文中。选择图片后直接提问；模型使用随音频提交的图像。配对终端不开放该分享功能；移动端无屏幕接口时按钮禁用。

设备免按键唤醒使用本地工作进程：

```sh
PYTHONPATH=backend .venv/bin/python -m desk.agents.voice --language zh
```

需先在偏好中允许本地唤醒，且已配置服务。当前开发唤醒词为 **Hey desk**／**你好桌伴**，不是最终品牌决定。sherpa-onnx模型在本地识别，检测到词后才申请语音会话。sounddevice路径需使用合适的AEC麦克风／扬声器通道；尚无真实回声或唤醒率结论。浏览器会话与本地工作进程共用单会话限制。

当前完整Alice角色出口为`?surface=avatar`，支持旋转／缩放及原生表情；纯黑输出加`&clean=1`，反射显示可加`&mirror=1`。嘴部跟随浏览器实际输出音量，尚无逐音素口型或跨设备声音桥；风扇／反射器接口与光学仍需实物确认。

## 6. 灯光与机械臂

默认停机，API只接受命名预设，没有任意角度、脚本或抓取接口。控制器需持续心跳；命令5秒过期、只领取一次、重启不重放。模拟回执显示Simulated。

```sh
PYTHONPATH=backend .venv/bin/python -m desk.agents.outputs --driver simulator --runtime .runtime/demo --api http://127.0.0.1:8832
```

真实驱动使用PCA9685／ServoKit与GPIO Zero，需在目标Linux安装相应驱动。以[outputs.example.json](../config/outputs.example.json)复制至`.runtime/outputs.json`，完成台架标定后再填写实际限位、脉宽、预设和停机GPIO；样例`commissioned=false`不能直接启动电机。

```sh
PYTHONPATH=backend .venv/bin/python -m desk.agents.outputs --driver pca9685 --config .runtime/outputs.json
```

采用常闭停机检测；实际设备还需要独立电源切断，不把GPIO软件检测当成物理急停。首次启用先在台架设定的rest位置开始。没有编码器，`driver_completed`仅说明驱动写入完成，不证明机械角度正确。实物型号／电源／包络仍须验证。

**RIG-Arm候选（2026-10-05）：**[研究与接入缺口](../../research/2026-10-05-rig-arm/secondary-development-review.md)已核对，尚未增加RIG驱动；不要把上面的PCA9685命令用于其SCS009总线舵机，也不要把端口80 `/mcp`当作所有出厂固件均有的接口。先取得实际型号／版本和工具清单，再完成停止、限位和反馈台架检查；teach_stop或关闭空闲微动不能当作动作急停。开发时保留当前输出默认停机。

## 7. 日历、分享与恢复

- 普通事件保存本地墙钟时间和IANA时区；全天事件以日期表达。查询最多62天，最多3000个发生项；单库最多500项主事件。
- 重复按公历；每月31日或闰日不存在时跳过。农历目前用于显示，不是农历重复。
- 声音默认关闭；常亮屏需要主动启用声音。安静时段抑制声音，不删屏内提醒。简报使用可用的本地系统语音；没有本地语音时仍可显示／提示。
- 香港天气每10分钟刷新，失败保留来源时间并标过期。假期数据覆盖2025–2027，指公众假期；其他地区未选时不猜测。
- ICS导入展开所选范围内的发生项为单次副本，默认私人／无提醒。预览显示新增、相同、变化与跳过原因；匹配变化只有明确勾选后替换，版本冲突会拒绝整个应用。
- ICS导出包含原生系列和例外。文件不是云端实时同步。
- Google连接使用只读scope、一次性状态、PKCE和后端加密令牌。需自己的Cloud OAuth客户端与回调地址；导入前预览，不向Google写入，也不自动删除本地副本。
- 忙闲分享只返回合并时间段；详情分享只返回可展示标题和时间。分享码在URL片段中，API校验撤销／到期；不自动发送链接或暴露公网。
- 业务备份包含事件、例外、设置快照、事务及每件最近20条进展，不含登录、配对、云令牌、原始媒体或vault密钥。恢复只合并缺少的事项，保留现有事项、事务和当前设置；恢复的新增事务默认暂停跟进。JSON校验值用于发现损坏，不是加密或真实性证明。

## 8. iPhone与系统功能

```sh
cd frontend
npm ci
npm run build
npx cap sync ios
node scripts/configure-ios-features.cjs
cd ..
.venv/bin/python scripts/prepare_ios.py
```

`prepare_ios.py`是Xcode下载受阻时的可复现路线：下载官方8.5.2框架、验证其官方SHA256、引用本地Swift包。不修改框架内容。SDK版本改变后需要重新核查，不能沿用旧校验值。

打开`frontend/ios/App/App.xcodeproj`，scheme为App，bundle为`dev.group2.deskcompanion`，iOS17+。2026-10-28全屏Alice版本已在iPhone17Pro／iOS26.5编译、安装、启动并检查实际画面；原生触控／键盘尚未通过完整自动验证，见QA (local historical material: `output/qa/2026-10-27-phone-simulator/verification.md`; not included in this checkpoint)。真机Team、App Group与签名需使用拥有者账号配置，未进行App Store提交。

正常首次填桌面HTTPS地址，再配对。当前本机模拟器已设置回环主机地址并使用上述免登录预览；HTTP回环只对Simulator开放。手机进入全屏Alice首页，从Plan查看日历／事务、More打开管理面板；对话输入在面板切换时保留。通知由使用者在Settings（原Device）页面启用，最多缓存未来七天64条，离线时远端修改不会自动同步，重新打开App刷新。私人标题在通知及小组件中始终隐藏。

WidgetKit含小／中尺寸，缓存超过20分钟提示刷新。系统控制实际刷新频率。快捷入口为打开Today和准备新事件，后者只打开表单，不直接创建。退出或撤销后本App清理本地快照和通知；没有跨设备推送服务。

## 9. 主动事务与文字AI

Tasks中创建并保存事务，记录截止与下一步。需要安排工作时点时选择“Choose time in calendar…”，检查并保存独立日程；这不会自动标记事务完成。下次检查到期后出现一个入口，可以保存进展、延后一小时、暂停、完成或取消；完成／取消可在History恢复。步骤全部勾选仍须明确确认整体完成。

未配置AI时，助理明确使用本地规则：`Track: report`／`跟进：报告`准备事务草稿；在事务详情选择“Discuss this task”记录新进展，检查后保存。本地规则不会理解任意表达，也不会自动把进展改成新的状态。

拥有者配置Qwen Omni后，输入框与语音使用同一模型、上下文与记忆。下面是保留的独立文字适配器配置，主要用于显式启用的后台建议，不是Omni日常对话的第二个聊天模型：

| 环境变量 | 内容 |
|---|---|
| DESK_TEXT_PROVIDER | none（默认）、qwen或gemini |
| DESK_TEXT_MODEL | 账号实际可用、支持JSON输出的文字型号 |
| DESK_TEXT_API_KEY | 该服务的密钥，仅留后端私有配置 |
| DESK_TEXT_ENDPOINT | Qwen官方工作空间兼容接口，路径以/compatible-mode/v1/chat/completions结束；Gemini可留空 |
| DESK_TEXT_BACKGROUND | 默认0；明确启用后1，为待跟进提示补充AI建议 |

后台建议最多20次尝试／UTC日，失败计入，不自动重试中断请求；失败保留本地规则提示。主程序关闭后不能继续检查，主机仍须常开。自然语音单独按第5节配置；没有从本机其他项目读取或复用密钥。

详情与数据边界见[事务契约](task-tracking.md)。可选文字服务尚未真实试测；第5节 Omni 已完成虚构日历／记忆全链与合成多语言采样。`configured`只是配置有效，不能当作质量或费用验收。当前事务尚无远程锁屏推送、邮箱监控或学校服务器部署。

## 10. 受限电脑作业

默认`DESK_COMPUTER_ENABLED=0`，只控制专用笔记目录。拥有者还可以在 Computer jobs 指定一个已存在的真实文件夹；该路径的任一层不能是符号链接，也不能是运行目录本身、上级或子目录。按[电脑作业操作说明](computer-jobs.md)试用。助理面板内的 Computer jobs 要求拥有者会话，配对终端不能批准；模型只能准备、查询或请求取消，不能提交路径。每项作业核对全文及目标后再批准，结果未知时先核验，不要重复生成相同任务。

没有安装LCU、启用Mac录屏／Accessibility或操作硬件。已新增Linux专用Mousepad→Chromium流程并在隔离ARM64容器实际跑通，DESK_LINUX_DESKTOP_ENABLED显式启用；它不具备任意桌面操作能力。10月6日[云端核验](../../output/qa/software-completion-2026-10-06/verification.md)保留当时浏览器受限的事实；10月9日[本地整合核验](../../output/qa/2026-10-09-dot-integration/verification.md)补充实际浏览器操作及语音断连回归。普通启动仍默认关闭笔记执行；需要试用时只按作业说明在独立运行目录启用。

## 2026-10-15 记忆与人格

拥有者可在Saved memories查看／更正事实，在Assistant style展开编辑共享指令；网页Settings取代原Device管理入口，原URL仍兼容。配对终端不能经助理草稿、文字或语音取得事实。人格冲突会保留草稿；“放弃草稿并加载当前人格”才替换为服务端版本。保存回执丢失时使用“核对保存状态”（原“安全重试”），不另建操作；恢复只清理匹配的草稿。重置默认人格仍增加版本。业务备份暂不包括记忆、人格和作业，请勿将日历备份误称完整恢复。

## 当前助理与常驻人物操作（2026-10-22）

Assistant opens directly into one composer. Empty text shows the configured microphone action; entered text shows Send. More opens file activity, help and character review; rejected A1 studies remain historical. Plus provides briefing, or selected-image/screen controls during an eligible owner voice session. File actions still require full-text review; unknown writes are independently reconciled. Local mode states the supported text-rule scope. With Qwen Omni enabled, owner text and voice use the same model and context; typing does not request a microphone.

2026-10-23续轮：新连接最多缓冲5秒早到语音，取消立即丢弃；对话失败或10分钟到期后需本人再次发起，不自动收费重连。记忆确认后重新连接会读取新事实，旧连接释放期间短暂等待。改口产生的新草稿会取代同一事项旧稿，取消及过期不能再确认。若最新日程无法核实，显示失败并停止连接，不把旧数量当成新结果。

The current resident is AliceChan. Drag, wheel/corner/slider resize and left/right/bottom docking remain available, with recall and intact2D fallback. Click produces a short response; native expressions and speaker-output mouth amplitude remain. Rejected A1 motion studies are historical. See [avatar limits](avatar.md). Resident display never starts a microphone, screen share or paid session automatically.


## 2026-10-27 网页布局与操作更新

桌面角色默认位于侧栏预留区域，伙伴控制可切换自由悬浮／回侧栏。编辑和审核模态框会暂停角色；宽屏助理保持角色可见。1200px及以上助理打开在右侧，主页面可以继续使用；小窗口回到弹层，跨断点保留输入。事务讨论使用同一个网页助理入口，已有对话时先正常关闭／处理草稿，不再叠开第二个助理。

新建日程先填标题和时间，详情／提醒可展开；收起仍显示分类、隐私和提醒，保存／取消固定可见。记忆删除先确认，风格编辑保留未保存保护；记录筛选可展开和清除。日／周／月与中文日期展示已回归。此段是27日网页及共享组件结果；28日手机实现另见上述接续说明，不代表Pi部署。[完整说明](../../planning/2026-10-27/web-ui-implementation.md)。
