# HISTORICAL: Senplate food-monitoring product contract

This is a preserved copy of the product contract immediately before the user replaced the project direction on 2026-09-25. All subsequent “current” wording below is historical. The active Group 2 contract is [product.md](../../product.md).

# Group 2 Project Contract

**2026-09-21：Marco最新反馈正在技术复核。**相机必要性与番茄炒蛋的混合／遮挡营养是本轮重点。当前工程建议先验证普通RGB相机＋称重＋固定照明，Gemini 2改为可取得且有可测收益时的增强对照；营养采用批次配方／食材量／成品得率支持的估算，整批与分份准确性分别评价。用户尚未决定把营养改为唯一主线，老师也未正式批准新选型。[反馈分析与修订文字](planning/2026-09-21/marco-camera-and-nutrition-review.md)。既有Proposal Word／PDF保留为初稿，尚未纳入本轮建议；本轮不开发或采购。


**2026-09-21：学校Project Proposal已完成英文10页Word／PDF，当前优先审阅与按反馈修订。**依据AY26指南的七项要求，补入单盘位三配置、当前iPhone／Web架构、拟议硬件与模型验证、40／30／30分工和约六个月团队里程碑。团队提交目标为9月28日星期一；Moodle截图期限为9月29日星期二23:59，两种格式均需提交。[Proposal制作记录](planning/2026-09-21/proposal-spec.md)／[DOCX](<output/docx/AY26_ProjectProposal_Group 2.docx>)／[PDF](<output/pdf/AY26_ProjectProposal_Group 2.pdf>)。签名和导师意见留空，未上传或获得正式批准；原两版Suggestion保持。本轮未继续M1.3或重新验证软件服务在线状态。

**2026-09-19：P0补餐、M1.1菜单／订单与M1.2个人餐食／学校匿名样本本地原型已实现并验证。**现有SwiftUI iPhone、厨房／管理Web、独立设备控制台、FastAPI／PostgreSQL和模拟输入。M1.2新增120秒配对及设备核对、逐项差值、4项USDA参考与未知项、历史快照、总余量单列、学校样本／CSV和隐私隔离；默认英文、可切简体中文，沿用V7及VI。[餐食样本契约](planning/2026-09-19/meals-samples-contract.md)／[本批QA](output/qa/development-m1-2-meals-2026-09-19/verification.md)，原[菜单订单契约](planning/2026-09-19/menu-orders-contract.md)继续适用。完整配置、配方／学校计划管理、餐末去向及实物模型继续分批实施。

**同轮语言纠正：所有端默认英文，支持切换简体中文并记住选择；en／zh-Hans取代此前繁体中文要求。**现有VI及字体原件保留，中文界面使用Noto Sans SC。

**主标志仍为用户已选的V7无刻度纯碗，现已完成VI V1。**用户澄清本次要整套视觉识别。已交付独立图形／字标、横向／上下组合的绿黑白12版本、11页规范、4页矢量总表、App图标及应用模板、字体和许可核查。[VI交付](planning/2026-09-18/senplate-vi-v1.md)／[字体核查](research/2026-09-18-font-licences/font-licence-audit.md)。原V7和所有旧稿保留，辅助规则与应用为本次VI设计；应用首批已在本地实现，完整范围见P0记录。

2026-09-18新增[当前纯碗商标初筛](research/2026-09-18-senplate-trademark/trademark-review.md)：香港官方300条图像候选、227个不同编号；BASAO为重点视觉参照，OpenRice为点餐／餐厅管理软件相关参照。美国本次文字查询无结果，但发现历史同名Senplate iOS原型使用线索。尚未完成全球清查，香港文字结果未刷新；不能把旧名称初筛或字体许可解释为当前图形可注册。V7及VI保持，未开始重画。

另一任务已完成Senplate中文版商业计划书V1。[完整正文](planning/2026-09-16/business-plan-zh.md)和17页Word／PDF涵盖客户、产品、竞争、收费、获客、六个月实施、试点、单位经济、三年情景及资金用途。机构客户优先、HK$14,800设备加HK$680月费、HK$50,000原型资源额度均为商业建议，不是已批准定价、预算或订单；一台FYP设备、不注册公司的范围保留；软件已进入P0＋M1.1＋M1.2本地原型阶段。

更新：2026-09-21。FYP只做一台demo，一个独立称重盘位、三个软件配置；多餐位留作未来商业研究。训练复用M2 Pro／16GB MacBook，单机主机暂保留Pi5 8GB，相机按本轮建议先测RGB，RGB-D为有条件对照。统一供电已细化为12V5A适配器、亚博Pi5 PD电源板和独立供电USB3 Hub两支路，仍待接口及台架验证。两版Project Suggestion DOCX/PDF原样保留，旧件尚未同步工程细节；新的Project Proposal已纳入当前范围，修订方案未正式批准。

**项目英文品牌已由用户确定为Senplate。**此前[商标与域名公开初筛](research/2026-09-16-senplate-name-check/senplate-trademark-and-domains.md)记录香港、美国、欧盟查询未见同名结果；中国内地和WIPO未取得正式查询结果，不能视作全球法律清查通过。九个域名结果仅对应此前查询时点，未购买。中文“知餐”仍为候选；本次Logo与VI不改变该权利状态，旧[命名候选](planning/2026-09-16/naming-shortlist.md)及[视觉V1](planning/2026-09-16/brand-visual-directions.md)留作历史。

软件方向仍为App优先：用户明确只做iPhone，个人／顾客与员工／管理者都在同一个App内按角色区分，厨房和餐厅管理可保留网页。当前[软件讨论稿](planning/2026-09-16/software-scope-and-architecture.md)采用一个iPhone App＋一套厨房／管理Web＋设备专用界面，共用后台，另有组内模拟器。原全网页建议已归档；SwiftUI与厨房／设备Web已用于P0；实物、模型训练与外网部署尚未进行。依据见[Metafoodx App研究](research/2026-09-16-metafoodx-app/app-review.md)。

已形成V1[页面与权限](planning/2026-09-16/app-pages-and-permissions.md)、[状态与API](planning/2026-09-16/software-workflows-and-api.md)、[开发批次／验收](planning/2026-09-16/software-mvp-and-acceptance.md)。包含两套四入口导航、页面／操作编号、后台权限矩阵、补餐／订单／配对状态、首批19项接口及设计场景。规格保留完整业务基线；P0目录及首批接口已经实现，订单和最低菜单维护已由M1.1实现；M1.2受控餐食和匿名样本已实现，完整配置仍在P1后续范围。

当前采用3页[硬件制作询价V3.1附图版](planning/2026-09-15/hardware-fabrication-enquiry-v3-1-images.md)：前两页保留V3简化需求，第三页新增参考图，全篇共4张图片；供应商制作并集成类似Metafoodx外形的一台完整硬件，系统、代码、校准和测试由我方处理，不向供应商要求软件或测试服务。原10页RFQ V2保留为历史，当前不按其复杂验收／工程服务清单询价。亚博IPS屏仍可作为官方DSI屏的替代建议，未确定换屏；型号变更需配齐对应线材。未发送、下单或正式委托。

## 当前依据

同日用户质疑目标餐厅可能已有成熟采购。当前仅将餐中余量反馈／补餐协同作为待验证的局部问题，不假设成熟餐厅缺少采购系统，也不声称新设备普遍必要。若现有流程可靠且收益不足以覆盖设备、维护及操作负担，则不适配该客户。[成熟流程下的价值条件](planning/2026-09-21/marco-camera-and-nutrition-review.md)。未确认新客户、采购集成或正式改题。

2026-09-21围绕导师反馈进一步复核Metafoodx痛点：公开主线是降低厨房记录负担，用菜品级生产／取用／剩余与去向资料改善备餐、菜单及采购；Pomona校方确认服务前后称重／拍照／测温工作流。此价值不依赖精确维生素C检测，仍不能把取用写成个人实际摄入。[复核第9节](planning/2026-09-21/marco-camera-and-nutrition-review.md)。这是定位分析，用户未据此决定删除营养或其他配置，原Proposal仍待修订。

参赛最新范围为**现在至2027年8月前**，优先高认可度、尽量有现金奖励，需区分报名和完整作品交付。[2027年7月底前参赛计划](research/2026-09-16-competitions/plan-to-july-2027.md)取代旧名单的当前排序：Techathon+已有2027正式安排，香港大学生赛及海峡两岸作品赛按下一届准备；中美创客有作品公开／获奖限制，YPEC作专业补充，广东省赛另走学校实操训练。其余2026日期只作历史参考；比赛在8月后及未确定2027举办的赛事单列，未报名或联系。

用户对世界职业院校技能大赛表达兴趣，已整理[学校报名路线与Marco询问草稿](research/2026-09-16-competitions/world-vocational-registration.md)。2026国内基础报名8月27日、详细材料9月10日已截止，未查到港澳补报；建议先由Marco转介课程／竞赛负责人核对机构、组别和下一届安排。港澳直接报名仍需校方办理，三人非永居不自动排除或归入国际组；尚未联系或报名。

大陆赛事进一步筛选见[全国与省级路线](research/2026-09-16-competitions/mainland-national-provincial.md)。新增节能减排港澳台及国际赛道、世界职业院校技能大赛AI方向和广东省技能赛院校通道；物联网、移动应用、iCAN创新的VTC报名／分组分别核对，不能把主题匹配当资格已获批。原“不注册公司”约束保持，未报名或联系，不改变当前品牌和产品范围。

2026-09-16另完成[大陆／香港赛事筛选](research/2026-09-16-competitions/competition-shortlist.md)，用户补充暂不打算在任何地方注册公司。当前按[无公司落地候选](research/2026-09-16-competitions/no-company-options.md)筛选学生／个人作品赛，新增海峡两岸暨港澳作品赛、中美创客、HKIE电子、HKETA IFF及IET YPEC。原香港大学生赛、Techathon+学生现金奖方向保留；深创赛／广州创业落地奖移出主选，不把培育基金算作可自由领取的比赛现金。三位均非香港永久居民；已对世界职业院校技能大赛表达兴趣，尚未报名或联系，不改变当前品牌及一台设备／三配置范围。

用户转述已与 Marco 老师讨论，老师认为原技术、硬件和痛点基本可行，建议扩展到更有社会价值的场景，例如中小学或个人营养监测。当前 V2 采用一套食物监测核心、三个应用配置；这是本轮提出的修订方案，不代表老师已正式批准 V2。

## 保留的要求

- 三人、核心开发约半年、硬件预算尽量低，必须包含硬件与可执行反馈。
- Group 2；Yuan Yuchen 40%、Xu Ziqian 30%、Li Wenhua 30%，均为计划工作占比。身份资料以结构化文件为准。
- 食物在监测期间保持在设备上，进行原位持续实时监测；借鉴 Metafoodx 的底座、立柱、感测头和屏幕布置。
- FYP只交付一台用于demo的完整装置；多盘位共享相机、额外称重节点和多机通信留作未来商业部署研究，不追加到本期采购或验收。
- Pi 5 单机优先验证，当前采购目标为8GB版但未确认已购。已有 Arduino UNO R4 WiFi 可选，不是必需组件。
- 保留补餐、厨房任务、剩余记录，以及辅助QR菜单／基础点餐；默认英文，可切换简体中文并记住选择。首版手机只做iPhone，App含个人／顾客及授权工作角色；厨房／管理保留Web，设备屏单独处理。
- 不代签或自行勾选导师审批；本地文件完成、老师讨论、正式批准和 Moodle 提交是不同状态。

## 当前题目和应用配置

项目品牌：**Senplate**（用户已确定英文名；中文名未定）。

**AI and IoT Based Food and Nutrition Monitoring System**

1. 供餐模式：自助餐／批量备餐自选快餐，追踪余量和需求，给出补餐时间及批量建议，管理在制任务和剩余去向。
2. 学校模式：中小学配餐点或示范餐位，记录份量及食物组，对照审核过的配餐计划，并汇总剩余，支持供餐沟通与营养教育。
3. 个人模式：成年人餐食记录，显示实测份量、参考营养和食物组反馈；在映射和用户确认足够时记录标注为估计的摄入。

一套可配置原型，一个独立称重盘位，4–6 类登记食物／配方。此前“最多三个独立称重位置”是助手的扩展建议，不是用户要求；扩展不再默认属于首版交付。一个平台中的多个称重元件可以共同输出一个总重，不能据元件数量推断分项食物重量。

同一设备轮流演示三个配置；容器必须在同一结构的载荷、尺寸、视野和有效精度范围内，分别去皮／校准。多个容器或不同场地若需同时独立持续监测，另算通道或设备。原型不追踪已经离开设备的饭盒或餐盘。详见[单盘位与识别可靠性](planning/2026-09-14/single-station-recognition-reliability.md)。

## 营养与数据规则

用户在2026-09-21进一步强调，希望精确判断学生全天营养是否达到参考标准，并以维生素C为例。当前相机／称重不能保证该目标，配方估算也不等于实测营养；未获得足以可靠判定个人每日达标的误差验证。任何未来每日参考比较都需完整摄入来源、适用年龄／性别／地区标准与明确不确定性，不能以单餐或一天低于RDA等直接判缺乏。先明确能否接受估算辅助，再调整Proposal；不将此讨论记成已批准儿童个体营养诊断功能。[直接结论](planning/2026-09-21/marco-camera-and-nutrition-review.md)。

2026-09-21补充：一道番茄炒蛋的逐项装盘仅测得这道菜的总量，不能自动拆出内部番茄、鸡蛋及油盐。已知配方的整批营养与按平均比例估算的某份营养分开；选择性取食不能沿用原始配比持续扣减。若配方不可取得，保留重量及未知／有限参考。小量油盐与100–3000g主平台的精度分别验证；同一个盘位的备料和持续供餐不能同时发生。[详细复核](planning/2026-09-21/marco-camera-and-nutrition-review.md)。

- 营养值由匹配的食物／配方参考和可食用重量换算，不能从相机或电子秤直接测得人体营养状态。M1.2采用4项官方USDA SR Legacy固定记录及未知混合项，来源和版本见[资料核查](research/2026-09-19-nutrition/reference-audit.md)；当前学校200／100／150g模板仅示范，未经学校审核，不作为营养合规标准。
- 记录来源 ID、单位、生熟状态、配方版本和时间；初版优先本地使用少量 USDA FoodData Central 开放记录与登记配方。
- 提供量、余量、估计供给营养和经确认的用餐记录分开。总重量下降不直接等于吃下了同等重量或已知分项营养。
- 混合食物无法合理分配重量时标记不确定；先验证分别称量食物或适用的已知配方，不承诺任意混合餐识别。
- 食物身份优先用登记菜单／配方和批次确认，视觉提供候选及变化线索。俯视 RGB-D 不能看到被遮住的配料，不能直接测油盐或以颜色验证肉已熟透；生熟／烹饪状态由可靠记录确认，未知时保留未知。
- 单盘位可在装盘时逐项加料，以稳定重量差记录提供量；用餐中的总重下降仍不能唯一确定每项摄入。混合菜按配方的平均营养需满足得率、分布等假设，选择性取食后不能继续称为精确分项营养。
- 学校原型使用匿名样本餐和汇总信息，不建立儿童健康档案；个人演示先采用成年人。功能用于膳食理解，不进行医疗诊断或治疗性饮食处方。
- 学校规则按适用计划与指引审核配置；称重或食物组识别本身不证明午餐全面合规。

## 技术与评价

Pi 5 接一个称重测量系统及 ADC、顶部相机和显示／提示；温度模块依已界定的用途选择。RGB-D 为增强候选，与 RGB 基线比较后判断收益；不因增加学校／个人配置就默认加第二相机或分格秤。FastAPI、PostgreSQL、React/TypeScript及本地双语资源已用于P0；OpenCV与轻量模型仍为M2候选，未引入i18next。相机、ADC、内存、安装结构和预算仍需测试后确定。

P0的iPhone使用Swift／SwiftUI，厨房Web使用React／TypeScript／Vite，共享Python/FastAPI＋PostgreSQL后台；设备显示页已可在Mac浏览器查看，独立控制台配对已在Mac模拟环境实现，Pi本地全屏、真实校准与实物绑定仍待实物阶段。App与Web共用API、权限和状态，不直接共用界面代码。采集／视觉与业务分开，单设备HTTP接入和前台WebSocket更新；不默认增加MQTT、Redis或云部署。原顾客PWA／全Web方向不再采用，Android不在首版。

App中的个人／工作切换由后台授权，不能让普通注册用户自行取得管理权限，也不把员工私人的餐食自动共享给餐厅。App不承担持续称重／核心推理，后台和Pi继续工作；退到后台的手机可能被挂起，需要后台提醒时另接APNs。先用App内扫码和前台同步演示，云端远程访问、系统推送与上架后续按需安排。学校仍为匿名样本／汇总，个人仍不用厨房流程。

模拟器与实物共用数据接口，记录simulated／replay／hardware及识别来源；模拟结果只证明对应软件流程，不证明硬件或模型性能。物理余量、已接受未配出的订单预留、在制未来供应分开；同一份不因订单与重量再扣两次，任务与事件重发去重。所有端使用后端的同一业务状态，营养仍依照下文资料规则，不推断未知混合菜的精确摄入。

细化规则：接受建议创建一次任务；制作完成还不是实际补入，加料事件确认不能再把计划量加到已经更新的秤重。订单接受时才预留，配出核对前不提前释放预留；未监测菜单项按人工可供份数处理并标来源。同一监测会话区分自取与员工配餐，不自动猜随机减重对应哪张订单。会话重新绑定／换模式不自动增加提供量，关闭前处理未决任务和预留。

评价测量／食物识别、未知类别错误接受与拒识、参考数据下营养换算与人工计算的一致性、空盘和剩余、操作负担及故障恢复。食物识别按独立烹饪批次／日期测试，补餐保留人工／固定阈值／消耗速度基线。营养换算验证不等于食物化学成分检测；受控实验不等于真实健康效果或商业减损。当前所有误差与效果指标均待实测。

Metafoodx 和 Controliza 继续作为直接参照；扩展场景本身不证明市场独有或商业领先。用有限条件下可复现的改进和清楚的能力取舍解释价值。

## AI 训练与部署建议

当前主候选是 MobileNetV3-Large 的 IMAGENET1K_V2 预训练权重，Small 保留作对照；用 Python／PyTorch 在现有 MacBook 上对4–6类菜品微调。用户提供M2／16GB信息，只读系统检查进一步确认当前工作机为M2 Pro、16GB，学校GPU资源未知。经独立批次测试和导出一致性检查后，在Pi 5运行ONNX Runtime CPU推理。最终仍需按实测选择模型，未开始训练或部署，不承诺特定识别率或吞吐。

图片／视频抽帧须有正确标签，同盘／同批次／同视频保持在同一数据划分，深度信息只有通过相应输入处理才会被使用。补餐预测另用有效重量与餐期数据，营养用已确认资料换算；Kimi／DeepSeek 大模型不是首版必需，API 调用不等于本地训练或本地推理。详见[训练与 Pi 部署路线](planning/2026-09-14/ai-training-and-pi-deployment.md)。

若采用 RGB-D，优先测试 RGB 轻量模型＋经标定的显式深度几何处理，再比较加入小型融合分类层的收益；直接四通道或双分支输入作为按需对照。RGB、原始深度、标定、正确菜名及批次记录需对应。固定模型的参数量不会随训练照片数线性增加，但图像处理和整机服务负载需要单独核算。Pi 5 仍是未实测的候选，不能保证最终模型与整机一定满足要求；兼容性和初步计算验证应在完整训练之前开始。

## 当前采购建议

下文及旧工作簿为2026-09-15的历史采购候选：Gemini2 USB完整相机、Pi5 8GB、Active Cooler、microSD、NAU7802与10kg四线全桥称重梁、7英寸Touch Display2。2026-09-21建议先测RGB，Gemini2不再作为本期必买；新相机及配套尚未定稿，旧表不能直接作为当前下单单。称重工作毛重先≤5kg，平台和偏载待测。相机另备A-C USB3数据线；显示套装线不重购。当前集成电源按下文两支路设计；原官方27W Pi电源及独立灯电源只保留为旧台架／诊断方案，不与新电源包全部叠加采购。

用户当前不设总预算上限，但仍平衡性能、准确性和成本。清单51条含配套／复用／后续项，当前计入人民币预留4314–6651元、不含运费；这不是国内实时报价。淘宝被工具站点策略拦截，京东Chrome要求登录后用户选择按厂家资料继续，未获得国内商品SKU成交价。详见[采购说明](planning/2026-09-15/procurement-guide.md)及[采购数据](planning/2026-09-15/procurement-data.json)。

该清单是单机台架／展示参考，Pi与灯使用各自适配器，含工具与校准用品；不是统一电源或十盘位餐线BOM。工作簿与结构化数据本轮原样保留，不可直接乘十当成商业报价。

## 统一供电与多盘位扩展建议

用户希望借鉴Metafoodx整洁走线。当前工程建议具体化为12V5A成品适配器（参考GST60A12-P1J）、亚博YB-MPP01-V1.0 Pi5 PD电源板和ORICO-BT2U3-7AB Hub：Pi／屏幕／风扇／ADC用Pi支路，相机和两条≤2.5W的5V灯用Hub支路。Hub自身接12V，故不另加灯用降压板；该型号不能直接接24V。亚博板输入用KF301螺丝端子，USB-C输出经5A e-marker线接Pi，不占GPIO作供电板通信。

供电专项18条含套装／复用项，当前新增预留RMB451–807，不是国内实时报价。主件规格和官方图片已核对，但Hub DC公头尺寸／极性、上游防倒灌、相机组合及完整负载仍待验证，不能按猜测上电。具体见[单机供电细化](planning/2026-09-15/power-supply-detail.md)及[数据](planning/2026-09-15/power-supply-data.json)。原采购XLSX／JSON仍保留，电源部分的替换关系以专项说明为准，未重算旧工作簿总价。

Gemini2保留为可选深度增强对照；先验证普通RGB与重量，只有具体任务的增益值得其成本与复杂度时才保留3D。不为未来多路相机提前升级主机。多餐位共享和成本估算仅作未来部署研究，不能进入本期工作量／预算或成为demo验收前提，详见[相机、供电与扩展](planning/2026-09-15/camera-power-and-scaling.md)。

## 集中供货、制造协助与个人贡献

亚博中文目录已看到Pi5、散热、存储、线材、7寸屏和USB Hub等；Gemini2／335系列也有官方产品或课程。称重元件、NAU7802及适配餐盘的称重结构尚未确认现货；一站代采、单台定制、交期和费用需分项报价。官网欢迎OEM／ODM／定制，不等于已接受本项目。

用户已明确本次询价工作边界：供应商负责部件配套、整机结构制作、固定、内部配电及全部接线集成；我方负责系统安装、驱动与采集代码、校准、AI、后台／网页及后续测试，AI助手协助编写与联调。当前不要求供应商提供测试报告、软件例程、系统镜像、基础标定或复杂图纸资料包。RFQ V3移除读卡器、运输／售后条款、18项细分报价和逐编号验收回复，仅询问能否制作1台、整机价格、周期与必要替代。40／30／30保持计划分工，实际工作按发生内容记录。

V3只保留制作必需的参考：约450×400mm底座、350×250mm浮动平台、镜头距承载面450–600mm、10kg平台传感器与工作毛重≤5kg，以及12V5A单线入机、Pi5专用供电和USB3 Hub。供应商可按实际模块提出紧凑结构，制作前确认。旧V2中的±5g、重复／偏载／漂移和热盘等测试目标不再作为对外询价或供应商服务要求；组内后续研究仍需真实校准与硬件数据，简化询价不代表性能已经得到验证。

学校指南第4页鼓励产业合作但要求导师保障监督和评核，第11页表中个人贡献占78%；这不是全面禁止外部制造。指南12页未给出专门生成式AI使用比例，不能因此认定AI包办代码已获允许。实际委托和AI协助边界应让Marco了解，外部软件／文档交付承诺遵循指南要求。详见[亚博采购与定制评估](planning/2026-09-15/yahboom-sourcing-and-customization.md)及[未发送询价草稿](planning/2026-09-15/hardware-fabrication-enquiry-draft.md)。

## 当前文件

- [学校Project Proposal](planning/2026-09-21/proposal-spec.md)：英文10页，七项学校要求、资源、参考和意见签名；[Word](<output/docx/AY26_ProjectProposal_Group 2.docx>)／[PDF](<output/pdf/AY26_ProjectProposal_Group 2.pdf>)，9月28日团队提交目标，9月29日23:59平台期限，尚未提交。
- [当前品牌规范](brand.md)：用户已选V7无刻度纯碗；字体、配色、当前矢量素材及历史关系。
- [餐食计量Logo R5](planning/2026-09-17/senplate-logo-measured-plate-r5.md)：历史语义探索，已由用户选定A版取代。
- [GPT网页版图像生成提示词](Senplate_Logo_ImageGen_Brief.md)：历史探索简报，用户已上传并选定结果，不再等待选稿。
- [Profile／层序Logo R4](planning/2026-09-17/senplate-logo-profile-r4.md)：视觉尚可、意义不足的参考稿，原Figma几何和导出保留。
- [Interval图形近似初筛](research/2026-09-17-logo-similarity/similarity-review.md)：旧稿证据；香港图像查询及两条第9类详情、Aqua美国有效注册，不能套用到R4。
- [Interval旧矢量Logo](planning/2026-09-17/senplate-vector-logo-studies.md)：气质曾获初步认可，图形因近似问题由R4取代；原Figma几何、SVG和预览保留。
- [Logo真实标记审美校准](planning/2026-09-16/logo-reference-calibration.md)：用户已选Polestar与Linear；参照来源及上轮QA保留。
- [Senplate Logo方向重整R3](planning/2026-09-16/senplate-logo-reset-r3.md)：A／B已在负面反馈后撤下，旧资产保留，不再要求用户二选一。
- [Senplate Logo修订R2](planning/2026-09-16/senplate-logo-refinement-r2.md)：三个符号均被用户否决，旧文件保留，不再作为待选组。
- [Senplate Logo与VI方向V1](planning/2026-09-16/senplate-logo-vi-directions.md)：第1版已选为工作基准，原Logo需改；旧三图与拟议色值保留。
- [Senplate中文版商业计划书](planning/2026-09-16/business-plan-zh.md)：当前商业方案与假设；[Word](<output/docx/Group 2_Senplate_商业计划书_中文版_V1.docx>)、[PDF](<output/pdf/Group 2_Senplate_商业计划书_中文版_V1.pdf>)。
- [Senplate商标与域名初筛](research/2026-09-16-senplate-name-check/senplate-trademark-and-domains.md)：当前名称决定、三地文字检索、两个访问缺口、近似使用线索及九个域名原始结果；无申请或购买。
- [命名讨论稿](planning/2026-09-16/naming-shortlist.md)：历史候选和取舍；用户已选择Senplate，中文搭配未定。
- [品牌命名与视觉方向V1](planning/2026-09-16/brand-visual-directions.md)：旧探索保留；三张未选中的概念图、原始提示词、显示映射及待调整项，不继续出图。
- [iPhone页面与权限V1](planning/2026-09-16/app-pages-and-permissions.md)：导航、页面、四条操作链、Web／设备职责、权限与异常文案。
- [业务状态与API V1](planning/2026-09-16/software-workflows-and-api.md)：状态转换、关键对象、幂等／版本、首批接口、JSON示例和错误处理。
- [软件开发批次与验收V1](planning/2026-09-16/software-mvp-and-acceptance.md)：M0/P1/实物阶段、演示脚本、待执行场景和三人分工。
- [软件范围与架构讨论稿](planning/2026-09-16/software-scope-and-architecture.md)：保留的业务与技术基线；iPhone双角色、厨房／管理Web、设备界面、共享后台和模拟器；P0已运行，完整范围分阶段完成。
- [Metafoodx App研究](research/2026-09-16-metafoodx-app/app-review.md)：官方功能、全部公开商店截图、更新记录、角色定位与本项目取舍。
- [V2 DOCX](<output/docx/AY26_ProjectSuggestion_Group 2_v2_MultiScenario.docx>)、[V2 PDF](<output/pdf/AY26_ProjectSuggestion_Group 2_v2_MultiScenario.pdf>)：保留的四页多场景建议书，签批留空；盘位和识别细节待下一次修订同步。
- [多场景方案与营养依据](planning/2026-09-14/multi-scenario-suggestion-v2.md)：当前功能／场景与详细分工。
- [持续监测硬件](planning/2026-09-14/continuous-monitoring-architecture.md)：共用硬件、采集与异常处理。
- [相机、供电与十盘位成本](planning/2026-09-15/camera-power-and-scaling.md)：当前选型比较、单线入机候选、共享架构及未实测的物料情景。
- [单机适配器、电源板与接线](planning/2026-09-15/power-supply-detail.md)：当前12V两支路、采购补充、接口未决项和台架步骤。
- [亚博采购与定制评估](planning/2026-09-15/yahboom-sourcing-and-customization.md)：中文目录、屏幕、定制费用构成及学校贡献边界。
- [硬件RFQ版本入口](planning/2026-09-15/hardware-fabrication-enquiry-draft.md)：当前3页V3.1 Word／PDF，2页简化需求加1页附图，仅整机硬件制作与集成；V1/V2/V3保留为历史，尚未发送或获得报价。
- [组员资料](planning/2026-09-14/group-2-details.json)：唯一结构化身份和当前导师状态。
- [handoff.md](../../handoff.md)、[decision-log.md](decision-log.md)、[work-log.md](work-log.md)：交接、决定与历史。
- [V1 DOCX](<output/docx/AY26_ProjectSuggestion_Group 2.docx>)、[V1 PDF](<output/pdf/AY26_ProjectSuggestion_Group 2.pdf>)及[V1 范围](planning/2026-09-14/scope-and-roles-for-review.md)：历史版本，保留供比较。
