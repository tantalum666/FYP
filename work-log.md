# Group 2 Work Log

Updated: 26 October 2026. Current state: [handoff](handoff.md). Pre-pivot Senplate entries are preserved in [the archive](archive/senplate/work-log.md).

## 2026-09-25 智能工作台／AI电子日历转向研究

- **目标：**执行用户推翻 Senplate 并研究组员新想法的指令；用户补充适用家庭或办公室桌面，并明确 Chrome 中已打开指定 OpenAI 视频。
- **开工阅读：**按 AGENTS 完整盘点和读取86份项目自有 Markdown、7847行、69批；批次截断处逐项补读，记录显示阅读期间无文件变化。[阅读记录](output/qa/new-concept-2026-09-25/reading-record.json)。两份组员原文件只读提取；DOCX两页结构与页面渲染核对，渲染环境缺中文字体，故正文判断依据结构提取。原件SHA-256、旧Proposal哈希留在本轮QA。
- **公开研究：**核对 Echo Show 存在感知、Skylight Calendar、Microsoft Viva、Upright GO 2、Razer AVA、Pi官方规格、Google日历API、OpenAI GPT-Live官方技术／价格、微软提醒时机研究、OSHA／NIOSH，以及情绪推断与AI情感使用研究。Chrome 实际播放指定约55秒X视频，查看0:06、0:16、0:21、0:30、0:39、0:51画面／可见字幕，再与OpenAI官方完整技术文章交叉。未声称观看所有音轨或复现视频装置。
- **研究结论：**电子日历、存在感知、姿态反馈和语音角色已存在；“更有硬件／功能”本身不是差异。首选可测命题是基于日程紧迫度、在桌状态和用户专注设置减少不合时宜提醒，同时守住重要事件的及时性；用用户确认构成闭环。情感障碍治疗和自动情绪诊断不在可承诺范围；LCD角色可做，反射影像和小云台仅作可选实验。GPT-Live语音按需开启，官方按活跃会话秒数收费，后端另计。
- **交付：**[新方向完整分析](research/2026-09-25-desk-companion/feasibility-review.md)，含竞品矩阵、四种定位、商业假设、硬件与语音架构、验证、六个月分工和英文Proposal表述。重写[product.md](product.md)，将旧全文保留在[product-senplate-historical.md](archive/senplate/product-senplate-historical.md)；README、brand、旧软件总规范、商业计划、RFQ入口与旧Proposal规范标历史，更新decision-log与handoff。
- **未完成：**团队与Marco尚未选定具体新题、新硬件清单和用户试点；新英文Proposal DOCX／PDF尚未制作或提交。没有新代码、采购、语音API调用、实物精度测试、真人访谈、外部消息、签名或Moodle上传。旧学校文件与软件保持原样，不把历史验证移植为新项目成绩。
- **收尾验证：**[QA核对](output/qa/new-concept-2026-09-25/closeout-validation.json)检查新旧规范及修改文件中的本地链接、两份组员原件和旧Proposal双格式哈希、Senplate旧product逐字内容归档；文档任务没有运行软件或硬件测试，也没有新DOCX／PDF可供渲染。

### 同日补充：语音模型与成本重新选型

- **目标：**回答用户对GPT-Live按时间计费的成本担忧，比较可替换的实时、分段和本地方案，以及自训是否值得。
- **范围与阅读：**沿用同一新方向研究的[全库阅读记录](output/qa/new-concept-2026-09-25/reading-record.json)，本次补读AGENTS、product、handoff、当前报告、最新决定及要改文件；官方新资料实际打开核对。没有重做旧食物项目测试。
- **证据：**OpenAI官方语音架构、价格、Realtime每音频token计量与Mini能力边界；Google Gemini3.8 Live价格／重复上下文费与地区；阿里云Model Studio香港区域及Qwen3.8 Flash香港文字单价、Qwen3.8 Omni Flash香港音频输入→文本能力；Azure Speech East Asia基础语音服务；whisper.cpp、llama.cpp、Piper及Qwen3-ASR／TTS开源资料。记录两家直连Developer API未列香港的限制；阿里云香港实时语音价未核清，不移植新加坡价。成本算例分新音频、会话历史、文本和TTS。
- **交付与建议：**[语音成本专项](research/2026-09-25-desk-companion/voice-model-cost-review.md)与总体报告、product、handoff、decision-log同步。先用可替换的按键说话链／本地ASR、受控日历工具及本地TTS验证；动态文字模型可用香港区域服务，真人式双工会话作为选测。不要从零训练语音大模型；若需学术模型贡献，收集允许使用的反馈来验证轻量提醒时机模型。
- **未完成：**没有建立/试用任何API账号、支付、下载模型、用Pi跑语音、收集录音或产生实测月费；新学校Proposal还未改稿。

### 同日补充：免按键实时语音与设备控制再次比选

- **目标与用户条件：**不以地区或按键说话筛选；对比能免按键实时交互、打断及调用设备工具的主流型号，给出性价比首测候选。
- **开工衔接：**沿用[新方向86份Markdown全读记录](output/qa/new-concept-2026-09-25/reading-record.json)，补读AGENTS、product、handoff、前次语音专项、最新决定／工作记录；新报告写完后再逐段读回。旧食品方案没有重新启动。
- **新核官方来源：**Qwen3.8 Omni Flash Realtime型号、价表、计量和会话限制；OpenAI Realtime 2.1／Mini与GPT-Live计费；Gemini3.8 Live监听与历史计费；Amazon Nova2 Sonic、Grok Voice、Hume EVI、ElevenAgents、Deepgram Voice Agent、Azure Voice Live及豆包端到端／RTC的工具与价格可比性。把MiniMax TTS与文字模型区分于完整语音代理。只以有公开证据的方案纳入，不声称穷尽世界所有型号。
- **交付：**[同口径比选与实验方案](research/2026-09-25-desk-companion/realtime-voice-model-comparison.md)；Qwen3.8新加坡价在仅新增音频的5＋5分钟／天算例约US$0.27／月，8小时输入＋10分钟输出／天约US$6.05／月。多轮历史、文字、重试等额外费用另计；没有实际账单或任务成功率数据。首测Qwen，用OpenAI Realtime Mini与Gemini3.8 Live对照。受限工具由Pi执行，模型不得直接执行任意GPIO／shell。同步product、上一版语音研究的取代提示、decision-log与handoff。
- **验证与剩余：**[QA记录](output/qa/realtime-voice-comparison-2026-09-25/validation.json)检查算式、当前规范链接和文件存在性。未使用语音API、连接硬件、训练、采购、发送外部消息或重做学校Proposal；正式题目、供应商和硬件组合仍待组员／Marco核定，新英文Proposal双格式仍需制作与逐页审阅。

### 同日补充：用户确定语音候选顺序

- **用户决定：**在免按键唤醒词交互前提下，依次优先考虑Qwen、Gemini、Realtime、Live；保留前轮语境下Realtime＝OpenAI GPT-Realtime-2.1 Mini、Live＝GPT-Live 1的暂定映射。
- **落实：**更新[当前规范](product.md)、[交接](handoff.md)、[实时语音比选](research/2026-09-25-desk-companion/realtime-voice-model-comparison.md)和decision-log，使顺序与用户最新选择一致；四款不是同时集成的交付承诺，供应商尚未最终锁定。
- **验证／剩余：**[本次QA](output/qa/voice-priority-2026-09-25/validation.json)检查术语、文件及内部链接。没有新API或硬件测试，也没有学校新Proposal双格式；下一步仍是制作新题目的英文Proposal审阅稿并逐页核对。

### 同日补充：新题目中文版 Proposal 审阅稿

- **用户目标：**先看新方向的中文完整 Proposal，再讨论英文正式稿。以学校原指南和一页 Proposal Guidelines 为结构依据，不复用 Senplate 旧正文。
- **资料与研究：**沿用本轮[86份项目Markdown全读记录](output/qa/new-concept-2026-09-25/reading-record.json)及其后语音补读；本次聚焦读AGENTS、product、handoff、最新决定、新方向研究、学校指南扫描页和范例、课程结构化组员资料。重新核对微软提醒时机研究、Echo占用例程、Skylight、Razer AVA、Pi5、Qwen官方型号和Google Calendar开发文档。学校指南第5页列初期报告要素，第12页列A4／12pt／页边距／参考资料规范；一页 Proposal Guidelines 列七项必需栏目。
- **交付：**[中文版正文源](planning/2026-09-25/desk-companion-proposal-zh-review.md)、[12页可编辑Word](<output/docx/Group 2_DeskCompanion_ProjectProposal_ZH_Review.docx>)及[可重建脚本](scripts/build_desk_companion_proposal_zh_20260925.py)。核心问题为在不遗漏关键日程前提下减少不合时宜的桌面提醒；一台树莓派候选原型、本地唤醒词、Qwen第一候选、受限工具控制、明确失败降级；三人40／30／30新角色，六个月拟议阶段。未将情感障碍治疗、全息或六轴臂列为必做。
- **渲染与修复：**首轮LibreOffice渲染缺中文；从官方Noto CJK仓库取得OFL字体，仅置于任务QA并以本地fontconfig渲染；修复Title继承蓝色边框、封面摘要溢出、参考资料与意见页分页。最终render-05为12页，逐页视觉检查与上一轮像素比较无缺字、截断、表格重叠。a11y高0／中0／低7，低级项均为可追溯来源的原始URL显示。[本轮QA](output/qa/new-proposal-zh-2026-09-25/validation.json)。
- **剩余：**中文稿待用户／团队审阅；Marco尚未正式批准该具体题目。没有硬件、语音API、用户访谈或真实效果实测；英文提交版DOCX／PDF尚未生成、签署或上传。

### 同日补充：根据用户反馈重写中文Proposal第二版

- **用户纠正：**坐姿必须持续监测、作判断并给反馈；机械臂大概率加入；“提醒时机／可检验的桌面工作流程”表述太抽象；重新看组员材料，若学校没要求调查访问就删掉。第一版保留为历史而非覆盖。
- **材料与要求：**重读组员DOCX全部段落和智能屏／电子墨水竞品Markdown全文，核对学校一页Proposal Guidelines七项，无访谈、问卷或调查访问要求；新核Google MediaPipe Pose Landmarker实时模式、Raspberry Pi Camera Module3、OSHA工作站姿态及UPRIGHT现有姿态设备。原组员文档的“防脊椎损伤”“姿态得分／专注度／工作质量”不作为已验证能力。
- **改稿：**[第二版中文正文](planning/2026-09-25/desk-companion-proposal-zh-review-v2.md)与[可编辑14页Word](<output/docx/Group 2_DeskCompanion_ProjectProposal_ZH_Review_v2.docx>)。主问题改为固定机位的持续可见姿态偏离判断、屏幕／语音／计划中小型机械臂提示与复测；电子日历保留多类日程、私人／公开、冲突、TimeTable和每日记录；明确预训练视觉关键点只是输入，个人标定、时间窗、遮挡拒判和对照实验由本组实现。机械臂拟2–3自由度轻载非接触提示，最终型号／安全尚待台架。删除访谈人数和调查里程碑。
- **验证：**[本次QA](output/qa/new-proposal-zh-v2-2026-09-25/validation.json)记录学校七项、术语、来源与组员资料核对；最终render-02逐页检查14页，中文字体完整、表格跨页重复表头，参考资料与意见页分开；a11y高0／中0，低9项为原始来源URL显示。未运行姿态模型、接摄像头、驱动机械臂、调用语音API或收集真人数据；新英文双格式及导师批准／提交仍未发生。

## 2026-09-26 Razer AVA 式实体形态可行性

- **目标：**回答用户希望把桌面设备做得像Razer AVA、实现会否过于复杂；保留坐姿监测必做和机械臂计划。
- **官方核对：**Razer现行官网与官方结构图确认圆柱罩、5.5英寸“3D hologram”角色、双远场麦克风、HD相机、灯环、底座扬声器、USB-C供电／数据；FAQ说需直连Windows电脑，图中没有机械臂。官方没有公开光学堆栈或Pi独立运行规格；查看官方两张产品图片，未观看完整宣传视频。对照Adafruit Pepper's Ghost对亮度／双影／视角的说明和Looking Glass Go的6英寸光场屏／Mac Apple Silicon条件。
- **分析交付：**[AVA式外观可行性专项](research/2026-09-26-desk-companion/razer-ava-like-feasibility.md)分圆柱小屏、倾斜反射片和现成光场屏三层。建议先做圆柱小屏＋深色罩＋角色表情／口型及灯环；若要求漂浮感再做反射样机，真实多视角显示需光场屏与Mac主机集成验证。姿态摄像头固定，机械臂从侧底座伸出，单外部电源经内部合适支路供电，不能直接假设Mac单口能带Pi／屏／电机。
- **状态与验证：**只完成公开资料研究与工作区规范同步；[QA记录](output/qa/ava-form-factor-2026-09-26/validation.json)核对本地链接和修改文件。未购买、搭建光学原型、实测画面、运行Pi负载或驱动机械臂。中文第二版原稿与Word保持，英文正式提交稿仍未制作／签署／上传。

### 同日补充：AVA式圆柱小屏路线实施草案

- **目标：**把用户所问“第一种怎么做”落到模块、连接、外壳、软件状态、供电和逐步验收，不把推荐候选当实测采购单。
- **官方复核：**Pi5双HDMI／双MIPI与5V／5A、USB外设预算；Waveshare 5.5英寸HDMI AMOLED竖屏及Pi兼容说明；Seeed ReSpeaker XVF3800四麦、AEC、LED环、实体静音、USB／3.5mm输出；Adafruit伺服独立供电；openWakeWord现成框架。当前Pi5操作系统与具体屏幕版本、中文自定唤醒词仍需真实验证。
- **交付：**[A路线详细草案](planning/2026-09-26/ava-cylinder-route-a.md)提出上盖麦阵列／相机、深色外罩与后置AMOLED、底座Pi／扬声器／侧边2–3DOF轻载机械臂；姿态相机可在筒顶和显示器边缘换位。软件拆分本地姿态、角色日历UI、唤醒/Qwen会话、白名单工具与预设臂位。四道早期门槛是光学可见性、相机姿态视野、Pi并行负载／AEC、机械包络与电源。角色和TimeTable在同一小屏切换，不同时塞满。
- **边界／验证：**[本次QA](output/qa/ava-cylinder-route-a-2026-09-26/validation.json)检查当前规范与链接；未生成新DOCX、采购、搭台、测帧率、发语音API或驱动机械臂。中文Proposal第二版保持，英文正式双格式仍未制作／签署／提交。

### 同日补充：AVA光学机制与淘宝风扇／无风扇盒辨别

- **目标：**回应用户纠正“AVA不一定是直接塞屏幕”，解释所附全息风扇和有斜透明片的非风扇盒如何成像，修正本组原先A路线的优先级。
- **已完成：**重新查看IMG_0297的旋转臂图及IMG_0294红盒侧放图的斜片；核Razer官方产品页及新闻稿（5.5英寸display，但无内部光路）、Adafruit Pepper’s Ghost实作（玻璃反射、45°与亚克力双影）、旋转LED风扇公开专利、Looking Glass Go官方光场规格。记录哪些是截图可见、哪些是光学推断、哪些仍未知。[光学辨别报告](research/2026-09-26-desk-companion/ava-optics-fan-vs-reflection.md)。
- **规范修正：**将[形态复核](research/2026-09-26-desk-companion/razer-ava-like-feasibility.md)、[A路线后备草案](planning/2026-09-26/ava-cylinder-route-a.md)、[当前产品规范](product.md)、[交接](handoff.md)和decision-log统一成“先做隐藏屏＋斜反射片的便宜光学台架；直接屏作后备／对照；不宣称AVA内部结构已知”。
- **验证与剩余：**检查本轮文件及内部链接，证据见[本次QA](output/qa/ava-optics-2026-09-26/validation.json)。未购买、联系卖家、拆机、搭建或测试设备；无法从截图认证卖家的屏幕位置和AVA结构。英文Proposal仍需双格式制作并逐页检查；旧中文稿保留。

### 同日补充：全息风扇成熟度再判断

- **目标：**回答用户全息风扇是否成熟，纠正可能过早排除成熟显示模块的工程建议。
- **公开核对：**HYPERVSN官网与知识库的四叶商业设备、HDMI／RTSP、保护罩、停机和M/L噪声；HDFocus 18cm带罩款、Giwox 20cm款、Fursol 18cm款的内容格式与更新方式。证据表明成熟的是预制内容播放和较大商业系统，具体小款的低延迟实时视频输入尚未证实。没有使用淘宝截图价格作采购价或把大机指标外推到小机。
- **交付与修正：**新增[成熟度专项](research/2026-09-26-desk-companion/hologram-fan-maturity.md)，更新[光学辨别](research/2026-09-26-desk-companion/ava-optics-fan-vs-reflection.md)、[形态复核](research/2026-09-26-desk-companion/razer-ava-like-feasibility.md)、product、handoff及decision-log。当前把带罩小风扇纳入与反射像的并列候选；用户未做最终选型。
- **验证与剩余：**[本次QA](output/qa/hologram-fan-maturity-2026-09-26/validation.json)记录阅读范围、来源与内部链接核对。未联系卖家、购买、获取样品、测试噪声／延迟／安全；英文Proposal双格式仍待制作。

### 同日补充：风扇预置视频与即时反馈输入方式

- **目标：**回答小风扇是否只能预置视频、及时反馈是否必须HDMI。
- **证据：**复核HYPERVSN官方Player／HDMI／RTSP模式、HDFocus 18cm文件／App更新和其100–180cm HDMI系列；另见公开厂商手册中App选现有文件的操作。仅确认**相关型号**公开能力，不把人工App动作当开放API。
- **落实：**在[成熟度专项](research/2026-09-26-desk-companion/hologram-fan-maturity.md)加入“预制内容可由实时事件触发，但需Pi可调用切换接口；动态逐帧内容可经HDMI或其他实时渠道”的分层说明；同步product、handoff和decision-log。自动控制、延迟、语音同步均未实测；[本次QA](output/qa/hologram-fan-feedback-2026-09-26/validation.json)。

## 2026-09-28 Group 2团队日志与新桌面Proposal复核

- **目标及澄清：**填写学校双周日志并再检查Proposal。用户确认9月14至27日周期，最新转述老师每组一份；此前个人提交推断已撤回，最终由Yuan代表Group 2，备注列三位成员。
- **开工：**全量读取96份项目Markdown共8742行、43批，截断批次均补读至EOF；记录[阅读清单](output/qa/logsheet-proposal-2026-09-28/reading-record.json)。重核学校日志DOCX、Proposal Guidelines、Guide扫描页和组员身份，Chrome只读课程／作业页获得真实截止及学期节点。
- **文档：**[一页团队日志DOCX](<output/submission/2026-09-28/AY26_Logsheet_Group 2_YuanYuchen_250342840.docx>)／[PDF](<output/submission/2026-09-28/AY26_Logsheet_Group 2_YuanYuchen_250342840.pdf>)完成四块内容；[12页中文v3](<output/docx/Group 2_DeskCompanion_ProjectProposal_ZH_Review_v3.docx>)及[11页英文DOCX](<output/submission/2026-09-28/AY26_ProjectProposal_Group 2.docx>)／[PDF](<output/submission/2026-09-28/AY26_ProjectProposal_Group 2.pdf>)加入相机边界、显示接口、拟议指标、实际学校计划和AI辅助记录。详见[复核说明](planning/2026-09-28/logsheet-and-proposal-review.md)。
- **验证：**日志最终log-render-05为1页；英文proposal-en-render-04为11页；中文proposal-zh-render-05为12页。逐页视觉检查，中文2至4页与已检查render04像素完全一致；所有身份、日期、七项内容、表格和页码核对。学校日志原件SHA256保持9cdca9493e9fabd6a0e671ea6d226f38419d437e7ac0269acc3d8c73500bacb7，成品仅word/document.xml变化。两份proposal的a11y高0／中0，低11为公开来源URL标签。使用打包运行时及局部fontconfig，未安装全局字体。
- **流程同步：**更新product、handoff、README、decision-log、本条work-log和聚焦复核；本轮[QA](output/qa/logsheet-proposal-2026-09-28/validation.json)保存结构、产物、阅读与链接核对。旧提案与学校原件保留，未重跑旧软件测试，也没有新硬件/API测试、采购、外部联系、签名或Moodle提交。
- **剩余：**团队／Marco审阅和学校提交；后续才验证相机、显示、Pi负载及机械臂。日志截止9月28日17:00，Proposal截止9月29日23:59；期限来自本轮页面，不等于已提交。

## 2026-09-28 新桌面助理软件与跨端讨论

- **目标与补充：**梳理软件平台、功能与显示。用户明确手机／电脑控制及设备触摸偏好，角色／日历布局未定；补问是否需要Linux软件，已解释现成OS＋本地全屏界面＋独立后台。
- **全读：**99份自有Markdown、9198行、71批，所有正文至EOF；初始组合截断后补读2／3、decision-log140–220、13和34批，期间无文件变化。[记录](output/qa/desk-software-scope-2026-09-28/reading-record.json)。另读取组员原DOCX正文，不重做旧软件测试。
- **研究：**官方Pi kiosk和Touch Display 2触控／键盘、Capacitor移动原生容器、Flutter平台／Linux构建、FastAPI WebSocket单进程示例、MediaPipe实时及Pi示例、Qwen工具与VAD、PWA安装前提。没有下载安装或执行厂商代码。
- **交付：**[软件范围V1](planning/2026-09-28/desk-software-scope-v1.md)，三端矩阵、7类页面／面板、显示方案对照、核心图、AI职责、同步／离线规则、三条旅程与6阶段开发计划。建议React／Capacitor＋Python本地核心，Flutter保留；一屏验证／二显示候选并存，外网和Android范围未定。
- **验证与同步：**检查Markdown围栏、表格、内链、成员计划及新旧状态；更新product、handoff、README、decision-log和本条工作日志，[QA](output/qa/desk-software-scope-2026-09-28/validation.json)。本轮未改学校文件、未创建新产品工程或运行应用／硬件测试，无采购、API调用、外部消息、上传或签名。
- **唯一下一步：**细化触摸屏／手机首页与电脑日历布局和状态，按反馈再实现；继续保护坐姿判断与反馈复测为必做，不被外观或跨端数量稀释。

### 同日日志修订：三人工作列在同一份内

- **目标：**按老师进一步要求，把一份组日志改成逐人可辨的工作、发现、待完成及下阶段计划；用户授权直接安排角色归属。
- **阅读：**作为同一日志任务的内容纠正，沿用日志制作全读及其后99文件／9198行全读记录，补读当前入口、变更日志、软件新稿、原日志构建器、身份与模板契约；[补读记录](output/qa/logsheet-members-v2-2026-09-28/reading-record.json)。没有机械重读未变历史。
- **交付：**[三人明细DOCX](<output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.docx>)／[PDF](<output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.pdf>)，仍为1页学校横向表。表头三人，正文名字加粗，三个个人行与一行共同工作清楚分开；[脚本](scripts/build_logsheet_member_breakdown_20260928.py)。
- **内容边界：**个人归属按计划职责整理，用户未核实各人原文作者或实作，成品备注保留member-review draft和AI辅助说明；无虚构硬件、语音API或个人独立代码结果。
- **验证：**首轮因姓名／学号强制换行将备注挤到第二页；去除多余换行后render-02为1页，全部实际查看。原节、表格网格、合并、标签与包部件保留，仅word/document.xml改变；6份学校原件／既有交付hash不变。修改入口与内部链接检查见[QA](output/qa/logsheet-members-v2-2026-09-28/validation.json)。
- **剩余：**组员核对本人工作归属；本地修改不等于学校提交。本轮没有改Proposal、软件应用、采购或外部操作。


## 2026-09-28 学校服务器本地语音选型

- **目标：**回应学校可提供服务器的新条件，比较本地语音与第三方API及不同配置；用户确认配置未知、先分档分析。
- **阅读：**100份自有Markdown／9463行完整读取，长批拆段，所有截断区间另补，阅读期间无变化；[阅读记录](output/qa/local-voice-models-2026-09-28/reading-record.json)。未继承旧全读计数冒充本轮阅读。
- **官方研究：**Qwen3-ASR／TTS、Qwen3.5 4B／9B及Qwen3.8 27B模型卡、MiniCPM-o 4.5与官方本地Demo、Step-Audio 2 mini、Qwen3-Omni、CosyVoice3、sherpa-onnx中英唤醒、Silero VAD及vLLM-Omni的TTS／分轮／双工接口；未把公开benchmark、初始化显存或参数量当整机实测。
- **交付：**[服务器与本地语音比较](research/2026-09-28-local-voice/server-deployment-comparison.md)包括具体组件、两条主路线、CPU至多卡分档、API概念、训练／推理区别、设备分工、故障边界和首测计划。建议模块化Qwen为功能主线、MiniCPM-o为自然语音对照，不自动撤销云服务备用顺序。
- **规范：**同步product、handoff、README、软件范围V1和旧云比较入口；追加decision-log。正式学校Proposal／身份文件hash保持，日志未改。新MD内部链接、围栏、语音网络／执行边界和文件存在性核对见[QA](output/qa/local-voice-models-2026-09-28/validation.json)。
- **剩余：**服务器GPU／显存／系统／权限／网络与常驻条件；选型后同任务测试。未登录服务器、下载权重、安装、启动服务、训练、调用收费API或进行真实音频／硬件测试，未联系学校、采购或提交。

### 同日服务器补充：DGX-1／V100兼容性

- 用户初步提供DGX-1／Tesla V100。沿用本任务100文件全读，补读入口、完整比选／软件稿及最新决定；截断尾部补齐，[补读记录](output/qa/dgx-v100-followup-2026-09-28/reading-record.json)。
- 官方核对16／32GB版本、Volta sm_70、CUDA12.x／13差异、PyTorch cu126、vLLM≥7.5和标准FA2支持范围；查Qwen3工具／llama.cpp、TTS FP16选项及Qwen3.5 PyTorch回退。官方DGX规格正文直达失败，只用其官方索引，不伪称实机确认。
- 追加[比选第8节](research/2026-09-28-local-voice/server-deployment-comparison.md)，给1／2张16GB、1张32GB及多卡布局、受限工具／音频边界和只读检查命令。首测文字基线改Qwen3-8B以减少兼容变量，3.5／MiniCPM仍待比较。
- 同步product、handoff、README与软件范围，保留正式Proposal／身份。验证内链、围栏及保护文件hash，[QA](output/qa/dgx-v100-followup-2026-09-28/validation.json)。一次Python更新因输入编码在执行前失败，改用补丁完成，未修改学校文件。没有服务器登录、命令执行、安装、权重下载、GPU／真实语音测试、驱动修改、外部联系或学校提交。

### 同日自然语音偏好：Qwen实时与本地模型的区别

- 用户进一步强调自然交谈；沿用本任务全读和V100补读，读当前入口、完整服务器比选、最新决定／日志及要改区段，[本次阅读记录](output/qa/qwen-natural-voice-2026-09-28/reading-record.json)。
- 官方核对Qwen3.8 Omni型号／声音／语义VAD／工具，新增Qwen-Audio-3.1-Realtime-Plus的smart_turn、语音表现力、工具与价目；技术报告只读摘要，未复现或移植其结果。公开Qwen组织元数据查询返回7项omni、4项audio，未见两款同名开放权重；网页列表读取失败没有被当成零结果。
- [比选新增第9节](research/2026-09-28-local-voice/server-deployment-comparison.md)给出体验优先建议及N01–N08用例；本地8B分段链留作基线，首个体验验证建议3.1 Plus与3.8 Omni对照，非已定收费方案。补清模型原生双工与服务端轮次／打断适配的区别。
- 同步product、handoff、README、软件范围及历史云比较入口，追加决定；[QA](output/qa/qwen-natural-voice-2026-09-28/validation.json)检查链接、围栏、公开元数据和学校文件hash。未试听音频、用API、开通账户、支付、下载权重、连服务器、测试硬件或上传学校文件。

## 2026-09-29 自然语音与工具调用全面复核

- **目标：**补全候选覆盖；不按本地／API筛选；核对第三方真人自然度和工具任务证据，修正此前Qwen聚焦推荐。
- **阅读：**沿用同一语音选型任务100文件全读，重新盘点得到101份自有Markdown／9735行（修改前），补读入口、当前服务器稿、软件范围、历史云比较与最新决定／工作记录。未把新指纹当新全库阅读；[本轮阅读记录](output/qa/voice-ai-broad-review-2026-09-29/reading-record.json)。
- **研究：**官方型号／能力、Qwen3.1和StepAudio3论文相关章节；AA总表／Arena／方法、Jarvis v0.5浏览器可见结果／方法／公开转写，另核Scale旧版测评和FDB-v3适用边界。补入StepAudio3、Seeduplex／SeedRealtime、Grok2.0及开放／组合候选；未把介绍文章当独立复现。
- **交付：**[自然语音与工具复核](research/2026-09-29-voice-ai/naturalness-and-tools-review.md)，包含分维度标准、少量有版本的第三方结果、候选取舍、证据缺口和同任务短测计划。建议Gemini／Realtime完整版／Qwen3.1首轮，不是最终供应商决定。
- **规范与验证：**同步product、handoff、README、软件范围，历史云比较及服务器第9节明确取代关系；追加decision-log。检查相对链接、Markdown围栏、成员身份和6份保护文件hash；[验证结果](output/qa/voice-ai-broad-review-2026-09-29/validation.json)。没有需要重跑的代码或DOCX渲染变更。
- **剩余与状态：**中文实测、工具状态读回、真实麦克风／回声／延迟和实际费用仍待做。没有试听、API调用、付费、录音、模型下载、服务器访问、硬件测试、采购、外部联系或学校提交。

### 同日价格补充

- 用户要求加入价格后给排名；作为同一选型任务补充，沿用全读及刚完成研究，读入口、当前报告、最新决定／日志并盘点102份Markdown。[阅读记录](output/qa/voice-price-followup-2026-09-29/reading-record.json)。
- 完成[性价比报告](research/2026-09-29-voice-ai/price-and-value-ranking.md)：主线仍建议Gemini，低价Qwen Flash提升；Step官方网页确认Realtime Preview限时免费；核对豆包统一费率但保留3.0映射缺口；修正Grok默认server_vad按会话计量及Gemini连续监听的算例。
- 官方token换算与[条件算例](output/qa/voice-price-followup-2026-09-29/calculations.json)区分新增音频、全段输入、历史重算与真实账单。更新product、handoff、README和研究入口，追加决定；[QA](output/qa/voice-price-followup-2026-09-29/validation.json)核对链接、算术及保护文件。
- 未试听或调用API、开通账户／免费试用、付费、录音、远程登录、实测硬件或改学校文档。最终型号和实际每成功任务费用仍待同条件测试。

## 2026-09-29 电子日历Part 1组员需求归档

- **目标：**整理并保存用户转发的组员功能清单；保留原文、区分主要功能与增强建议，与当前桌面设备方案衔接。
- **开工阅读：**独立盘点并全文读取103份自有Markdown、9992行，44批及入口全文，组合截断区间补齐；阅读期间无源文件变化。压缩后沿用同轮记录继续未读部分，没有重启全库阅读。[阅读记录](output/qa/calendar-part1-2026-09-29/reading-record.json)保存文件、范围、排除项、补读与完成时间。
- **交付：**[原始清单](planning/2026-09-29/calendar-part1-teammate-source.md)保留用户转发正文；[功能整理稿](planning/2026-09-29/calendar-part1-functional-scope.md)按视图、录入、共享、同步、纪念日、提醒及AI组织，列13项主要功能、5项建议、1项未定义备份条目，以及三端分工、待细化问题和未执行的验收例子。
- **细节：**分清批量／周期、私人详情／Busy-Free／分享对象、内部同步／外部同步、提前时间／强度／输出端。原文gmail规范为Google Calendar，CalDAV只保留研究候选；没有新增读邮件需求或未经核实的统一兼容承诺。天气地区、农历重复与闰月、分享机制、同步方向、Widget平台及备份方式留待定义。
- **规范同步：**更新product、软件范围V1、README、handoff、decision-log与本日志；旧“天气／农历／共享／同步一律后续”改为当前需求池逐项排期。没有把整理输入写成全数首版必做，持续坐姿判断、反馈和复测保持。handoff下一步转为日历范围与三端页面流程细化。
- **验证：**逐项核对来源覆盖、功能编号、Markdown结构、当前文件链接、三位成员身份及计划比例，保护原Proposal／日志和身份文件哈希；结果记录于[本轮QA](output/qa/calendar-part1-2026-09-29/validation.json)。一次删除／新增同路径的组合patch被工具拒绝且未生效，随后以完整重写handoff及独立补丁完成；没有把失败尝试当作成功。
- **边界与剩余：**本轮仅Markdown整理，无新Word／PDF，因此不重跑其渲染；未改应用代码、运行模型、进行硬件／API测试、联网研究、采购、外部联系或提交。首版范围与若干交互细节未决定，学校文件未吸收此次新清单，语音及硬件候选未重新选定。

## 2026-09-29至30 桌面软件规划与B1本地日历

- **目标：**按用户要求先细化范围、架构和开发顺序，再开始新桌面软件；视觉采用简洁高级风格。
- **开工：**105份自有Markdown、10220行全文完成，[阅读证据](output/qa/desk-development-batch1-2026-09-29/reading-record.json)含清单、区间、排除和完成时间。压缩后沿用同轮进度、补读入口与修改文件；未将指纹当作阅读。保护107项学校／身份／旧代码文件。
- **规划与视觉：**先保存[开发计划](planning/2026-09-29/software-development-plan.md)，对应完整Part 1；ImageGen制作电脑周历／手机Today参考，[设计依据](design/desk-companion/b1/design-spec.md)记录色彩、字体、组件、文案和允许差异。参考并非用户逐页批准。
- **实现：**独立[desk-companion](desk-companion/README.md)，React／TypeScript／Vite与FastAPI／SQLite；本地认证、真实日程持久化、日周月、批量、公历重复和单次例外、冲突、隐私展示、屏内提醒、确认／延后、完成、操作记录和英简切换。记录版本与操作ID，断线／超时／500保留同一请求重试。未连接能力明确显示状态。
- **验证：**后端45项通过，Ruff通过，前端类型与生产构建通过；15组真实浏览器检查，包括丢失HTTP200回执后的刷新恢复及替换为500后的去重。1536×1024、390×844、320×740、1024×600均检查；主预览七条示例与QA数据库分开。启动脚本在占用端口时退出，实际重启后数据／会话保持。[完整QA](output/qa/desk-development-batch1-2026-09-29/verification.md)。
- **发现与修复：**日期输入画面与保存旧值不一致改为正确input事件；离线切日期后同版本恢复会重新获取窗口；手机日期改全宽、checkbox不再继承满宽；窄周视图标题明确截断、可打开详情；错误结果未知时不宣称未保存。
- **工具边界：**IAB业务测试成功，但其移动截图缩放异常；使用Chrome复核响应式显示并保留真实截图。Chrome既有扩展发出警告，应用来源日志为空；临时网络拦截与屏幕大小已恢复。没有用图片编辑生成验证截图。
- **文档与保留：**更新product、范围V1、Part 1路由、开发计划、设计依据、README、handoff、decision-log及本日志；新增启动与字体／图标许可说明。原Proposal／日志／旧Senplate代码和身份原样保留。40／30／30继续是计划份额。
- **剩余与下一步：**开始B2真实相机输入、个人标定、持续判断、提示和复测，随后接Pi／iPhone；自然语音、角色、机械及其余日历增强按计划推进。本轮没有采购、项目语音API调用、真实人体采集、供应商消息、Moodle提交或正式批准。

## 2026-09-30 独立常亮设备界面

- **目标：**用户否定B1设备页面沿用手机／网页；重做适合常亮、远观和触摸的专用画面，同时保留共享日历核心。
- **开工：**109份自有MD／10526行全文、63个分块与截断补读，01:11:50+08:00完成；[阅读记录](output/qa/device-ambient-redesign-2026-09-30/reading-record.json)。本轮压缩后精简恢复，沿用已读范围。
- **规划与实现：**先写[设备规范](planning/2026-09-30/device-display-spec.md)与日夜完整ImageGen参考，新增`src/device/`独立入口、常亮画面、触摸面板、主题／时钟／闲置／唤醒状态与共享API日历连接。原手机／网页仍单独使用App。日历为主未被记作用户已确认选择。
- **验证：**7项前端测试与构建通过；1536×1024／1024×600／720×1280及英简检查，实际UI新增跨时区事项、提醒延后确认、隐私隐藏、退出锁定、断网换日期恢复；81秒草稿保留、普通浏览75秒检查已返回；网页／390px手机回归。真实页面已用view_image对照两张原图。结果及有限差异见[QA](output/qa/device-ambient-redesign-2026-09-30/verification.md)。
- **修复：**日期圈被压扁，小屏提醒导致长标题消失／次要内容被截，周历列宽，国外时区保存后导航，以及月份网格额外未查询周。主应用热更新期间旧错误经最终重载消失；未将扩展警告当本项目错误。
- **保护与清理：**112项哈希不变，主演示7条示例保持；独立QA9条记录／1项已确认提醒留作证据。QA服务与标签关闭，断网／尺寸／唤醒测试设置恢复，主8831／5190预览及内置浏览器设备页保留。后端没有修改，不重跑已通过的B1业务套件。
- **文档：**同步product、handoff、软件范围、开发计划、B1设计说明、README，新增设备设计索引与验证；本决定追加decision-log。学校文件未改变或提交。
- **剩余：**Pi实际常亮／背光／触摸键盘与长期身份未验证；姿态／自然语音／角色／机械仍未接入。下一步B2相机观测契约、个人标定、持续判断及复测。

## 2026-10-02至03｜完成无需用户参与的软件工作

**目标：**用户要求持续完成软件类、无需其参与的工作，不按单批停止。先完成111份自有Markdown／10623行／77块阅读并保存范围记录，跨日沿用同轮；备份新工程源码和主库，核对107项旧代码／学校／身份保护文件。

**实际完成：**在独立desk-companion工程加入姿态标定／质量门槛／持续判断／复测／活动与记录、MediaPipe采集、长期配对、iPhone Keychain、受限助理与确认、Qwen／Gemini实时协议、PCM播放与打断、本地双语唤醒、状态角色与黑底镜像、命名输出与PCA9685／GPIO工作进程；完成天气／农历／公众假期／占用／安静时段，ICS、只读分享、备份恢复和Google只读预览连接；加入同源服务、Linux安装／诊断及iPhone WidgetKit／App Intents／缓存本地通知。

**修复与验证：**84项后端和11项前端检查通过；生产构建、Ruff、iOS本地签名构建通过，npm审计0项已报告漏洞。修复模型运行库、官方框架下载、原生桥与安全区／输入缩放、重采样相位、表单回执字段、发生项审阅日期、缓存隐私、输出停止通道与文件下载。浏览器完成草稿保存、三步合成标定、持续前倾／still_deviated／adjusted、配对、导入、匿名分享／撤销和真实备份下载／恢复；iPhone配对、重启进入、跨午夜及App Group写入已观察。Mac空帧／静音模型与404帧合成评价实际运行。

**文件：**[软件README](desk-companion/README.md)、[安装与操作](desk-companion/docs/operator-guide.md)、[架构](desk-companion/docs/architecture.md)、[评价](desk-companion/docs/evaluation.md)、[本轮QA](output/qa/software-completion-2026-10-02/verification.md)。同步product、handoff、decision-log、当前完成计划与常亮规范；旧开发计划标为HISTORICAL，学校双格式和旧食品项目不改。

**保留与运行：**主库仍7条原有sample。主8831／5190启动并留本地预览；QA8832／5191独立，iPhone模拟器使用其测试数据。未提交Git／学校文件、未采购／对外联系、未录真人、未调用付费语音或移动电机。模型／协议／模拟器结果不构成Pi、真实姿态、自然声音或机械准确率。

**剩余：**实际硬件／账号／许可／标签后的集成与测量；下一步为真实闭环联调，详见handoff。三位学生实际贡献仍需成员审查补充，不把本轮AI辅助产物直接归为三人完成。

## 2026-10-03｜Your dot主动事务跟进研究

- **目标与澄清：**回答本组AI能否像新推出的Dot持续跟踪事务；用户已确认所指为Codex／ChatGPT中的Your dot。
- **开工：**116份项目Markdown／10988行、180分块完整读取；补读decision-log 96–268及多场景稿27–34的截断。2026-10-03 02:29:00+08:00完成，期间文件未变，[阅读证据](output/qa/2026-10-03-dot-feasibility/reading-record.json)。生成式SPM README额外纳入，未遗漏项目规范；依赖／缓存及QA自动证据排除。
- **证据：**OpenAI官方Meet dots、Tasks and memory、9月28日至10月2日更新实际获取；核对当前Store、assistant、app生命周期、Runtime、语音和Google连接范围。未把官方产品说明当本组性能或API接入证明。
- **交付：**[主动事务跟进可行性](research/2026-10-03-dot/proactive-task-tracking.md)，包含跨日报告示例、自动化分层、已有／缺少模块、事件与持久调度、模型及成本安排、三端显示和拟议评价。方案为建议，不是已实现功能；此前S1–S10完成口径保持其原范围。
- **同步与核对：**更新product、handoff、README、decision-log和本日志；较早整机／日历需求稿补充当前路由，防止恢复到B1待开发状态。本轮QA核对文件链接、成员资料及145项代码／学校／身份文件保留；无源码改动，因此不重跑既有业务测试或DOCX渲染。
- **边界与剩余：**没有创建自动化、开启用户事务监控、连接邮箱、获取新个人数据、调用收费模型、访问DGX、移动机械臂、对外发消息或提交学校文件。通用任务状态、跟进工作进程和跨会话记忆尚待开发；首版验收契约是后续软件起点，真实硬件／服务验证继续保留。

## 2026-10-03｜主动事务增强与UI／UX代码审查

- **目标：**承接Dot研究，按用户顺序先增强软件，再审查交互逻辑并落实修复。沿用同轮117份阅读覆盖，补读相关新旧代码与规范；先备份源码和隔离数据库，重启主服务前另备份主SQLite。
- **实现：**任务／进展依据／持久检查、状态与步骤、用户确认完成、暂停延后、跟进复查、Qwen／Gemini可选文字协议和背景建议限额、语音共用工具、Tasks／Today／常亮面板、备份合并与暂停恢复。
- **UI／UX修复：**日期值丢失、输入与偏好退出保护、并发冲突加载当前版、真实步骤控件和超限不截断、草稿可审阅性、处理中输入、读取断连与未知写入分开、历史刷新、设备私人投影、窄屏／中文日期、记录来源和周期事项范围文案。
- **验证：**101项后端、11项前端、Ruff／生产与iPhone模拟器构建通过；实际UI覆盖创建进展到完成恢复、草稿确认、跨端冲突、计划检查、断连重连、英简、320px手机与1024×600日夜设备。模拟器进入事务列表及详情，保持既有配对。
- **证据：**[QA](output/qa/task-enhancement-ux-2026-10-03/verification.md)、[契约](desk-companion/docs/task-tracking.md)、[执行计划](planning/2026-10-03-task-enhancement.md)。入口、架构、操作、历史路由、product、decision-log和handoff已同步；源码包放output/software，运行数据不进入交付。
- **保留：**107项学校／身份／旧Senplate文件不变；主7条事件内容哈希不变。测试事务只在隔离QA库；未调用付费服务、采集真人、启动真实硬件、登录DGX、发送外部消息、发布或提交学校。
- **剩余：**真实服务／硬件／标签条件后的闭环与性能验证。事务自动化不含邮箱／全电脑监控或远程锁屏推送，本轮不作自然AI质量结论。

## 2026-10-05｜全项目 GitHub 协作仓库与完整远端核验

- **目标：**按用户要求建立暂名FYP的新仓库，将所有项目工作集中上传，并提供邀请组员与协作方法。
- **开工：**119份项目自有Markdown / 11,237行 / 51批全文读取，无阅读期间变化；新复制的组员原始Markdown全读并核对字节。压缩后沿用本轮范围，不重启全库阅读。[阅读记录](output/qa/2026-10-05-github-bootstrap/reading-record.json)。
- **准备完成：**当前 / 退役工程、学校各版、需求、研究、采购、设计、品牌及QA全部纳入；从Downloads补14份明确附件，原件保留。新增[协作说明](CONTRIBUTING.md)、输入来源清单与精确Gitleaks误报配置，更新README / product / 软件启动路径。
- **验证：**Gitleaks目录与待提交扫描通过；104初始告警均核对为校验值 / 公开编号 / 存储键。另将13个已知私有配置值与所有文件 / 归档内容对比，发现两份二进制iOS记录含本机测试密码，备份原件后只替换密码；清理后无匹配。107项学校 / 身份 / 旧代码哈希未变、14份附件一致、9个源码 / 品牌ZIP无私有运行文件，无超限文件或剩余软链接。151条当前本地链接通过。没有应用代码或学校正文变更，不重跑旧业务测试 / 渲染。
- **Git及远端：**首次提交 `fc5c7c9`，6,003文件。CLI GraphQL / REST新建被令牌权限拒绝，改用登录Chrome建立 [tantalum666/FYP](https://github.com/tantalum666/FYP)，确认Private。早期HTTPS推送403，现有SSH / OS凭据也未能认证。用户明确同意仅加入FYP并自行完成邮箱验证后，保留其余设置保存该范围；HTTPS全项目推送成功，main跟踪origin/main。首次远端6,005路径及所有类型 / 模式 / Git内容哈希完全一致，默认main且Private。
- **收尾：**同步product / README / handoff / decision-log / 本日志及[本轮QA](output/qa/2026-10-05-github-bootstrap/verification.md)，收尾材料同样提交推送，最后回读HEAD及全文件树；[远端核验脚本](output/qa/2026-10-05-github-bootstrap/verify_remote.py)。只有现有令牌范围增加FYP，没有新令牌或SSH密钥注册、成员邀请、应用发布、学校提交或外部消息。邀请和组员本机环境由相应人员按协作说明完成。

## 2026-10-05｜RIG-Arm二次开发与自有AI对接研究

- **目标：**按Marco建议与用户链接，核对能否购买现成机械臂、更换小智所用AI，以及可改的软硬件层次；不提前锁定新硬件或修改正式Proposal。
- **开工：**122份项目自有MD／11,376行／36批全读，截断处补读；期间无文件变化，15:31:24+08:00完成。[范围记录](output/qa/2026-10-05-rig-arm-feasibility/reading-record.json)。压缩只恢复入口、当前决定和聚焦文件，继续原轮范围。
- **研究：**Chrome实际读取MakerWorld／整机商城／官方Arm开发、MCP、版本、下载与原理图索引；只读缓存rig_omni c2b42cd及rig_local 486500a，追踪Arm工具／IK／舵机反馈、local HTTP MCP构建与启动、文字工具回填和音频协议。确认套件109美元／整机124美元及预售；更新“原理图仍待发布”的旧评论印象为已有9月22日PDF入口。官方装配视频仅定位链接，未整段观看。
- **交付：**[评估](research/2026-10-05-rig-arm/secondary-development-review.md)、[来源表](research/2026-10-05-rig-arm/source-register.json)，区分更换文字LLM、完整实时语音、外部AI控制RIG／RIG调用本组工具、本地控制器与主机、动作接受／到位、两个分支示教／微动差异及代码／模型许可。采购前问题仅在文档列出，未发送。
- **同步与验证：**更新product、README、架构、操作、决定与当前handoff；[QA](output/qa/2026-10-05-rig-arm-feasibility/verification.md)记录源码静态证据、网页转录与截图、JSON／本地链接／组号／保护hash。应用源码和学校DOCX／PDF未改，不重跑既有业务测试或文档渲染。研究分支codex/rig-arm-research已推送并核对远端ref／tree，登录Chrome建立[Draft PR #1](https://github.com/tantalum666/FYP/pull/1)，页面确认保存且附加当前聊天；CLI的PR权限不足未扩权，也没有合并main。
- **剩余：**实际SKU／板型／固件／MCP入口、原装供电、负载、动作完成／取消／失联与台架；RIG输出驱动和重用设备音频仍未实现，固定姿态相机与独立大屏继续保留。没有采购、模型收费调用、厂商源码执行／编译、刷机、机械动作、外部联系、代签或学校提交；不把AI辅助研究当学生实际贡献成绩。

## 2026-10-06｜个人 AI Agent 讨论归档与 GitHub 交接

- **目标：**按用户要求先把本轮讨论推到GitHub，明确个人Agent必须具备真实、受限的电脑／软件操作，并保留固定姿态闭环和已有日历／任务基础。
- **阅读：**沿用本次讨论前已完成的main固定SHA阅读报告：122份项目／历史Markdown及13份QA；本阶段重新读取AGENTS、product、handoff和相关软件规范／新近日志，核对关键调度／语音源码。历史完整逐文件阅读清单本阶段未取得，因此本轮QA明确区分继承报告、实际补读与盘点，不伪造新全读或本地测试。
- **交付：**[完整讨论与下一步](planning/2026-10-06/personal-agent-discussion-and-next-steps.md)包含要求／建议／实现／未验证区分、统一助理架构、异步任务与确认恢复、LCU候选和许可／权限、电脑操作证明矩阵、当前语音型号、RIG／Pi／屏幕／可拆卸清洁概念、角色分工与验收计划。
- **同步：**更新product、handoff、根README、软件README、架构路由，追加decision-log与本日志；既有RIG研究PR #1仅引用，保持未合并。本轮从main `5b8ce5b81dd075cae3cef6787c964bf0406591e2` 建立 `codex/personal-agent-plan-20261006`。
- **验证：**核对文档相对链接、来源、当前／计划状态、术语与分支基线；逐文件Git blob生成文档提交并回读远端内容／树。结果见[本轮QA](output/qa/2026-10-06-personal-agent-plan/verification.md)。没有运行应用测试、API自然度测试、硬件或安装；101／11项仅引用历史结果。
- **剩余：**P0／P1最小电脑任务和强制权限边界、小范围独立读回验证；随后持久任务／长工具与语音集成。真实硬件、台架安全、目标区域／模型及实际费用仍待确认。学校原件／身份／历史源码保持，不把AI整理归为三人实际完成贡献。

## 2026-10-09｜Dot远端整合、代码审查与本地验证

- **目标：**按用户要求检查GitHub的Dot工作、直接修复问题并合并应用。远端讨论`597cfe7`、代码`ba2b164`均未进main；本地RIG研究`085dc01`保留，一起整合。
- **阅读：**[本轮记录](output/qa/2026-10-09-dot-integration/reading-record.json)完整读取123份本地Markdown；19份远端变化版本的全部新增／替换正文另读，只有本轮已实际读过且逐行完全相同的文本继承范围。142个文件版本／15,358行覆盖验证，原文件阅读期间未变；压缩沿用记录。
- **修复：**四份根文档冲突保留两边记录。语音重复ID拒绝回复误记送达，导致断连漏清理迟到草稿；两项回归先失败后通过。同步作业容量提示、安装说明和当前／历史状态。
- **验证：**149后端、15前端、Ruff、TypeScript／Vite通过。实际界面准备→批准→63字节双语文件与独立哈希一致；取消前无文件、篡改后unknown且只读不覆盖、恢复后核验成功；HTTP200回复丢失后相同操作去重且保留新草稿；关闭保护、1280×800英文／320×740简中／1024×600独立常亮检查。测试选择器和CDP模式限制已处理并清除拦截／尺寸覆盖，未把首次失败当成功。
- **证据与文件：**[核验记录](output/qa/2026-10-09-dot-integration/verification.md)、新回归测试和语音调度修改；product、两个README、架构／操作／作业说明、两份云端历史路由、决定和handoff同步。旧学校／身份／Senplate保护项与正式文件保持。
- **实际合并与应用：**[整合PR #2](https://github.com/tantalum666/FYP/pull/2)已按审查head `9bbd6d3`合并，main软件提交`8ca728d`；RIG PR #1随祖先提交纳入后已标为合并。本地main快进、8831／5190主预览启动，实际原拥有者登录与新面板通过，四工作循环ready，七条日程内容hash保持，主库零测试作业且执行默认关闭。隔离QA服务已停止。收尾文档与证据随后提交；应用源码与已测试整合版本一致。无真实模型、LCU／系统权限、硬件动作、邀请、采购或学校提交；真实应用执行等缺口保持。

## 2026-10-14｜拥有者记忆与模型上下文

- **目标：**让 Desk Companion 更接近 Muse／Dot 式个人代理。main 已有批准后的笔记作业；本步补上可更正的长期记忆，并保持重大写入必须由拥有者确认。
- **完成：**`desk/memory.py`、`desk/context.py`、助理草稿工具、英文／简体中文记忆页。[契约](desk-companion/docs/memory.md)。删除的事实不进入打包上下文；配对屏不能读记忆接口。
- **验证：**`uv run --no-sync pytest -q` 152 通过；`ruff check backend scripts tests` 通过；前端 `npm test` 15 通过，`tsc --noEmit` 通过。没有付费模型，没有浏览器点击记忆页，没有商业客户端逆向。
- **剩余：**指定一个测试应用或目录，沿现有作业契约做批准、独立读回和取消。其后才是人格文件、跟进静音和有花费上限的供应商试用。PR #4／#5 仍未合并。

## 2026-10-14｜指定文件夹作业

- **目标：**在现有电脑作业上增加一个拥有者命名的文件夹动作。批准全文、独立读回、取消。不平行再做一套队列，也不改动 PR #7 的记忆提交。
- **完成：**`FolderDropExecutor` 与 `JobService` 按动作选择执行器。拥有者接口保存一个绝对真实目录。作业绑定名称和路径指纹，不保存路径。界面有英文和简体中文。[契约](desk-companion/docs/computer-jobs.md)。
- **验证：**`uv run --no-sync pytest -q` 162 通过；`ruff check backend scripts tests` 通过；前端 `npm test` 16 通过，`tsc --noEmit` 通过。记录见 [QA](output/qa/2026-10-14-folder-job/reading-record.md)。没有付费模型，没有浏览器点击新表单，没有商业客户端逆向。
- **剩余：**文字和语音共用一份人格文本，然后才是单独调低跟进。PR #4／#5／#7 仍未合并。

## 2026-10-14｜共用人格文本

- **目标：**文字规划和语音会话使用同一份拥有者可编辑的人格，而不是两处硬编码说明。
- **完成：**`desk/persona.py` 保存正文和版本。三个通道先放正文，再附上各自的工具协议。界面有英文和简体中文的人格页。
- **验证：**`uv run --no-sync pytest -q` 165 通过；`ruff check backend scripts tests` 通过；前端 `npm test` 16 通过，`tsc --noEmit` 通过。没有付费模型，没有浏览器点击人格页。
- **剩余：**已经排队的可选文字建议，在事务关闭跟进后仍可能发给模型。PR #4／#5／#7／#8 仍未合并。

## 2026-10-14｜关闭跟进后跳过文字建议

- **目标：**跟进可以单独关掉，而不删除事务；已经排队的可选文字建议也不再发给模型。
- **完成：**`TextAssistant.enrich_one` 在 `follow_up_enabled` 为假时把该条建议标为 skipped。正常的事务更新仍会结束待处理跟进。
- **验证：**`uv run --no-sync pytest -q` 167 通过；`ruff check backend scripts tests` 通过。没有付费模型。
- **剩余：**有花费上限之前不比较托管供应商。通用应用执行仍未做。PR #4／#5／#7／#8／#9 仍未合并。

## 2026-10-14｜安静时段与限流跟进

- **目标：**跟进可以提醒，但安静时段不刷屏，长时间离开后也不一次弹出全部到期事务。
- **完成：**`quiet_until` 计算安静时段结束。`tasks.tick` 在时段内改期，平时每次最多新建 3 条。`enrich_one` 在安静时段不调用模型。
- **验证：**相关任务与安静时段测试通过；其后跑完整后端和 Ruff。没有付费模型。
- **剩余：**电脑作业的取消、读回和指纹失败在界面上还不够清楚。PR #4／#5／#7／#8／#9／#10 仍未合并。

## 2026-10-14｜作业卡片的可恢复说明

- **目标：**笔记和文件夹作业在取消、读回失败或路径指纹变化时，界面写出原因和下一步。
- **完成：**`readBackCopy` 与 `recoveryCopy`。文件夹卡片显示绑定指纹前 12 位。
- **验证：**前端作业测试 6 项通过，`tsc --noEmit` 通过。没有付费模型。
- **剩余：**文字模型调用还没有可替换适配器。PR #4／#5／#7／#8／#9／#10 仍未合并。

## 2026-10-14｜文字适配器与作业绑定表

- **目标：**Qwen 和 Gemini 可以按配置替换，以后的有边界应用动作可以挂到同一套作业上。
- **完成：**`text_providers.py` 两个适配器。`JobService._bindings` 登记笔记和文件夹。
- **验证：**`pytest -q` 173 通过，Ruff 通过。没有付费模型。
- **剩余：**有花费上限之前不比较托管供应商。通用应用执行仍未做。PR #4／#5／#7／#8／#9／#10 仍未合并。

## 2026-10-14｜安静时段偏好与合并顺序

- **目标：**已保存的安静时段在重启和修改之后仍然约束跟进；给组员一份 PR #6–#13 的合并顺序。
- **完成：**`task_quiet_holds`。改短或关掉安静时段后按新偏好调度。指定检查和延后不会被提前。合并顺序见 `planning/2026-10-14/pr-stack-merge-order.md`。作业卡片的新文案锁定英文和简体中文，批准截止时间跟随界面语言。
- **验证：**`pytest -q` 175 通过，Ruff 通过。前端 `npm test` 17 通过，`tsc --noEmit` 通过。没有付费模型。
- **剩余：**有花费上限之前不比较托管供应商。通用应用执行仍未做。PR #4／#5 与 #6–#13 仍未合并。

## 2026-10-14｜Review for Codex merge

- **Goal:** Review PRs #6–#14 for maintainability, bugs, folder-path safety, tests, and merge readiness. Leave English merge instructions for Codex. Do not merge.
- **Done:** PR #6 docs no longer say to extend PR #5. `planning/2026-10-14/pr-stack-merge-order.md` is the English merge procedure, including #14. PR bodies carry the same procedure.
- **Checks:** Tip already had pytest 175, Ruff, frontend 17 tests, and typecheck green. This pass changed docs and PR text only.
- **Left:** Codex merges in the written order. No spend cap, so no provider trial. No unrestricted app control. PRs #4 and #5 stay unmerged.

## 2026-10-15 Git工作独立审查、修复和合并

- **目标：**按用户要求检查Grok bot工作并在验证后合并。完整恢复148份自有Markdown／13,432行；补读32个远端文档版本的全部不同正文，完全相同文本才继承本轮范围。旧角色分支保持。
- **发现与修复：**配对终端可经助理访问／确认记忆；目录校验与打开之间的上级链接变化可改向；人格重置复用版本；失败覆盖草稿。回归先失败后通过。追加拥有者边界、逐级目录句柄、持久递增版本及明确加载／安全重试；修复已有source-map-js 1.2.1告警。
- **验证：**原始175后端／17前端通过但未覆盖上述缺口；修复后的实际main代码`2c1e465`为182后端／17前端、Ruff、类型、生产构建与npm审计零发现。保留一条Starlette上游弃用提示。浏览器实际保存更正、双端人格冲突、HTTP200回执丢失后原操作恢复、审批前零文件与审批后27字节／SHA256读回一致；390×844简中无横向溢出。
- **Git：**PR #7至#14已按依赖顺序合并，修复回推到对应分支，普通merge保留祖先；[PR #6](https://github.com/tantalum666/FYP/pull/6)承载公开研究的状态纠正、规范同步及本轮QA。原PR #4／#5保持开放另线，未强推或改原A1分支。
- **规范／证据：**同步product、handoff、两个README、架构、记忆／作业／操作、协作和历史合并路线；重写三份tooling文档中过期的实现／下一步。证据、逐文件阅读范围、日志、截图和代码合并回执见[QA](output/qa/2026-10-15-grok-review-merge/verification.md)。
- **保留与剩余：**原学校／角色文件和私人运行区保持。隔离测试服务、两标签、拦截与尺寸覆盖均清理。无真实模型、音视频、硬件、部署、采购或学校提交；下一步为一个明确真实应用任务与允许范围，然后沿同一作业契约验证。

## 2026-10-23｜Xu Ziqian硬件进度与最新图册协作上传

- **目标：**上传当前硬件工作到团队GitHub，明确不部署、由组员统一部署。用户已确认仓库并允许仅核对本次相关文档，不声称完成132份全库阅读。
- **资料整理：**[硬件进度](research/2026-10-23-mini-robot-hardware/README.md)记录固定主机、luwu rig arm、具体亚博屏幕、学校Pi 5/已有microSD、单电池免焊Mini、自动回座无线充电、15–20分钟及HK$2,000目标。保留软件既有成果和职责，不归作硬件成员贡献。
- **交付：**原样复制最新9页/13实物图/30链接PDF；13项去本机绝对路径来源、22行完整性表、采购前验证顺序与软硬件协作需求。轮马达/轮胎/支架/万向球/六针线全部可见，D6现货转接链等缺口明确保留。
- **核验范围：**文件存在性/哈希、JSON与数量、引用路径、PDF复制一致性、敏感路径排查、远端tree/分支/PR差异；本次未重生成PDF或改代码，因此不重跑软件测试、旧PDF渲染或固件。具体检查见[本轮QA](output/qa/2026-10-23-hardware-progress-upload/verification.md)。
- **限制与剩余：**无新采购、实机/续航/桌边/充电测试；成品接口、电池/风机/Qi供电、结构及完整HK$2,000BOM仍待闭合。旧V3和后续裸驱动简图是历史候选，不作为本版装配承诺。部署与软件集成留给相应组员，本次不启动服务、刷写、合并或部署。

## 2026-10-26 硬件PR #17审查与修订

- 完整读取本轮仓库Markdown及PR新增版本，逐页渲染查看图册9页，核对13来源、22完整性项、原件哈希及US$76.89小计。
- 修复Pi事实覆盖、设计目标归属、9mm轴长和新加坡价格币种，补齐受限控制契约；PDF原件及软件源码保持。
- [审查证据](output/qa/2026-10-26-repo-cleanup/pr17-review.md)记录本地检查与无远端CI的限制。先推回原分支，按实际审查head合并；后续进行Senplate归档。

## 2026-10-26 仓库归档、硬件PR审查及运行验证

- **目标：**集中归档退役Senplate，检查组员PR并修复合并。
- **完成：**全量阅读176文件版本／16,752行；PR #17原PDF全部9页检查，修复Pi归属、设计目标表述、电机轴长、报价币种和控制契约，按审查头合并为`4417e3656959bd3deb7e0d42a2e42654723dfba4`。远端确认merged。
- **归档：**5,127个文件迁到[统一目录](archive/senplate/README.md)，维护[原路径与SHA清单](archive/senplate/archive-manifest.json)；食品历史日志与旧产品资料归档，学校原件／桌面Proposal／Log sheet继续保留。成员身份及份额未改，食品专属字段保存在原始快照。
- **修复：**新深层路径的PostgreSQL socket限制改为loopback TCP；两前端Vite升级8.3.5，归档source-map-js为1.2.2。修复导航与本机凭据的链接表达。
- **验证：**当前182后端／17前端、归档55后端、两前端类型／构建、两套Ruff通过；npm audit均零报告。隔离新建PostgreSQL，不复用旧演示库；无模型API／真实音视频／硬件或部署。完整记录见[QA](output/qa/2026-10-26-repo-cleanup/verification.md)。
- **保留与剩余：**原主检出及最新AliceChan／统一Omni本地工作区保留；PR #4／#5／#15／#16仍待单独按当前方向审查。整理分支已通过文件／运行校验，经[PR #18](https://github.com/tantalum666/FYP/pull/18)交付；具体Git回执以整理QA和远端PR状态为准。

## 2026-10-28 · AI task context and maintainable software checkpoint

Goal: continue software/AI independently with maintainable structure and publish an important, verified milestone. Startup used the owner's new focused-reading rule; AGENTS now records that rule and publication expectations.

Delivered a dedicated phone composition with separate home/plan/management/data/environment modules and shared web/phone login, session recovery and calendar editing. Added coalesced/scoped calendar reads, late editor-read protection, progress-note tab guards and visible modal notices. Fixed the unified conversation's missing selected-task ID, including server lookup, owner/task replay binding, current-version refresh and explicit-input-only reconnection.

Local integrated source passed303backend/65frontend checks, Ruff and TypeScript/Vite; actual browser flows and independent readback passed. Controlled session expiry retained exact unsent drafts in web and phone, and a delayed response did not reopen a closed editor. The current iPhone17Pro/iOS26.5 build was installed/launched and its real frame inspected. Native touch/keyboard and real media/device measurements remain open.

Built the publication checkout from main46ac167 at`/Users/tantalum/.codex/worktrees/software-ai-maintenance/FYP`, branch`codex/software-ai-maintenance-20261028`. Preserved the archive, the older dirty source and private backups, retained Vite8.3.5, and added CI with models/executors disabled. Distributed model assets retain their source/licence metadata; personal authoring originals and omitted historical raw QA stay local.

Current contract:[software-maintenance](desk-companion/docs/software-maintenance.md). Evidence:[QA](output/qa/2026-10-28-maintainable-ai/verification.md). Publication checks/readback are finalized there and in handoff. No new model charges, microphone/camera/user-screen sharing, Pi/Luwu action or school report change/submission.

Publication readback: pushed code commit71e4bd8a76533cb4a734dbf04e89f158432ed303 and opened[PR #60](https://github.com/tantalum666/FYP/pull/60) as a draft. Remote branch/head match; PR was mergeable and unmerged. Hosted CI did not execute because GitHub refused runner admission at the account level; local303/65 checks remain the actual test evidence. No account setting was changed. Final documentation records this boundary; the next software acceptance gate is native touch/keyboard and draft recovery.

## 2026-10-28 · Review and integrate Grok PRs20–59 with #60

**Goal:** inspect Grok's work, repair blockers and perform the owner-authorized merge while preserving current Alice/mobile/Omni behavior and maintainability.

**Completed locally:** captured all40 Grok heads plus#60; resolved the three dependency stacks on an isolated candidate; reviewed196 authoritative source items with an independent architecture pass; reproduced and repaired permission, context/cache, imported-job/folder, SSE recovery, omitted-field and cross-stack failures. Shared modules and the original job queue remain; no new global transcript table or second voice model loop. The separate pre-fix review checkout and prior dirty work are preserved.

**Validation:**450 backend/89 frontend, Ruff/types/build; real1365×900 web and390×844 phone UI. Controlled principal downgrade removes private chat/diagnostics. Stream EOF retains the operation key; recovery produces one draft with zero approved facts, clears matching error/input and labels the result correctly. Preview-session expiry preserves unsent text and next send works. Phone calendar save appears on web; Alice and Plan/More remain; alias edits are guarded. No native Simulator reinstall or hardware/live-model result is claimed.

**Files:** [QA](output/qa/2026-10-28-grok-review-merge/verification.md), [reading record](output/qa/2026-10-28-grok-review-merge/reading-record.json), [publication receipt](output/qa/2026-10-28-grok-review-merge/publication.json), updated root entry/handoff/product/decision and affected software contracts. Historical merge/report notes are explicitly marked.

**Pending at this entry:** final publication and exact-head GitHub merge/readback. Hosted-CI account restrictions remain separate. After receipt closeout, resume the native Plan→New→Save→Back/keyboard validation gate; Pi and prior API budgets stay paused/closed.

### GitHub receipt closeout — same task

[PR61](https://github.com/tantalum666/FYP/pull/61) is merged: reviewed head `923a1e2a53f79d432db0ba0bf31f6c216f5e292c`, main merge `c2037cda480fde7448dbfbfc4ea9aac2e4086ba8`,2026-10-28T06:14:19Z. All41 original PRs20–60 were individually read back as merged. Twenty-six stacked bases were retargeted to main and#60 marked ready, preserving source heads/ancestry; no force-push or unrelated PR merge. Remaining open PRs are4/5/15/16/19. The fix checkout fast-forwarded to the software merge; this closeout changes records only.

The exact-head Actions run40642113382 returned failure annotations saying both jobs never started due to account payment/spending limits. Local450/89 checks passed. No account or branch-protection setting changed. Current next product gate is native Plan/new/save/back and keyboard recovery; the software/source merge is complete.

## 2026-10-28 · 撤除CI，明确本地验收

用户再次明确不用CI。移除唯一的当前工作流，更新AGENTS／product／CONTRIBUTING／README／START_HERE／维护规范和精简handoff，取消“CI账户问题”待办。本机Actions管理API无相应权限，因此通过仓库源码删除工作流实现，不扩大令牌权限。

本轮只改工作流配置和文档，核对应用文件哈希、工作流清单、差异空白与内部链接，不重复运行未受影响的450／89项应用测试。450／89是上轮修复后成绩，并非Grok原始交付直接通过。阅读和验证见[本轮QA](output/qa/2026-10-28-local-validation-only/verification.md)。

## 2026-10-28 · Older-memory continuity and current native build

**Goal:** continue AI/software toward real delivery, starting from the open native phone gate and long-term assistant reliability. Startup used focused Markdown reading; exact scope is recorded in[reading record](output/qa/2026-10-28-native-memory/reading-record.json).

**Implemented:** one model-safe active-fact projection, complete active-memory query/draft/exact-forget access, whole-memory revision invalidation while keeping40 prompt/8 query result limits. SharedMemoryFactList handles web/phone local search and rendering; MemoryPanel keeps requests, versions and unsaved guards. Correction cannot be replaced by search/another row; save/error feedback is adjacent and prior wording separates cleanly. No new dependency, queue, model adapter or transcript store.

**Validation:** original source failed8 of9 meaningful regressions; repaired source passes43 related and459 full backend tests,89 frontend tests, Ruff and type/Vite build. Real1365×900 web and393×852/320×740 phone browser checked42-fact English/Chinese search, empty/clear, correction, navigation/return guards and independent API/current recall readback. Phone Plan→New→Save→Back passed in browser. The current source passed pinned native framework checks, Capacitor sync and fresh Simulator build/install/launch. Its actual Alice frame showed the browser-created event through native API reads. Native touch/soft keyboard remains open because mirror/native input automation did not produce a reliable app transition; no native pass is claimed.

**Files and next step:**[QA](output/qa/2026-10-28-native-memory/verification.md), updated memory/Omni/maintenance/phone contracts, product/readmes/entry/handoff/decisions and[delivery gates](desk-companion/docs/delivery-readiness.md). Next is one task → approved bounded job → independently verified result → phone continuation with lost acknowledgement/restart. Older runtimes/worktrees and school originals are preserved.

**Boundaries:** all checks local; no CI, hosted calls, live media, external accounts or Pi/Luwu. Qwen remains a baseline, alternatives stay open. Important progress is published on a separate branch/PR after diff/secret/evidence checks; exact publication readback is recorded separately, not treated as main merge/deployment.

Publication readback: code commit`1c6c589607eb3c61e7ef0b03531d2deb50705488` pushed to`codex/native-memory-reliability-20261028`;[draft PR64](https://github.com/tantalum666/FYP/pull/64) opened and attached. GitHub returned the matching head/base. The PR remains unmerged; this receipt closeout changes documentation only.

## 2026-10-29 · Task continuity and shared assistant permissions

**Goal and steering:** continue the task→file→phone acceptance journey, then incorporate the owner's explicit request for conversational approvals, optional Full access and consistent web/application UX. The task was continued through compaction; earlier completed checks were retained.

**Completed:** task-scoped local file commands; TaskJobs results and current revision refresh; fresh terminal-task read-only verification; shared ProposalActionCard/JobActionCard and requests; full-screen PhoneScreen navigation with draft guards; shared composer/settings permissions backed by owner-only PermissionService. Automatic policy is separate from the model, tied to fresh authenticated requests and checked on application/dispatch. It records truthful provenance and permits revocation independent of unknown business writes. Existing queues/services/context boundaries remain.

**Repairs found by verification:** English/Chinese editor-preview task scope; confirmation crash recovery after a real committed effect; stale-policy/replayed pending action boundaries; forgotten old request text entering new RAM context; narrow-screen long title touching the discussion-end button. A content-free retired-request marker in the existing operations ledger fixes the last memory regression without adding a transcript store.

**Evidence:**489 backend,89 frontend,31 final focused memory/permission/conversation checks, Ruff, frontend format and TypeScript/Vite. Actual web and phone task/file approval, independent SHA/mtime readback, real API restart and lost-response recovery, phone verification/cancel/progress/manual completion; new inline once/full actions and recovery preserve unsent text. Current source synced/prepared/built/installed/launched on the pinned iPhone17Pro/iOS26.5. Live frame shows newAsk first control; fresh mirror tap still did not navigate, so native touch/keyboard remains open. The incorrect configuration-helper path in one build command was corrected before final successful native build.

**Files:**[current QA](output/qa/2026-10-29-assistant-permissions/verification.md), [earlier business journey](output/qa/2026-10-28-task-journey/reading-record.json), [permission contract](desk-companion/docs/assistant-permissions.md), affected software/docs/readmes/design/entry/handoff. School deliverables unchanged. Older8832/5191 processes stopped after checking ownership; their data preserved. Current preview8833/5190 uses fictional data, providersnone, fixed-note executor only and finalAsk mode/version5.

**Publication:** scoped draft [PR65](https://github.com/tantalum666/FYP/pull/65) opened on PR64; implementation commit `4c6b8911ae19862a44b9d68450aaed4f2615ccdb` matches GitHub and git remote. [Receipt](output/qa/2026-10-29-assistant-permissions/publication.json). Both remain unmerged. **Remaining:** next implementation slice is one mixed-action task with partial-success/revocation/restart semantics using offline providers. Local checks only, no CI; no paid models/media/external accounts/Pi/Luwu or school submission.

## 2026-10-29 · Bounded OpenAI Realtime and GPT-Live evaluation

**Goal:** compare both real-time voice products using the newly authorized OpenAI credit cautiously. The owner clarified both are real-time, completed Platform reconnection/project selection and explicitly approved the local ignored key destination. No plaintext key was exposed or committed.

**Implemented:** separate paid-evaluation runner with atomic persistent reservations, closed-round refusal, conservative unknown usage, response/session/output bounds and no retry/reconnect. Share actual existing FYP tools/runtime in isolated fixtures. Two direct wire paths cover Realtime GA and Live+Responses delegation, including nested function items, explicit continuation and terminal usage. Local synthetic English/Mandarin/Cantonese audio is paced, not uploaded as an instantaneous microphone substitute.

**Actual experiments:**16 sessions;11 final controlled trials across Realtime2.1,Live1+Luna and oneMini English reference. Both principal routes returned the three correct calendar starts, prepared one pending fact without saving and changed toReady after interruption. Early automatic-language failures, one premature harness close and a misleading Live acknowledgment were retained and corrected/retested. First non-silent network audio is not first useful speech or DAC playback. Real naturalness/phonetics require human listening.

**Validation and cost:**504 backend,15 focused, lint/format pass; no frontend/native source change or relabeled acceptance. All usage receipts finalized, USD0.3035168833 conservative estimate including iterations; billing account not independently reconciled. Budget ceilingUSD5; actual ledger now closed and rejects further reservation. No active paid service, other-provider call, microphone/camera, CI, hardware/Pi or school-file action.

**Files:**[QA and audio](output/qa/2026-10-29-openai-realtime/verification.md), [plan](planning/2026-10-29/openai-realtime-evaluation.md), [evaluation contract](desk-companion/docs/openai-voice-evaluation.md), runner/package and15 tests; updated current product/entry/handoff/delivery boundaries. Source published as draft[PR66](https://github.com/tantalum666/FYP/pull/66) onPR65, verified commit`f5b9417cfda62e6f8400c7b5ac85ec3a49be3b2a`;[receipt](output/qa/2026-10-29-openai-realtime/publication.json). Scoped secret/link checks pass. No main merge or deployment.

**Next:** bounded App integration and user-controlled A/B listening through existing voice/permission boundaries. No final model choice or general autonomy/real-device claim follows from these small synthetic samples.

## 2026-10-30 · Prepare a harder voice-to-application acceptance task

Started29October and continued across local midnight without restarting completed reading. The owner rejected the simple note-preview proposal and requested a harder task.

Created the fictionalGroup 2demo-preparation challenge:11 task rows, meeting update, three-member availability/current events, frozenFX and four suppliers/five versions in actual localHTML. The main workflow requires browser/Calc/Writer/PDF/calendar/task evidence, then budget/quantity/day corrections, necessary clarification and one lost-save/restart recovery. Separate variants cover revocation, cancellation, source/layout changes and untrusted source instructions.

The independent reference verifies initialAster809.60HKD, no feasible revised colour offer, then approved black-and-whiteDelta669.24HKD including minimum50copies; rate variation changes the winner. It also checks9 distinct/7 open tasks/14.5hours and conflict-free rehearsal updates. Six local checks plusRuff/format pass. These are fixture checks, not a model/GUI execution pass; no production source or paid round changed.

Updated product, delivery/computer-job/maintenance/OpenAI boundaries, entry/handoff and decisions. [Specification](planning/2026-10-30/complex-application-acceptance.md),[fixture](desk-companion/evals/app_workflow_v1/README.md),[QA](output/qa/2026-10-30-complex-app-task/verification.md). Next is bounded application execution/readback/recovery on existing task/job/permission services. Published as draft[PR67](https://github.com/tantalum666/FYP/pull/67), verified fixture/reference commit`6f2e076c6927bc79641caec548e86515e2997b15`;[receipt](output/qa/2026-10-30-complex-app-task/publication.json). Scope/secret/link checks pass. No merge, deployment or complex-task execution.

## 2026-10-30 · Bounded application execution, restart recovery and shared UI

The owner authorized starting implementation of the harder task. Added separate typed application operations, fixed transport/source scope, real UNO/CDP bridge and owned desktop supervisor. Reused existing jobs/tasks/permissions/receipts; no second queue or model transcript store. Added reviewed cell/document previews, immutable downloads and task-stage projection to shared web/phone components.

Actual controlled execution read the fictional browser quotes, built/reopened a four-sheet XLSX in Calc, produced Writer ODT/two-page PDF, action plan and unsent draft, and updated the original second calendar rehearsal. Costs were 809.60 initially, no feasible revised colour offer, then 669.24 after a scripted black-and-white clarification. The main process deliberately exited after the final workbook save; a new process/app environment reconciled the original job without changing file hash or mtime. A separate clean container restart verified all five files; revoked Full authority blocked a queued write.

Real failures revealed unresolved cross-sheet names, canonical XLSX sheet prefixes, installed Writer style naming, wrapped-PDF text order and stale display locks on restart. These were fixed with failure evidence retained. Native Mac UNO failure did not lead to weakening host protections; the dedicated Linux VM mounts only the owned app inputs/support/workspace. Reproducible setup and pinned-profile helper were added.

Local validation: 524 full backend and 89 frontend, final targeted checks, Ruff/format, TypeScript/Vite, actual web creation and phone update/decline/readback/download, independent file checks and all PDF pages inspected. The 393px phone check retained unsent input; Alice home remains. Existing native Simulator source was not rebuilt in this round.

Files: [QA](output/qa/2026-10-30-application-execution/verification.md), [execution contract](desk-companion/docs/application-execution.md), application modules and acceptance driver. Updated root entry/handoff/product/decisions, maintenance/architecture/permissions/jobs/delivery contracts and fixture status. Important progress is published on the independent application-execution branch above PR67; read back the publication receipt, not an assumed merge.

Remaining: resumable model-driven task turns over these tools and offline unseen variants, production OpenAI session integration, then a newly scoped paid voice comparison. This run is explicitly scripted and has zero model calls. No CI, old-budget reopening, hardware/Pi, external message, purchase, school-file change or submission.

Published as draft [PR68](https://github.com/tantalum666/FYP/pull/68) on PR67; verified implementation head `20581f387a99d0ecd19f2c194683ad114275aea8` matches GitHub and git remote. [Publication receipt](output/qa/2026-10-30-application-execution/publication.json). The PR remains open/unmerged; this receipt closeout changes documentation only.

## 2026-10-30 · Recover personal-agent research and reconnect delivery priorities

The owner challenged the generic answers about email, shopping and travel after several prior competitor-research rounds. Recovered the research chain from 3/6/12/14–15/29 October. Live GitHub PR5 metadata and the local remote ref agreed on 11dc2b84cebe6e8250b28ca4442fc91f0dfec676; six detailed product/gap reports existed there but not in the active checkout. The later architecture index omitted Grok links, and the latest handoff omitted the research route. These were context/retrieval and handoff defects, not missing user intent.

Restored the six report bodies with historical banners, original-commit supporting links and source/recovered hashes: 1,304 original lines / 205,227 bytes. Copied no PR5 application kernel, old avatar, workflow or runtime. Focused rereading is logged separately from complete blob recovery. Rechecked 15 official pages: three current product mechanisms, action/payment distinctions, ongoing responsibility, mail events and the managed-harness boundary. Corrected the active Dot identity, stale Grok approval-expiry advice, Muse's previously inaccessible announcement and the narrow Codex-only framing.

Created [one research entry and implementation map](research/personal-agent-research-index.md); rooted it in AGENTS, README, START, product and handoff; marked old product/architecture advice historical and restored all six study links. Current code inspection confirms a calendar-only Google scope, task-based local checks and bounded app execution, with real mailbox monitoring, merchant/payment and flight ticketing still missing. The next proposed code gate is the real email-to-task-to-suggestion journey with resumable model turns, followed by the recorded shopping/travel acceptance gates.

[QA](output/qa/2026-10-30-agent-research-recovery/verification.md) contains provenance, read scope, current sources and documentation checks. Validation is original/recovered hash and narrative checks, internal links, source-tree preservation, whitespace and secret scanning. PR68's 524/89/73 checks remain prior application evidence; no new runtime test or competitor behavioral score is claimed. No CI, personal-mail access, monitoring schedule, outgoing message, purchase, model fees, hardware or deployment.

Published as draft [PR69](https://github.com/tantalum666/FYP/pull/69) on PR68. Research commit `3196d0f855c8d16b5e67d17311b0527cee034bf6` matched the remote branch and GitHub PR head; [publication receipt](output/qa/2026-10-30-agent-research-recovery/publication.json). The PR remains open/unmerged. This receipt closeout changes documentation only.


## 2026-10-30 · Review all outstanding PRs and integrate the compatible stack

The owner authorized a fresh review of all open PRs and merging those without unresolved problems. Frozen set: 4, 5, 15, 16, 19, 64–69. Used a new managed `all-pr-review-20261030` worktree because previous attached checkouts retain evidence or active preview work.

Reviewed the latest software stack, original branch provenance and overlapping contracts. Original PR5's 1380 backend cases yield 1334 passes and 46 failures on this Mac. A directory-link-count migration defect was reproduced on synthetic data; a diagnostic-only fix passes 129 focused cases, but the current memory row remains invisible to the old API after upgrade. PR5 also collides with current runtime/application protocols. It is retained for compatible porting rather than given an unsupported green merge. Old 4/16 presentation and 15's original Omni changes are superseded by the current baseline; four voice/media helpers are byte-identical.

PR19's dated hardware package passed all five-page rendering checks, unchanged PDF SHA/size and budget arithmetic, including 13 unpriced required items. Resolved its five root-document conflicts toward current software/AI/Alice decisions, preserving hardware records and paused deployment. The candidate fixes one misleading cancellation reply: edited staging is distinguished from final publication. Latest full backend 524, frontend 89, focused cancellation/permissions 36, type/build and Ruff pass. Actual web/393px phone memory search, exact once-approved file bytes, linked-task continuation, Alice and draft guards pass.

[Review and evidence](output/qa/2026-10-30-all-pr-review/verification.md) distinguish eligible merges (19,64–69), superseded closures (4,15,16) and blocked 5. No CI, live models, real user database migration, media capture, hardware/Pi, external purchase or school submission. Final remote receipts are appended after publication; this entry alone is not a merge claim.


### Verified merge and original PR disposition

PR70 merged reviewed candidate `4872f7bf8fad1f7dce9d58bf62154ea1761e9760` into main as `78e9bc2c343c629b7e66725a61f34bc46453dbe0`; full Git trees match. GitHub individually confirms PR19 and64–69 merged. PR4/15/16 were closed as superseded (merged=false), preserving branches and all original heads. PR5 stays open/draft; its description now includes the reproduced failures and current-data compatibility gate. [Receipt](output/qa/2026-10-30-all-pr-review/publication.json). This final closeout updates documentation only; application source stays at the verified integration.

## 2026-10-31 · PR5 compatibility repair and authorized merge

Owner requested repairing and merging PR5. Started from main18d2056, retained original11dc2b8 as a merge parent, restored current shared modules before explicitly integrating retained Work/source/artifact/watch/routine capabilities. Current Alice/Omni, canonical facts, permissions and real office executor remain authoritative. Superseded art/demo-record code and historical output files stay in Git ancestry instead of entering the active application.

Repaired macOS migration identity, explicit legacy-fact conversion, current-memory projection/forgetting, Work-linked approval after redaction, bounded JSON, provider dispatch, shutdown isolation, hidden job APIs and approved intent hashing. UI shares Tasks/approval cards and current memory editor, fixes Work width, keeps phone Alice and protects a consumed voice handoff from unmounting its composer. Optional browser dependency is locked; no browser binary, CI or live API was run.

Evidence: [compatibility contract](desk-companion/docs/pr5-integration.md), [QA](output/qa/2026-10-31-pr5-repair/verification.md), 45-table current-main fixture migration, actual local download hash, same-task approval/watch/mobile readback. Current test totals and remote publication are recorded in QA after completion. Real user DBs and prior runtimes were preserved. Next product gate remains an authorized real-mailbox journey through the existing task/Work core, not consumer-agent parity by model API alone.

Publication verified: PR5 closed/merged, reviewed112f912 → main9b655e1, exact Git trees match. Final1686backend/300frontend passed; staged secrets scan and504local-link checks passed. This closeout updates status/receipts only; next work is the scoped mailbox journey.

## 2026-10-31 · Pi resumed at home, portable Wi-Fi/Ethernet seed

Owner resumed Pi work, supplied home Wi-Fi privately and authorized the existing VPS if needed; then specified home Wi-Fi, classroom Wi-Fi/Ethernet and dorm Ethernet. Read the referenced VPS chat and focused Pi recovery docs; inspected the current Mac LAN, original card identity, old boot status and paired host public key. The earlier Halls/Student boot ended without connectivity; it was not treated as a password diagnosis.

Added a network-only SD preparer and Pi installer with bounded active-private-LAN SSH rules, NetworkManager event refresh, home/wired profiles, preserved classroom Wi-Fi and disabled dorm Wi-Fi autoconnect. Original users/keys/app/data stay in place.25local checks and Ruff pass. Two boot seed files were backed up privately, written, read back and parsed; other boot files unchanged; Linux partition not written by Mac; FAT verify0 and safe ejection. Generic Mac LAN launcher copied to Downloads.

Owner was requested to reinsert/power the Pi. The initial bounded UDP receiver saw no matching packet; actual home connection and app/desktop acceptance remain pending, not failed or completed by inference. No VPS/proxy change, paid call, media/motor activation or application database upgrade. [QA](output/qa/2026-10-31-pi-home-resume/verification.md) / [network contract](desk-companion/docs/pi-network-profiles.md).

Published sourcebdd9c6d and sanitized evidence to draftPR73; remote head verified. Card seed matches checked source, no credential published, no CI. Initial observer ended without a matching packet; temporary mDNS query stopped. Live boot acceptance remains pending.

### 2026-10-31 · Actual home boot, web/desktop acceptance and power finding

The owner confirmed reinsertion/power. mDNS followed the changed DHCP lease; direct-LAN routing and the original pinned SSH key were independently checked. Home profile/SSID, network-ready status, active app/VNC services, loopback listeners, actual SSH/firewall policy and all three network priorities passed live readback. Existing owner web login, Alice/device rendering and Mac Screen Sharing passed. Pi-local Chromium rendered after cancellation of an unsolicited new-keyring prompt; no credential was created. Final low-load check at04:46:40+08:00 still returned home connected, both services active and health ok.

Recorded the real browser-start undervoltage event rather than declaring full stability: kernel detected04:29:57, normalized04:29:59; browser window closed; subsequent0x50000 records historical undervoltage/throttling, with no active flags. Supply capability reports3000mA, actual PSU/cable awaits the owner. A later rail sample5.04242V is not a load-time guarantee. Ethernet remains unavailable/no cable; the optional home-router test is unanswered. The missing cloud-init module warning and country-command exit1 are retained alongside independently verified networking and global/persisted CN.

Updated current product/entry/handoff, both Pi guides, network contract, decisions, reading record and selected QA evidence. Full selected diagnostics and genuine UI screenshots stay owner-private; no secrets/raw profiles/images published. Network source is unchanged, so prior25local checks/Ruff remain dated preparation evidence; no redundant full app tests or CI. This is networking and old-app acceptance, not a latest-main upgrade, real user database migration, model call or mechanical test. Next gate: confirm supply/cable, then one bounded stability retest before software deployment. [Evidence](output/qa/2026-10-31-pi-home-resume/verification.md).
