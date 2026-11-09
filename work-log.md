# Group 2 Work Log

Updated: 6 November 2026. Current state: [handoff](handoff.md). Pre-pivot Senplate entries are preserved in [the archive](archive/senplate/work-log.md).

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

## 2026-11-03 · Integration acceptance harness

**Goal:** Encode the 28 October Codex integration-review lessons as a regression suite on main `dac527b386c268caa96d9388d0c11d206b4f6856`, so later slices fail if they return. No feature work and no production redesign.

**Done:** `desk-companion/tests/test_integration_acceptance.py` (seven tests) and Node fixtures that load the real `frontend/src/api.ts` recovery path. Checklist mapped in [integration acceptance](desk-companion/docs/integration-acceptance.md). Handoff notes the harness and keeps the mailbox journey as the one next step.

**Verification:** `uv run --no-sync ruff check tests/test_integration_acceptance.py` and `uv run --no-sync pytest tests/test_integration_acceptance.py -q` — 7 passed. No paid calls, GitHub Actions, Pi, Alice wake, desktop chat, or Work UI edits. [QA](output/qa/2026-11-03-integration-acceptance/verification.md).

**Remaining:** The authorized mailbox journey is unchanged. This harness can merge on its own unless a later branch edits the same test or doc lines.
## 2026-11-03 · Offline mailbox journey

Owner instruction: implement the mailbox journey named in handoff, starting only with offline fixtures. No Gmail/Outlook connection, credentials, spend, or paid API. Reuse TaskService, the existing task as the Work item, PermissionService, and NoticeInbox.

Added `desk-mailbox-fixture-v1` under `desk-companion/fixtures/mailbox/` (duplicate, out-of-order, interrupt/restart, revoke, disconnect). `MailboxService` keeps a durable history cursor and read offset in the same SQLite store (`BEGIN IMMEDIATE`, owner session rechecked). One thread updates one task; omitted fields do not clear notes, waiting reasons, or deadlines. Advice drafts cite the mail id and `observed_at`, require owner confirm, and never send. Notices publish only for a new or changed task, a deadline inside 24 hours, or a decision.

Local evidence: `PYTHONPATH=/tmp/desk-py python3 -m pytest tests/test_mailbox_journey.py -q` → 8 passed. Ruff on the touched Python files passed. Full backend after installing the same packages onto the system site: 1693 passed, 1 failed. The failure is pre-existing `test_public_unicast[::ffff:93.184.216.34]` (`IPv6Address.is_reserved` is true for that mapped address on this interpreter). That file was not modified. No model call and no live mailbox. [QA](output/qa/2026-11-03-mailbox-offline/verification.md), [contract](desk-companion/docs/mailbox-journey.md).

Published as open [PR79](https://github.com/tantalum666/FYP/pull/79); not merged. Next step is an explicit real-account scope before any live mailbox. Do not start shopping or a paid round from this slice.

### Same day: quiet-hour delivery and portable mailbox backup

Owner asked to close the two gaps on PR #79. A meaningful mailbox notice observed during quiet hours is stored and published by the existing `Runtime.tick` through `Notifier` once quiet hours end. The hold remains until that publish is delivered or recognized as a duplicate. Portable JSON backup now includes the cursor, read offset, thread link, message fingerprints, sync attempts, and quiet holds. Preview validates the records; restore keeps an existing connection and does not create a second task when the same messages are synced again. A display cannot preview or apply the backup.

Checks: `python3 -m pytest tests/test_mailbox_journey.py` → 9 passed. Backup, notice, and nudge files `test_exchange.py`, `test_backup_persona_jobs.py`, `test_memory_gaps.py`, `test_risk_gaps.py`, `test_tasks.py`, `test_integration_boundaries.py`, `test_notify.py`, `test_nudges.py` → 64 passed. Ruff on the touched Python files passed. Still no live mailbox or paid API. Confirming a draft still uses the existing note action, which clears `check_in_local`.
## 2026-11-03 · Offline shopping fixtures

- **目标：**把离线购物夹具接进现有 Task、暂停的 Work、草稿批准和通知。不连接商店或支付，不改邮箱、Pi 或 Codex Work 界面。
- **完成：**`desk/shopping` 读取夹具，按序号提交游标，同一商品或订单只保留一个事务和一条暂停的 Work。重复、乱序、断线、撤销和重启都走这条映射。有意义的变化才通知；建议草稿必须由拥有者确认，省略的事务字段在确认时保留。
- **验证：**`uv run --no-sync pytest tests/test_shopping_fixtures.py tests/test_permissions.py -q` 为 28 passed（12.03s）。Ruff 通过。没有付费调用，没有 GitHub Actions。记录见 [QA](output/qa/2026-11-03-shopping-fixtures/verification.md)。
- **剩余：**真实商店、运费、地址、支付和订单回执仍未做。邮箱旅程仍由另一条工作推进。
- **同日补充：**可移植 JSON 备份写入并恢复购物游标。拥有者预览校验后才恢复；已存在的连接不回退游标。备份后再次同步同一夹具仍是原来的一个事务。`disconnect_after` 为 0 时不读文件、不提交，`completed` 保持 false。
## 2026-11-03 · Offline calendar fixture journey

Mapped `desk-calendar-fixture-v1` files through the existing task, calendar event, proposal, and notice services. One event or series keeps one task. Omitted location, notes, and reminders stay stored. Conflict and prepare drafts cite the event id and observation time; owner confirm does not accept an invite or send an RSVP. Duplicate, stale, restart, revoke, disconnect, quiet hours, and owner permission are covered by the HTTP journey tests.

No mailbox, shopping, Pi, or Codex Work UI files were changed. No live calendar API and no paid call.

Quiet-hour calendar notices are held and released by the existing rules tick through Notifier. Portable JSON backup now includes the calendar cursor, revisions, conflict pairs, attempts, and held notices. Owner preview validates the bundle. Restore then sync keeps the same task. Restart does not drop or duplicate a held notice.

Files: [contract](desk-companion/docs/offline-calendar-journey.md), `desk-companion/backend/desk/offline_calendar/`, `desk-companion/fixtures/offline-calendar/`, [QA](output/qa/2026-11-03-offline-calendar/verification.md). Remaining: review this PR without connecting an account; mailbox and shopping stay on their own branches.
## 2026-11-03 · Offline-journey merge guide

Wrote a Codex-facing merge order for the open Grok offline slices: #78 harness, #79 mailbox, #80 shopping, then #82 offline calendar. Drafts #73–#77 are left on Codex's stack. This guide is #81 and can merge last or anytime. Docs only. Record: [guide](docs/offline-journey-merge-guide.md), [QA](output/qa/2026-11-03-offline-journey-merge-guide/verification.md).

## 2026-11-04 Grok offline journey independent review

Reviewed PR78/79/80/82/81 against frozen main dac527b in an isolated worktree. Kept each reviewed head in ancestry and combined all router, proposal, backup and notifier wiring. Repaired stale mail updates, deferred/scoped shopping notices, owner stop/logout boundaries, portable Work reattachment/atomic paused admission, calendar conflict/operation/cursor/cancellation bookkeeping, backup reference/receipt validation, and shared source-aware review/success UI. Split mailbox backup logic from ingest.

[QA](output/qa/2026-11-04-grok-journey-review/verification.md) records actual failing regressions, fixed-source full runs, Web/393px phone interactions and independent task readback. A separate combination with PR77 preserves current Alice/OpenAI/application Work code; it is not a merge/deployment of that stack. Original worktrees/data and school files remain unchanged. No CI, paid model, live account, external message/transaction or Pi action. Final publication follows the locally verified source and records remote heads separately.

### 4 November publication readback

[PR83](https://github.com/tantalum666/FYP/pull/83) merged at89dc92f41d945783af43dcb4f56f0e7e6d0edb1a. Remote main exactly matches the complete tree of reviewed bb6443c. Original PR78–82 were individually read back closed/merged; source63e538b remains the tested application. [Receipt](output/qa/2026-11-04-grok-journey-review/publication.json). This follow-up records publication only, with no CI, deployment, model or hardware action.
## 2026-10-31 · Personal-agent Work connected to real applications

Owner paused Pi and prioritized cross-application personal-agent software after PR5. Created a separate worktree/branch from verified main dac527b, preserving Pi PR73 and all real runtimes. Refreshed four relevant primary vendor pages and mapped persistent task state, connectors/browser execution, independent permission and result verification to the current implementation.

Added application Work adapters with explicit selected task/input scope, source-hash binding, exact child-intent recovery, Ask first/Full capture, parent-run execution fences and independently verified continuation. Reused JobService and existing office executor; no duplicate queue/core or new migration. Added immutable-version readback for revised files, compact model-result projection and formula normalization after a real UNO format failure. UI shares job cards, puts needed actions first, collapses diagnostic tool detail and distinguishes office files from report artifacts and calendar/task proposals.

Local verification:1,701 backend/303 frontend, Ruff, TypeScript/Vite. Real Chromium quote read, initial and revised Calc, owner-test minimum-order question, Writer and two-page PDF passed using offline scripted decisions. Actual lost completion followed by application-container and runner restart preserved SHA/mtime and did not repeat the write. PDF pages rendered/inspected. Web allowed once then continued to document proposal; parent cancellation preserved workbook and stopped unpublished document.393px phone downloaded identical bytes and reviewed/discarded a scoped draft. No native keyboard, live-model quality or consumer transaction was claimed.

[QA](output/qa/2026-10-31-personal-agent-cross-app/verification.md) and [contract](desk-companion/docs/application-work.md) hold exact evidence/limits. Updated product, research index/supplement, current entry/handoff, AGENTS header, Work/executor/module docs and decision log. Old budgets closed, paid calls0, no CI or Pi continuation. Ordinary Alice/Omni long-task admission/recovery is the next offline implementation step. Publication receipt is finalized after branch push and PR readback; local completion is not main merge.

Publication verified: source `b277cef` is the head of draftPR74, based on main dac527b. Remote metadata matches the pushed source; PR is open and unmerged. Final receipt changes only documentation. The original Pi worktree entry now routes to this software continuation; its documentation-only pause commit1cad1df is preserved on PR73.

## 2026-10-31–11-01 · Concise everyday UI

Owner reported excessive text across pages. Audited eight real desktop surfaces before editing, then shortened shared Work, task, settings/permissions, memory, style and data views. Moved technical metadata, storage, history and optional configuration into disclosures; actual questions/errors/actions stay visible. Phone Work selection replaces the list with detail and uses the existing guarded return. Alice and saved user content are preserved; no new dependencies, state machine, queue or backend change.

Local frontend303/type/build passed. Actual desktop/Chinese393px phone, keyboard disclosure, preserved optional/persona draft, close/discard guard, cancelled Full-access draft, explicit retention and UI-created deterministic Work→two reports passed. AI-mode provider/share choices remain explicit; no model run was submitted. Default new-work visible characters1368→290, import/share1184→200; the latter is progressive disclosure, not removed functionality. Initial stale-label/format-sensitive test failures and a transient JSX development error were corrected before final verification. Existing large-chunk build warning remains.

[Interface contract](desk-companion/docs/ui-copy.md), [QA](output/qa/2026-10-31-ui-copy-cleanup/verification.md) and selected actual screenshots record scope/limits. Updated AGENTS, product, decision, maintenance, dated UI/permission guidance and current handoff/entry. Native touch/keyboard, real accounts, models, backend tests and Pi were not rerun. No CI or live provider cost. Next: concise ordinary-Alice long-task admission/recovery via existing Work, offline first. Publication is a separate branch stacked on PR74; no merge claim.

Publication verified: UI source752ab66 pushed to draftPR75, targeting PR74 head89f215e. GitHub reports open/draft/unmerged and exact matching head. The final receipt and original Pi-checkout routing updates are documentation-only; no code/test result is added by those commits.

## 2026-11-02 · Reopen webpage for owner

Restarted stopped Vite5191/API8861 against the existing synthetic UI dataset, with scheduler and AI/computer execution off. Opened visible in-app-browser Tasks page and confirmed connected content/Alice controls, then marked it to remain open. Updated runtime handoff and [read/verification record](output/qa/2026-11-02-open-preview/verification.md). No source change, paid call, Pi/VM action or CI; no new implementation/test claim.

## 2026-11-02 · Primary conversation and Mac media

Replaced the width-dependent desktop assistant modal/dock with the default primary chat page. ConversationWorkspace keeps shared conversation/drafts across navigation; media suspends on leaving. Added LocalCapture/MediaDevicePanel for explicit local camera/mic checks and selected-frame sharing through existing VoiceAudio. Responsive navigation/composer and floating-avatar avoidance preserve Alice; removed dead docking CSS. No backend/dependency/new queue or model client.

309 frontend tests and type/build pass. Actual Mac1280x720 camera, built-in mic input, draft return, short-window permission menu and narrow keyboard navigation checked. Qwen configuration is restored, but owner chose manual trial; no agent-paid request or uploaded device-check media. Initial QA resized the visible user tab; restored100%/1291x681, moved further emulation to a separate tab, cleared/closed it.

Updated current contracts/product/entry/handoff/decisions and [QA](output/qa/2026-11-02-conversation-desktop/verification.md). Native/Pi/model quality remain separate. Next: existing Work admission/recovery from Alice, offline first. Publication is stacked on PR75, not a merge.

Publication verified: sourceff0b401 on draftPR76, basePR75 head34de1e7; exact remote source head matches, open/draft/unmerged. Receipt and original-checkout routing updates are documentation-only.

## 2026-11-02 · OpenAI production adapter and Alice local wake

Owner requested OpenAI and chose calling Alice to wake. Reused the confirmed FYP key, read current official costs, and used a fresh announcedUSD1 ceiling. Extracted the existing realtime response/tool/cancel core, added OpenAI GA format/rate/credential policy, and connected owner-only local keyword PCM to the existing browser voice client. Wake model files stay ignored and local; private audio is not recorded. New owner/local-channel lifecycle regressions and real model inference retain the existing service/authority boundaries.

Four synthetic live attempts preserved date-argument, output-truncation and Mini numerical failures. Full2.1 with revised generic guidance correctly read three meeting start times. No model ranking or human quality score is claimed. Test ledger closed: observed upper estimate0.1692086, accounted0.6499936 including unknown reservation. Actual local WS detection and browser waiting/off were checked with no additional paid call; temporary test-tab ticket blocking was cleared. Existing Full policy preserved.

Current API80987/Vite5191 use real OpenAI full2.1 and the local Alice model on synthetic work-ui-01; scheduler/computer/background work remain off. Updated current product, entry/handoff, decisions and voice/operator/maintenance/architecture contracts plus [QA](output/qa/2026-11-02-openai-alice-wake/verification.md). No CI, Pi, VM, real-account connection or transaction. Next: ordinary Alice long-task admission/recovery through existing Work, while human wake/noise/voice acceptance remains separately open.

Publication verified: source6406503 on draftPR77, basePR76 head17df074, exact remote source head matched. Final receipt/routing is documentation-only. All experimental budgets remain closed; normal explicit owner use is distinct.

## 2026-11-04 Merge PR74–77 into the reviewed main baseline

Owner explicitly requested74–77. Based on main4855987, retained every stack head through the77tip and resolved only eight Markdown conflicts; application code matches the prior b0375f4 compatibility tree exactly. Full1769 backend/319 frontend, Ruff/type/build and actual primary-chat/phone draft/advice checks passed. [QA](output/qa/2026-11-04-merge-74-77/verification.md). No CI, paid provider/media/hardware or deployment action. Current docs replace the separate-stack next step with ordinary Alice-to-Work continuation on the unified baseline; publication is recorded after remote readback.

### PR74–77 publication readback

[PR85](https://github.com/tantalum666/FYP/pull/85) merged atb663204938fa11cb5c3631f2995800466840b55e. Main's full tree equals reviewed affbad2d. Original74/75/76/77 were each read back closed/merged after retargeting the stack to main. [Receipt](output/qa/2026-11-04-merge-74-77/publication.json). This closeout changes documentation only; verified application151f807 and1769/319 local results are unchanged. No deployment, CI, paid model or Pi work.


## 2026-11-06 Pi免登录、Alice与本机跨应用

用户要求所有端撤下Sign in、Pi保留Alice和语音；随后暂缓自动红灯调查，继续Pi软件，重点跨应用。实现共用可信回环会话恢复、DeviceHome与既有对话／媒体复用，修复自身媒体面板被遮挡监听关闭、只读模型目录写入和生产页面camera策略。新版本已备份后部署Pi，Qwen配置与原用户数据保留；手机模拟器连接实际Pi。Pi未枚举麦克风，本轮未真人／付费语音验收。

在Pi安装普通用户Podman运行环境，复用原ApplicationExecutor／JobService／Work与批准边界。保留Docker范围哈希，跨engine使旧准入失效；固定本地命令且不传供应商／远程容器环境。修复镜像manifest/config身份核对、首次映射等待、Pi缺失memory controller与PID1信号转发；显式记录无RAM硬上限，CPU/PID／网络／文件隔离保留。用户应用服务开启，API原NoNewPrivileges保留。

Pi真实四作业：选定HTML→36份900元表格→改48份950元／同意50份起订→Writer／两页PDF；唯一可行902元方案经Calc重算。人为丢失保存回执后重启恢复，SHA／mtime不变。最终容器重建后再次打开四历史版本和三当前文件，无改写；正常停止0.38s。离线规划脚本，不是模型自主成绩。完整后端1789／前端324，后续媒体19／voice-wake33／launcher-transport10和最终launcher3通过；类型／构建／Ruff通过，PDF逐页查看。源码、范围和证据见[QA](output/qa/2026-11-06-passwordless-device/verification.md)。

同步AGENTS、当前入口、product、decision、handoff及受影响设备／应用／维护规范；新增连接与Pi运行契约。私有备份、依赖镜像、凭据、截图和二进制测试产物不入Git。重要源码推独立分支／draftPR，具体HEAD见发布回执；没有合并、CI、付费模型、真实账户交易或学校提交。用户澄清先红灯再拔插，旧正常按键重启说法无效；供电调查未继续。唯一下一步：把普通Alice／语音请求接进同一持久Work，先离线验收，再另行限定付费比较。


<!-- Preserved network-recovery history from PR73/87. Later Pi software/physical-restart corrections take precedence. -->
## 2026-10-31 · Pi resumed at home, portable Wi-Fi/Ethernet seed

Owner resumed Pi work, supplied home Wi-Fi privately and authorized the existing VPS if needed; then specified home Wi-Fi, classroom Wi-Fi/Ethernet and dorm Ethernet. Read the referenced VPS chat and focused Pi recovery docs; inspected the current Mac LAN, original card identity, old boot status and paired host public key. The earlier Halls/Student boot ended without connectivity; it was not treated as a password diagnosis.

Added a network-only SD preparer and Pi installer with bounded active-private-LAN SSH rules, NetworkManager event refresh, home/wired profiles, preserved classroom Wi-Fi and disabled dorm Wi-Fi autoconnect. Original users/keys/app/data stay in place.25local checks and Ruff pass. Two boot seed files were backed up privately, written, read back and parsed; other boot files unchanged; Linux partition not written by Mac; FAT verify0 and safe ejection. Generic Mac LAN launcher copied to Downloads.

Owner was requested to reinsert/power the Pi. The initial bounded UDP receiver saw no matching packet; actual home connection and app/desktop acceptance remain pending, not failed or completed by inference. No VPS/proxy change, paid call, media/motor activation or application database upgrade. [QA](output/qa/2026-10-31-pi-home-resume/verification.md) / [network contract](desk-companion/docs/pi-network-profiles.md).

Published sourcebdd9c6d and sanitized evidence to draftPR73; remote head verified. Card seed matches checked source, no credential published, no CI. Initial observer ended without a matching packet; temporary mDNS query stopped. Live boot acceptance remains pending.

### 2026-10-31 · Actual home boot, web/desktop acceptance and power finding

The owner confirmed reinsertion/power. mDNS followed the changed DHCP lease; direct-LAN routing and the original pinned SSH key were independently checked. Home profile/SSID, network-ready status, active app/VNC services, loopback listeners, actual SSH/firewall policy and all three network priorities passed live readback. Existing owner web login, Alice/device rendering and Mac Screen Sharing passed. Pi-local Chromium rendered after cancellation of an unsolicited new-keyring prompt; no credential was created. Final low-load check at04:46:40+08:00 still returned home connected, both services active and health ok.

Recorded the real browser-start undervoltage event rather than declaring full stability: kernel detected04:29:57, normalized04:29:59; browser window closed; subsequent0x50000 records historical undervoltage/throttling, with no active flags. Supply capability reports3000mA, actual PSU/cable awaits the owner. A later rail sample5.04242V is not a load-time guarantee. Ethernet remains unavailable/no cable; the optional home-router test is unanswered. The missing cloud-init module warning and country-command exit1 are retained alongside independently verified networking and global/persisted CN.

Updated current product/entry/handoff, both Pi guides, network contract, decisions, reading record and selected QA evidence. Full selected diagnostics and genuine UI screenshots stay owner-private; no secrets/raw profiles/images published. Network source is unchanged, so prior25local checks/Ruff remain dated preparation evidence; no redundant full app tests or CI. This is networking and old-app acceptance, not a latest-main upgrade, real user database migration, model call or mechanical test. Next gate: confirm supply/cable, then one bounded stability retest before software deployment. [Evidence](output/qa/2026-10-31-pi-home-resume/verification.md).

Live evidence commit `d29648b` was pushed and matched both remote branch HEAD and GitHub PR73 metadata. PR73 remains open/draft and unmerged; its description now distinguishes passed home access, actual undervoltage, untested wired access and the older installed app. This receipt update changes no runtime code.

## 2026-10-31 · Correct Pi device-display entry and deployment explanation

Owner questioned why the Pi was shown as a generic website despite the earlier dedicated device work. Recovered the September30 device contract and current route/launcher code; read the installed kiosk, welcome, session and autostart files over pinned SSH. The dedicated DeviceApp exists in both source and the Pi bundle. The previous reply used ordinary workspace settings (`?page=device`) instead of the dedicated display (`?surface=device`). This is a presentation/handoff error, not deletion of the device implementation.

Restored the expired Mac SSH tunnel and rendered the Pi's existing display at1280×720 on the Mac: clock/month/locked calendar; Touch to manage opens login; close returns to display; no app warn/error. Genuine screenshot remains private. Pi-local Chromium was not restarted, credentials/settings/data unchanged. Actual autostart still opens the first-start helper; kiosk full-screen startup and recovery remain unfinished, alongside the existing power gate and new-version deployment.

Updated product, current entry/handoff, display contract, Mac access guide and decisions. [QA/read scope](output/qa/2026-10-31-pi-device-entry/verification.md) distinguishes installed code, rendered preview and physical delivery. No application source edit, redundant app suite, CI, model request, device reboot or automatic-start mutation. Next physical gate remains supply/cable confirmation, followed by a bounded load retest and dedicated-device deployment work.

## 2026-10-31 · Pi paused; route active software continuation

Owner paused Pi and prioritized personal-agent cross-application software. The new implementation is in `/Users/tantalum/.codex/worktrees/personal-agent-20261031/FYP`, branch `codex/personal-agent-cross-app-20261031`, [PR74](https://github.com/tantalum666/FYP/pull/74). Updated this original checkout's AGENTS/product/entry/handoff and Pi guide headers so the next chat follows the active software work rather than restarting hardware. Pi evidence/power/wired/kiosk gaps remain preserved; no device action or source-code change. Software evidence and1,701/303 checks belong to74, not this Pi branch.

## 2026-11-01 · Route to concise-UI software continuation

Updated AGENTS/product/entry/handoff and current decision after the owner reported excessive UI text. Active software tree remains personal-agent-20261031, now branch codex/ui-copy-cleanup-20261031 and draftPR75 on PR74. Its code/QA are not copied into this Pi branch. Read current routing documents and latest related sections; confirmed clean starting state and documentation-only diff. No Pi/network/model/runtime action; power/kiosk/wired gaps remain paused. [Routing check](output/qa/2026-10-31-ui-copy-cleanup/routing.md).

## 2026-11-02 · Route to primary-conversation software

Updated entry/product/handoff/AGENTS and latest decision to software branch codex/conversation-desktop-20261102 / draftPR76. Read current routing and related latest sections; clean starting tree, documentation-only changes. Source,309-test evidence and Mac device checks belong to the software worktree. No Pi/VM/provider request here. [Routing record](output/qa/2026-11-02-conversation-desktop/routing.md).

## 2026-11-02 · Route OpenAI/Alice continuation

Clean starting checkout; read current routing/entry and latest related decision/work-log. Updated six root Markdown routes and [QA note](output/qa/2026-11-02-openai-alice-wake/routing.md) to software PR77. Actual source, model tests, costs and local media remain in the personal-agent worktree; no copy of code, credentials, data or model weights. No Pi/provider/CI action from this checkout.

## 2026-11-04 · Dorm Pi recovery waiting for the original card

Owner resumed hardware, confirmed wall-socket Ethernet and official27W supply, and selected normal shutdown followed by attaching the original SD card to the Mac. No monitor is available; explained that ordinary MacBook HDMI is an output. Bounded exact-host discovery and passive known-device matching yielded no current Pi IP. The historical Ethernet address routes through VPN and was not probed. Card checks found no bootfs; no SSH, card write, device change, deployment or power/load result.

Reviewed the preserved network/SD implementation. Wired DHCP already exists, but ordinary guard events do not refresh the boot status file; its timestamp must be checked before relying on an address. Updated AGENTS, product current route, current entry/handoff, network/Mac-access notes, decisions and this log. [Read scope and checks](output/qa/2026-11-04-pi-dorm-ethernet/verification.md). Existing school/merge records are preserved. This is a local recovery checkpoint, not a new code milestone or GitHub publication. No app tests, CI, paid model, global network setting or VPS change. Next: identity-verified, read-only card inspection after owner attachment.

### Original card inspected and recovery seed prepared

Owner attached the card and ran the private read-only administrator helper. Initial captures failed; retained exact inode-bitmap checksum error, then recovered11 selected files through read-only debugfs -c. Saved wired lease gives a candidate outside Mac subnet. Read-only e2fsck4 explicitly skipped journal replay; no physical-failure or repaired-filesystem claim.

Added opt-in one-owner wired /32, fresh guard-event status/boot ID, explicitHK and bounded discovery.29 network tests and Ruff passed. Changed only boot user-data/meta-data with private backups and exact independent readback, checked unrelated hashes and FAT readonly0, safely ejected. Owner confirmed new boot; observer is active, pinned SSH/power/post-replay checks pending. Source branch codex/pi-dorm-network-recovery-20261104 is based on the preserved PR73 line; no latest-main application deployment or paid call.

Publication receipt: recovery source7c6790d is pushed in draftPR87 over PR73; not merged. Fresh diagnostic packet and authenticated SSH remain absent after owner-confirmed boot. Interface-bound candidate SSH/TCP timed out. Existing VPS authentication succeeded over the Mac’s current route; direct campus SSH and HTTPS/TLS checks did not establish a usable relay. No VPS or global Mac changes. Await owner LED observation, then inspect fresh boot state if still unreachable.

### Consolidated verified bootstrap after incomplete relay installation

Owner confirmed three-place requirements and rejected a hotspot. Fresh card records proved wired DHCP/source configuration, but no authenticated access. Prepared and tested a dedicated restricted VPS relay; its first Pi attempt had no banner. Collected cloud-init/permission evidence read-only after owner admin action. Empty relay files with already-run write markers and missing receipts exposed a false-success gap; readonly journal caveat preserved.

Added one bootstrap source embedded in bootcmd/runcmd, atomic/readback-verified managed-file restoration, only-current-instance command retry, expected Pi fingerprint, actual command receipts and completion after successful setup.62 local checks/Ruff passed, plus real VPS positive/negative transport and conditional diagnostic-log privacy probes. Durable seed prepared with private backups, exact readback and preserved unrelated files. New [contract](desk-companion/docs/pi-owner-relay.md) separates home/classroom/dorm configuration, actual acceptance and optional relay. Live Pi identity remains pending; no CI/AI call/app migration.

### Consolidated package publication and physical handoff

Reviewed sourcefe9725720b24f7cfbe03fb2cc2a6b7f26b03719d was pushed and read back on PR87. The connector temporarily failed and the CLI token could not edit PR metadata; the owner's authenticated browser updated title/body, then the CLI read back the62-test description. PR remains open/draft. Browser proof is private and was shown to the owner; no private capture/credential was published.

The durable seed passed exact readback and FAT readonly0 and was safely ejected. A900-second observer finished without a stage or SSH banner while the latest reinsertion/power confirmation remained pending. One final pinned relay probe did not authenticate. This is not evidence of a failed boot of the new durable seed: the owner has not confirmed that physical step. No observer remains running. Resume by observing this prepared seed after the owner's new power-on confirmation; do not rewrite the card or ask for a hotspot by default.

## 2026-11-05 · Fixed443 management transport prepared

The owner confirmed the durable boot; matching stages reached setup_completed but direct VPS TCP remained unavailable. The earlier Mac fixture used the existing encrypted path, not Pi's plain22 path. A fresh isolated client forced to en0 authenticated the pinned VPS and dedicated key over443 without changing Mac proxy settings. Verified the official matching ARM64 archive/digest/static ELF and rehearsed the entire protected package privately.

Added strict fixed-target transport installation, loopback SSH dialing, bootstrap receipt/order integration and offline-archive backup/readback/rollback.79 focused checks and Ruff passed; [QA/read scope](output/qa/2026-11-05-pi-443-transport/verification.md). Real card is not yet updated; owner was asked to return it. No hotspot, CI, model call, global proxy/DNS/TUN change or application migration.

Publication checkpoint: source7bbeae2a was pushed to draftPR87; the browser saved the79-test/fixed443 description after the connector/CLI write paths failed. The real card still needs this package. Owner input pending is normal shutdown and original-card return, not a hotspot. Source/operational proof and the verified upstream artifact remain separate; no authenticated Pi access or three-place field acceptance is claimed.

### Original-card443 package deployed; owner confirmed boot

Verified original media identity and previous durable-trial receipts, then applied the existing tested443 package with private backups. Exact readback checked all three changed boot files, ten payloads, three setup steps, original host fingerprint and unchanged home/wired/other boot configuration. Classroom profile was not targeted. Refreshed the selected Mac /32 after detecting a new DHCP lease. FAT read-only check returned0; post-remount readback and safe whole-card eject passed. Updated only the exact-trial VPS log filter, verified nginx configuration/reload, and prepared the new-stage observer. Owner confirmed boot; file-restoration and network-setup progress observed, original Pi SSH pending.

Updated current entry, AGENTS, product, handoff, network/Mac/relay guides, decision and [QA with card checks](output/qa/2026-11-05-pi-443-transport/verification.md). Existing79 local tests are reused because implementation did not change. No Linux-partition write by Mac, CI, model call, global networking change, new app deployment or school-file modification. Private seeds/keys/binary stay outside Git.

### Authenticated access, actual unified runtime rollout and recovery

Original Pi SSH identity, wired/default route, pinned transport, enabled services and Mac HTTP/VNC passed. Transport restart recovered without reboot. Added private-config Mac relay support to the shared connector, strict host checks and argument validation;13 boundary tests join79 existing checks (92passed), plus Ruff/shell syntax. A later stale VPS session was removed and only that relay account received20/3 liveness after syntax/effective-root comparison. Recovery was later clarified by the owner as unplug/reconnect after spontaneous red LED; new boot ID, original identity and Mac automatic retry passed. SIGTERM freed both owned local listeners; final owner tunnel restarted.

Owner asked to prioritize software. Verified source tree matches remote mainabf6387, rebuilt frontend, obtained30 hash-locked ARM64 core wheels and verified the305-file package on Pi. Preserved the old app, created an independent release, rehearsed actual schema1 data migration on Mac/Pi, and ran ARM64 auth/read/create/idempotent-retry checks on a copy. Activated the real migration and API service with32 original tables preserved. Post-reboot original-owner HTTP login/core endpoints, new frontend hash and VNC passed. CUA1280×720 device display and management open/close passed with no console errors/warnings; primary sign-in route renders. No browser-authenticated Alice/voice or Pi-local Chromium test.

Final backup inspection rejected the second Pi-only pre-activation copy after finding empty files. The original Pi/Mac snapshot remains valid; old-app login/read on a separate copy passed. Current identity/env bytes match the original snapshot. A synced current schema3 archive was copied to Mac and verified with SQLite sidecars and quick_check. Additional post-reboot checks found no mismatch in274 source/frontend or2159 installed dependency files. Low voltage remains in real kernel logs; no causal certainty or sustained-stability claim. [Network evidence](output/qa/2026-11-05-pi-443-transport/verification.md), [rollout/backup evidence](output/qa/2026-11-05-pi-runtime-upgrade/verification.md).

Updated all current routes, affected Pi guides, decision, handoff and selected QA. Private media/keys/archives, prior school/merge edits and the normal Mac preview are preserved outside this publication. No CI, paid model, firmware update or physical-output operation. Next is offline conversation-to-supported-application acceptance on the deployed Pi.

Publication receipt: sourceeeb96fc was pushed to draftPR87 and its remote HEAD/title/body read back; no merge.11 changed Markdown link sets and the staged secret scan passed. [Rollout publication](output/qa/2026-11-05-pi-runtime-upgrade/publication.json).


## 2026-11-06 · Ordinary text goal change into existing Work

- **目标：**在统一 main 上实现普通 Alice 文字把中途改口送进已有 Work，并覆盖这条路径的中断和未知结果恢复。只做离线夹具。不接真实账号、支付或 Pi，不动 Codex 草稿 #73、#87、#88。
- **完成：**`ConversationWork` 在模型循环之前识别明确改口，调用既有 `AgentRunService.action(steer)`。同一事务只有一项当前 Work 时直接改它；多项、已取消、已改过一次或不属于该事务时不改。提交前中断保持原目标。steer 已写入但对话回执丢失时，同一操作号恢复且不第二次改口。流式关闭不是成功回执。Full access 不会因此产生作业或建议草稿。`Goal:` 仍只建新事务草稿。
- **验证：**`uv run --no-sync ruff check` 针对新模块和接入点通过。`pytest tests/test_conversation_work.py -q` 为 9 passed。`pytest tests/test_integration_acceptance.py -q` 为 7 passed。文字会话、目标、权限、购物、邮箱、离线日程和 `test_agent_runs.py` 共 97 passed。付费调用 0，无 GitHub Actions。记录见 [QA](output/qa/2026-11-06-conversation-work-changed-goal/verification.md)。
- **剩余：**夹具外的说法和来源版式，以及语音快照改已有 Work。真实账号、支付和 Pi 仍分开。

## 2026-11-06 · Held-out phrases and voice-snapshot steering

- **目标：**在 #89 的文字改口上补夹具外的中英文说法和来源版式，并让已复核的语音快照走同一条 steer。离线。不接真实账号、支付或 Pi。
- **完成：**`owner_instruction` 只留一行所有者指令。引用、来源标题、问句、`Goal:`／`目标：`、以及没有运行编号的多项当前工作都不会改已有 Work。语音快照经 `voice_origin_ref` 核对后进入同一个 `ConversationWork.turn`。提交前中断、丢失回执和流式关闭与文字相同。Full access 不产生作业或建议。配对设备仍是 403。
- **验证：**`uv run --no-sync ruff check` 通过。`pytest tests/test_conversation_work.py -q` 为 47 passed。`pytest tests/test_integration_acceptance.py -q` 为 7 passed。文字会话、目标、权限、购物、邮箱、离线日程和 `test_agent_runs.py` 为 97 passed。`test_voice_work.py` 为 44 passed。付费调用 0，无 GitHub Actions。记录见 [QA](output/qa/2026-11-06-conversation-work-unseen-voice/verification.md)。
- **剩余：**语音复核页仍只开始新的 Work。下一步是让该页把已复核快照送进这一条改口。真实账号、支付、Pi 和付费比较仍分开。

## 2026-11-06 · Voice review screen updates one current Work run

- **目标：**让语音复核页把已复核快照送进已有 Work 的同一条改口。一项当前工作时目标明确；多项必须由拥有者点名；没有当前工作时仍开始新的 Work。离线。不接真实账号、支付或 Pi。
- **完成：**复核页读取既有运行列表。更新请求是普通助手消息，带 `voice_origin_ref`、`voice_steer: true`，以及在多项时必须带的 `steer_run_id`。`ConversationWork.turn` 仍调用 `AgentRunService.action(steer)`。同一操作号覆盖提交前中断、丢失回执和流式关闭。配对设备是 403。Full access 不产生作业或建议。改过的措辞不会被当成快照去改已有 Work。
- **验证：**`uv run --no-sync ruff check` 通过。`pytest tests/test_conversation_work.py -q` 为 54 passed。`pytest tests/test_integration_acceptance.py -q` 为 7 passed。文字会话、目标、权限、购物、邮箱、离线日程、`test_agent_runs.py` 与 `test_voice_work.py` 加上整合验收的一条命令为 148 passed。前端 `tests/voice-work*.test.ts` 为 19 passed，`tsc --noEmit` 通过。付费调用 0，无 GitHub Actions。记录见 [QA](output/qa/2026-11-06-voice-review-steer/verification.md)。
- **剩余：**改口后的下一次离线核验结果还没有回到同一条对话。真实账号、支付、Pi 和付费比较仍分开。

## 2026-11-06 · Verified offline result in the same conversation

- **目标：**文字或语音改口提交后，在同一条对话显示既有离线 Work 执行器的一项已核验结果。结果要体现改后的目标。不调用付费模型，不接真实账号、支付或 Pi。
- **完成：**`ConversationWork` 在 steer 之后只推进这一次运行的既有确定性执行器，并读回已发布 Markdown 的 `Goal:` 行。未核验、失败和中断都不是成功回复。未知结果用同一操作号恢复，且不第二次发布。另一个登录看不到这条对话里的结果。配对设备是 403。Full access 不产生作业或建议。
- **验证：**`uv run --no-sync ruff check` 通过。`python -m pytest tests/test_conversation_work.py tests/test_integration_acceptance.py -q` 为 67 passed（对话 60、整合验收 7）。全量 `python -m pytest -q` 为 1828 passed、1 failed；失败项是既有 `test_public_unicast[::ffff:93.184.216.34]`。前端 `npm test` 为 323 passed，`tsc --noEmit` 通过。付费调用 0，无 GitHub Actions。记录见 [QA](output/qa/2026-11-06-conversation-work-verified-result/verification.md)。
- **剩余：**后一轮提问还不能再次读出这一条已核验结果。真实账号、支付、Pi 和付费比较仍分开。Codex 合并顺序是 #89 → #90 → #91 → 本 PR。



## 2026-11-06 待合并PR组合审查

冻结73／87／88／89–92，独立codex/openai-personal-agent-20261106组合，保留所有祖先。根状态文档保留最新软件状态，网络历史保留并服从后续物理重启澄清。修复邮件／日历源内容指令误判、旧assistant回执兼容、报告核验语义及Goal前缀误匹配；新增4回归。1949后端／328前端、类型／生产构建／Ruff通过；浏览器实际先拒绝来源指令，再改已有Work目标并显示文件核验，控制台无错误。新费用调用0、无CI、未更改Pi现场网络。完整证据及即将记录的合并回执见[本轮QA](output/qa/2026-11-06-openai-agent-merge/verification.md)。后续继续默认OpenAI和真实浏览器／computer use接入。


## 2026-11-06 OpenAI default and general browser milestone

User asked to review/fix/merge pending GitHub work, broaden toward Dot/Grok Bot/Muse and shopping/travel/computer use, default to OpenAI, then selected general browser first without fixed websites. PR93merged73/87/88/89-92after source-instruction, old-receipt and misleading-result fixes; reviewed tree matches main.

Implemented native Responses computer protocol, fresh browser executor, typed actions, owner-selected public sites/screen sharing, actual screenshots, explicit state continuation and normal stop recovery on existing jobs/permissions. Added OpenAI Responses text/default configuration and protected existing-key references; no silent Qwen fallback. Refreshed primary-source research and documented authenticated-account/payment/interactive-takeover gaps.

Full feature backend1991/frontend330, subsequent33configuration/OpenAI/computer and95browser/job checks, typecheck/build/Ruff passed. Real Mac Chrome shopping/flight/public catalogue/stop cases and shared desktop/phone UI passed; planning remained scripted. Pi initially hit Chromium Unix-socket path length; private short scratch fixed it without disabling sandbox. A later connection loss produced no success receipt; owner unplugged/reconnected. Host/data/source were verified,20-file stopped backup copied and verified on Mac, source3ffb857activated with old release retained. Pi then passed actual shopping/flights/stop cases under bounded NoNewPrivileges units. No real orders/bookings or paid inference.

Mac normal8831/5190is configured and Pi8891relay/device UI was verified with Alice. Pi OpenAI model catalog403unsupported-region is shown explicitly and cloud requests disabled; MacGET200is not live inference acceptance. Red-LED diagnosis stayed paused. Existing account/data, applications, network configuration and wake weights preserved; no native package rebuild or human voice claim.

Source pushed, draftPR94created through authenticated browser after connector transport failure/local PAT write limitation. Final docs/QA/handoff, local links and publish scope were checked; final remote HEAD readback is retained in the publication receipt. Evidence: output/qa/2026-11-06-openai-agent-merge; private receipts/screens/backups under ~/.config/desk-companion/openai-computer-use-20261106. Next: one owner-started live public-browser task with actual usage and output verification; old paid budgets remain closed.


## 2026-11-07 Pi -> owned VPS -> OpenAI

Owner first asked for VPS-backed real merchant/payment/ticket/takeover work, selected JD/Taobao, then explicitly prioritized Pi OpenAI connectivity. Read focused entry/contracts/current source and official documentation; real-account findings were recorded without claiming implementation.

VPS TLS/unauthenticated401passed. Pi's initial forward was rejected by the existing per-key discard-port restriction. Replaced only that outbound target with api.openai.com:443, preserving key identity, restrict/forced command and management reverse grant. Added two bounded loopback Pi services and explicit OpenAI-only transport selection to text/computer/Realtime; no key copied to VPS, no TLS bypass or general proxy changes. Fixed the real websockets Host-without-default-port compatibility issue.

Actual Pi model-list200with96models and configured IDs; actual Realtime session.created for gpt-realtime-2.1and normal close. No audio/response.create/paid inference.357cross-provider regressions,14final bridge checks and Ruff passed.21-file stopped backup copied/rehash-verified on Mac; source9625f137and284runtime files activated with previous environment/source retained. Normal text/voice/computer configured, owner identity retained, background generation off. Actual Pi UI shows Alice, enabled voice and unchecked wake; old region notice removed. Mac viewer relay was restarted, independent of Pi's permanent OpenAI services. No physical reboot or power investigation.

Evidence: output/qa/2026-11-07-openai-vps; private SSH/probe/backup/readback files under ~/.config/desk-companion/openai-vps-20261107. Source publication extends the existing independent OpenAI/browser review, with remote head verification. Next is real JD owner takeover/login and deliberate return to Alice; transactions and paid inference still require their concrete inputs/authority.


## 2026-11-07 Live OpenAI commerce/travel/mail tests and Pi fixes

Owner requested real tests beyond office apps, approved a fresh USD1 ceiling and one harmless message to their own test mailbox. Ran31actual GPT6.1Sol generations on Pi through its owned VPS; conservative accounting USD0.37970163, every receipt reconciled and the durable ledger closed. No old budget reopened, CI or hardware/power investigation.

Real-model controlled browser work passed cart preparation and changed price/quantity/coupon/shipping with explicit stored-state continuation, flight comparison including baggage/fees/next-day arrival, separately initiated calendar-tool followup with timezone conversion/approval/idempotence, and cancellation during a provider response. Real JD reached verification; Cathay failed initial load. FYP's adversarial email draft stayed bound to owner fields. Exact draft sent once using Codex Gmail and independently read back in the owner's inbox; this is connector-assisted delivery, while native FYP mail remains unconnected. No order, booking, payment or ticket occurred.

Fixed actual API JSON-mode and pointer-modifier mismatches; navigation/capture/input races and stored-state filtering; bounded initial-load diagnostics; misleading calendar local-time/reminder schema; lost/stale usage receipts after cancellation. Background writes remain blocked. The test-only folder fixture uses a stable clock after retained DB timestamps exposed a host wall-clock jump during the full suite. Final2036backend/330frontend, types/build/Ruff and actual Pi browser-scope/free-shopping regressions passed. Failed intermediate live cases remain in private evidence.

Source d40457fe activated on Pi after a stopped/checkpointed21-file backup copied/verified on Mac and288source/asset checks. Two interrupted management transfers were reconciled before switching the active release. Owner data/keys, schema, Alice, wake assets, office executors and provider environment preserved; normal readiness and exact frontend read back, no model call during deployment. Mac normal service/native builds were not changed.

Updated product, research status, browser/VPS/application/maintenance/delivery contracts, decisions, entry and handoff. Public evidence: output/qa/2026-11-07-live-agent-eval (sanitized results, fictional screenshots, runtime receipt). Private raw reports, closed-ledger receipt, exact email delivery and backup: ~/.config/desk-companion/live-agent-eval-20261107. Publication is a separate receipt. Next: implement owner takeover/return for the existing generic browser job; real mailbox/account/transaction and autonomous voice acceptance stay open.


PR94 closeout: published reviewed head7043510a, marked ready and merged asa9fb6da; fetched remote main and verified exact whole-tree equality. Final administrative documentation records this result; deployed code remainsd40457fe. No CI. See the dated publication receipt.


## 2026-11-07 Open Web and phone previews

Owner requested both interfaces for inspection. Started current source855e60ee using the existing Mac owner runtime on8831and Vite5190; opened desktop Chrome and a393x852in-app phone preview. Cleared unsuccessful temporary CDP metric overrides and used the supported in-app viewport setting. Both pages visibly show connected status, Alice/composer and OpenAI Realtime with microphone off, and are retained for the owner. No app-code/configuration edit, native rebuild, model request or Pi change. Read/display evidence: output/qa/2026-11-07-web-phone-preview/verification.md; private process logs under ~/.config/desk-companion/web-phone-preview-20261107. Current product next step is unchanged.


## 2026-11-07 · Shared Alice home, permission recovery and GPT Live

- Goal: carry the accepted phone visual to Web/Pi, keep Alice dominant with full phone calendar/time/weather, restore hands-free local Alice wake and integrate the owner's selected GPT Live route. Later corrections covered flickering input, overlapping read errors and repeated location prompts.
- Completed: shared scene/agenda/conditions, existing-reader reuse, dark composer and optional navigation; bounded short-screen agenda; pre-paint input sizing and one read recovery row; loopback cookie names per port; permission-aware/coarsened location with single pending read, five-second watch deadline, durable failure flag and explicit retry. Existing owner data, licensing, drafts and permissions retained.
- Voice: native Live/Responses adapter within current VoiceService/ToolDispatcher, invariant Alice identity, persistent local opt-in, single wake/voice capture slot, bounded history/session and reconciled receipts. Main Mac wake configuration fixed. Realtime retained explicitly; Live voice-only, typed Responses unchanged.
- Validation:2051backend/341frontend, Ruff/Prettier/types/build; actual Web/phone navigation/draft/responsive/read-fault checks, stable8-sample input geometry, final1000Mac HTTP responses all200; local synthetic positive/negative wake clips. Fresh authorized real Live trial20providerseconds/two backend requests, correct Alice and calendar read, no writes, received audio and slot release. ConservativeUSD0.0518613333; ledger closed. No human/acoustic quality ranking.
- Runtime: source1660ffc active on Mac/Pi;292release hashes; safe21-file stopped backup/off-device verification; original keys/data and existing VPS route preserved. Configuration/UI readiness is separate from physical Pi microphone/speaker acceptance. No new paid activation calls, CI or power investigation.
- Files: [contract](desk-companion/docs/alice-home.md), [QA](output/qa/2026-11-07-alice-home-wake/verification.md), [activation](output/qa/2026-11-07-alice-home-wake/activation-summary.json), private media/backup under owner config. Updated product/decisions/voice/connection/maintenance/handoff/entry. Original preview-only records preserved.
- Remaining: human wake/interrupt/AEC, native background and physical Pi audio; browser owner takeover/login/real transaction receipts and native sender remain separate work. Next product slice is explicit owner takeover and return in the same generic browser job.

Publication: [PR97](https://github.com/tantalum666/FYP/pull/97) open/unmerged; independent branch pushed, reviewed source/docs head85f91f9 verified remotely before receipt-only follow-up. Runtime source1660ffc remains separate from publication.


## 2026-11-07 · Owner-reported wake failure and complete self-acceptance

- Owner asked why calling Alice failed despite Mac microphone access, then explicitly requested autonomous complete acceptance. Found full-catalog schema conversion deleting business title fields; actual27-tool preflight400before/200after confirms the defect. Earlier paid fixture advertised a restricted query list; corrected its documented scope.
- Added exact shared input selection for local meter/wake/voice, with session fallback if storage is blocked; normal Web saved to built-in Mac microphone and real local levels read back. Safe failure identifiers and phase now survive in existing receipts; retry clears the old notice. No authority, system-wide audio setting, dependency or CI change.
- Actual complete-app browser fixture used native permission/capture lifecycle and synthetic transmitted MediaStream, full27tools, real Live/Sol/calendar and playback. Two greeting/idle cycles plus one complete identity/calendar cycle finalized, resumed local waiting and made no calendar writes. First useful playback6.393seconds; human/noise/AEC statistics remain unmeasured. Private fixture streams/tab/server cleaned up.
- Fresh engineering capUSD0.50; final conservativeUSD0.1864995with all receipts finalized, ledger closed. No older budget reopened.2054backend/343frontend, lint/types/build pass. Details: [repair QA](output/qa/2026-11-07-alice-wake-repair/verification.md).
- Sourcef2a33e9active on Mac/Pi after292file hashes and a22-file stopped/checkpointed backup verified off-device. Pi keys/environment/VPS route unchanged; physical audio still separate. [Activation](output/qa/2026-11-07-alice-wake-repair/activation-summary.json). Updated current contracts, product/decisions/handoff/entry and earlier smoke-test scope note. Next: offline useful-answer latency profiling before the later merchant takeover slice.


## 2026-11-08 · Voice UI closeout

The actual model-answer screenshot exposed an optional Work-conversion card covering the home. Kept its state mounted but moved visibility behind expanded Conversation; offline browser replay verified hidden/visible/hidden with the same content retained.343frontend tests/types/build passed again, zero paid calls. Final source3079390active on Mac/Pi;292Pi files verified and environment/keys unchanged. Core voice2054backend and full-browser acceptance remain tied to unchanged f2a33e9logic. Updated current routing, contracts and [repair QA](output/qa/2026-11-07-alice-wake-repair/verification.md). PR97 stays open/unmerged; all test ledgers closed.

## 2026-11-08 Latest-turn conversation and Alice voice preferences

Owner requested latest-only home speech, distinct multi-turn history, removal of Voice input cards, readable dark styling and a light/natural Mandarin/English/Cantonese voice. Implemented independent timeline grouping and existing RAM updates after grounding, clean history layout and owner-versioned Live voice/delivery preferences. A free original prompt voice was created; the real USD0.25 audition failed before output with no final receipt, so USD0.249remains conservatively reserved in its closed ledger. Silent startup buffer and disconnect-drain failures were repaired; no additional paid call without the pending fresh approval.

Local2064backend/348frontend tests, lint/types/build pass. Actual separate desktop/phone browser replay verified two exchanges, late fragments,6.5-second startup, a real local calendar_query, no Voice input cards, contrast/scroll/composer boundaries and settings save/reload. This is offline protocol evidence, not naturalness acceptance. Source00387d6activated on Mac/Pi after stopped/checkpointed private backups (11/22files; Pi checked off-device),293Pi file hashes and preserved environment/credentials. Voice profile selected for next call; preview unavailable. No CI, new package, power investigation or native/human audio claim.

Updated product, decisions, Alice/voice/desktop/maintenance and legacy voice-work boundaries, handoff and START. Evidence: [QA](output/qa/2026-11-08-dialogue-voice/verification.md), [activation](output/qa/2026-11-08-dialogue-voice/activation-summary.json). Next: approved capped voice-only trilingual sample with final receipt, then cache output for repeat audition. Original voice IDs, private files, audio and backups excluded from Git.

## 2026-11-08 19:29 HKT · Open owner test pages

Opened normal Web and phone preview; restored the existing loopback-onlyPi8891forward and confirmed all three services reachable. Owner will test personally. No source/deployment/CI/paid-model change or microphone activation. Updated [handoff](handoff.md) and [port evidence](output/qa/2026-11-08-owner-preview/verification.md); original voice quality remains unverified until actual results.


## 2026-11-08 Evening · Native email connections, captions and effective voice

The owner reported overlapping captions, an unwanted technical footer, missing native email and unnatural voice. Added wrapped dark captions, a measured phone conversation reserve, sustained speech onset, playback buffering/diagnostics and effective-voice echo checks. Bright is selected with actual cached samples. The fresh USD1 round closed at conservative USD0.346456 with five finalized sessions. The first full-browser attempt failed on review timeout; after repair the second 29-tool run passed. The later 30-tool catalog has local coverage and no additional paid run.

The owner rejected SMTP/app-password setup. Replaced it with bundled Google/Microsoft browser OAuth, shared PKCE/encrypted tokens, bounded reads and existing owner review. Actual owner Google consent, native FYP self-send and independent Gmail provider-ID/content readback in SENT/INBOX passed once. Google Calendar is configured; Microsoft365/Teams/SharePoint software is prepared, with actual authorization explicitly deferred. Office file-directory access is not cloud editing; no automatic mail monitoring or real purchase was added.

2103 backend/351 frontend checks, types/build/lint passed. Desktop/393×852/320×568 checks found and fixed long-caption/agenda overlap without shrinking Alice. Source232b065 is active on Mac/Pi;305Pi source/asset hashes and both services verified; original owner keys retained. Initial Pi activation rolled back after the operator package omitted configuration files. All five tracked config files were restored and an isolated workspace returned200 before the successful retry. Mac stopped backup and the22-file Pi/off-device backup were verified. Client/voice cache installed privately; Mac account grant not copied to Pi.

Updated product, decisions, research, app/home/voice/maintenance/conversation contracts, entries, handoff and [current QA](output/qa/2026-11-08-caption-mail-voice/verification.md). The Pi preview visibly shows Alice and the new home; temporary QA server/tab and overrides were cleared. Publication and remote HEAD are recorded separately. No CI, closed-budget reopening, power investigation or human/native-audio acceptance. Next: owner takeover/return in the existing browser job.

Publication: [PR97](https://github.com/tantalum666/FYP/pull/97) remains open/unmerged. Reviewed code/activation head1afb556 was pushed and matched the remote branch; [publication receipt](output/qa/2026-11-08-caption-mail-voice/publication.json) records the check. Runtime source remains232b065.


## 2026-11-09 · Reference voice feasibility and Outlook identity

Confirmed the owner's newly connected personal Outlook account through the plugin profile only; FYP Microsoft configuration remains absent. Reviewed/pinned VibeVoice, GPT-SoVITS and Fish Speech primary sources, including current V5/Drama3 distinctions, language/reference/platform capabilities and code/weight licensing. Verified Mac/Pi/VPS resources read-only. Owner selected a reference voice they approve and have rights to use; no clip yet supplied.

Delivered [research and integration proposal](research/2026-11-09-custom-alice-voice.md), a14-line fictional trilingual/mixed-language audition corpus and [QA](output/qa/2026-11-09-custom-voice-research/verification.md). Marked current Bright as technically selected but not owner-accepted; GPT-SoVITS first remains an engineering proposal. Updated current product, decision, voice contract, research index, handoff and continuation entry. JSON/link/diff/secret checks only; no app code, runtime/default, model installation, paid inference or deployment changed. Next: obtain approved reference/transcript and run the bounded local audition.


## 2026-11-09 · GPT-SoVITS technical testing and classroom Ethernet

User selected GPT-SoVITS testing and requested classroom Pi access. Verified wired DHCP/preferred route and original-pin SSH through the existing VPS; app, automatic-owner workspace/device page and OpenAI models metadata read passed. Direct LAN SSH was closed. One-shot Mac preview dropped; unchanged Pi boot ID was confirmed and the existing reconnecting launcher restored web/VNC loopback access. No network/security/power configuration changed.

Installed official04a44eb V2ProPlus CPU source/models in a separate Mac Python3.12 environment. Fixed missing resampy, upstream NLTK path and language-cache setup; retained the rejected auto-download record and used already verified offline corpus data. Generated six public-domain-reference test cases. Streaming first non-silent PCM1.641–2.679seconds in a short batch; variable slower repeat/initialization results preserved. First interruption followup timed out30seconds; repeat4.05seconds, so stability remains open. Local WhisperSmall content matched English/Mandarin; Cantonese numeric readback mismatch is unresolved. This is not a human naturalness/owner-voice pass.

Added the loopback-only evaluation probe and six passing boundary checks. Scoped lint/compile and JSON/link/artifact/diff checks complete; no full production test rerun, deployment/default change, training, hosted generation or CI. Test API9880 stopped, source/model cache/samples retained, Pi preview kept available. Updated evaluation/network/product/research status, decisions, work log, handoff and entries. [Current QA](output/qa/2026-11-09-sovits-classroom/verification.md). Next: the owner's reference/transcript for the actual desired-voice audition.

## 2026-11-09 · Sweet Taiwan-Mandarin voice auditions

Owner rejected the SoVITS public-reference sound, clarified a sweet/soft/cute Taiwan-Mandarin direction, and explicitly approved USD0.10 for two original OpenAI samples, at most40seconds combined. Verified the normal Mac still selects Bright and has no active session. Checked current official custom-voice/pricing docs and relevant Doubao/Qwen catalog labels; catalog inspection was not a listening evaluation or provider switch.

Created two original young-adult feminine profiles, then generated the same short sentence through voice-only GPT Live. First free creation attempt failed on a short script_hint; longer guidance resolved it without changing audition text. Both distinct provider voice echoes, complete transcripts, valid non-clipped24kHz mono PCM16 WAVs and final usage were checked. Total provider duration20seconds; conservative USD0.0183333, fresh ledger CLOSED. No microphone, delegated model, business action or old-budget reopening. Presented both cached audio clips and requested subjective preference; no sound-quality claim is inferred from metadata.

Added [voice brief](planning/2026-11-09/alice-sweet-taiwan-voice.md) and [QA](output/qa/2026-11-09-sweet-taiwan-audition/verification.md); updated product/voice/evaluation/research/index/decisions and continuation routing. Prior SoVITS measurements remain with dated owner rejection. Audio, raw IDs, requests and ledger stay in the owner-private directory; public evidence is sanitized. JSON/link/artifact/budget/diff/material checks are scoped to this documentation/experiment change; production suites were not rerun. Runtime232b065/Bright remains unchanged, no CI or Pi/network/power change. Next: apply only a voice the owner explicitly accepts; English/Cantonese and actual dialogue quality remain separate later checks.

Publication: trial code/evidence4156a31 pushed to PR97 and remote HEAD verified. The PR remains open/unmerged; local experiment/default/runtime boundaries are unchanged. [Receipt](output/qa/2026-11-09-sovits-classroom/publication.json).


Same-day owner follow-up: A is promising but sounds too mature; retain it and refine toward a younger college/school-age impression. Kept original A and prepared an18–20-year-old adult college-freshman delivery using the exact same saved voice. The owner explicitly approved one additional20-second /USD0.03 session. A1 returned the same voice and full text, finalized9seconds at conservative USD0.00825; its separate ledger is CLOSED. Clip presented, listening feedback pending, production Bright unchanged. No new voice creation, microphone, delegated model, pitch/speed post-processing or old-budget reopening. Current next step is feedback on A1, not another blind sample batch.


Further owner feedback: A1 sounds older than original A, so A1 is rejected and A is retained. Changing only delivery did not meet the desired age impression. Created a new adult18–20Taiwan Campus base voice for A2, then received explicit USD0.05 /maximum3attempts /45seconds total authorization for sequential refinement. First connection reset before session.started/audio; USD0.0145 and15seconds remain conservatively allocated. Retry returned the requested new voice and complete text, finalized9seconds at USD0.00825. A2 clip presented; feedback pending. Current scope has one attempt left, max15seconds, conservative accounted USD0.02275; close on selection/cancellation/exhaustion. No automatic further generation or production-default switch; earlier ledgers remain closed.
