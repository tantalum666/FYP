# Group 2 Decision Log

Updated: 6 November 2026. Current state: [handoff](handoff.md). Pre-pivot Senplate entries are preserved in [the archive](archive/senplate/decision-log.md).

## 2026-09-25 用户推翻 Senplate，研究智能工作台新方向

- **用户决定：**明确“推翻整个方案”，转向组员的智能工作台／AI电子日历材料；希望研究语音AI、具形象的桌面陪伴、小型全息视觉和机械臂可能性。用户补充使用环境可为家庭或办公室职员桌面，没有已选定的真实试点或更细人群。旧 Senplate 提案、品牌、采购及本地软件不再定义本组当前FYP，原成果保留为历史。
- **输入与证据：**两份组员文件是设想／竞品判断，不是老师要求或已验证事实；用户指定的 OpenAI Developers X 视频已在其 Chrome 播放并检查关键画面，配合官方技术文章核对。公开资料显示 Echo Show 已有存在感知、Razer AVA 已展示带语音与角色的桌面产品、姿态提醒和数字日历也有成熟替代；原材料“智能屏一概只能被动显示”的主张不成立。
- **工程建议而非用户批准：**以“情境感知的桌面任务转换与休息提醒”作为单一可测主问题；存在传感器＋日程紧迫度＋明确专注模式决定提示时机和强度，按钮／按需语音完成确认与再次核对。坐姿、非临床交流、反射影像和轻量云台作为受控扩展，不把临床情绪识别或全息机械臂设成必做。方案、对照基线、成本、竞争和证据边界在[新研究](research/2026-09-25-desk-companion/feasibility-review.md)。
- **状态和替代关系：**[当前产品规范](product.md)取代旧内容，旧全文保存在[历史副本](archive/senplate/product-senplate-historical.md)。2026-09-21食品[Proposal](archive/senplate/planning/2026-09-21/proposal-spec.md)的 Word／PDF 未修改，不能用于新方向提交；新 Proposal 尚未生成，Marco 未正式批准新题。9月28日是团队先交目标，9月29日23:59为截图所示平台期限，需双格式。

### 同日补充：语音成本、自训与香港可用性

- **用户追问：**GPT-Live的活跃会话费太贵，询问其他模型和自行训练是否更好；没有指定某个新模型或授权采购／开通账号。
- **新核证据：**OpenAI Docs 将GPT-Live、按音频token收费的Realtime Mini和ASR→文字模型→TTS链分开；Google Gemini Live、阿里云Qwen实时及文字模型另作公开价比较。OpenAI API与Google Gemini Developer API地区清单未列香港；阿里云Model Studio列香港区域及Qwen文字模型明确价，但香港实时语音型号／价位仍要以实际工作空间核对。[语音专项](research/2026-09-25-desk-companion/voice-model-cost-review.md)。
- **工程建议而非用户决定：**首版以本地或可替换的三段式语音为主，按钮／屏幕和日历规则离线可用；香港可用文字模型按需接入。训练不从零做大语音模型，若取得足量反馈再训练“何时提醒”的轻量策略，优先验证现成多语言ASR和TTS在Pi上的真实表现。旧研究中直接依赖GPT-Live的表达已加地区提示；新Proposal未定稿。

### 同日再比较：免按键实时语音与设备工具

- **用户明确改变比较条件：**本次先不考虑地区问题和按键说话，要求再次比较语音模型的性价比，最好能自动操纵桌面设备。这是选型比较条件，并不等于已批准采购、开通账户或确定新题目的正式功能范围。
- **新核证据：**[同口径报告](research/2026-09-25-desk-companion/realtime-voice-model-comparison.md)核对Qwen3.8 Omni Flash Realtime、OpenAI Realtime 2.1／Mini与GPT-Live、Gemini3.8 Live、Nova2 Sonic、Grok Voice，以及ElevenAgents、Hume和本地链。公开价格及音频计量下，Qwen3.8在本次新增音频算例最低，具备服务端VAD、流式音频、自定义函数／MCP；完整月费、延迟、中英文、打断和正确动作率均无本组实测。
- **工程建议而非用户决定：**先以Qwen3.8 Omni Flash Realtime建立免按键语音＋Pi受限工具调用原型，并用OpenAI Realtime Mini、Gemini3.8 Live做同任务对照；本地唤醒词／VAD可自动开短会话，保留真正全天送音作为成本与误触发对照。日历写入需程序校验与明确确认，实体动作不得授予模型任意GPIO／shell权限。此前“按键说话首选”不再作为本次筛选前提。新学校Proposal仍待定稿。

### 同日用户确定语音候选的考虑顺序

- **用户决定：**接受类似“小度／小爱同学”的免按键唤醒词体验，语音模型按 **Qwen → Gemini → Realtime → Live** 优先考虑。此为候选和验证顺序，不等于要求同时集成四款或最终供应商已锁定。
- **名称解释：**依据前一轮明确比较对象，将“Realtime”暂对应OpenAI `gpt-realtime-2.1-mini`，“Live”对应 `gpt-live-1`；若用户以后指定完整版Realtime，应更新此映射，不把猜测写成用户点名的精确型号。
- **执行影响：**首个设备工具原型使用Qwen方向；Gemini为第二验证／回退，OpenAI Realtime第三，GPT-Live第四。当前仍没有API调用、Pi实测或实际费用；是否切换用同任务成功率、打断、延迟与实际费用决定。[比选报告](research/2026-09-25-desk-companion/realtime-voice-model-comparison.md)。

### 同日先制作新题目中文 Proposal 审阅稿

- **用户指令：**在正式英文稿之前，先写一份中文版供其查看。这是审阅顺序，不构成对当前研究命题、硬件清单或导师签名的批准。
- **文稿取舍：**按学校一页 Proposal Guidelines 的七项必需内容写[中文正文](planning/2026-09-25/desk-companion-proposal-zh-review.md)：问题、背景、系统方法与范围、适切性、阶段、交付物、组员职责；另列资源、风险、引用和导师／第二阅卷人意见留白。拟议主问题仍是桌面情境提醒，不把心理疾病治疗、六轴机械臂或全息投影列为首版承诺。Qwen为第一语音候选，其余按用户顺序作备选。
- **状态：**[可编辑中文Word](<output/docx/Group 2_DeskCompanion_ProjectProposal_ZH_Review.docx>)完成12页逐页渲染检查；正式英文DOCX／PDF、导师批准、签字与Moodle上传仍未发生。

### 同日用户纠正中文版 Proposal 范围

- **用户明确决定：**持续视觉坐姿监测是必做，必须判断并给反馈；机械臂大概率纳入。第一版以“提醒时机”作为抽象核心问题不符合团队原构想，“可检验的桌面工作流程”措辞过于抽象。要求重新看两份组员材料；学校Proposal若无调查访问要求就删除。
- **学校要求核对：**一页 `Proposal Guidelines AY26.doc` 的七项为问题、背景、方案与范围、适切性、阶段、交付物和成员责任；不要求访谈、问卷或调查访问。第二版删掉相应承诺，用可重复的姿态、反馈和日历功能测试说明验证方法。
- **第二版工程表述：**[中文版正文第二版](planning/2026-09-25/desk-companion-proposal-zh-review-v2.md)以固定机位摄像头识别持续可见前倾／侧歪、时间阈值、屏幕／语音／计划中2–3自由度轻载机械臂提示、复测是否回到个人基准为必做闭环；电子日历保留长期／重复／单日事项、私人／公开、冲突和TimeTable。单帧与持续时间判定对照，按人／日期分开的姿态测试，不能承诺医学健康效果。机械臂具体型号、安全与Pi负载尚未实测，不能把计划写成完成。
- **保留与状态：**第一版中文Markdown／12页Word原样保留为历史；[第二版14页Word](<output/docx/Group 2_DeskCompanion_ProjectProposal_ZH_Review_v2.docx>)已完成逐页渲染。正式英文DOCX/PDF、导师签字与提交均未发生。

## 2026-09-26 用户进一步明确 AVA 式外观偏好

- **用户偏好：**希望新设备尽量做成Razer AVA那样，询问实现复杂度。这加强了圆柱外壳、可见角色和语音互动的重要性；用户未指定必须实现Razer未公开的光学结构、360度观看或Windows PC Vision模式。
- **官方证据：**[Razer AVA](https://www.razer.com/razer-ava)展示圆柱装置、5.5英寸动态“3D hologram”、顶部摄像头／远场麦克风、灯、底部扬声器和USB-C口；FAQ说需直连Windows电脑，官方结构图不含机械臂。Razer没有公开足够的光学／外壳／性能数据供原样复刻。另核[Adafruit反射成像限制](https://learn.adafruit.com/monster-mask-augmented-eyes-toon-hat)及[Looking Glass Go光场屏](https://checkout.lookingglassfactory.com/products/looking-glass-go)的Mac支持；都不是AVA内部方案的证明。
- **工程建议而非用户最终选型：**按[形态复核](research/2026-09-26-desk-companion/razer-ava-like-feasibility.md)先试圆柱深色外罩＋小屏角色／灯环；反射像作第二光学样机，现成光场屏作需Mac主机的更高成本路线。固定姿态摄像头与机械臂分开安装，机械臂收在底座侧边。当前中文版第二版仍作为已完成审阅稿保留；具体外观路径须在光学、Pi并行负载和机械包络测试后写进正式英文稿。没有采购或实测。

### 同日补充：第一条圆柱小屏路线具体实施

- **用户追问：**若采用圆柱外壳、前向小屏和深色背景角色，具体如何做。用户尚未把Waveshare屏、Seeed麦阵列或其他SKU确定为采购项。
- **工程草案：**[A路线实施说明](planning/2026-09-26/ava-cylinder-route-a.md)把上盖麦阵列／灯／静音、筒身屏与遮光、底座Pi／扬声器／侧边机械臂分开；拟用5.5英寸HDMI AMOLED、USB四麦AEC阵列、可换位UVC姿态摄像头、PCA9685类伺服板和独立电源支路。角色与TimeTable按状态切换；本地姿态时间窗与复测优先，Qwen只经白名单工具请求日历／角色／预设臂位动作。是否内置姿态摄像头由视野测试决定，不为外形牺牲必做检测。
- **验证门槛：**先做正常室内光线下屏幕／外罩样机，再测筒顶与显示器边缘摄像头、Pi5并行姿态＋角色＋语音、机械包络／回声／供电。当前没有采购、接线或性能结果，故不承诺“真全息”、单USB-C带动整机、固定中文唤醒词准确率或具体SKU已兼容当前Pi系统。

### 同日补充：用户图片纠正 AVA 光学路线的优先顺序

- **用户观察与偏好：**用户指出AVA片中角色似乎不是一块正面可见屏幕；提供淘宝旋转风扇款和无风扇透明盒款图片，追问两者如何实现。这不是用户已确认某一具体SKU或下单决定。
- **公开证据及图片观察：**Razer官网明确写有5.5英寸display，但未公开屏幕位置或光路，故先前“直接塞正面屏”的说法不能用作AVA内部事实；风扇款图有旋转叶片，另一盒子侧放图有斜透明板。结合Adafruit的Pepper’s Ghost实作，后者**很可能**是隐藏屏＋斜透明片形成反射虚像，但卖家技术细节与AVA是否相同均未证实。[专项辨别](research/2026-09-26-desk-companion/ava-optics-fan-vs-reflection.md)。
- **修正的工程建议，尚非用户最终选型：**若目标是角色似乎悬浮，先用已有手机／小屏、黑色遮光及约45°透明片做无风扇反射像小台架；原前向屏A路线保留为后备／对照。旋转LED风扇与光场显示分别是不同技术，当前不作为首个台架。该修正取代本日志上方“先试前向小屏，再进阶反射像”的顺序，但不改变坐姿闭环、日历、语音和拟议机械臂要求。未购买、拆机或实测。

### 同日补充：旋转LED全息风扇的商品成熟度

- **用户追问：**全息风扇技术是否已很成熟；这是可行性询问，未指示购买或确认采用风扇。
- **证据：**HYPERVSN商业风扇有预制内容、HDMI／RTSP实时输入、保护配件与停机；18–20cm带罩桌面款亦有厂商产品页。但公开的小款页面通常只列App／Wi-Fi／文件更新，没有逐型号证实实时视频输入，不能借大机功能断言廉价小款可做语音口型同步。商用M款1m噪声数据也不能转移到小款。[成熟度专项](research/2026-09-26-desk-companion/hologram-fan-maturity.md)。
- **工程建议调整，非用户最终决定：**风扇不再因“像广告机”被排除；先用现有材料做反射像小样，并平行筛选**有保护罩、可实时输入的具体小款**，同桌面距离、光线、声音和角色状态切换条件下比较。原正面屏仍是保底。此项补充取代上段“风扇不作为首个台架”的工程取舍，AVA片真实光路仍未知；未采购或测试。

### 同日补充：预置片段和 HDMI 的关系

- **用户追问：**全息风扇是否只能播预置视频、即时反馈是否一定需要HDMI；这不是新的硬件选型决定。
- **官方资料：**HYPERVSN分别有机内Player、HDMI和RTSP Stream模式；HDFocus公开18cm款列文件／App更新，另一官方页面把实时HDMI系列列为100–180cm。厂商App能手动选预置视频，不自动证明Pi可程序切换。来源与边界写入[成熟度专项](research/2026-09-26-desk-companion/hologram-fan-maturity.md)。
- **工程解释：**坐姿事件可先由Pi即时驱动语音／灯，再经有文档的本地接口切换机内预置提醒片，因而不以HDMI为必要条件；逐帧口型或动态日历需要HDMI、实时流、逐帧SDK或开放机内渲染中的一种。选购小款前须证实自动切换接口和延迟，不能把手动App上传写成自动反馈。

## 2026-09-28 首份团队日志与新方向正式提案

- **用户确认：**本次日志按9月14至27日记录、9月28日填表。用户最新明确转述老师要求一组交一份；此决定取代此前助手从学校表头和Moodle个人文件名作出的个人提交推断。只制作Group 2团队版，Yuan为表头及文件名代表，三位成员在备注列出；内部个人贡献记录与提交份数分开。
- **学校当前证据：**只读Moodle确认日志#1于9月28日17:00截止、Proposal于9月29日23:59截止，均需DOCX及PDF。课程节点已写入新提案；HDAIST采用AI作为组员的公告并未给出最终评分比例，不自行分配。
- **工程建议：**在中文v2基础上补充可见姿态边界、数据划分和可测目标；角色显示保留反射像／带罩旋转LED择一，明确可编程片段切换与连续输入区别；机械臂仍是待验证轻载提示。6人分组、F1、误报与时延数值均为建议验收计划，不是用户批准的最终阈值或已实现成绩。
- **文件与替代：**[中文v3](planning/2026-09-28/desk-companion-proposal-zh-v3.md)及[对应英文](planning/2026-09-28/desk-companion-proposal-en.md)成为当前提案正文；英文双格式放入output/submission/2026-09-28，旧中文v1／v2、食品Proposal及学校原件保持。新日志1页、英文提案11页、中文12页均检查。
- **权限与事实：**本轮只完成本地文件和要求复核，没有上传、签名、导师正式批准、硬件／语音API／真人测试。

## 2026-09-28 新桌面项目软件范围与触摸屏

- **用户明确要求：**梳理软件、平台、跨端与显示内容；补充手机和电脑都可控制，希望设备有触摸屏直接操作。角色与日历是否共用显示区尚不确定。Linux追问是实现方式咨询，不是要求自研操作系统或指定Qt／原生框架。
- **工程建议：**[软件V1](planning/2026-09-28/desk-software-scope-v1.md)采用现成Raspberry Pi OS、React／TypeScript共享界面、Pi Chromium kiosk、Capacitor混合手机App和电脑浏览器，Python／FastAPI／SQLite本地核心；Flutter为备选。最终框架尚未获用户选择，不能记为既成实现。
- **显示与网络：**软件分开角色与日历场景；先同屏验证，再评估触摸屏＋独立悬浮区，用户尚未批准双显示单元。先局域网为建议，用户未回答是否首版必须支持外网远程，不以可跨平台代替网络打通；Android、后台推送与上架分别决定。
- **功能与边界：**持续姿态和提醒复测仍在设备独立运行；三入口共享日程与设置，冲突、重试、离线有明确状态；默认英文／简体中文。语音以设备麦克风为主，日历工具经校验、读回确认与真实结果；角色状态与显示技术分离，不用生成视频替代实时反馈。
- **状态：**本轮仅研究与规划，没有新应用编码、运行测试、API使用、采购或提交，学校Proposal／日志和旧食品代码保持。

### 同日日志纠正：一份中必须逐人列工作

- **老师要求，用户转述：**三个人做到一份里面，每个人的工作都要列出来；取代前版仅用整组口吻、备注列成员的填写方式。
- **用户安排授权：**询问两位组员实际工作及材料作者后，用户回复“你直接安排”。因此沿用既定职责整理个人归属草稿，不能把这句授权当作逐人既有工作和文档作者已经核实的证据。
- **实际处理：**新增一页member-breakdown-v2，姓名／学号表头三人齐全，Part I／II／III按Yuan、Xu、Li和共同项分别列，Not Done也分人。Yuan统筹及AI方案，Xu硬件／显示，Li日历／交互；只分配既有团队研究，备注明确成员核对稿；新硬件和API实验仍未完成。
- **保留：**旧日志及Proposal双格式原样保留。记录期9月14至27日、填表9月28日不变，9月28日触控跨端方案只写下阶段计划。未上传、签名或声称个人归属已通过确认。


## 2026-09-28 学校服务器与本地语音模型评估

- **用户新事实与要求：**转述老师可提供服务器部署AI，配置暂时未知；明确要求先按不同配置比较，不把取得配置作为本轮回答前提。未提供账号或授权远程安装。
- **工程建议，未锁定：**[比选](research/2026-09-28-local-voice/server-deployment-comparison.md)以Qwen3-ASR＋Qwen3.5-9B量化＋Qwen3-TTS为可检查的功能链，MiniCPM-o 4.5为中英自然双向语音对照；4B／0.6B作资源不足备选，Step-Audio 2 mini及Qwen3-Omni另列候选。不是同时实现全部，也不是已经比较出实测冠军。
- **部署边界：**不必买第三方API，学校自托管仍提供本组API并依赖设备到学校的获授权网络；本地姿态／日历／受限动作继续由Pi负责。免按键可由本地唤醒实现，打断、AEC和结束判断是独立工程；全双工须按具体模型与运行时能力核对。
- **配置口径：**24GB级GPU为模块化首测建议；MiniCPM PyTorch建议超过28GB、量化路线12GB起点不同。Qwen3-Omni约78.85GB是特定BF16视频配置，不当纯语音统一门槛；多卡显存不自动合并。
- **取代关系：**软件讨论不再预设商业Qwen云端是唯一语音路径；原商业提供商候选顺序仍保留。预训练推理先行，不从零训练。现有Proposal双格式、中文v3和日志原样保留；待资源及选型明确再修订正式文档。无下载、部署、训练、实测、外部联系或提交。

### 同日补充：服务器初步指向DGX-1／V100

- **用户原话：**“服务器配置好像是NVIDIA DGX-1（搭载Tesla V100）”。保留初步／待核，不写成已获全部8卡或固定显存。
- **官方证据：**DGX-1 V100有每卡16GB及32GB；V100为Volta sm_70。最新vLLM标准要求≥7.5；CUDA13移除Volta离线编译／相关库支持，PyTorch2.12仍有cu126 Volta发行包；标准FA2与BF16硬件路径需区别。完整证据及访问限制追加到[原比选第8节](research/2026-09-28-local-voice/server-deployment-comparison.md)。
- **工程修正：**不再仅按显存选型。先以兼容运行时＋Qwen3-8B量化／0.6B ASR／0.6B TTS验证，Qwen3.5-9B与MiniCPM-o后测；2张16GB按组件分卡或1张32GB为建议，不是最低保证。不能直接重用基于最新版vLLM-Omni的流式方案，也不能凭32GB保证MiniCPM原示例可运行。
- **状态：**未登录、运行nvidia-smi、下载权重、变更驱动或部署。学校Proposal与成员身份保留，首个下一步为实际配额／环境只读核对。

### 同日补充：自然交谈优先于本地分段链的部署便利

- **用户偏好：**“我还是想要更自然的语音体验，所以qwen能解决吗？”这是体验优先级，未明确坚持全部本地，也未批准收费API或选定某个型号。
- **新证据：**官方Qwen-Audio-3.1-Realtime-Plus指南、型号、客户端参数和技术报告摘要提供实时双向语音、smart_turn、语音表现力和工具资料；Qwen3.8 Omni Realtime仍支持音视频／工具。Qwen公开组织模型检索未见这两款同名开放权重；不把API示例或较早Qwen3-Omni权重当成同款。
- **工程建议调整：**按[比选第9节](research/2026-09-28-local-voice/server-deployment-comparison.md)重点对照3.1 Plus与3.8 Omni自然度／实际费用；V100分段链转作技术基线／备用。服务端duplex适配不自动等于模型原生全双工，不能由可加载或音色好听推导自然交谈达标。
- **验证安排与状态：**拟用N01–N08短时场景测试犹豫、附和、插话、改期、中英、噪声与失败；不新增市场问卷。没有试听、API调用、账号开通、实际账单或硬件测试。服务器仍待核，正式学校文件保持。

## 2026-09-29 重新比较自然语音与工具，加入第三方证据

- **用户明确要求：**先不考虑本地或API，以自然交谈和能调用工具为条件全面补查，并参考第三方测评。用户指出此前较晚才提Qwen-Audio-3.1，担心候选遗漏；本次不把历史Qwen优先偏好当作质量排序。
- **实际研究：**[新复核](research/2026-09-29-voice-ai/naturalness-and-tools-review.md)覆盖Gemini、OpenAI Realtime／Live、Qwen Audio／Omni、Grok、StepAudio3、Seeduplex／SeedRealtime、Nova、组合平台和开放模型。浏览器读取Jarvis榜单、配置、方法及转写；结合AA真人任务、工具轨迹、对话动态和测量说明。没有试听或亲自调用模型。
- **工程建议，尚非用户决定：**首轮同条件比较Gemini 3.8 Live、GPT-Realtime-2.1、Qwen-Audio-3.1-Realtime-Plus；若必须先接一款，Gemini为当前证据下的起点。Grok为工具强对照，StepAudio3／Seeduplex补入第二轮，GPT-Live与ElevenAgents按后台任务／角色声音需求比较。取代此前仅比较两款Qwen的首测建议，不承诺同时集成全部。
- **证据边界：**Jarvis自然度与AA任务成功测量不同，区间重叠不宣布显著胜负；英文、旧版与新中文场景不混排。Qwen3.1论文的半双工S2T工具成绩不能直比AA全双工S2S，3.0或TTS榜不代表3.1Realtime。StepAudio3慢首音是特定推理测试，SeedRealtime发布页不是已证实可直接集成的Seeduplex接口。
- **范围与状态：**保持本地姿态、日历、三端和受限机械预设；V100只约束后续自托管。正式Proposal／日志、成员资料保留。未开通账户、付费、部署、录音、联系外部或提交。

### 同日补充：加入价格的综合优先级

- **用户要求：**在刚完成的自然度／工具比较中增加价格，询问排名；没有选定型号、改变功能要求或批准收费调用。
- **新证据：**[价格补充](research/2026-09-29-voice-ai/price-and-value-ranking.md)刷新Google、Qwen Audio／Omni、OpenAI、Grok与ElevenAgents计费；浏览器核对StepAudio3 Realtime Preview限时免费，以及豆包统一实时语音价表。Audio3.1／Flash为12.5 tokens/s，Omni3.8输入7／输出12.5，不能混用。Grok默认server_vad按会话时长收费。
- **工程建议：**综合起点仍为Gemini3.8，Qwen Audio3.0 Flash／Omni3.8 Flash成为主要低价对照；Qwen3.1 Plus价格接近Gemini，保留中文质量对照。Step当前免费优先短测，不保证以后免费。学校本地方案不因未收调用费自动最划算。
- **算例边界：**一台设备、每天10分钟／月300分钟，表列新增音频／会话基础项；重复上下文、文字、思考、工具、后台、税和重试另算。豆包价表未逐版本映射3.0，不硬排名；没有实际账单或模型测试。学校文件不变。

## 2026-09-29 组员电子日历Part 1清单整理保存

- **用户要求：**转发组员总结，要求整理并保存；没有要求本轮实现全部功能、重做Proposal或选择模型。具体撰写成员未注明。
- **保存结果：**[原始正文](planning/2026-09-29/calendar-part1-teammate-source.md)与[功能整理稿](planning/2026-09-29/calendar-part1-functional-scope.md)分别保存。CAL-01至13对应主要功能，CAL-14至18保留增强建议性质，CAL-19仅记录原文标题下尚未定义的备份要求。
- **范围取代：**此前软件稿将天气／农历／外部同步／共享整体列作后续，是当时工程建议。新清单把它们纳入当前日历需求池，旧建议不再直接排除；本次整理不自动把全部功能升级为已批准首版验收。具体平台、同步方向、分享机制及提醒输出等待逐项细化。
- **整理时的工程解释：**批量日期与周期重复分开，私人详情与获准忙闲共享分开；公开不默认互联网公开，单机公开标记不能代替外部协同。gmail暂按Google Calendar整理，不追加邮件读取；CalDAV保留候选而不宣称已核实统一兼容。AI录入沿用澄清／确认／实际保存回执；Widget、后台提醒、同步和备份分别定义。
- **保持：**坐姿判断、反馈与复测必做，三处控制与英／简切换不变；角色和计划机械臂不删。框架、显示安排、语音最终型号仍未定；学校文件、身份资料、旧代码原样保留。后续转向首版日历与页面流程细化，不在本轮继续语音测试或外部行动。

## 2026-09-29至30 软件开发计划与B1实施

- **用户决定：**现在开始软件开发，先仔细梳理规划，再进行工作；界面偏好“简洁并高级”。这是本地开发授权，不是AI付费、设备采购、学校提交或外部联系授权。
- **工程选择：**先建立[开发计划](planning/2026-09-29/software-development-plan.md)，将日历19项输入全部对应B1–B5。采用React／TypeScript／Vite＋FastAPI／SQLite，放入独立`desk-companion/`；手机Capacitor、Pi kiosk仍待实物阶段。历史Flutter比较保留，但不再把本轮已实施框架记为尚未起步。Desk Companion仅开发名称。
- **执行顺序：**B1本地日历核心；B2尽早做相机／标定／持续判断／具体反馈／复测及连接；B3自然语音与角色／合格硬件输出；B4天气、双历、节假日、日期级忙闲、外部日历、真实分享与备份；B5整机收敛。日期级标记与事项级Busy／Free分开；前者不冒称B1全部完成。排期是工程安排，不是老师批准删除某项。
- **界面依据：**先用ImageGen生成完整电脑周历和手机Today，再保存token／组件规范及实现。助手按用户风格选作参考，没有声称用户逐页确认；代码与真实文本构成应用，没有截图冒充交互。实际日期／示例声明、提醒入口、私人图标属于必要差异。
- **B1结果：**真实持久化、认证、日周月、重复例外、批量、隐私展示、冲突、屏内提醒与记录、英简、版本和幂等恢复均已实现；1.5秒轮询共用API，尚未使用WebSocket。[QA](output/qa/desk-development-batch1-2026-09-29/verification.md)记录45项后端检查、生产构建及15组浏览器检查。发现并修复日期输入提交旧值、离线改日期后未刷新的问题、移动表单挤压及5xx结果未知时的重试保留。
- **边界：**仅Mac本地运行与浏览器尺寸验证。未接真实姿态、语音、API、机械、Pi或iPhone，未实现外部共享／同步／天气／农历；界面明确未连接。107项旧代码、学校文件和身份资料保持，不把AI辅助产物自动计入三位组员的实际贡献。

## 2026-09-30 常亮设备界面与手机／网页分开

- **用户明确纠正：**Linux设备屏会常亮，必须区分手机与网页；否定原B1设备构图。取代B1从手机Today延伸和更早常驻四栏的设备设计建议，手机／网页不受这一否决影响。
- **本轮工程选择：**[独立常亮规范](planning/2026-09-30/device-display-spec.md)采用大时间／日期、月历、近期安排、触摸控制与真实提醒；日夜独立配色、按日历时区自动切换、闲置60秒返回并保护编辑。日历为主是等待可选偏好回答后的工程起点，不是用户选项确认。相同React构建分出DeviceApp，不需要重做操作系统或另建日历业务。
- **执行结果：**先生成完整日夜参考，再实现真实代码与API数据；7项前端针对性检查、构建和[浏览器验证](output/qa/device-ambient-redesign-2026-09-30/verification.md)通过。修复小屏提醒／长标题挤压和两个共用日期问题。参考由助手选取，最终视觉待用户审阅。
- **常亮边界：**浏览器唤醒按实际返回显示启用／释放，测试后关闭，未改系统休眠。Pi开机、背光／触控与连续运行未实测；原8小时拥有者会话不延长，长期设备配对身份仍归B2。不是以关闭认证换取常亮。
- **保留：**学校文档、112项保护文件和后端源码不变；旧食品代码／品牌保留。未接API／相机／机械、未提交或外部联系。下一步仍B2真实姿态闭环。

## 2026-10-02至03 无需用户参与的软件集中完成

- **用户决定：**“把软件类的东西，不需要我参与的东西，全部搞定为止。”继续同一任务，不按批次自行停止。原始学校文件、旧食品方案与组员身份保持。
- **工程实施：**本轮按S1–S10接入姿态核心与采集适配、长期配对、受限助理、Qwen／Gemini实时协议及本地唤醒、命名输出驱动、角色、天气／双历／假期、交换／分享／备份、Google只读连接、Linux安装与iPhone。细节见[完成计划](planning/2026-10-02/software-completion-plan.md)。
- **平台决定：**iPhone采用Capacitor8.5.2，Keychain留存令牌；增加WidgetKit／App Intents／缓存本地通知，目标iOS17+。这是工程选择，未发布App Store。Xcode下载官方框架阻塞后，核查官方SHA并采用可复现的本地SPM引用，未改框架内容。
- **模型决定：**Mac的MediaPipe1.0.1 CPU图故障已复现，Mac固定0.10.35；Linux1.0.1有官方aarch64包，尚未实跑。唤醒使用官方中英3M int8模型，当前开发词为Hey desk／你好桌伴，品牌未定。没有从零训练或声称自然度／识别率已经验证。
- **功能口径：**文字规则模式与AI语音分开；Google为只读预览更新，ICS展开为选定范围内的副本，JSON恢复保留已有数据。角色是状态动画，未声称唇形或光学模块已实现。模型不能调用确认接口，实体动作排队与驱动回执分开。
- **验证边界：**隔离软件、合成输入、模拟语音协议、iPhone模拟器与App Group存储已检查；真实相机／音频／机械／Pi、本人OAuth和Apple真机签名仍需外部条件。原始音视频未采集，付费语音未调用，学校文件未提交。最终证据集中在[QA](output/qa/software-completion-2026-10-02/verification.md)。

## 2026-10-03 Your dot与主动事务跟进可行性

- **用户意向与澄清：**希望本组AI像新Dot一样自动跟踪事务；已确认指Codex／ChatGPT中的Your dot。当前请求为可行性分析，未指定全平台权限、最终模型或替换坐姿主线。
- **官方证据：**读取Meet dots、Tasks and memory及9月28日至10月2日更新；支持聊天之间继续跟进、持续笔记、自行安排再次检查及受支持事件触发。连接来源不自动建立监控；官方说明不证明本组具备同等实现或可直接嵌入Dot。
- **工程建议：**[首版方案](research/2026-10-03-dot/proactive-task-tracking.md)增加事务、进展依据和持久化跟进调度，先支持用户交代、补充进展和有意义的主动追问／日历草稿。模型按变化或检查时点调用，不要求全天活跃语音、额外硬件或从零训练。
- **范围与状态：**现有日历／语音／配对／屏幕可复用，通用任务记忆和主动跟进尚未开发。完成依据区分用户确认与系统回执，摄像头不证明任务完成。邮件／文件连接按具体范围再接，当前Google只读日历权限不含Gmail。只更新研究和路由，未启用个人监控、动作或新后台任务，学校文件与源码保留。

## 2026-10-03 主动事务首版及UI／UX审查实施

- **用户决定：**“先做软件增强，然后做一轮代码审查，这轮主要审查交互逻辑类，也就是ui和ux”。取代同日Dot研究中“尚未开始实施”的当前状态，不改变历史研究文本的证据身份。
- **工程实施：**增加独立事务／依据／持久检查、规则提醒、可选Qwen／Gemini文字模型、事务工具与待确认草稿，扩展Tasks／Today／独立设备入口及业务备份。模型仅准备草稿；完成需本人确认。默认不配置模型、不开放邮件／屏幕监控或外部执行。
- **审查与修复：**日期输入、步骤真实勾选和超限不截断、表单／偏好退出保护、并发版本恢复、读取断连文案、草稿动作说明、跟进历史刷新、私人投影、窄屏与来源标签均已修改并核对。原有日历／坐姿必做与设备独立构图保持。
- **验证：**[本轮QA](output/qa/task-enhancement-ux-2026-10-03/verification.md)记录101项后端、11项前端、Ruff、生产和iPhone模拟器构建及实际UI操作。原7条主事件和107项学校／身份／旧代码保护项不变。自然语音、真实文字提取、Pi和机械性能仍待实测，不把模拟协议当成自然度结果。
- **取代关系与权限：**[研究](research/2026-10-03-dot/proactive-task-tracking.md)转为历史基线，当前以[事务契约](desk-companion/docs/task-tracking.md)为准。没有批准具体付费型号、云部署、学校提交、外部联系或新个人数据接入。

## 2026-10-05 GitHub 全项目协作仓库

- **用户决定：**新建暂名 **FYP** 的 GitHub 仓库，上传全部项目工作，方便三位组员协作，并说明如何邀请组员。此次明确授权首次提交、建仓和推送，取代旧轮“未获初始 Git 提交授权”的当前限制；当前产品开发名称 Desk Companion 保持。
- **工程安排：**采用用户 `tantalum666` 下的私人仓库，保留当前 / 退役代码、学校文件、需求与研究、采购与设计、交付包和项目生成 QA；补入14份用户明确提供的原附件。排除凭据 / 私有运行数据、已安装依赖 / 缓存和本机字体链接；两份二进制 iOS 测试记录的本机测试密码被隐去，原记录在私有运行目录保留。
- **当前结果：**本地首次提交 `fc5c7c9` 已完成；[私人仓库](https://github.com/tantalum666/FYP)已通过 Chrome 建立。早期CLI令牌缺少新仓库权限，HTTPS推送403。用户随后明确同意仅增加FYP，并完成邮箱验证；仅该仓库范围已保存，其他权限保持。全项目推送成功，首次6,005文件远端路径 / 类型 / 模式 / Git内容哈希与本地完全一致；阻塞已解决。
- **协作边界：**[CONTRIBUTING.md](CONTRIBUTING.md)说明独立 Git 身份、克隆、运行、分支 / PR 和成员邀请。未发送成员邀请，未开源第三方资料，未改变软件功能、代签、提交学校或部署应用。

## 2026-10-05 RIG-Arm现成机械臂与更换AI评估

- **用户要求：**转述Marco推荐MakerWorld的RIG-Arm，提供LuwuDynamics组织链接，询问买整机及不用小智所用AI的二次开发程度。这是研究请求，未锁定采购、取消AVA显示或授权刷写实体设备。
- **本轮证据：**[研究](research/2026-10-05-rig-arm/secondary-development-review.md)核对官方整机US$124／套件US$109及预售、MCP两种方向、原理图发布入口、固件源码两份固定commit。Arm工具、动作／IK／反馈与local局域网HTTP MCP可定位；没有编译、运行或实测。
- **工程建议：**用现成ESP32／五总线舵机承担表达动作，Pi／Mac保留日历、主动事务、固定姿态摄像头、独立常亮触摸屏与可替换语音AI。RIG不需要另加UNO／PCA9685，当前PCA9685代码也不直接兼容它；新增受限驱动为后续。把原拟2至3DOF调整为可选5DOF硬件候选，非用户已批准数量变化。
- **模型与行为边界：**小智是语音框架；local文字LLM可换兼容端点，但其ASR／TTS路径及实时Qwen／Gemini并非填key即可互换。两个分支示教结束与默认微动不同，动作接受不等于完成，须固定版本并补取消／期限／回执／失联契约。
- **许可与保留：**omni README声明Apache2，local整体许可未核清；机械模型SDFL-C另有限制。仅保存本组研究、链接和原创规范，不把第三方源码／STL加入私人FYP。学校Proposal／日志及应用源码未改；Git研究成果按协作分支／PR保留，未自动合并或联系任何人。

## 2026-10-06 个人 Agent 核心、具身形态与电脑执行候选

- **用户明确要求：**本项目要做个人AI Agent，持续体验还不够，必须能在授权范围内真正操作电脑或软件；认可这一定位，并要求纳入可被其他模型调用的Codex computer-use接入方案。用户指出amontlabs/lcu比先前候选更值得关注，本轮将其提高到优先验证候选，不把关注度当可靠性结论。
- **用户分工与概念：**用户负责软件／AI，另两人负责硬件；RIG-Arm＋Pi＋屏幕＋可拆卸迷你桌面清洁模块作为讨论形态。具体两项硬件职责未对应姓名；ESP32、BOM／尺寸、采购、自动回座和无线充电未确认。
- **保留要求：**统一身份、持久任务／记忆、语音／屏幕、现有日历；固定摄像头的标定、持续判断、具体反馈与复测不被取消。坐姿与电脑执行是各自需要证据的能力。
- **工程建议，非供应商决定：**一个实时语音入口＋确定性持久任务核心，复杂任务按需文字推理；长工具快速返回job_id，权限绑定意图／版本，写入结果未知先读回。电脑服务可换API、浏览器或GUI执行器，机器人保持独立本地安全控制。
- **LCU证据边界：**第三方MIT包装层复用本机官方专有runtime，非完整开源引擎／再分发许可。Mac优先小验证；Linux没有同等逐应用审批，Pi adapter是agent框架。未证明本组Gemini／Qwen端到端兼容，未安装或采用。
- **取代关系：**这次明确电脑执行为核心，取代仅以“持续跟进即可满足个人Agent”的不完整定位；不改写此前软件已完成的原范围，也不取消固定姿态必做。完整[讨论与阶段计划](planning/2026-10-06/personal-agent-discussion-and-next-steps.md)成为本次新增能力入口；语音提供商与LCU正式采用仍未定。
- **授权与结果：**用户要求“开始吧，先把这轮的讨论结果推到github上”。因此本轮仅在私人仓库独立分支推送文档和QA；不合并RIG研究PR #1，不修改代码、安装、变更凭据／权限、付费、动硬件、采购、提交学校或部署。

## 2026-10-06 架构审查、云端延续与受限执行首版

- **用户决定：**读取GitHub并审查架构／层级，继续完成未完成的软件；随后明确优先使用云端，节省本地任务额度。已有本地开发已停止，单次获准交接后在云端继续。
- **工程选择：**保留模块化单体，在共享事务核心旁分出持久JobService与ComputerExecutor；首个适配器仅操作应用专用笔记目录。此范围证明真实文件写入与独立回执，不代表满足全部PC／GUI核心需求。
- **实际新增：**意图／版本审批、持久状态与恢复、未知结果只读对账、非阻塞语音工具及有界取消清理、拥有者作业UI。没有把模型提供商、LCU或硬件候选擅自定型。
- **修复依据：**独立审查及定向测试覆盖写后核验异常、Stop限额、任务分页、打断发送竞态、队列背压、UI未知请求恢复；完整证据见[云端QA](output/qa/software-completion-2026-10-06/verification.md)。
- **保留边界：**固定摄像头坐姿闭环、任务与作业分开、实体独立停止不变。不新增CI自动化，测试实际在云端运行。没有LCU安装、系统／浏览器权限、付费模型、真实GUI、硬件运行、学校提交、main合并或部署。

## 2026-10-09 Dot工作审查、修复及合并授权

- **用户决定：**“dot做了一些工作，你去github看一下并且合并应用，有问题的话你直接修”。授权检查私人FYP远端、修复、验证、合并及本地应用，取代10月6日云端交付当时不合并main／不恢复本地工作的限制；不扩大为LCU安装、系统权限、模型消费、硬件运行或学校提交。
- **工程安排：**从RIG研究`085dc01`建立`codex/dot-integration-20261009`，合入Dot代码`ba2b164`（含讨论`597cfe7`）；保留两边历史、研究和学校原件，同步过时产品／交接状态。受限笔记仍默认关闭，通用PC／GUI核心尚未完成。
- **发现与修复：**拒绝同ID的不同／无效参数时，语音结果循环仅凭ID标原调用已送达，断连漏掉原调用及迟到草稿清理。现要求送达结果对应该调用实际结果对象，两种失败回归转通过。修正容量提示指向尚不存在的归档操作，以及试运行说明可能移除可选依赖的步骤。
- **验证：**149项后端、15项前端、Ruff、TypeScript／Vite和实际三种界面检查通过；准备无文件、批准真实写入、取消、只读对账、回复丢失去重恢复、草稿保护与中英／窄屏均有[本地QA](output/qa/2026-10-09-dot-integration/verification.md)。真实模型／硬件、Pi与iPhone原生未重测，不把模拟协议称为自然语音测试。

- **实际交付读回：**[PR #2](https://github.com/tantalum666/FYP/pull/2)按已审查head `9bbd6d3`成功合并，main软件提交`8ca728d`；RIG PR #1也由GitHub标记已合并。本地main已快进并启动8831／5190，原7条日程内容hash一致、四个工作循环ready，新面板实际加载且默认未启用执行。后续提交只补充本轮收尾文档与证据，不改变已测试应用代码。

## 2026-10-14 拥有者记忆，沿用既有作业契约

- **用户决定：**Desk Companion 要接近 Meta Muse、ChatGPT Dot 和能在用户应用里行动的个人代理：保持记忆、后台工作、重大动作先征求批准，并保留坐姿、本地日历和中英界面。没有组员冲突，要求继续实现而不是只写文档。编码希望用可用的最强编码后端；本环境无法调用该后端，因此在当前分支完成这一片。
- **工程选择，不是把 PR #5 整支合入：**未合并的 agent kernel 叠在 PR #4 上，范围远大于这一步。main 已有专用笔记作业的批准、独立读回和取消。本步只加拥有者记忆：`desk/memory.py` 保存事实，`desk/context.py` 决定发给模型的内容，草稿仍走现有确认接口。不自托管模型，不要求付费密钥，不新开第二套作业系统。
- **未改变：**供应商锁定、学校正文、采购、合并 PR #4／#5、通用 GUI／LCU。下一步仍是 owner 指定的一个测试动作。

## 2026-10-14 指定文件夹沿用同一作业契约

- **用户决定：**继续接近 Muse／Dot／Grok-Bot。下一项是用笔记作业的同一契约做一个拥有者命名的测试应用或文件夹动作：批准全文、独立读回、取消。保持 PR #7 的记忆改动完整，并自行选定安全沙箱路径和结构。
- **工程选择：**不新开第二套队列。`JobService` 按动作选择执行器。`LocalNotesExecutor` 行为不变，仍受 `DESK_COMPUTER_ENABLED` 控制。新增 `FolderDropExecutor`，只把 `<作业ID>.txt` 新建到拥有者指定的一个绝对真实目录。路径存在 SQLite，作业里只留名称和路径指纹。目录必须已存在、不是符号链接，且不能是运行目录、其上级或其子目录。模型没有 path 字段。批准前目录变化返回 `COMPUTER_SCOPE_CHANGED`。
- **未改变：**供应商锁定、学校正文、采购、合并 PR #4／#5／#7、通用 GUI／LCU。下一步改为文字和语音共用一份人格文本。

## 2026-10-14 文字和语音共用一份人格

- **用户决定：**文件夹动作之后，若还有余量，继续做人格文件，再考虑把跟进单独调低。
- **工程选择：**`desk/persona.py` 保存一份正文。未编辑时用内置文本，版本为 1。拥有者替换后版本递增，可以恢复内置文本。`text_system`、`voice_instructions` 和 `followup_system` 都先放这段正文，再附加各自的工具协议，避免人格编辑删掉「不能自行确认」。模型没有写入工具。配对屏不能改。
- **已有跟进开关：**事务上的 `follow_up_enabled` 已经能停止新的本地检查。尚未拦住的是已经进入待处理状态的可选文字建议。
- **未改变：**供应商锁定、学校正文、采购、合并既有 PR、通用 GUI／LCU。

## 2026-10-14 关闭跟进后跳过已排队的文字建议

- **工程选择：**不新增第二套静音开关。事务更新关闭跟进时，待处理跟进本来就会被标为已处理。`enrich_one` 再检查 `follow_up_enabled`：即使队列里还有一条待处理跟进，也不把可选文字建议发给模型，也不删除事务。
- **未改变：**供应商锁定、学校正文、采购、合并既有 PR、通用 GUI／LCU。下一步改为：有花费上限之后才比较托管供应商。

## 2026-10-14 安静时段与限流跟进

- **用户决定：**继续接近 Muse／Dot／Grok-Bot，但不要付费试用托管模型，也不要做不受限的应用控制。跟进要能提醒，同时避免刷屏。
- **工程选择：**沿用工作空间已有的安静时段，不另做一套日程。安静时段内 `tasks.tick` 把到期检查推到时段结束，`enrich_one` 不调用模型。一次 tick 最多新建 3 条跟进，其余按分钟错开。关闭跟进的事务移出到期队列。
- **未改变：**供应商锁定、学校正文、采购、合并既有 PR、通用 GUI／LCU。

## 2026-10-14 作业卡片的可恢复说明

- **用户决定：**继续接近 Muse／Dot／Grok-Bot，但不要付费试用，也不要做不受限的应用控制。电脑作业的取消、读回和指纹失败要能看懂并恢复。
- **工程选择：**不改作业状态机。卡片根据已有 `result.reason` 和错误码说明下一步：核验已有文件，或按当前文件夹重新准备。指纹只显示前 12 位。
- **未改变：**执行器、批准全文、独立读回、供应商锁定、通用 GUI／LCU。

## 2026-10-14 文字适配器与作业绑定表

- **用户决定：**继续接近 Muse／Dot／Grok-Bot，但不要付费试用，也不要做不受限的应用控制。Qwen／Gemini 以后要能切换而不重写调用方。以后的应用动作要能挂到同一套作业上。
- **工程选择：**`text_providers.py` 登记 Qwen 与 Gemini。`generate` 只按配置取适配器。`JobService._bindings` 登记笔记和文件夹动作。新动作是多一行，不是第二套队列。测试使用模拟 HTTP，没有开通账号。
- **未改变：**供应商锁定、学校正文、采购、合并既有 PR、通用 GUI／LCU。下一步仍是有花费上限之后才比较托管供应商。

## 2026-10-14 安静时段跟随已保存的偏好

- **用户决定：**仍没有花费上限，不要开通托管模型账号，也不要做不受限的应用控制。组员需要 PR #6–#13 的合并顺序。安静时段的配置要能持久生效。
- **工程选择：**被推迟的跟进写入 `task_quiet_holds`。重启后不重复生成。保存的安静时段变了，下一次调度改到新的结束时间，或在已经不处于安静时段时放回队列，仍每次最多 3 条。本人指定的未来检查和延后会清掉这条推迟。文字适配器和语音适配器仍分开，因为报文不同。合并顺序写在 `planning/2026-10-14/pr-stack-merge-order.md`：先 #7 再 #8 至 #13，#6 在 #7 之后处理四个活文档的冲突。PR #4／#5 不并进这条线。
- **未改变：**供应商锁定、学校正文、采购、合并既有 PR、通用 GUI／LCU。

## 2026-10-14 Review before Codex merges

- **Owner decision:** Review PRs #6–#14. Mark them ready or leave them draft with required fixes. Do not merge. Codex merges later. Handoff text is English for that coding agent.
- **Review result:** No blocking defect in the folder path gate, the job contract, or the quiet-hour hold. PR #6’s original “extend PR #5” lines were stale. Those lines now point at the #7–#14 stack and still forbid opening a hosted account.
- **Unchanged:** No spend cap, so no provider trial. No unrestricted app control. PRs #4 and #5 stay unmerged. This review did not merge #6–#14.

## 2026-10-15 独立审查、修复并合并Grok bot工作

- **用户授权：**检查Git新增工作，确认没问题就合并。该新指令允许本批PR #6–#14的实际合并，取代这批文档中“留给Codex、尚未合并”的旧待办。
- **审查结果与工程修复：**记忆拥有者边界必须覆盖助理草稿／决定、文字上下文／缓存和语音；指定目录必须逐级无符号链接打开；人格重置不能复用旧版本，失败也不能清除未保存草稿。新增回归先复现后修复，并更新source-map-js到1.2.2。
- **交付方式：**先将修复以普通推送放回对应PR，逐层合并main以保留修复；功能栈使用merge commit。PR #6用普通merge对齐main，保留两边历史并修正过期路线，不使用force push。实际代码合并回执和182／17检查见[本轮QA](output/qa/2026-10-15-grok-review-merge/verification.md)。
- **范围：**A1完整2D及PR #4、PR #5另线保持；真实提供商／模型和花费上限未选择，未开账号或调用模型；真实应用、硬件和学校提交没有被测试数替代。

## 2026-10-23 硬件进度协作上传（不部署）

- **用户授权：**将本人当前FYP硬件工作上传到已确认的私人团队仓库tantalum666/FYP；不部署，由组员统一部署。用户明确允许本次仅核对相关文档与协作规范，覆盖AGENTS.md的本轮全量阅读要求，不永久改动该规则。
- **硬件成员Xu在该次讨论中确认的设计目标：**学校借Pi 5/microSD已有；单电池Mini、自动回座无线充电、15–20分钟、免焊且不依赖商家定制成品线、无面包板；固定主机英标Type-G单根主电源低压分配，主机无轮/垃圾仓。已有CAM不是普通30针主控。Mini最终尺寸未锁硬上限。
- **工程候选而非已定案：**Robo ESP32 + Maker ESP32、可选风机驱动、Grove传感器和带编码器行走件；详见[本次目录](research/2026-10-23-mini-robot-hardware/README.md)。SH转接链、电源/Qi、风机和结构尚未形成可装配闭环，不能按图册宣称整机已能直接采购或预算已达标。
- **上传边界：**新增硬件记录、最新PDF、去本机路径的来源和检查表，同步仓库入口/产品补充/交接/日志。保留既有软件、学校原件及历史材料；不上传升学/课程文件、凭据、本机运行区或第三方机械模型。创建分支与PR供组员审阅，不自动合并、运行部署或启用实物。

## 2026-10-26 硬件PR独立审查

- 仓库拥有者授权检查组员PR、修复后合并；原上传任务的“不自动合并”范围不限制本次新授权，部署仍未请求。
- 区分学校借机规格待核与Yuan已确认的Pi5 8GB测试机，保留Pi暂停。硬件成员的设计目标不直接升级为整组采购或台架批准。
- 按厂家资料修正5113输出轴9mm及Robo新加坡货币标注；原PDF保留并在入口附勘误。补命令身份／去重／期限／停止优先级和真实完成证据，均为待实现契约。

## 2026-10-26 Senplate集中归档与仓库入口整理

- **用户要求：**Senplate相关内容集中归档；检查组员未合并PR，有问题修复后合并。当前新任务取代上一轮真人语音验收的下一步，不启动新收费测试或恢复Pi工作。
- **归档：**5,127个原文件迁至`archive/senplate/`，保留Git历史、二进制和许可。旧食品决定／工作日志拆入归档；学校原件、桌面学校交付和成员身份保持独立入口，原身份记录的食品字段另存精确快照。
- **审查：**Xu的PR #17已修复并合并。其他4个开放PR为拥有者历史分支／草稿，依赖与冲突已记录；本轮不把已否决人物或未审查栈直接恢复到main。
- **工程修复：**归档路径触发PostgreSQL socket长度限制，开发集群改用既有客户端所用的loopback TCP；Vite修补到8.3.5，归档source-map-js到1.2.2，重新验证。应用业务源码保持。
- **当前状态：**AliceChan、统一Omni、语音计时和Linux最新增量在本地未发布工作区；根文档区分已提交与未发布，避免把早期主分支误称最新成果。证据见[整理QA](output/qa/2026-10-26-repo-cleanup/verification.md)。

## 2026-10-28 Maintainable AI/software and milestone publication

- **Owner instruction:** continue AI/software autonomously, build maintainable code, read Markdown selectively at startup, update docs/handoffs promptly, and push important milestones to GitHub. This replaces automatic full-library startup reading and the earlier no-publication boundary for the authorized milestone; it does not resume Pi or paid budgets.
- **Implementation:** separate phone presentation/data/environment responsibilities; share login, session recovery and event editing with web. Coalesce calendar reads, reject stale results and closed-editor responses, preserve scoped drafts, show blocked actions within the modal, and layer full conversation correctly.
- **AI correction:** selected task ID now reaches the real voice-start route, is resolved by the server and binds owner/task replay. Switching task closes the old connection and clears its resume handle; explicit input is still required to reconnect. Model approval rights and provider selection remain unchanged.
- **Evidence:**303backend/65frontend, lint/types/build, real browser save/readback/guards, controlled session-expiry and delayed-read recovery; native build/install/launch/visual proof. New provider tests are scripted, not new hosted-model quality results. Native touch/keyboard/real-device acceptance remains separate.
- **Publication choice:** integrate current application source on a new branch from archived main, preserve main's Vite8.3.5 and the original dirty checkout, add default-off CI, keep private runtime/authoring/raw history local. No blind merge of previous art/kernel/agent-loop PRs. Exact publication receipt is in the current QA/PR; source propagation is not main merge or Pi deployment.

## 2026-10-28 Grok stack and current baseline integration

- **Owner authorization:** review Grok's GitHub work and merge if sound; the owner explicitly chose to include #60, retaining the latest Alice/mobile/unified Omni baseline. This authorizes the reviewed integration and necessary repairs, superseding earlier per-slice “not merged” text. It does not include historical art/kernel PRs4/5/15/16 or hardware19, deployment, paid-model spending, media capture or Pi work.
- **Engineering decision:** preserve all captured source heads through an integration branch, retain #60's shared modules/layouts, and resolve old-base conflicts at responsibility boundaries. Do not adopt the unimplemented plan to start a second HTTP model loop from the Omni socket.
- **Privacy and execution:** keep temporary replay and recall focus in the existing login/task-scoped RAM container. Durable principal-scoped operation receipts are separate, allowing explicit same-owner recovery after reauthentication without replaying old chat. Fresh read tools do not reuse deleted facts. Backup final apply and goal-tagged drafts require owner authority; imported intents and folders must satisfy current schema/path/fingerprint controls.
- **Verification:** complete pre-fix196-file diff review, offline reproductions and independently recorded fixes;450 backend/89 frontend, type/build/lint and actual browser recovery/privacy/mobile checks. Retired one obsolete handoff prose assertion that enforced nonexistent APIs/unimplemented design; replaced it with actual cross-login recall behavior coverage. No behavior assertions were weakened to hide the original three failures.
- **Evidence/publication:** [integration QA](output/qa/2026-10-28-grok-review-merge/verification.md) and [receipts](output/qa/2026-10-28-grok-review-merge/publication.json) separate local validation, branch publication, GitHub merge and deployment. The historical software-chapter draft is not an updated or submitted Progress Report I.

- **Verified GitHub result:** integration PR61 merged reviewed head923a1e2 as mainc2037cd at2026-10-28T06:14:19Z. All41 original PRs20–60 read back merged;4/5/15/16/19 remain open. Hosted run40642113382 did not start because of the account-level restriction. No admin override, billing/protection change, deployment or new spending was used.

## 2026-10-28 用户重申：只做本地验证，不使用CI

- **用户决定：**“我说了不用CI，本地弄就好。”此要求取代此前添加工作流、排查Actions或把账户限制保留为待办的工程安排。
- **落实：**移除`.github/workflows/desk-companion.yml`，同步AGENTS、产品、协作、入口、维护规范和handoff；保留本地测试／lint／构建／实际交互验收。此前“default-off CI”的表述不准确：工作流实际配置了push、pull_request和手动触发，现撤除。
- **边界：**GitHub继续用于源码、PR及合并；不调整账单或申请额外Actions权限。历史CI失败记录保留为历史证据，不再是当前门槛。该次改动不修改应用源码；Grok质量评价以已完成的审查和复现为依据。

## 2026-10-28 继续推进：长期记忆与实际交付门槛

- **用户指令：**继续推进，指出离目标仍有距离。保留本学期软件／AI优先、可维护性、精简阅读与本地验收，不据此开启收费试验或恢复硬件。
- **工程修复：**把活动事实投影与最近40条提示窗口分开，查询／草稿检查和精确忘掉覆盖全部有效事实；修订指纹也覆盖旧事实删除／到期。保留200条存储上限、40条初始化／8条查询结果和确认时版本核对。网页／手机共用MemoryFactList，Panel继续负责请求和写入，搜索／并行更正不能替换未保存编辑。
- **实际证据：**先复现8个失败，再通过43项相关和459项全套后端；89前端、lint/types/build、42条虚构事实的实际搜索／更正／草稿保护／API读回。当前原生包已重装／启动并显示数据，但镜像／Device Hub输入没有可靠触控转换，因此原生软键盘仍未通过。
- **工程推进顺序：**新增按用户旅程而非功能数量记录的[交付门槛](desk-companion/docs/delivery-readiness.md)，下一步验证同一事务从批准作业到结果读回再到手机继续处理，沿用已有队列和证据。不是新建一套任务或代理系统，也不是声称当前产品已完成。
- **发布边界：**本轮重要增量经本地检查后推独立分支／PR，保留原工作区／学校原件／运行数据。该新功能PR不自动继承此前Grok整合的合并动作；最终分支／PR回执见本轮QA。

## 2026-10-29 跨端助理权限与对话内操作

- **用户决定：**指出Your plan和权限申请体验不合适，希望借鉴Codex／Muse／Dot／Grok，并可在设置中选择完整权限；随后明确“web版和应用端版也不应该这样，不止是手机端”。这些要求取代把批准流程集中在多层计划／作业管理弹窗的旧界面安排。
- **工程落实：**网页／手机／原生App共用对话操作卡片与输入框旁／Settings权限入口；手机管理改整页导航，Alice保留。Ask first默认；Full access仅对新拥有者请求中的已支持软件操作形成版本化持续授权，模型不能修改权限。旧待审／背景／配对／实体输出继续独立控制。
- **授权与恢复：**复用原业务服务和队列，来源记owner_policy或单次确认。撤回可从旧界面生效并围栏迟到的Full请求；排队自动作业执行前复核。丢失业务响应不阻塞权限设置；旧回执恢复不重放副作用。忘掉后保留无正文的请求身份，修复旧用户句子回流RAM上下文的问题。
- **证据：**489后端／89前端、lint/types/build/format及实际web／phone批准、自动执行、取消、丢回执恢复、事务接续与文件SHA／mtime读回。当前iPhone包重建安装并看到新版入口；镜像触控仍未成功，原生键盘不计通过。新模型相关检查仅离线／模拟。
- **发布与下一步：**本轮在PR64之上推独立分支／PR，不隐式合并。只做本地验证，不使用CI；Pi与旧收费预算保持暂停／关闭。下一步是混合软件任务的部分成功／撤回／重启恢复契约，沿用已有服务，不新增平行队列或聊天存储。详见[QA](output/qa/2026-10-29-assistant-permissions/verification.md)和[权限契约](desk-companion/docs/assistant-permissions.md)。

## 2026-10-29 OpenAI实时语音与新小额预算

- **用户授权：**表示OpenAI API约有170美元额度，要求节省，并测试“gpt voice”和“gpt live”；随后澄清两项都测实时语音。用户选择安全创建Key、确认组织／项目，并明确允许保存到FYP的desk-companion/.env.local。此前“所有供应商都未获新收费授权”的状态在本轮OpenAI范围内被取代；旧Qwen预算与Pi暂停不变。
- **工程限制：**先采用已向用户说明的5美元操作上限；不把170美元余额当实验预算。选用官方Realtime2.1和Live1＋Luna，Mini只作低价英文参照。独立评测脚本、合成PCM、隔离虚构数据与原有工具服务；不切换日常App或自动采集真人音视频。
- **实际结果：**16次真实短连接，11次最终控制条件检查；英／普／粤日历、待批记忆和合成插话通过各自检查。保留自动语言偏差、测试脚本过早收尾和Live含糊记忆铺垫句；固定语言、修正收尾与草稿措辞后复测。504后端／15专项检查通过，未运行CI。
- **费用／关闭：**基于已返回token／duration及当前官方价格保守估算USD0.3035168833，包含全部校准；不是已核Platform账单。全部用量回执已归集、16连接均结束，实际账本关闭后拒绝新预留。Key只在0600的Git忽略文件中。
- **下一步，尚未完成：**接进现有App会话／权限边界后做用户可控制的短A/B试听；真人语音、自然度、噪音／AEC、弱网、持续负载及多步骤业务恢复另验。没有最终排除Qwen／Gemini或决定只用OpenAI。详见[评测契约](desk-companion/docs/openai-voice-evaluation.md)与[QA](output/qa/2026-10-29-openai-realtime/verification.md)。

## 2026-10-30 提高真实应用任务复杂度

- **用户要求：**认为拟议的“写笔记并在浏览器核验”太简单，要求更难的真实任务。该要求将其降为冒烟检查，主门槛提高为多步骤、跨应用、可修改和恢复的工作。
- **工程选择：**采用虚构Group 2演示准备包：来源／版本核对、四家报价五版、跨币种／最低数量／运费／预留、Calc公式、Writer／PDF、两次日历排练及事务状态。首次改口故意形成不可行约束，须必要澄清后重算；另设回执丢失、重启、撤回和资料夹带指令变体。具体场景与权重是工程方案，并非用户逐条指定。
- **实际完成：**输入文件、报价HTML、控制器改口脚本、独立参考事实及六项离线一致性检查。没有运行模型或桌面应用，没有宣称完成复杂任务。现有六种笔记动作及单次effect循环不足，需要补受限办公应用适配器和持久阶段证据，沿用已有任务／作业／权限边界。
- **边界与下一步：**无新费用、CI、外部联系、采购、学校提交或硬件；旧OpenAI／Qwen付费轮保持关闭。下一步先补并离线验证应用执行／读回／恢复，再作同任务语音对照。方案见[规范](planning/2026-10-30/complex-application-acceptance.md)、[材料](desk-companion/evals/app_workflow_v1/README.md)和[QA](output/qa/2026-10-30-complex-app-task/verification.md)。

## 2026-10-30 实现受限应用执行与真实恢复

- **用户授权：**“开始这些工作吧”，承接更复杂的真实应用任务；沿用本地验证、可维护代码、更新交接和重要进度推 GitHub。没有新收费或硬件授权。
- **工程实现：**独立类型的 application 作业与原六种笔记动作并存，继续使用同一 JobService／PermissionService／TaskService。UNO／CDP 适配器只接收受限单元格、文档块、PDF及文字意图；来源与依赖哈希、任务和权限版本在发布前重核，暂存／不可变历史／活动文件分开。阶段从已有作业投影，不新增队列、聊天存储或一次性全能解题工具。
- **实际证据：**真实 Chromium 资料读取，Calc 809.60 → 彩印不可行 → 脚本澄清后 669.24，Writer／两页 PDF及其余产物；同日程 ID 改期；主进程保存后退出、应用重启和只读恢复保持文件 SHA／mtime。完整权限撤回阻止排队写入。524 后端／89 前端，网页与手机批准／修改／拒绝／下载通过。
- **实测修复：**先建齐工作表再解析公式，保留绝对单元格引用的 XLSX 规范化，Writer 样式名、PDF表格内容顺序及容器显示锁修复。失败记录保留，没有把未知写入自动重试。
- **环境选择与限制：**Mac UNO不可用后采用独立 ARM64 Linux VM，仅挂载虚构输入与产物；保留 Chromium 自身沙盒、内部网络和非 root 进程。无密钥、控制器答案或 core 数据库挂载。此选择不是 Pi／Wayland 或任意GUI验收。
- **下一步：**模型驱动的持久任务接续与离线变体，然后正常 App OpenAI 接入和另行限定的小额语音对照。受控脚本验收不等于语音 Agent 自主通过；旧预算继续关闭，调用为零。详见[执行契约](desk-companion/docs/application-execution.md)和[实际 QA](output/qa/2026-10-30-application-execution/verification.md)。

## 2026-10-30 恢复个人 Agent 研究与用户目标

- **用户纠正：**要求查看 Grok Bot、Meta Muse 和 Dot 实际如何实现，指出此前已要求多轮研究，不能再次当作缺少资料而泛泛解释。此前一条消息已明确邮件持续跟踪／建议、语音购买日用品和旅行预订的目标体验。
- **发现：**10 月 3、6、14–15、29 日研究／方案仍在当前树；最完整的六份三家机制／差距报告留在未合并 PR5 的固定提交 11dc2b84cebe6e8250b28ca4442fc91f0dfec676，当前树缺少它们。旧架构索引漏列 Grok，最新 handoff 没有持续携带研究入口；旧拆解还混入了 New Computer Dot。上一轮回答未恢复已有结论，是上下文和交接衔接遗漏。
- **已完成：**恢复六份研究原文主体（1,304 原始行／205,227 字节），加历史标记、原提交链接和哈希清单。重新核对 15 篇相关官方页面，区分成品机制、公开 API、当前 FYP 代码和未测效果。Muse 逐笔购买确认与 Grok Vault／Link 不同支付路线、Grok 新审批期限等变化进入当前索引。没有合并 PR5 的旧内核或 CI。
- **工程方向：**[统一研究入口](research/personal-agent-research-index.md)成为个人 Agent 任务恢复路由。下一个完整验收建议为真实邮箱变化→同一事务→有来源的建议／草稿→有意义通知，并在该旅程补模型接续；日用品采购与机票预订分别核验真实订单／支付／出票。Codex SDK、managed Agents API 和其他 loop 是候选后端，不能替代上述产品工作。
- **授权与证据：**本轮是研究和文档修正，未接入个人邮箱／创建监控、发信、购买、付费模型调用、原生重建、硬件或部署。用户目标不等于具体交易许可。PR68 软件证据保留原范围；当前不重复运行或重命名旧应用测试成绩。


## 2026-10-30 全部未合并 PR 审查与条件合并授权

- **用户明确授权：**询问旧 PR 为何未合并，并要求“你全都检查一遍没问题就合并”。该授权取代历史分片中对本轮审查／合并的暂缓安排；保留无 CI、Alice、现有用户数据、旧预算关闭及硬件暂停。
- **实际范围：**冻结 11 个开放 PR（4、5、15、16、19、64–69），在独立工作树审查。旧 5 原版后端实测 1,334 通过／46 失败；迁移目录 link count 误判已在诊断副本定位，修正后 129 项迁移专项通过，但当前 owner_memories 未映射到旧 personal_memories，旧接口看不到已存事实。原版内核、应用执行器和当前协议也冲突；未满足直接合并条件。
- **工程处置：**准备合入 19 和 64–69；4／16 的旧 A1 路线及 15 的早期 Omni 版本由新实现取代，完成主线整合后按 superseded 关闭，保留分支而不声称已合并。旧 5 保留待兼容移植，研究已通过 69 恢复。
- **候选验证：**最新 524 后端／89 前端、类型构建与 Ruff 通过；修正应用暂存取消回执文案，36 项针对性回归通过；网页／393px 手机记忆、批准、真实文件哈希、任务接续与草稿保护通过。19 的五页 PDF 原字节、预算与未报价状态已核对。未运行 CI／收费模型／硬件。最终远端合并状态以[本轮回执](output/qa/2026-10-30-all-pr-review/verification.md)为准。

- **实际远端结果：**PR70 已合并为 main `78e9bc2c343c629b7e66725a61f34bc46453dbe0`，与已测候选 `4872f7b` 的完整树一致。#19／#64–#69 已逐一读回 merged；#4／#15／#16 以 superseded 关闭且保留分支，不能称为 merged。#5 保持 open/draft，已附当前阻塞与复现证据。最后一轮只写发布回执与当前入口，代码不变。

## 2026-10-31 修复并合并 PR5 的明确授权

- **用户决定：**“你修复然后合并5”。本轮直接授权修复、完成本地验证后合并该PR，不再沿用30日只保留draft的临时处置。无CI、Alice保留、现有数据、旧付费轮关闭和Pi暂停不变。
- **兼容选择：**当前Runtime／owner_memories／TaskService／JobService／PermissionService和真实应用执行器为主；整合持久Work、来源产物、变化审阅、定期检查、可选保存会话及公开工具边界。普通Omni与保存会话标识分开，源数据只保留一套。旧A1和假记录应用按被当前实现取代处理，原代码留在Git历史。
- **修复：**迁移目录身份不再包含易变的目录链接数；旧事实转换需显式执行并在冲突时回滚；原主线事实无需复制即可被Work读取。删除正文后保留摘要重试屏障；被隐私清理的已关联提案仍受Work权限守卫保护。JSON有明确深度限制，真实provider dispatch重核上下文，生命周期清理互不跳过。
- **实际验证：**未修改的main代码生成schema1虚构库，两个迁移后45张原表逐行保持；网页创建Work、实际报告下载／哈希、一次批准、同一事务变化审阅、已读后安静，以及393px手机进展与Alice均已检查。测试、发布回执和仍未交付的外部旅程见[QA](output/qa/2026-10-31-pr5-repair/verification.md)。没有迁移真实数据库或开启模型／邮箱／支付／硬件服务。

- **实际发布：**PR5已于2026-10-31 02:20:17（Asia/Shanghai）合并，代码合并9b655e1；远端main与已测112f912完整树相同。最终1,686后端／300前端检查通过，文档收尾只记录回执与下一步，不改变已测应用。

## 2026-11-03 离线邮箱旅程（未接真实账户）

- **用户指令：**实现 handoff 点名的授权邮箱旅程，并且只从离线夹具开始。不连接 Gmail／Outlook，不索取或编造凭据，不花钱、不调用付费 API。复用现有 TaskService／Work／PermissionService／NoticeInbox，不另建任务、作业或记忆核心。发送不得自动发生。
- **工程选择：**用本地 `desk-mailbox-fixture-v1` 夹具和同一 SQLite 上的邮箱游标表驱动现有任务、提案和通知。Work 项就是现有任务 id，不新写 `agent_runs`，也不改 #73–#77 所属界面。邮箱草稿种类 `mailbox_reply` 不进入可自动执行的软件提案，确认只记任务备注且 `sent` 为 false。不把邮箱行放进便携 JSON 备份，因此本切片没有未校验的导入路径。
- **明确不做：**真实收件、发信、付费模型、撤销后的重新连接。这些都不是本轮用户授权。详见 [契约](desk-companion/docs/mailbox-journey.md) 与 [QA](output/qa/2026-11-03-mailbox-offline/verification.md)。

## 2026-11-03 补上离线邮箱的安静时段通知与便携备份

- **用户指令：**在同一分支补上 PR #79 列出的两个缺口。安静时段暂缓的有意义通知要在安静时段结束后送达，复用已有通知调度，不另建通知器。便携 JSON 备份要包含邮箱游标和持久摄取状态，沿用现有拥有者权限和导入前校验；恢复后再次同步不得产生重复事务。仍然只使用离线夹具。
- **工程选择：**暂缓的通知写入 `mailbox_notice_holds`，由现有 `Runtime.tick` 在安静时段结束后调用 `Notifier.publish`。投递或重复确认之后才删除暂缓行。便携备份增加 `mailbox_bundle`（连接、线程、已见消息指纹、同步尝试、暂缓通知）。缺这个键的旧备份仍可恢复。已存在的连接保持原游标，不覆盖。
- **明确不做：**不连接真实邮箱，不改 #73–#77，不开始购物或旅行模块。
## 2026-11-03 离线购物夹具进入现有事务

- **用户要求：**在邮箱旅程之外，用离线夹具做第二条验收：购物／购买意向映射到现有 Task／Work 和通知。不连接真实商店，不调用付费接口，不改邮箱、Pi 或 Codex Work 界面分支。
- **工程选择：**同一商品或订单对应一个事务和一条暂停的确定性 Work。游标在事件提交后前移。建议是 `shopping_advice` 草稿，只有拥有者确认才写入事务；完整软件权限不会自动批准这种草稿。价格降幅未过阈值、重复和未变化不发通知。
- **未授权：**没有商店账号、支付、自动结账、真实订单回执或语音下单验收。夹具结果不能写成已经购买。
- **同日补充：**可移植 JSON 备份纳入购物连接、游标、已应用回执、乱序缓冲和商品到事务的映射。预览先校验，恢复不改写已经存在的连接。备份不含会话、草稿、通知或 Work 运行行。下一次同步同一夹具不会另开事务。
## 2026-11-03 离线日程夹具旅程

- **用户指令：**第三条真实验收切片是离线日历／日程夹具，映射进现有 Task／Work 与通知。不要连接 Google／Outlook 或任何实时 API，不付费调用，不改邮箱和购物包，也不改 Pi 与 Codex Work UI。
- **工程选择而非用户批准连接账号：**新增 `desk/offline_calendar/`。一个事件或系列对应一个现有任务和一条本地日历记录；省略的地点、备注和提醒保持原值。冲突、会前准备和 RSVP 只产生带来源的草稿，拥有者确认后只写“未接受邀请、未发送 RSVP”的事务备注。撤销、断开和中断都不是成功同步。
- **明确未做：**没有把完整权限自动确认扩到 `calendar_advice`。这不代替邮件或旅行验收。
- **同日补上两处缺口：**安静时段的有意义通知写入 `offline_calendar_notice_holds`，由现有 `Runtime.tick` 在安静结束后经同一个 Notifier 发出；重启不丢、不重复。可移植 JSON 的 `offline_calendar_bundle` 含游标、修订、冲突对、同步尝试和暂缓通知，预览校验后仅拥有者可恢复，再次同步不新建同一事务。
- **证据：**[契约](desk-companion/docs/offline-calendar-journey.md)与[本轮 QA](output/qa/2026-11-03-offline-calendar/verification.md)。

## 2026-11-04 Grok PR78–82修复后合并授权

用户明确要求检查Grok新工作，有问题先修、通过再合并。冻结五个新PR并在独立工作树从main dac527b进行组合审查；保留所有原PR祖先，已按具体业务路径解决路由、提案、备份与tick冲突。旧Pi/学校目录的未提交变更保留。

本轮修复离线状态和回执真实性，并补同一运行实例、联合备份、静音恢复、撤销/登出和浏览器卡片检查。购物Work原子暂停入队；可移植恢复后仅在明确同步时重新关联，不恢复旧运行权限。Grok合并指南旧头和“日程无备份”说法标为历史。

PR74–77的主对话/Alice/OpenAI栈只作独立组合兼容检查，不混入本次五个Grok PR的主线合并，也不替换正在使用的服务。Pi暂停、所有实验预算关闭、无CI继续有效。真实账户/发信/购买/支付/出票未获本轮具体授权，也未执行。最终结果以[QA及远端回执](output/qa/2026-11-04-grok-journey-review/verification.md)为准。

### 4 November publication readback

[PR83](https://github.com/tantalum666/FYP/pull/83) merged at89dc92f41d945783af43dcb4f56f0e7e6d0edb1a. Remote main exactly matches the complete tree of reviewed bb6443c. Original PR78–82 were individually read back closed/merged; source63e538b remains the tested application. [Receipt](output/qa/2026-11-04-grok-journey-review/publication.json). This follow-up records publication only, with no CI, deployment, model or hardware action.
## 2026-10-31 暂停Pi，优先个人Agent跨应用接续

- **用户决定：**“pi先暂时放一边”，继续personal agent，特别是跨应用；恢复PR5后的三家机制理解，不够时自行补充并实现。取代此前供电／kiosk作为当前下一步。旧付费轮不因此重开，不新增CI、外部联系或交易授权。
- **研究与工程选择：**重新阅读Grok持久电脑／连接器／skill与routine、Muse隔离运行／浏览器broker／独立动作边界、Your dot持久责任／选定上下文／恢复与结果审查。沿用既有非eve栈；把PR5 Work注册表接入现有真实office executor，不另建任务／队列／权限内核。来源与实现映射见[研究补充](research/2026-10-31-cross-application-continuation.md)。
- **实现：**显式选择事务／应用资料，绑定输入哈希与执行环境；模型只提严格类型工具请求。新Work捕获既有Full版本，后开Full不能追认旧Work；Ask first使用共用操作卡。准备／批准／排队执行／发布均受父Work状态、会话和既有权限约束。回执丢失找回原child；已替换文件读不可变历史，最新文件核对当前发布内容。waiting_effect区分应用运行与真正需要人批准。
- **实际发现修复：**真实Calc拒绝直接传入的逗号分隔公式；在执行边界复用规范化，保留原批准请求。原型页面里审批卡位置、已生成表格却显示“无输出”、日历权限与应用权限文案混淆一并纠正；技术活动折叠，明确文件／报告区别。
- **证据：**1,701后端／303前端、Ruff、类型与生产构建通过；真实Chromium→Calc两版→Writer→两页PDF；36份／900元变48份／950元，从Aster776.60变为Birch50份902.00；问答为标明的合成用户事件。丢失保存回执、应用／进程重启后SHA／mtime不变。网页一次批准与取消、393px手机同状态、实际下载哈希和范围审阅通过。
- **边界：**规划为离线脚本，真实应用为实跑；模型调用0，不冒充真实模型自主完成。真实用户数据库／账户／学校文件未改变，Pi未继续，PR73单独保留。下一步将普通Alice／Omni长任务入口和恢复接入这套已准入Work，先做离线变体。邮件／购物／旅行和通用GUI仍各自验收。[完整QA](output/qa/2026-10-31-personal-agent-cross-app/verification.md)。

## 2026-11-01 减少默认界面文字

- **用户要求：**指出各页面堆了过多文字，要求面向真实使用而非把工程说明摊开。保留此前Alice、手机差异化和跨端共用权限要求。
- **工程落实：**Work主区先显示目标／状态／文件／需要处理的动作；IDs、计数、历史、存储和可选配置进入详情。设置、记忆、风格、事务及导入分享删去重复叙述。手机选中Work后显示详情，通过原有草稿守卫返回列表；不增加状态机或轮询。
- **边界：**具体批准对象、AI目的地／费用、永久保存限制、未保存保护和错误恢复保留；不删除用户内容，不把结构核验写成目标完成。后端及权限服务未改。
- **证据：**303前端、类型／生产构建通过，8类桌面前后截图、中文393px手机、折叠及离开草稿、未选保留时阻止开始、真实本地报告流程通过。默认新工作1368→290可见字符；不是全站统一比例。无新付费模型、CI、Pi或真实账号操作。
- **接续：**[界面契约](desk-companion/docs/ui-copy.md)成为后续UI修改约束；接着继续Alice／Omni长任务接入已有Work，先做离线验收。发布保持独立分支并以PR74为基线，不把推送当合并。[本轮QA](output/qa/2026-10-31-ui-copy-cleanup/verification.md)。

## 2026-11-02 Web主对话、Mac媒体与预览纠正

- 用户要求恢复Codex／ChatGPT／Grok式主界面、自适应比例和Mac媒体入口；对提出的1元复测选择“先接好服务，我自己点击试用”，没有批准自动付费测试。
- 旧1200px阈值在实际150%缩放下改成大弹窗；前次启动又关闭了供应商。本轮改默认主对话页，复用原业务／权限和草稿，删除过时docked CSS。
- 本机摄像头预览／麦克风检测独立于云端；显式单帧分享复用VoiceAudio。恢复现有Qwen配置，不自动连接模型；OpenAI等候选未排除。
- 309前端、类型／构建及真实浏览器布局／草稿往返／权限／导航检查通过，Mac摄像头和麦克风有真实输入；无新增云端回答成绩。
- 曾在用户正看的窗口做窄屏测试，用户再次指出比例异常；已恢复正常Web窗口和100%缩放，后续转独立QA标签页，验证用户窗口仍1291×681。不是设备端交付；之后不得在用户正在查看的标签页修改测试尺寸。
- [契约](desk-companion/docs/desktop-conversation.md)／[QA](output/qa/2026-11-02-conversation-desktop/verification.md)。下一步仍是普通Alice／Omni长任务接入既有Work；Pi暂停，无CI或自动收费。

## 2026-11-02 OpenAI试接、Alice唤醒与费用

- **用户决定：**要求试接OpenAI，询问无感对话费用，并明确选择“叫Alice才唤醒”。这取代前一轮只准备Qwen供本人点击的当前任务安排；不恢复Pi或旧实验。
- **工程选择：**沿用已确认的FYP专用Key，采用已说明的新USD1操作上限；本地sherpa关键词→既有VoiceService→安静30秒回本地。初次页面需启用，刷新／关闭即停止；不是OS常驻或真人准确率保证。
- **实际修正：**共享Realtime生命周期从voice.py拆出，OpenAI保留现有工具／权限；16k输入在适配边界转24k。实测暴露日期缺时区、512输出截断和Mini误读09:30为10:30；保留失败。工具描述／owner_clock／输出与读数提示改进后，Full2.1正确读回3场09:30／14:00／16:00，作为当前配置。提示也有变化，不是受控模型排名。
- **费用事实：**官方Realtime按token、VAD过滤空白且连接不收费；Live按包括安静的在线时间另加后台。待机留在本机避免一直上传／调用。新实验已关闭，回执保守估算USD0.1692086，含未知回执预留的记账USD0.6499936；不是Platform账单，旧USD170余额未重新核对。
- **范围：**本地模型、真实本机WebSocket、浏览器待机／关闭和四次合成语音实际API分开记录。未做真人唤醒率、真实声学插话、长时间后台／功耗、Pi／原生手机或购物邮箱验收。现有Full设置保留，没有扩大权限。见[契约](desk-companion/docs/openai-alice-wake.md)／[QA](output/qa/2026-11-02-openai-alice-wake/verification.md)。

## 2026-11-04 用户明确要求合并74–77

用户说“把74-77也合并”，取代上一轮保持该栈独立的临时范围。#77包含74–76，采用一个集成候选保留全部祖先，并使原PR75–77指向main，以便实际合入后逐一核对merged。四个原PR在完整本地验证后由draft转ready。

应用代码无冲突，且与上一轮已检查的组合b0375f4完全一致；处理八份Markdown状态/历史冲突，保留Grok修复与主对话/Alice/OpenAI基线。完整1769后端/319前端、类型构建和静态检查通过。此次无新源代码功能、CI、付费模型、真人媒体采集、Pi、真实数据迁移或服务部署；只更新代码主线与交接。

### PR74–77 publication readback

[PR85](https://github.com/tantalum666/FYP/pull/85) merged atb663204938fa11cb5c3631f2995800466840b55e. Main's full tree equals reviewed affbad2d. Original74/75/76/77 were each read back closed/merged after retargeting the stack to main. [Receipt](output/qa/2026-11-04-merge-74-77/publication.json). This closeout changes documentation only; verified application151f807 and1769/319 local results are unchanged. No deployment, CI, paid model or Pi work.


## 2026-11-06 Pi软件、免登录与跨应用

- **用户决定：**全部应用端撤掉Sign in，Pi应有Alice与语音。随后明确自动待机／红灯调查暂缓，继续Pi软件，特别是跨应用；这不等于暂停Pi，也不重开付费模型预算。
- **事实纠正：**用户明确红灯先自行出现，随后才拔插电源，未按电源键关开机；旧“正常按键重启”不成立。其电源铭牌5V/3A与本轮系统读数一致，但尚未证明自动红灯的具体原因。供电监测已结束，不再作为本轮软件前置。
- **工程选择：**可信回环工作区默认自动建立普通有限期拥有者会话，所有端移除密码表单。公网、转发和配对权限边界不变。Pi复用现有Alice／ConversationWorkspace／语音与批准机制；修复媒体面板被自身遮挡监听立即关闭，以及唤醒词配置写入只读模型目录的问题。
- **跨应用：**Pi补rootless Podman，通过固定传输复用既有ApplicationExecutor／JobService／Work；浏览器、Calc、Writer隔离运行，仅挂载选定资料和产物目录。保留Mac Docker实现与旧回执范围，不给模型任意shell或用户主目录。
- **验证边界：**本地完整与实际Pi结果、发布状态见[本轮QA](output/qa/2026-11-06-passwordless-device/verification.md)。没有新模型请求，脚本规划不标成AI自主完成；Pi输入硬件尚未枚举到麦克风，Mac浏览器输入与Pi本机拾音分开记录。


### 6 November target evidence and runtime limitation

The new release is active on Pi and the four-job real Chromium/Calc/Writer/PDF case passed, including changed constraints and restart recovery with unchanged bytes/mtime. Text planning remains offline-scripted for this acceptance; normal standalone text provider stays none. Pi kernel lacks the memory controller; explicit operator opt-in skips that unavailable RAM cap while retaining2CPU/256PID, rootless/scoped/offline isolation. Added container init for graceful0.38sstop and enabled the user service without weakening API NoNewPrivileges. No hardware reboot or new power test. Exact deployment/publication evidence is in the current QA.


<!-- Preserved network-recovery history from PR73/87. Later Pi software/physical-restart corrections take precedence. -->
## 2026-10-31 恢复Pi与三地网络配置

- **用户决定：**回到大陆家中，明确恢复树莓派工作，提供家庭Wi-Fi并允许必要时使用其现有Bandwagon VPS；随后要求家里Wi-Fi、教室Wi-Fi＋网线、宿舍网线。这取代此前Pi暂停，未重新授权付费模型或机械臂动作。
- **实现范围：**保留原卡系统／用户／密钥／应用，新增家庭与有线DHCP配置；教室沿用已成功的NETGEAR02，Student/Halls保留凭据但关闭自动连接。连接事件更新独立SSH来源规则，只接受原拥有者密钥；不清空系统防火墙或公开应用／桌面端口。
- **证据：**原卡容量／卷与root标识／已配对主机公钥一致；25项本地检查、两份启动文件独立读回、其余文件不变、FAT只读检查0与安全弹出。等待实际开机／SSH／网页验收，不能把准备写成连通。
- **边界：**VPS聊天已读，当前未修改VPS／Mac代理。凭据仅在私有本机及设备配置，不进Git；新软件主线、Pi旧安装版本和真实部署分开。见[本轮QA](output/qa/2026-10-31-pi-home-resume/verification.md)。

### 2026-10-31 实机联网通过与供电门槛

- **用户操作：**确认原卡已插回Pi并通电。已用mDNS定位、原固定主机密钥认证；家庭SSID私下比对通过，网络状态network_ready，实际优先级及禁用旧宿舍自动连接均已读回。
- **实际验收：**家庭Wi-Fi、SSH、loopback应用／桌面服务、Mac网页登录／Alice和屏幕共享通过；有线最后仍无载波，不能据配置声称学校网线已通。现有隧道保留便于用户查看，临时发现观察器已结束。
- **新发现与工程处置：**Pi本机Chromium启动时真实低电压，内核两秒后记录恢复；窗口已关闭。后续0x50000为历史低电压／节流位，供电能力读数3000mA。先请用户确认电源／线材，再做有界负载复测；不通过屏蔽警告、强制供电覆盖或重刷来消除证据。此为实测问题后的工程顺序，不是用户恢复Pi授权被撤销。
- **OS记录：**cloud-init已结束，errors=[]，缺少cc_netplan_nm_patch的可恢复警告保留；country命令exit1但global CN和启动参数已验证。没有改系统厂商配置或重跑provisioning来将状态变绿。
- **未完成：**连续运行、家中及学校有线、最新软件／数据库升级、Pi端语音／声学／机械验收。旧模型预算仍关闭，实际调用0。详见[更新QA](output/qa/2026-10-31-pi-home-resume/verification.md)。

### 2026-10-31 Pi专用端入口与交付口径纠正

- **用户纠正：**指出之前已经专门开发Pi端，质疑为何展示普通网页。沿用9月30日“设备常亮界面与手机／网页分开”的已确认要求，不新造一种平台选择。
- **核对事实：**DeviceApp代码、设备规范、全屏脚本及Pi已安装编译资源都存在；正确入口为`?surface=device`。前一轮回复截图为普通工作区`?page=device`设置页，是展示和说明错误，不能据此推断专用端被删除。
- **现有实现与缺口：**React独立设备界面＋Pi本地API＋Chromium应用／kiosk窗口；实机autostart仍是session.sh→welcome.py，全屏开机进入尚未完成。通过Mac渲染Pi资源检查了常亮锁定页→登录面板→返回，无控制台warn/error；没有重启Pi本机浏览器、改变认证或启动配置。
- **后续顺序：**供电核对后，将新版软件部署与专用端全屏自启动、配对／会话恢复、重启／触控验收一起收尾；远程管理页仅作为管理／诊断入口。详见[核对记录](output/qa/2026-10-31-pi-device-entry/verification.md)。

## 2026-10-31 Pi再次暂停与软件工作区路由

用户明确“pi先暂时放一边”，优先personal agent跨应用软件，取代供电／kiosk作为当前下一步。Pi实测与未完成门槛保留，未再连接或更新设备。软件从main dac527b在独立工作树实施并发布[draft PR74](https://github.com/tantalum666/FYP/pull/74)；本分支只同步暂停与恢复入口，不混入另一分支的未合并代码。旧预算关闭、无CI及私有数据边界不变。

## 2026-11-01 界面精简与当前软件路由

用户指出各页面文字过多。软件工作区已按主操作／结果优先、技术与可选信息折叠实现，并发布[draft PR75](https://github.com/tantalum666/FYP/pull/75)，以PR74为基线；保留Alice、具体批准与草稿恢复。303前端／类型构建及实际网页／中文手机检查属于软件分支证据。本Pi分支只同步入口，不新增实机工作或重复声称软件测试。

## 2026-11-02 Web主对话与媒体路由

用户要求正常Web主聊天界面、自适应比例和Mac媒体，并选择自行点击已配置Qwen而不授权自动收费测试。软件分支PR76承接75／74；本Pi分支只同步入口。不得将窄屏测试当设备端，也不得在用户当前预览窗口更改测试尺寸。Pi暂停、无CI及私有数据边界不变。

## 2026-11-02 OpenAI与Alice唤醒软件路由

用户请求OpenAI试接并选择叫Alice唤醒。实际实现和分开记录的本地／真实API证据在软件PR77，当前Full2.1配置不等于排除其他模型。工程采用的新USD1测试轮已关闭；此Pi分支仅同步入口，不运行模型或硬件。

## 2026-11-04 宿舍恢复Pi与原卡诊断

- **用户决定：**重新开始Pi工作，网线接宿舍墙口，供电确认官方27W；没有显示器，选择先正常关机并把原SD卡接到Mac。这取代此前Pi暂停，不恢复付费模型预算。
- **实际观察：**本机定向mDNS与已知Pi邻居比对未发现当前地址；旧教室IP走VPN，未探测。最新磁盘检查没有bootfs。未登录Pi，未写卡／改网络／部署。
- **工程发现：**现有有线DHCP已启用；网络事件的`--guard`只更新来源规则，启动分区状态可能仍是旧设置记录，必须核对时间。尚不能认定墙口DHCP失败或校园隔离。
- **下一步：**原卡出现后按容量／boot UUID／root PARTUUID核对，再只读检查有日期的状态，按实际结果准备最小恢复。官方电源身份已确认，供电负载仍待读回与复测。见[恢复QA](output/qa/2026-11-04-pi-dorm-ethernet/verification.md)。

### 2026-11-04 原卡结果与有线跨网段恢复

只读确认原卡身份，读到有线DHCP保存租约，与当前Mac网段不同；不是本轮即时地址证明。旧Pi来源规则只允许本地网段，新增显式开启的Mac单一私有IPv4/32有线管理入口，默认关闭，原密钥与loopback服务不变。修复网络事件不刷新状态，加入boot ID；本轮countryHK、发现窗口600秒。29项本地回归及Ruff通过，两份启动文件备份／独立读回、其余三份未变、FAT只读检查0与安全弹出通过。用户确认已回插通电，管理连接仍在验收。

Linux只读检查返回4，并明确跳过journal recovery；needs_recovery及摘要／校验差异仍待正常启动后复核，不能直接宣布SD物理损坏。Mac未写Linux分区，未做离线修复、重刷或新软件部署。私有提取日志不进Git。

### 2026-11-04 三地保留、拒绝热点与完整性恢复

用户再次要求大陆Wi-Fi、教室Wi-Fi＋网线、宿舍网线，并明确不用热点、要求集中诊断修复。新启动原卡已读回有线DHCP、来源规则与HK区域，但不等于远程连接验收。可选VPS专用账号/密钥和Mac转发正反例通过；Pi尝试未建立通道，额外只读记录显示中转文件为空、write_files已标记执行。原始ext4视图仍有待回放日志，不据此宣称物理损坏。新增具备文件完整性、耐久写入、当前实例重试与实际回执检查的启动恢复，62项本地测试通过；原配对身份、应用数据和三地网络保留。VPS新增仅专用受限账号及无凭据阶段记录，未改原代理/SSH/防火墙路由。下一步是经过完整准备的一次实机启动验证，不再盲试地址。

## 2026-11-05 以已验证443接入取代未通的直连22假设

用户确认耐久恢复包已开机，阶段回报显示安装完成但VPS TCP不可达；尚未取得Pi认证连接。进一步核对发现Mac的成功VPS访问经过现有加密通道，不能当作Pi直连22的证据。独立客户端强制en0、关闭TUN/DNS/通用代理后，经同一443节点完成真实主机密钥与公钥认证。

据此打包同版本官方ARM64客户端，仅监听回环固定转发到自有VPS SSH，保留原SSH密钥与三地网络。79本地检查和实际离线包预演通过，软件/凭据/二进制分别保存。仅请求为已验证方案接卡部署；不用热点，不更改现有Mac代理或VPS主代理，实机与教室有线仍待验收。详见[QA](output/qa/2026-11-05-pi-443-transport/verification.md)。

### 2026-11-05 原卡应用443包

用户接回原卡，随后确认回插通电。原卡身份及上一轮当前实例回执已核对，确认安装完成和直连VPS超时；据既有授权应用已验证443包。写入三份启动材料并独立读回、FAT只读检查0及安全弹出通过，家庭／有线配置逐字节保留，教室配置不覆盖。重新读取变化的Mac租约后更新唯一管理/32；不改Mac网络设置。仅更新VPS本轮随机标识过滤与监控阶段，保留原代理／SSH／防火墙。实机认证结果单独记录，不把本次写卡等同于三地验收。

### 2026-11-05 实机接入、优先软件与真实部署

**用户决定：**确认原卡开机，说明官方电源直插且另接设备；随后要求不要继续纠缠外设细节，优先推进工作，并完成一次正常按键重启。工程上继续可远程完成的软件工作，保持无热点、无CI、预算关闭。

**实际结果：**443通道完成原Pi身份认证、宿舍有线、Mac网页／VNC及重启后访问。补充专用中转账号20/3失活检测和Mac自动重连；其他用户的有效SSH配置未变。统一main abf6387通过锁定ARM64环境、备份与迁移演练后实际部署，真实1→2→3及32张原表比对通过。原账号／密钥配置保留；没有将旧应用删除或把迁移成功写成语音／机械验收。

**持久化边界：**重启后第二份Pi本地副本出现空文件，明确排除该回退来源。最初Pi／Mac备份一致，旧程序已在其副本上登录／读取通过；新schema3档案经同步后复制到Mac并校验。运行身份文件与最初Mac副本一致，274程序／前端和2159依赖文件完整。低压及长期稳定性仍未解决，原因不强行归因。下一步先做新版Pi离线会话到应用作业验收。详见[部署QA](output/qa/2026-11-05-pi-runtime-upgrade/verification.md)。


## 2026-11-06 普通文字改口进入已有 Work

- **任务范围：**当前交接的下一步是离线改口用例，加上这条路径上的中断和未知结果恢复。这是既有下一步的实现，不是新的付费、真实账号或 Pi 授权。Codex 仍负责审查合并；#73、#87、#88 保持不动。
- **工程选择：**明确说法才调用既有 `AgentRunService` steer。同一事务上只有一项当前 Work 时可以不写运行编号；多项、已取消或已经改过一次则不猜测。不新建任务库、队列、schema 迁移或模型自批工具。`Goal:` 仍只准备新事务草稿。
- **恢复：**提交前中断不改目标，也不是成功回复。steer 已提交但对话回执丢失时，同一操作号恢复原更改；换一个目标则冲突，不会第二次 steer。流中断本身不是成功回执。
- **证据：**离线夹具 9 项、整合验收 7 项，以及文字会话、目标、权限、购物、邮箱、离线日程和 Work 运行共 97 项通过。付费调用 0。见[契约](desk-companion/docs/conversation-work.md)与[QA](output/qa/2026-11-06-conversation-work-changed-goal/verification.md)。
- **未做：**夹具以外的说法和来源版式、语音快照改已有 Work、真实账号、支付和 Pi。

## 2026-11-06 未见说法与语音快照改已有 Work

- **任务范围：**上一轮交接的下一步是夹具以外的说法和来源版式，然后用语音快照走同一条改口。仍是离线实现。不接真实账号、支付或 Pi，不动 Codex 草稿 #73、#87、#88。
- **工程选择：**匹配仍只在 `owner_instruction` 和 `parse_changed_goal`。引用行和来源标题不是指令。问句、`Goal:`／`目标：`草稿、多项当前工作且没有运行编号时不改。已复核的语音快照把原文放进同一 `ConversationWork.turn`，用 `voice_origin_ref` 核对，不另写 steer。
- **恢复：**文字和语音共用提交前中断、丢失回执后的同一操作号，以及流式关闭不是成功回执。快照还在时换一句是 `VOICE_INPUT_CHANGED`。快照消失后换一个目标是 `OPERATION_ID_CONFLICT`。都不会第二次 steer。
- **证据：**对话测试 47 项通过，其中未见夹具 31 项。整合验收 7 项、先前回归 97 项、语音 Work 44 项通过。付费调用 0。见[契约](desk-companion/docs/conversation-work.md)与[QA](output/qa/2026-11-06-conversation-work-unseen-voice/verification.md)。
- **未做：**语音复核页仍只开始新的 Work。真实账号、支付、Pi 和付费模型比较仍分开。

## 2026-11-06 语音复核页更新一项当前 Work

- **任务范围：**上一轮交接的下一步是让语音复核页把已复核快照送进已有改口。仍是离线实现。不接真实账号、支付或 Pi，不动 Codex 草稿 #73、#87、#88。
- **工程选择：**复核页在普通助手消息上带 `voice_origin_ref` 和 `voice_steer: true`。仍由 `ConversationWork.turn` 调用既有 `AgentRunService` steer。快照原文就是新目标，不必再说「Change the goal」。一项当前工作可以不写运行编号；多项必须带 `steer_run_id`；没有当前工作时不新建运行。改过的措辞只用于开始新的 Work。
- **恢复：**提交前中断不是成功。steer 已写入但对话回执丢失时，同一操作号恢复且不第二次改口。流式关闭不是成功回执。配对设备仍是 403。Full access 不产生作业或建议。
- **证据：**对话测试 54 项通过。整合验收 7 项通过。文字、目标、权限、购物、邮箱、离线日程、Work 运行和语音 Work 的一条回归命令 148 项通过。语音前端测试 19 项通过，`tsc --noEmit` 通过。付费调用 0。见[契约](desk-companion/docs/conversation-work.md)与[QA](output/qa/2026-11-06-voice-review-steer/verification.md)。
- **未做：**改口之后，同一条对话还不会显示既有执行器的下一次核验结果。真实账号、支付、Pi 和付费模型比较仍分开。

## 2026-11-06 改口后在同一条对话显示一项已核验结果

- **任务范围：**上一轮交接的下一步是，文字或语音改口之后，在同一条对话里显示既有离线 Work 执行器的一项已核验结果。结果必须体现改后的目标。不调用付费模型，不接真实账号、支付或 Pi，不动 Codex 草稿 #73、#87、#88。
- **工程选择：**steer 提交后，只对这一次运行调用既有 `AgentRunService.advance_one`。确定性模式读回已发布的 Markdown，对话里带上文件中的 `Goal:` 行。不新建任务库、队列、schema 迁移或自批工具，也不创建电脑作业或建议。模型模式不往下执行，避免变成一次提供商调用。
- **恢复：**未核验是 `CONVERSATION_WORK_RESULT_UNVERIFIED`，失败是 `CONVERSATION_WORK_RESULT_FAILED`，都不是成功。执行前中断不是成功，目标已经改了，同一操作号可以随后显示一次结果。文件已核验但对话回执丢失时，同一操作号读回原文件，不第二次发布。另一个登录打不开这条对话。配对设备仍是 403。Full access 不产生作业或建议。
- **合并说明：**Codex 按 #89 → #90 → #91 → 本 PR 合并。本 PR 的基线是 #91 的分支 `cursor/voice-review-steer-current-work-e7d6`。
- **证据：**对话测试 60 项通过。整合验收 7 项通过。全量后端 pytest 为 1828 passed、1 failed；失败项是既有的 `test_public_unicast[::ffff:93.184.216.34]`，本轮没有改那段传输检查。前端测试 323 项通过，`tsc --noEmit` 通过。付费调用 0。见[契约](desk-companion/docs/conversation-work.md)与[QA](output/qa/2026-11-06-conversation-work-verified-result/verification.md)。
- **未做：**后一轮提问还不能再次读出这一条已核验结果。真实账号、支付、Pi 和付费模型比较仍分开。


## 2026-11-06 合并全部待处理PR，默认转OpenAI

用户明确授权先审查GitHub全部待合并工作，有问题修复后合并；认为固定办公案例过于有限，要求推进Dot／Grok Bot／Muse式购物、订票和computer use。默认供应商改为OpenAI，取代此前Pi保留Qwen默认的决定；既有FYP专用Key继续使用，测试费用授权未重开。红灯调查仍暂缓。

组合73／87／88／89–92，保留原提交祖先和最新Alice／免登录基线。修复复制来源误当指令、旧回执指纹兼容及报告文件核验被写成目标结果的问题。完整1949后端／328前端、类型构建及实际对话检查通过。合并与后续OpenAI配置分开记录，购物／订票仍须真实来源、明确提交状态和独立回执；不把脚本或模型一句完成当购买／出票。

## 2026-11-06 通用浏览器先行

**用户决定：**先做通用浏览器能力，暂不固定商家；默认OpenAI，取代旧Qwen默认。只暂缓红灯调查，继续Pi软件。既有FYP Key沿用，付费测试预算仍关闭，不做CI。

**工程实现：**在既有JobService／PermissionService上注册原生Responses computer动作；UI提供目标、入口网站和显式画面分享，单次／完整权限控制新请求。保留实际浏览器观察与有限状态，用新指令／新批准继续；正常停止可续接，未确认清理则拦住后续执行。没有第二套事务库，不执行模型生成的任意脚本。

**范围与证据：**公开页面和演练任务；账户登录、敏感资料、最终付款／预订、交互式人工接管及真实订单核验未实现。浏览器HTTP过滤／DNS预检不宣称是操作系统网络隔离。复杂购物、航班、外部测试目录和停止恢复使用真实Chromium＋脚本规划通过，付费模型请求0。Mac模型目录GET成功，Pi同接口403地区不支持；明确显示错误，不改路由绕过，不静默换Qwen。普通配置不自动触发付费请求，后台模型关闭，浏览器默认8轮／最多12轮和180秒时限；调用数限额不等于美元封顶。

**合并：**PR93已合并七项原始PR，树与本地验收一致。新浏览器源提交与实际运行版本分别写入交接／QA；实际模型规划与账号交易不能由本地测试数量代替。


## 2026-11-07 Owner-requested Pi VPS route takes priority

The owner explicitly requested use of their existing VPS, real merchant/payment/ticket/takeover flows, selected JD or Taobao, then directed that Pi-to-VPS OpenAI connectivity be completed first. This supersedes the previous direct-only runtime choice; it does not authorize an unspecified purchase, booking or new paid-model experiment.

The fixed route reuses existing pinned transport and changes only the dedicated Pi key's exact outbound permitopen destination. An OpenAI-only loopback CONNECT bridge preserves end-to-end TLS; no API key is stored on VPS. Normal text/computer/Realtime clients select it explicitly, with no general environment proxy or fallback. Other providers, proxy services and management relay retain their configuration.

Real Pi HTTP200model listing and Realtime session.created/normal closure passed. No audio or response.create was sent. The old direct-region flag was cleared only after these results. Source9625f137was activated after a21-file stopped backup, off-device hash verification and284source/assets checks.357provider regressions and14final bridge checks passed. JD account work remains unimplemented and follows this connectivity milestone.


## 2026-11-07 Real OpenAI commerce, travel and mail evaluation

**Owner authority:** continued testing after Pi/VPS connectivity, explicitly including shopping, tickets and writing/sending email; fresh total OpenAI ceiling USD1 and one owner-provided test recipient. This does not authorize unspecified purchase/payment/booking. Old budgets stay closed, no CI and only red-LED diagnosis is deferred.

**Engineering decisions:** use actual Pi providers and Chromium with a single durable count/reserve/receipt ledger, isolated stores and independently checked page/calendar state. No scripted planner is substituted for live calls. Keep real-site attempts and connector-assisted mail separate from native product claims. The31generation receipts conservatively account USD0.37970163; the round is closed with zero unknown receipts.

**Evidence-driven changes:** real pointer keys:null normalization; JSON-mode input marker; document-generation/origin capture and input checks; filtered resume state; bounded navigation error classification; background writes still rejected without aborting unrelated readable pages; accurate local-time/reminder model schemas; usage retained on cancelled/invalid responses. Production business validation, default reminders, paid-request behavior and transaction scope are not relaxed.

Controlled shopping/flight cases, calendar followup and cancellation passed. JD stopped at verification, Cathay failed initial load, and ordinary FYP correctly reported no sender. Exact FYP-generated test mail was sent once/read back through the existing Codex Gmail connector; no Gmail credential/connection was installed in FYP. Next product slice remains deliberate owner takeover and return in the same generic browser job, now grounded in the actual JD verification boundary. [Evidence](output/qa/2026-11-07-live-agent-eval/verification.md).


## 2026-11-07 Shared Alice home, local wake and GPT Live

**Owner decisions:** carry the accepted simple dark mobile appearance across Web/phone/Pi; keep Alice dominant, remove the welcome question and conspicuous cards/white composer; retain a full phone month view and add clock/weather using location with Hong Kong fallback. Calling Alice should replace repeated manual voice clicks after initial opt-in. Select GPT Live, retain Realtime. Fresh synthetic voice test ceiling USD1/45seconds was expressly approved and is now closed.

**Engineering choices:** reuse the licensed model, shared conversation, calendar/workspace reads and current permission/job services. Separate local keyword waiting from short paid sessions. Add explicit Alice identity to speech and invariant persona rules. Adapt native Live and delegated Responses events without treating backend completion as speech completion. Configure approved existing keys and pinned wake models; no new key or continuous cloud listener.

**Feedback repairs:** consolidate background read errors, size the textarea before paint, constrain compact transcript and short-screen agenda, fix canvas CSS pixel ratio, isolate loopback cookies by port and suppress automatic geolocation permission requests. Failure uses Hong Kong until an explicit location retry; exact coordinates are not persisted. These are lifecycle fixes, not a broader browser permission grant.

**Evidence:**2051backend and341frontend tests, type/build and scoped lint; actual browser draft/navigation, read-failure recovery and geometry checks; local positive/negative synthetic wake clips; one real Live identity/calendar trial (20providerseconds, two backend requests, no writes), conservative USD0.0518613333. Human acoustics, native background behavior, Pi physical audio and real commerce transactions remain distinct. [Detailed QA](output/qa/2026-11-07-alice-home-wake/verification.md).


## 2026-11-07 Complete wake acceptance after owner-reported failure

**Owner direction:** investigate the failed Alice call and complete acceptance autonomously, instead of relying on the owner to discover defects. **Engineering cap:** a new, separate USD0.50repair ledger, with earlier budgets sealed; final conservative accounting USD0.1864995and all receipts finalized.

Confirmed old full-catalog rejection with a non-generation OpenAI preflight. Fix schema annotation traversal so business title/default fields survive; do not weaken validation or remove production tools to make startup pass. The earlier restricted query trial is explicitly reclassified by its actual advertised-tool scope. Native Mac input was separately verified and explicitly selected in the app, preserving system audio settings.

Complete browser testing reused production capture, keyword, Live/Responses, tool and playback code with synthetic transmitted input and an isolated fictional calendar. Three successful startup/idle cycles included one full identity/calendar answer and actual playback acknowledgement;6.393second first useful playback still misses the approximate5second goal. Keep errors stopping paid retries; retain safe diagnostic identifiers and clear stale notices on deliberate retry. [QA](output/qa/2026-11-07-alice-wake-repair/verification.md).
