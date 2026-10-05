# Group 2 Project Contract

更新：2026-10-05。状态：**DESK_SOFTWARE_READY_FOR_INTEGRATION**。

## 当前方向与用户决定

9月25日用户推翻旧Senplate食品监测方案。当前是家庭／办公室个人桌面的智能日历、坐姿反馈与语音助理设备，开发名称暂用**Desk Companion**。三位学生、约半年、一台实体原型；英文默认，支持简体中文。所有组号写Group 2，身份资料见[group-2-details.json](planning/2026-09-14/group-2-details.json)，其中旧食品范围不定义新项目。

**必做主线：**固定摄像头观察可见头肩 → 个人标定和持续时间判断 → 具体屏幕／语音／灯光及合格机械预设反馈 → 再观察并记录回到参考、仍偏离或无法判断。不能把“提醒时机”单独包装成核心，也不承诺情感障碍治疗、抑郁诊断、脊椎判断、工作质量／专注评分或长期健康改善。

用户要求手机、电脑都能控制，并能直接操作设备触摸屏。9月30日明确否定Linux常亮屏沿用手机／网页构图，因此设备用独立DeviceApp。触摸屏与角色输出分开组织，显示单元数量和最终光路未锁定。Razer没有公开AVA内部完整光路；反射像、带罩旋转LED和普通屏仍是待实测选择。自动切换片段不必然需要HDMI，逐帧内容则需可用的视频／SDK通道。[光学研究](research/2026-09-26-desk-companion/ava-optics-fan-vs-reflection.md)与[风扇接口](research/2026-09-26-desk-companion/hologram-fan-maturity.md)保留。

10月2日用户授权**完成所有无需其参与的软件工作，不能每批自行停止**。该轮已按[完成计划](planning/2026-10-02/software-completion-plan.md)完成独立软件及本地验证。框架、接口、预设与临时图形属于工程选择，正式名称／角色美术不是用户已确认的品牌决定。

10月3日用户希望AI参考Codex／ChatGPT的**Your dot**自动跟踪事务，并明确要求先增强软件、再审查UI／UX交互逻辑。[主动事务首版](desk-companion/docs/task-tracking.md)现已实现并通过本地验证：持久事务与进展、检查调度、暂停／延后／结束、助理草稿、可选Qwen／Gemini文字推理和三端入口。它不取代坐姿主线；模型与后台AI默认未启用，不自动读取邮件、屏幕或全盘文件。此前[可行性研究](research/2026-10-03-dot/proactive-task-tracking.md)保留为研究基线。

## 已实现的软件范围

10月5日用户授权将全部项目工作上传至新 GitHub 仓库，暂定仓库名 **FYP**，用于 Group 2 协作。采用私人个人仓库，当前软件名称仍为 Desk Companion；旧 Senplate、学校文件、研究、设计及 QA 记录保留。成员上手与分支 / PR 流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。本机凭据、运行数据库、已安装依赖与缓存留在本地；所有实际上传及远端核验结果见 [GitHub 建仓 QA](output/qa/2026-10-05-github-bootstrap/verification.md)。这次授权包含建仓、首次提交和推送；成员邀请的操作方法提供给用户，不自动发出邀请。

新代码位于[desk-companion](desk-companion/README.md)：React／TypeScript／Vite、FastAPI、SQLite；现场主机运行单个API进程，工作进程负责相机／唤醒／输出。旧食品代码与品牌保持独立。

- **日历：**Today、日周月、单次与多日期批量、公历重复和单次例外、编辑／删除／完成／恢复、冲突、提前提醒、延后、记录和CSV；版本与操作ID控制重复及未知保存结果。
- **常亮屏：**独立大时钟、日期、月历与近期事项；日／夜／自动，触摸进入控制和编辑，60秒闲置返回并保护未确认编辑。角色为另一可选画面；独立黑底／镜像页可供后续显示模块使用。
- **坐姿：**类型化关键点、质量门槛、个人参考／前倾／侧移标定、持续条件／冷却／延后、反馈后复测、可靠在桌时长和离桌判断、实时／回放隔离。没有把缺帧当作已恢复。
- **配对：**单次短码、拥有者核对批准、独立可撤销长期身份；iPhone原生Keychain保存配对令牌。常亮终端会话和拥有者8小时会话分开。
- **事务：**待处理／进行中／等待／完成／取消，截止与下一步、可勾选步骤、进展来源、一次待处理跟进、暂停／延后、完成依据、版本冲突；Today、Tasks和常亮屏入口共用数据。
- **助理：**事务／日历／姿态／设备查询，创建／修改／删除／进展／命名动作的可检查草稿、确认／取消／到期、版本校验和重复确认去重；模型不获得确认接口。软件停止可立即请求。
- **语音：**Qwen Audio与Gemini Live两种可配置适配器、PCM流式输入／输出、打断、取消未确认草稿、短票据、单会话与时限、用量记录。本地中英唤醒工作进程已实现；默认未配置提供商。
- **输出：**默认停机；预设、5秒时限、一次领取、取消、重启过期与驱动回执。PCA9685／GPIO驱动需实际配置校准；模拟结果不会标成实物成功。
- **日历辅助：**选择地区后读取香港天文台天气及来源时间，农历显示，香港2025–2027公众假期，日期占用摘要、安静时段、提示音和本地简报。
- **交换：**ICS预览、范围展开、去重与版本校验、系列／例外导出；只读忙闲／可展示标题分享与撤销；业务备份（含事务及每件最近20条进展）和保留现有内容的合并恢复；恢复事务默认暂停跟进。Google主要日历只读连接与预览更新代码已实现，未向Google写入或声称云端双向已验证。
- **平台：**同源生产服务、Linux kiosk／用户级systemd安装与诊断脚本；iPhone原生工程、文件导出、WidgetKit、App Intents和主动启用的缓存本地通知。

CAL-01至19的映射以[Part 1整理](planning/2026-09-29/calendar-part1-functional-scope.md)及[本轮计划](planning/2026-10-02/software-completion-plan.md)为准。公网发布、企业多租户、App Store发布、临床诊断和复杂抓取未加入首版。iPhone Widget不被称为电脑原生Widget；独立常亮页也不冒充操作系统小组件。

## 准确性、隐私与证据

姿态模型为MediaPipe Pose Landmarker。它提供可见关键点，个人标定与时间逻辑由本组软件实现；不依赖桌面遮挡下的髋点。二维前倾／侧移属于相对个人参考的候选，不能保证任意机位／遮挡／衣着都可区分。Mac使用已运行的0.10.35；Linux选择有aarch64发行包的1.0.1，尚未在Pi实跑。

默认不打开摄像头或麦克风，也不落盘原始音视频。选择并开始语音服务后，音频和所请求的日历上下文会经过该提供商；默认本地文字规则明确标注，不能冒充语言模型。可选文字服务与语音独立配置；自动文字建议默认关闭、每天最多20次尝试，模型不能自行确认修改。实时与回放的标定／记录隔离，回放提醒不会驱动真实硬件。

常亮屏的私人展示投影由服务端处理，断连时客户端也隐藏缓存中的私人字段。自动离桌隐藏不是身份识别；已批准终端属于同一拥有者的工作空间。分享只能读投影，配对令牌与云密钥不进入业务备份。

本轮使用隔离数据库、模拟协议、合成关键点与模型冒烟输入。实际浏览器已操作草稿保存、配对、三步回放标定、持续偏离、导入和只读分享；iPhone已构建、签名、安装并配对，原生共享容器写入也已核查。原功能检查见[S1–S10 QA](output/qa/software-completion-2026-10-02/verification.md)；最新101项后端、11项前端、三种界面及iPhone构建检查见[事务增强QA](output/qa/task-enhancement-ux-2026-10-03/verification.md)，不能把这些结果写成真实摄像头准确率、自然语音质量、Pi性能或机械角度成绩。

原提案的6名自愿成年人（开发／测试各3人）、F1目标0.80、误报不超过2次／小时、持续条件后95%本地反馈不超过2秒、两种桌面各2小时、100次动作仍是待验证计划。已提供[采集／标注／评价工具](desk-companion/docs/evaluation.md)，真人资料和标签必须另行取得，不增加市场问卷或调查访问。

## 语音与学校服务器

用户强调自然交谈和可靠工具调用，先前Qwen→Gemini→Realtime→Live顺序已被后续全面质量与价格比较取代为历史考虑。当前[自然度研究](research/2026-09-29-voice-ai/naturalness-and-tools-review.md)与[费用研究](research/2026-09-29-voice-ai/price-and-value-ranking.md)仍是选择依据，最终服务未由用户锁定。代码保留Qwen／Gemini适配，不代表本组已试听、计费或批准购买服务。

学校设备初步被用户描述为DGX-1／Tesla V100；每卡显存、可用配额、系统与网络权限仍未知。[服务器比选](research/2026-09-28-local-voice/server-deployment-comparison.md)保留Volta兼容条件。本轮未登录学校服务器，也没有把商业Qwen实时API型号当作同款开源权重。取得实际资源后可按既有比较验证自托管方案。

## 硬件与下一阶段

Pi5 8GB仍为现场主机候选，现有Arduino UNO R4 WiFi可选。普通UVC相机用于可见姿态输入；机位与视野要验证。机械臂拟2至3自由度、轻载、不接触人体、不抓取，独立电机供电与停机；相机不随机械臂移动。具体型号、供电、噪声、动作包络、触控键盘、屏幕常亮与散热仍依赖实物。

无需用户参与的代码工作与需要外部条件的验证分开：下一阶段取得目标设备、用户的音视频许可与个人标定、所选语音服务或学校连接、Google账号授权、Apple真机签名，再完成真实闭环验证。不能用增加软件功能替代这些数据和台架检查。

## 学校文件与历史

最新学校正文仍为[中文v3](planning/2026-09-28/desk-companion-proposal-zh-v3.md)和[对应英文](planning/2026-09-28/desk-companion-proposal-en.md)。

- [英文Proposal DOCX](<output/submission/2026-09-28/AY26_ProjectProposal_Group 2.docx>)／[PDF](<output/submission/2026-09-28/AY26_ProjectProposal_Group 2.pdf>)。
- [团队日志DOCX](<output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.docx>)／[PDF](<output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.pdf>)：一份列三人工作，9月14–27日记录，9月28日填表；成员归属为用户授权安排的member-review draft。

Yuan Yuchen为组长，计划40%；Xu Ziqian及Li Wenhua各30%。此比例不是本轮实际完成贡献或评分。本轮AI辅助实现不自动归作学生已完成贡献。学校原件、现有双格式交付与签名状态未改，没有代签、上传或联系导师。

10月26日Progress I、11月30日Initial、12月14日Progress II及后续节点以[学校提案／修订核对](planning/2026-09-28/logsheet-and-proposal-review.md)保留的证据为准。旧食品方案、品牌、采购、代码及Proposal均保留为历史，入口是[旧产品规范](product-senplate-historical.md)。

当前操作入口：[软件README](desk-companion/README.md)／[安装与操作](desk-companion/docs/operator-guide.md)／[架构](desk-companion/docs/architecture.md)／[交接](handoff.md)／[决定](decision-log.md)／[工作记录](work-log.md)。
