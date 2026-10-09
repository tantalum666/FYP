# Group 2 Work Log

更新：2026-10-10。追加式记录；当前状态以 handoff.md 为准。

## 2026-09-14 建议书制作与上下文协议

- 目标：完成英文建议书、明确 Arduino 可选，并建立可恢复的 Markdown 工作流。
- 已读：当前 10 份项目 Markdown 共 1,069 行；FanPass／Rillora 的 AGENTS 与交接相关部分；学校原模板三页。
- 已判断：资料足以填写建议书；相机型号、预算和试点属于后续验证项。Pi 单机方案可作为优先工程候选，已有 UNO 保留备用。
- 初始进度：新建 AGENTS、product、decision-log、handoff 和本记录，并开始制作建议书。
- 边界：未运行硬件，未代签、取得导师同意或提交 Moodle。

### 完成结果

- 按学校原模板生成英文 DOCX 和对应 PDF，均为四页。范围为原位持续监测、AI 辅助补餐、厨房任务与减损评价，QR 菜单／点餐为辅助必做；Pi 5 单机优先，UNO 可选。
- 表内精炼主要职责，保留 40／30／30；姓名、学号、邮箱及 Macro 待确认状态均核对。
- 修复成员表跨页、空白溢出页和标签孤立换页。最终四页以原始分辨率逐页检查，页码 1–4 正确，签批栏未改动。
- 原模板 SHA-256 保持 7cc26bead5d75b140a3044328bd724ac6e418dc5efaa703084f39b6d363b10d5；最终仅 word/document.xml 与字段更新设置变化，其余包部件及关系保留。结构、样式、字段和控件审查完成。
- 交付：[DOCX](<output/docx/AY26_ProjectSuggestion_Group 2.docx>)、[PDF](<output/pdf/AY26_ProjectSuggestion_Group 2.pdf>)。证据：[final-validation.json](output/qa/suggestion-2026-09-14/final-validation.json)。
- 上下文流程和当前产品／技术文件已同步；旧研究保留为有时间范围的证据，旧共享扫描预算不再作为当前报价。
- 剩余：Macro 口头同意和签批、实际预算与模块选型、真实场地或受控实验方案；没有采购、硬件测试或 Moodle 提交。

## 2026-09-14 多场景建议书 V2

- 目标：按 Marco 对场景和社会价值的建议修订，并保留刚完成的 V1。
- 开工完整阅读：15 份项目 Markdown，1,244 行；组合输出截断处已补读。研究 USDA FDC、CFS NIIS 和学生午膳指引，核对学校用途与营养估算方法。
- 设计结果：同一持续监测核心支持供餐、学校和个人三个配置，新增营养参考、配餐比较与个人餐食摘要；Pi 单机和辅助 QR 功能继续保留。
- 文档结果：[V2 DOCX](<output/docx/AY26_ProjectSuggestion_Group 2_v2_MultiScenario.docx>)与[V2 PDF](<output/pdf/AY26_ProjectSuggestion_Group 2_v2_MultiScenario.pdf>)均四页；沿用原模板并检查全部最终页面。
- 验证：V2 只有 word/document.xml 变化，成员身份、页式和签批表不变；V1 DOCX/PDF/脚本哈希未变。修复了正文末尾单独溢出一页的问题。证据在 [V2 final-validation](output/qa/suggestion-v2-2026-09-14/final-validation.json)。
- 当前状态：已记录与 Marco 的讨论，修订范围待审阅；签批留空，未上传或提交，未实际开展硬件／营养／学校试验。手册的相关页已读，不声称全文全部核对。
- 收尾：更新 product、README、handoff、decision-log、当前硬件说明和版本索引；V1 范围说明标为历史。

## 2026-09-14 单设备盘位与识别可靠性

- 目标：解释一套硬件和多个称重位置的区别，核对三个场景共用条件、混合食物／遮挡／肉类及生熟识别可行性。
- 开工阅读：本轮 16 份项目 Markdown 全文共 1,337 行；压缩后精简恢复并完成缺失正文，未用上一轮阅读记录替代。证据在 [full-read-completion](output/qa/single-station-reliability-2026-09-14/full-read-completion.json)。
- 研究：读取 Nutrition5k 原论文相关章节及作者数据说明，重新读取 Metafoodx FAQ、FDC 数据定义；FSIS 与 SparkFun 直达受限后使用官方搜索索引正文。未下载整个数据集、复现模型或再次观看视频。
- 结果：当前工程基线为一套设备、一个独立称重盘位，三个软件配置轮流演示。采用登记身份／配方、连续重量、有限视觉及确认；单秤逐项加料可记录提供量，但不能从混合餐总重下降得出精确分项摄入。RGB-D 不能消除完全遮挡或直接测成分，肉类颜色不能验证安全熟度。
- 文件：新增[单盘位与识别可靠性](planning/2026-09-14/single-station-recognition-reliability.md)，更新 product、README、多场景范围、持续监测架构、decision-log 和 handoff。旧研究／V1 范围保留历史语境。
- 验证：本轮 Markdown 及内部链接检查、当前基线一致性和旧建议书保留哈希记录在 [closeout-validation](output/qa/single-station-reliability-2026-09-14/closeout-validation.json)。硬件和识别验证只形成计划，未实际执行。
- 剩余：V1/V2 DOCX/PDF 及构建脚本未覆盖，V2 多盘位文字待下次建议书修订同步；具体量程／容器／相机与准确度待测试。未新增 V3，未签批、采购、联系或提交。

## 2026-09-14 AI 训练与树莓派推理解释

- 目标：向初学者解释图片／视频标注、迁移学习、Kimi／DeepSeek 与轻量视觉模型区别，以及电脑训练后部署到树莓派的过程。
- 开工：17 份项目 Markdown 全文共 1,473 行；补读组合输出截断区间。证据：[full-read-completion](output/qa/ai-training-deployment-2026-09-14/full-read-completion.json)。
- 研究：官方 PyTorch 迁移学习、Torchvision 模型、ONNX 导出与树莓派推理示例、MPS、AI HATs，以及 Kimi K2.5／DeepSeek-VL2 模型说明。只读 PyPI 元数据确认 Linux aarch64 包存在；未下载包或权重。
- 建议：PyTorch＋MobileNetV3-Small 作为首版训练候选，电脑／可用 GPU 训练，分批次验证后导出 ONNX，在 Pi CPU 推理。RGB-D 需要显式输入处理，补餐预测及营养换算另用各自依据；大模型和加速器不是默认必选。
- 文件：新增[AI 训练与 Pi 部署](planning/2026-09-14/ai-training-and-pi-deployment.md)，同步 product、README、持续监测架构、decision-log 和 handoff。
- 验证：[closeout-validation](output/qa/ai-training-deployment-2026-09-14/closeout-validation.json)核对内部链接、表格／脚注、文档状态及旧文件哈希。训练、导出和运行测试均未执行，说明中的性能／样本数只为候选或起步计划。
- 剩余：真实数据集、可用训练硬件、目标 Pi 环境兼容性和性能待实施；V1/V2 建议书原样保留，尚未将本轮技术细节同步到新的正式版本，无采购、云任务、提交或对外联系。

## 2026-09-14 RGB-D 训练与整机算力可行性

- 目标：解释 3D 数据怎样进入特定训练、模型大小与准确性的关系，以及 Pi 能否承担整机负载。
- 阅读：18 份初始项目 Markdown 全文 1,613 行；已补读 V1 范围尾部与竞品研究开头的截断范围，硬件长文分段完整读取。[阅读记录](output/qa/rgbd-compute-feasibility-2026-09-14/full-read-completion.json)。
- 研究：Nutrition5k §4.4 两类深度使用方式、RealSense 深度单位／对齐官方代码、Torchvision 模型规模、PyTorch Pi 运行示例的输入／量化条件及 ONNX 量化限制。没有下载数据集、权重或执行示例。
- 结果：优先 RGB 小模型＋显式几何处理，再比较小融合层；四通道／双分支按需对照。成对样本与标定必须一致，固定模型不会随照片数线性变大，精度及完整负载仍需本地验证。
- 文件：扩展[训练路线](planning/2026-09-14/ai-training-and-pi-deployment.md)，同步 product、README、持续监测架构、decision-log 和 handoff，没有再创建一份重复的训练规范。
- 验证：[收尾记录](output/qa/rgbd-compute-feasibility-2026-09-14/closeout-validation.json)核对 Markdown 链接、表格／脚注、当前边界和 V1/V2／身份文件哈希；训练、导出、Pi 性能及准确率测试均未执行。
- 剩余：相机／Pi 资源和最小台架实验、数据采集与实际融合效果；V1/V2 保留，正式文件待下一次修订同步。没有采购、云算力任务、导师联系或提交。

## 2026-09-15 详细采购参考与训练电脑

- 目标：给出训练电脑、Pi5 8GB模型及细到电源线／改装的清单。用户补充M2／16GB、学校资源未知、预算先不设上限，并允许Chrome；京东登录后选择按厂家资料和预算参考继续。
- 阅读：18份初始Markdown共1699行全文，补读截断；读取Spreadsheets技能、创建流程、API和样式规则。模板picker被拒绝后采用采购用途自建表，未因此暂停任务。
- 研究：Orbbec Gemini2／335当前官网价格、库存、线材；SDK的M2与ARM64边界；RealSense参考价、DFRobot低价相机、Pi电源／屏幕、NAU7802接线和参考称重梁。淘宝站点策略拒绝后没有绕过，Chrome京东停在登录页。
- 电脑与模型：当前系统只读核对M2 Pro／16GB、macOS26.5.2、约473GiB可用；建议Large IMAGENET1K_V2为主、Small对照，未安装或训练。
- 交付：[采购说明](planning/2026-09-15/procurement-guide.md)、结构化数据及[采购工作簿](<outputs/01a07aeb-a256-7572-a42e-bd7e4668674f/Group 2_Hardware Procurement_20260915.xlsx>)。51条记录、5相机、16接线；人民币预留4314–6651、不含运费，非实际报价。
- 表格验证：用Artifact Tool创建并重算，验证实际报价、零值、已有设备排除、数量空白和恢复。修复预览中0与空白比较混淆，使用ISBLANK并加强数值断言；检查10个最终范围、3个表的冻结窗格与来源注释，保留所有明细。
- 收尾：同步product、README、训练路线、共用架构、decision-log及handoff；[收尾记录](output/qa/hardware-procurement-2026-09-15/closeout-validation.json)记录内部链接、工作簿结果和旧版哈希。没有新增suggestion、采购、训练、Pi或真实营养／减损试验。

## 2026-09-15 相机比较、统一供电与十盘位成本

- 目标：回答Gemini／RealSense如何选、Metafoodx外部一根线如何借鉴、十个盘位是否需十套完整硬件及经济性。
- 阅读：19份初始项目Markdown全文1932行，组合截断已补读；[阅读记录](output/qa/camera-power-scaling-2026-09-15/full-read-completion.json)。查看用户照片，重新核对相机厂商／SDK、Pi供电、RealSense多机、成品低压电源及WittyPi5官方索引。
- 结果：维持Gemini2单机首测，明确连续监测是流程选择；解释宽视野与像素密度取舍。单线入机建议外置适配器、低压转换分路，24V60W／WittyPi5为候选而非最终接线。十盘位共用计算、屏幕和区域相机，独立称重路径不能省略；不增加FYP必做盘数。
- 文件：新增[相机、供电与扩展](planning/2026-09-15/camera-power-and-scaling.md)，同步product、README、持续监测架构、采购说明适用范围、decision-log及handoff。原工作簿／数据、V1/V2及身份资料原样保留。
- 成本：四相机区域、十称重节点、一共享Pi级主机的物料情景RMB13000–21700；条件与遗漏逐项列出，不是询价或商业售价。不把原4314–6651单机参考直接乘十。
- 验证：[收尾记录](output/qa/camera-power-scaling-2026-09-15/closeout-validation.json)核对名义视野／功率／成本算术、Markdown链接、当前数量边界及旧文件哈希。旧工作簿没有修改，因此未重跑表格渲染；新文件为Markdown，没有新DOCX/PDF。
- 剩余：单路实际SDK／几何／供电及称重台架验证、集成电源的具体稳压器／Hub／线束、真实布局和价格。没有采购、上电、训练、真实试点、重看视频、联系卖家／老师或提交。

### 同一讨论的范围补充：单台demo与国内电源

- 用户明确FYP只做一台设备；十盘位只是未来真正进入自助餐的疑问，并指出国内淘宝有电源适配器选择。
- 沿用本轮完整阅读记录，补读AGENTS、product、handoff、相机供电说明、decision-log、work-log、README及采购说明变更段；组合输出截断的decision-log已完整补读。
- 更新product、README、采购说明、相机供电说明、decision-log和handoff：移除本期追加节点／共享相机验证的建议，保留未来研究；国内成品电源按电压、电流、接口及Pi兼容性筛选，MeanWell／WittyPi5不再容易被理解为必买。
- 再次查阅Pi供电与Gemini2中文参数的官方索引，未取得淘宝实际SKU或报价。没有修改采购XLSX／JSON、V1/V2和身份资料，没有硬件或算法实验。
- 验证与阅读记录在[范围补充核对](output/qa/camera-power-scaling-2026-09-15/scope-followup-validation.json)；当前下一步只围绕一台demo的国内供电匹配与验证。

## 2026-09-15 继续细化单机电源

- 目标：把成品适配器、Pi电源板、Hub、低压分配和线材落实到可核对的型号与配线；仅一台demo。
- 阅读：沿用本轮全量阅读及补充记录，重新完整读取入口文件、相机供电长文、README、decision-log和work-log，补读采购及架构相关变更段。[阅读与盘点](output/qa/power-supply-detail-2026-09-15/reading-and-inventory.json)。
- 研究：官方明纬中国系列／中文数据表、亚博产品和Chrome接口／规格图、奥睿科产品与长图、PiPD／显示接口及Gemini2电源条件。未使用搜索中的旧型号或第三方数字替代当前图片；ORICO图为单口1.5A，官方上游字段与实物形态有矛盾，采用原装线并保留到货核对。
- 交付：[单机供电专项](planning/2026-09-15/power-supply-detail.md)及[数据](planning/2026-09-15/power-supply-data.json)：12V5A、亚博YB-MPP01、ORICO-BT2U3-7AB两路，Hub同时供相机和两条灯；18条记录，人民币预留451–807，非报价。
- 变更：同步product、README、采购说明、持续架构、相机供电旧候选状态、decision-log及handoff。原P02／M19／X01替换关系写清，原工作簿／JSON与V1/V2保留，未生成新版正式建议书或表格。
- 验证：[收尾验证](output/qa/power-supply-detail-2026-09-15/closeout-validation.json)核对BOM与预算、功率49.375W假设、内部链接和旧文件哈希。没有上电、PD协商、相机数据或称重实测。
- 剩余：取得样件后确认HubDC插头与极性、上游供电行为，再测单机整条采集与负载。没有淘宝／京东实际SKU、询价、购买、对外联系或提交。

## 2026-09-15 亚博中文供货与定制合作

- 目标：评估单供应商硬件覆盖、屏幕选择、定制费用和可保留的学生／AI实现工作。
- 开工：独立完成当前21份项目Markdown全文2348行；采购说明按1–100／101–EOF分段。记录：[full-read-completion](output/qa/yahboom-sourcing-2026-09-15/full-read-completion.json)。完整读取PDF技能；学校原指南12页为图片式，逐页渲染并查看全部页面。
- 研究：Chrome中文商城在加载完成后查到Pi5、散热、TF卡、7／10.1／15.6寸屏、电源和USB Hub目录；7寸中文详情／课程确认1024×600 TN／IPS、HDMI／USB及Pi5的microHDMI提示。Gemini系列课程与官方OEM／ODM合作说明支持询价候选，未证明单台接单或报价。
- 判断：优先集中供货和有限加工装配，完整硬件设计单列报价；核心采集、校准、模型、后台与网页和最终测试由组员在AI辅助下实现并能解释。学校鼓励产业合作且强调个人贡献，指南未明确AI比例，不替老师认定全部AI编码获准。
- 交付：[供应商与屏幕评估](planning/2026-09-15/yahboom-sourcing-and-customization.md)、[未发送询价草稿](planning/2026-09-15/hardware-fabrication-enquiry-draft.md)。人日成本只是明确假设，不是实际报价。
- 收尾：同步product、README、采购说明、decision-log及handoff；原采购XLSX／JSON、电源数据、V1/V2、身份和学校PDF保留。证据：[closeout-validation](output/qa/yahboom-sourcing-2026-09-15/closeout-validation.json)。
- 未完成：具体供货单、屏幕切换、电源重算、定制范围／交期和真实报价、Marco对合作边界的意见；没有外部联系、表单提交、采购、硬件测试、代码开发或新建议书。

## 2026-09-15 至16 详细硬件需求与供应商询价V2

- 目标：让供应商理解项目用途、原位持续工作流程和目标成品，并可按具体机械、量测、接口、供电、交付和验收条件报价。
- 阅读：本轮为紧接供应商评估的补充任务，沿用21份／2348行全读记录，补读新增和变化文件；压缩后恢复入口、当前决定、RFQ全文及待修改规范，组合截断补读。记录：[reading-record.json](output/qa/rfq-v2-2026-09-15/reading-record.json)。Documents／PDF技能已读取，模板选择被拒绝后使用适合技术RFQ的原生Word排版。
- 内容：明确一台、一个称重位置、同机三个配置；把用途、操作、Metafoodx外观、尺寸／受力／清洁、称重指标、RGB-D与照明、Pi／屏幕、供电线束、原始接口、资料与验收连成完整要求。主报价分别列标准物料和工程服务，补入示范容器；替代及热盘等按选配处理。所有数值为询价目标，供应商须逐项答复偏离。
- 图片：Chrome查看Metafoodx实际产品页，暂停页内视频并按可见DOM位置截取产品和结构区域；没有生成仿造产品图、推断内部电路或采用厂商宣传为验收值。两张实际使用图片及来源／哈希见[素材依据](planning/2026-09-15/rfq-assets/source.json)。
- 交付：[完整正文](planning/2026-09-15/hardware-fabrication-enquiry-v2.md)、[Word](<output/docx/Group 2_Hardware RFQ_v2.docx>)、[PDF](<output/pdf/Group 2_Hardware RFQ_v2.pdf>)。10页、9张原生表格、2张图片；报价表18个分项另加合计。旧RFQ全文保留在archive，原入口改为版本索引，两版suggestion及旧采购文件没有覆盖。
- 排版验证：使用随工具提供的Python和LibreOffice。初次CJK缺字，改为任务内Fontconfig引用现有Arial Unicode字体；未安装全局字体或修改依赖。修复图片段落固定行距导致的裁切及分页溢出，再检查最终render-06全部10页，中文可读且可检索，图表、页码与报价空格完整。最终PDF复制自该已检查渲染，失败的中间导出仅留在QA。
- 收尾：同步product、README、采购说明、供应商评估、RFQ版本入口、decision-log和handoff；[收尾核对](output/qa/rfq-v2-2026-09-15/closeout-validation.json)记录链接、要求编号、原件哈希、文件存在性及未含成员学号／邮箱。
- 剩余：供应商能否接受单台、具体型号与工艺、目标性能可达性、分项报价、交期和实际合作范围待答复。未发送询价、填商务表单、下单、签约、运行训练或硬件；正式建议书仍为之前保留版本。

## 2026-09-16 供应商硬件询价V3简化

- 目标：按用户反馈，把供应商工作收敛为类似Metafoodx外形的完整硬件制作和集成，移除过多采购琐项及软件／测试服务要求。
- 阅读：沿用同一RFQ任务已有全读和V2记录，补读入口、当前要求、V2全文及相关变更段；[本次阅读记录](output/qa/rfq-v3-2026-09-16/reading-record.json)。复用已读取Documents／PDF技能和已验证字体配置，没有重新选择模板或重做竞品研究。
- 交付：[V3正文](planning/2026-09-15/hardware-fabrication-enquiry-v3.md)、[2页Word](<output/docx/Group 2_Hardware RFQ_v3_Simple.docx>)及[2页PDF](<output/pdf/Group 2_Hardware RFQ_v3_Simple.pdf>)。一张真实Metafoodx截图、一张8类部件表；明确供方完成部件、结构、配电和接线，我方处理系统、代码、校准与测试。
- 删除范围：不列读卡器、运输条款、供应商驱动／系统、基础校准与测试报告、复杂资料包和细分验收；询价仅需能否制作、总价、周期和替代。参考尺寸和必要电气／受力条件保留，未将部件集成等同于性能达标。
- 验证：首次渲染即为2页，两页均按原始尺寸查看；中文、图、表、页码无裁切溢出。最终PDF来自已检查渲染。正文对应、文件／内部链接、旧版哈希与范围删除检查见[收尾验证](output/qa/rfq-v3-2026-09-16/closeout-validation.json)。
- 收尾：同步product、README、采购说明、供应商评估、版本入口、decision-log及handoff。原V2正文／Word／PDF、V1与两版suggestion、采购数据和身份保留。未发送、取得报价、下单、安装系统、写业务代码或测试实物。

## 2026-09-16 RFQ V3.1增加三张外观／场景图

- 目标：补充Metafoodx产品图片，保留用户确认的简化制作范围。
- 阅读与素材：同一任务增补，沿用全读与V3记录；查看既有官方结构截图、用户PNG和Pomona案例已渲染第1–3页，抽取第2页设备照片并视觉确认；[来源记录](planning/2026-09-15/rfq-assets/source-v3-1.json)。没有生成或修饰产品外观。
- 交付：[V3.1正文](planning/2026-09-15/hardware-fabrication-enquiry-v3-1-images.md)、[Word](<output/docx/Group 2_Hardware RFQ_v3.1_Images.docx>)、[PDF](<output/pdf/Group 2_Hardware RFQ_v3.1_Images.pdf>)。共3页、4图，前2页需求与V3一致，仅版本标记变化；附图页含结构大图和2张场景图。
- 验证：3页均以原始分辨率检查，图片完整、来源清楚、无页溢出；首次抽取PDF图片时误用文件名索引，改用pypdf图片序列后成功，源PDF未修改。[收尾验证](output/qa/rfq-v3-1-images-2026-09-16/closeout-validation.json)核对原正文、图片内容、旧文件保留及内部链接。
- 收尾：同步当前版本入口、product、README、采购／供应商说明、decision-log及handoff；原V3及更早文件保留，无发送、询价回复、采购或实物测试。

## 2026-09-16 软件端与架构先行梳理

- 目标：硬件暂未完成，先梳理客户端、各端功能、共用后台、三种场景与无硬件开发方法。
- 开工：按独立工作轮全量读取27份自有Markdown、2965行，共15批；对连续监测架构89–107及RFQ V2的94–195补读截断正文。各文件范围、排除项与完成时间见[全读记录](output/qa/software-architecture-2026-09-16/full-read-record.json)，文件在阅读期间未变化。
- 研究：官方React/Vite起步路线、FastAPI WebSocket单进程边界与后台重计算说明、MDN PWA安装条件、PostgreSQL行锁资料；无依赖安装或示例执行。当前无应用package.json／pyproject.toml／compose入口。
- 交付：[软件范围与架构讨论稿](planning/2026-09-16/software-scope-and-architecture.md)。四端＋内部模拟工具，共享Web与后台；各端页面、供餐／学校／个人映射、状态／权限／数据对象、单盘位覆盖、AI与规则分工、Mac到Pi路线及阶段成果均说明。
- 关键规则：余量／订单预留／未来供应分开，配出与测量对账防双扣，建议接受去重生成任务；模拟、回放、硬件及人工／占位／模型输出留来源；学校匿名样本与个人份量换算沿用既有边界。
- 收尾：同步product、README、持续采集架构、训练路线、多场景说明、decision-log及handoff。文件链接、状态一致性、分工和旧交付物保留见[收尾核对](output/qa/software-architecture-2026-09-16/closeout-validation.json)。
- 剩余：页面／字段／状态细则及实际开发、模拟器与硬件接入。没有业务代码、应用测试、训练、真实硬件／商业成效验证、对外联系、采购或部署；RFQ V3.1和两版suggestion保持原样。

## 2026-09-16 Metafoodx App研究与iPhone双角色方案

- 目标：按用户偏好改App优先，仔细研究竞品手机产品；异步补充已确认只做iPhone、同一App涵盖个人／顾客和员工／管理者。
- 阅读：同一软件规划任务的纠正，继承27份／2965行全读；补读AGENTS、product、handoff、当前软件稿全文及相关研究／变更段。[阅读记录](output/qa/metafoodx-app-architecture-2026-09-16/reading-record.json)。
- 研究：重读官方移动文章、公司署名2026-09-03发布稿、App Store说明／版本记录，Chrome逐项查看5张iPhone截图和3幅官方功能图。保存5张浏览器证据图；没有安装、登录、操作客户后台或观看专门App视频。HK条目被非重试访问策略阻止，未绕过；Apple部分文档使用官方索引正文，范围如实记录。
- 结论：竞品公开主线为运营移动查看、单次扫描记录与报告，不能把它当成已验证的顾客点餐／营养App。借鉴信息组织、异常可见性和数据分类；原位持续监测及动作反馈由我们的业务定义和实测来证明。
- 交付：[研究](research/2026-09-16-metafoodx-app/app-review.md)、[证据](research/2026-09-16-metafoodx-app/evidence.json)、修订后的[架构](planning/2026-09-16/software-scope-and-architecture.md)。SwiftUI iPhone App双身份＋厨房／管理Web＋设备界面，共用后台；旧全Web稿完整归档，前台同步、后台通知和外网访问分开。
- 收尾：同步product、README、多场景、持续监测、训练图示、decision-log及handoff；[收尾验证](output/qa/metafoodx-app-architecture-2026-09-16/closeout-validation.json)核对链接、身份／角色范围、历史保留和规划状态。未创建应用工程、签名、安装依赖、调用平台账户、训练或部署。
- 下一步：iPhone双角色页面流程、权限矩阵、API数据链。实际硬件验证及正式建议书修订仍待后续。

## 2026-09-16 App详细设计V1

- 目标：把既有App架构细化到可以分工开发的页面、权限、状态及首批接口；本轮未开始应用编码。
- 阅读：沿用软件梳理的全读和App研究补充，完整读当前入口、product、软件架构200行和App研究；补读相关日志和README。[阅读记录](output/qa/app-detailed-design-2026-09-16/reading-record.json)。
- 技能：首次应用SwiftUI UI Patterns，完整读取SKILL、app-wiring和navigationstack，参考Apple底栏与路径文档；只形成导航／状态设计，没有新SwiftUI视图或编译声明。
- 交付：[页面与权限](planning/2026-09-16/app-pages-and-permissions.md)、[状态与API](planning/2026-09-16/software-workflows-and-api.md)、[开发与验收](planning/2026-09-16/software-mvp-and-acceptance.md)。两套导航、共用／个人／工作／Web／设备页面编号、权限矩阵、四条主线、19项首批接口及JSON例子、批次和待执行场景齐备。
- 设计复核：明确入盘测量已经改变物理余量，任务确认不再加一次；订单预留在配出核对前保留；未来任务量不算当前供应；换模式／重新绑定不再重复累计上台量。P0基线明确为规则，模拟数据不标已训练AI。
- 验证：[收尾核对](output/qa/app-detailed-design-2026-09-16/closeout-validation.json)检查链接、表格／图代码围栏、页面与接口编号、JSON语法及数量算例、角色和旧文件保留；不代表文中场景已在App或后台通过。
- 收尾：同步product、README、总架构、decision-log及handoff；原RFQ、suggestion、采购资料、身份和App研究保留。下一步是M0.1本地最小工程，尚未安装、签名、部署、训练或进行任何硬件测试。

## 2026-09-16 品牌命名与三套视觉方向

- 目标：依用户最新要求暂停立即编码的安排，先提供名字、Logo、App图标和界面气质供选择，再还原。
- 阅读：承接同一软件规划任务的全读与补读；恢复当前入口、业务页面、架构和开发规格，读取Product Design ideate相关技能与ImageGen，预检无保存的设计上下文。[阅读记录](output/qa/brand-directions-2026-09-16/reading-record.json)。
- 命名：按三场景与双角色筛选，做有限公开同名搜索；Mealume、Serviqo等已见现成使用的候选未采用。Portemi、Traysen、Melsori仅作候选，没有宣称商标或域名可用。
- 交付：[品牌方向说明](planning/2026-09-16/brand-visual-directions.md)、[三张原图与显示顺序](output/brand/2026-09-16/manifest.json)、三个完整提示词。内置ImageGen独立生成，实际显示顺序1食度／2餐序／3餐伴，均未选定。
- 视觉检查：三图均已查看，文字／数量／来源／主动作足以比较方向；记录Logo小尺寸一致性、繁体字形、色标、手机比例等待定稿项。Traysen额外生成的托盘外观只作品牌应用示意，不当成硬件结构更改。
- 收尾：更新product、README、页面基线、软件架构、开发下一步、decision-log及handoff；[收尾核对](output/qa/brand-directions-2026-09-16/closeout-validation.json)检查资产／提示词／链接／保留资料。没有应用代码、Figma文件、训练、实物测试、对外消息、采购或部署。
- 唯一下一步：用户选择或组合／修改视觉；需要修改先出调整图。旧M0.1直接开工下一步已被本轮指令取代，原建议书和RFQ文件保持原样。

## 2026-09-16 仅命名的候选比较

- 用户先要求暂停出图、先想名字，随后要求直接给一些选择。本轮按同一品牌任务的纠正继续，未重新开展硬件／软件研究。
- [命名讨论稿](planning/2026-09-16/naming-shortlist.md)提供七个英文候选、中文搭配、建议读法、构词联想与取舍，未选定。做有限公开同名搜索，排除已见同类产品MealCue、Portionary、Dishloom；不宣称商标或域名可用。
- 已补读当前入口、品牌稿、README和相关规范／日志段；[阅读记录](output/qa/naming-only-2026-09-16/reading-record.json)继承前轮完整阅读。
- 同步product、README、品牌V1历史状态、架构／页面／开发下一步、decision-log及handoff；[收尾检查](output/qa/naming-only-2026-09-16/closeout-validation.json)检查链接和旧图／提示词／正式交付物保留。
- 未生成图片、改Logo、建立Figma或应用工程；无部署、训练、采购、对外联系和提交。下一步仅是用户对名字的反馈，再收窄候选。

## 2026-09-16 大陆与香港比赛筛选

- 目标：为AI／IoT食物监测FYP寻找兼顾含金量与奖金的比赛；用户补充三位成员均非香港永久居民。
- 开工：完整读取33份项目自有Markdown、4047行，截断范围已补读；[reading-record](output/qa/2026-09-16-competition-research/reading-record.json)。收尾发现同期品牌任务更新，补读新增品牌说明和变更，保留先选视觉、不立即编码的要求。
- 调查：读取香港大学生赛、Techathon+ 2027、教育部国创赛、深创赛、广州科技局赛、HKSEC、港科大香港站和Dyson公开规则；浏览器读取前海2026完整方案、ICT专上资格和获奖权益。主承办方、政府和院校正式发布为主要依据。
- 结果：[候选与资格说明](research/2026-09-16-competitions/competition-shortlist.md)及[source-register](research/2026-09-16-competitions/source-register.json)，明确8万港元香港大学生赛、1.5万港元Techathon+及有条件30万元大陆创业赛。现金、服务、培育资助与总奖池分开；2026已截止、2027已公布／未公布分开。
- 关键判断：Techathon+明确欢迎VTC高级文凭和FYP；“挑战杯”课外作品赛排除毕业设计；广州学生专项无落地要求但VTC定义需确认；前海常规赛面向企业且当前正文未列固定现金额，未套用宣传转介奖额。
- 访问边界：教育部两个附件提取失败；ICT PDF因约24.8MB超过提取上限改读动态页面；浏览器不支持内容导出，未伪造本地全文快照。2025“挑战杯”官方索引条款与2027院校通知交叉检查。
- 收尾：同步product、README、decision-log和handoff；[收尾验证](output/qa/2026-09-16-competition-research/closeout-validation.json)检查内部链接、奖励／日期口径、组员资料和保留文件。首次组合patch因同期product变化未通过验证，重读后仅添加赛事段落，未覆盖品牌工作。
- 剩余：正式选赛、相应资格确认、真实原型／用户数据、简报与报名。未注册账号或公司、发消息、提交、创建提醒、采购、编码、训练或测试实物；软件规格、品牌资产、RFQ、suggestion和采购资料保留。

## 2026-09-16 无公司注册计划下的参赛补充

- 目标：按用户新增约束筛选以学生／个人为主体、没有公司注册或落地前提的比赛，兼顾奖金和认可。
- 阅读：同一赛事研究的约束补充，继承33份／4047行全读，补读当前入口、首轮报告、新命名稿和最新日志；[记录](output/qa/2026-09-16-competitions-no-company/reading-record.json)。保留同期只讨论名字的安排。
- 研究：主办／承办官方页面核对五项新增赛事，区分明确高级文凭FYP、QF4及通用年龄／国籍入口；重新区分学生现金奖与后续培育。
- PDF：读取PDF技能与工作区运行时；保存中美22页、HKIE18页、IET5页原始PDF，文字定位后逐页查看共12页相关资格／作品限制／奖金／申请材料。原件未修改，未声称视觉读完所有页面。
- 交付：[无公司候选](research/2026-09-16-competitions/no-company-options.md)，补充[source-register](research/2026-09-16-competitions/source-register.json)；首轮报告、product、README、handoff、decision-log同步最新约束。深创赛／广州落地奖移出当前主选。
- 验证：[收尾检查](output/qa/2026-09-16-competitions-no-company/closeout-validation.json)核对内部链接、PDF存在性／页数与哈希、日期、奖金额和公司条件层次。中美按2026章程1.5万元，不套旧版或地方其他赛大奖；HKIE按2026正文6,000港元，不沿用2019的8,000。
- 未完成：下届公告、正式选赛与相应资格疑点、报名材料；无对外消息、提交、注册公司或比赛账号、定时任务、图像生成、编码、训练或实物测试。


## 2026-09-16 Senplate命名确定、商标及域名查询

- 目标：按用户明确选择采用Senplate，检查商标与域名注册情况；没有延伸为购买或申请。
- 阅读：继承本次品牌任务全读，补读入口、命名／视觉旧稿及同期赛事研究、无公司约束和变更；[阅读记录](output/qa/senplate-name-check-2026-09-16/reading-record.json)。
- 商标：浏览器实际提交香港、美国、欧盟文字查询，无Senplate结果；香港通配符sen*plate*亦无结果。较宽模式命中的恒生银行长标志留作噪声记录。内地正式门户403、WIPO访问被阻止，均未完成；香港人工验证页面后续可访问，代理未解验证码。
- 域名：按IANA注册局服务，查询.com／.net／.app／.io／.ai／.hk／.com.hk／.cn／.com.cn，未见登记记录；保存HTTP状态、原始响应、WHOIS主机及时间。.ai的403与另行WHOIS结果清楚区分。
- 交付：[初筛报告](research/2026-09-16-senplate-name-check/senplate-trademark-and-domains.md)、[商标结构化记录](research/2026-09-16-senplate-name-check/trademark-evidence.json)、[域名汇总](research/2026-09-16-senplate-name-check/domain-summary.json)及原始响应。浏览器内容导出不支持，没有伪造导出证明；作者SensePlate项目采用公开索引，正文访问限制另记。
- 收尾：同步product、README、命名选定状态、旧视觉路由、软件下一步、decision-log及handoff，保留同期不注册公司约束；[核对记录](output/qa/senplate-name-check-2026-09-16/closeout-validation.json)检查链接、JSON、九个域名与保护文件哈希。无新图、应用实现或实测。
- 剩余：内地／WIPO正式查询、完整目标市场近似与具体商品服务评估；如购买域名需届时复核可注册状态。没有申请、注册、购买、公司变更、外发消息、部署或提交。

## 2026-09-16 大陆全国及省级竞赛补充

- 目标：继续找大陆全国或省级学生赛，保持不注册公司、香港高级文凭与现有FYP范围。
- 阅读：同一赛事任务补充，继承33份／4047行全读及此前补充记录，读取当前入口、最新日志与赛事文件；[阅读记录](output/qa/2026-09-16-mainland-competitions/reading-record.json)。
- 新证据：全国节能减排港澳台／国际赛道明确专科及学籍；教育部2026世界职业院校技能赛允许港澳台学校队直接报名争夺赛；VTC官方有广东物联网省赛获奖先例；HKIIT移动应用往届与海峡两岸本届记录分开。
- 交付：[全国／省级研究](research/2026-09-16-competitions/mainland-national-provincial.md)，涵盖节能减排、世界职业院校、物联网、移动应用、iCAN创新及广东技能赛。技术适配、资格确定程度、奖项层级、日期与公司要求各自说明。
- PDF与访问：复用已读PDF技能；保留物联网6页章程和1页高职认定原件，查看章程1–5页及补充页共6页。部分官方网页提取失败后读同一公开URL；iCAN原始扫描件未成功本地取得，不声称全文已读。缺少bs4后用标准库，未安装依赖。
- 验证：来源登记、内部链接、PDF存在性／哈希、当前无公司约束见[收尾核对](output/qa/2026-09-16-mainland-competitions/closeout-validation.json)。同步product、README、handoff、原无公司报告及decision-log。
- 未完成：学院与主办的具体VTC身份／报名路径确认、下届规则、任何报名。未发送询问信息、提交或签署，没有创建提醒、公司、应用或增加设备范围。



## 2026-09-16 Senplate中文商业计划书V1

- 目标：把现有想法整理成中文商业计划书，提供可编辑Word与PDF，覆盖客户、产品、竞争、收入、获客、试点、团队、财务与资金。
- 开工：37份项目自有Markdown共4363行完整阅读，截断范围补读；[阅读清单](output/qa/2026-09-16-chinese-business-plan/reading-manifest.json)。收尾补读同期Senplate命名与全国／省级赛事新增资料，保留其他任务变更；第一次组合patch遇并行变更未通过后重读并仅追加当前方案入口。
- 研究：重新核对环保署2024厨余统计、教育局2025/26学校数、Metafoodx／Controliza公开功能、Pomona客户报道、USDA许可及卫生署指引入口。环保署图2.11所在印刷第14页另本地渲染查看，未将机构数或厨余总量直接当作客户需求／可减损量。
- 交付：[正文](planning/2026-09-16/business-plan-zh.md)、[Word](<output/docx/Group 2_Senplate_商业计划书_中文版_V1.docx>)及[PDF](<output/pdf/Group 2_Senplate_商业计划书_中文版_V1.pdf>)，17页、17张原生表格、7条公开来源；[构建脚本](scripts/build_business_plan_zh.py)。采用最新Senplate，中文名未定；无品牌图像生成。
- 内容核对：HK$14,800＋HK$680、原型资源HK$50,000和三年客户数均标假设。复算收入、成本、毛利、经营缺口、客户回收期和敏感性；补清未来12次八周试点至少需两台轮转设备及相应资金，不增加FYP当前一台数量。经营结余不叫净利润。
- 排版：使用工作区Python和随工具提供的LibreOffice，任务内Fontconfig复用现有中文字体。最终render-04共17页，所有页逐页视觉核对，未改页面与已检查版本像素相同；最终修改页另以原始分辨率复核。中文、表格、页码、标题及链接正常；可访问性审查high／medium／low均0。PDF复制自已检查最终渲染。
- 收尾：更新product、README、handoff和decision-log，并保留同期名称／赛事状态；[收尾核对](output/qa/2026-09-16-chinese-business-plan/closeout-validation.json)记录公式、内容对应、成员资料、页数、链接、文件存在性及哈希。无购买、注册公司、消息发送、报名、训练、应用实现、部署或实物测试。
- 剩余：真实供应商整机报价、预算方访谈、场地与实测结果；文中商业价格及资源建议未获用户批准，下一步先审阅其定位和假设。

## 2026-09-16 Senplate Logo与VI三方向

- 目标：按用户新指令启动Senplate Logo／VI，先给可选择方向；没有继续停在名称查询，也没有提前落应用代码。
- 阅读：继承品牌任务全读，补读新商业计划447行、大陆赛事61行、当前入口及名称初筛，晚些时候重读并保留并行商业计划交付更新；[阅读记录](output/qa/senplate-logo-vi-2026-09-16/reading-record.json)。
- 技能：复用已读Product Design ideate／相关前置与系统ImageGen，用户设计上下文预检为missing，未写全局偏好。查看并实际附加用户硬件照片，仅作应用外形背景。
- 交付：[Logo与VI方向V1](planning/2026-09-16/senplate-logo-vi-directions.md)、[三图与映射](output/brand/2026-09-16-senplate-vi/manifest.json)、完整提示词。三次独立内置ImageGen调用，各原生结果展示一次；当前顺序1分寸／2连续／3日常，品牌均为Senplate，无中文定名。
- 视觉复核：品牌拼写、单色版本、图标和色值标签可读，足以比较方向；不同尺寸轮廓统一、第二版S联想／未来感、第三版未显现的S切口、实际字体和小尺寸均列待定稿项。设备不作为新工程图。
- 数值检查：候选HEX对比度已算，深色正文组合充分，浅绿／陶土／金色在浅底不作为普通小字；核对W3C说明，Logo与UI正文规则分开。[计算](output/qa/senplate-logo-vi-2026-09-16/palette-contrast.json)不是图像或实现的验收。
- 收尾：更新product、README、软件下一步、旧视觉路由、decision-log和handoff；[核对](output/qa/senplate-logo-vi-2026-09-16/closeout-validation.json)检查图片、哈希、提示词、显示映射、链接和旧交付物保留。商业计划及赛事资料保留，不改其建议／未注册状态。
- 未完成：用户选方向及修订、矢量／透明／多尺寸Logo、实际字体与完整VI、App还原；无Figma文件、应用工程、硬件测试、购买、注册、外部联系或部署。


## 2026-09-16 世界职业院校技能大赛报名路线

- 目标：回答是否需要联系老师、校方报名步骤和2026是否仍可参加；承接本轮赛事研究，不重新开始全库阅读。
- 阅读：继承首轮赛事全读及两次补读，恢复AGENTS、product、handoff，读最新决定／日志、当前大陆报告、来源记录和组员基线；截断输出已补读。[阅读记录](output/qa/2026-09-16-world-vocational-registration/reading-record.json)。
- 核实：完整读取2026执委会报名通知转载正文，并与福建省教育厅公告交叉核对；确认8月27日／9月10日截止、学校账号、AI按院校层次分组、同校最多4人及最多2名本校专任教师。没有找到香港补报／校方指定负责人的有效公开公告。
- 交付：[专项路线和Marco可复制草稿](research/2026-09-16-competitions/world-vocational-registration.md)。现有大陆表由“未核此刻开放”更新为“常规已截止，港澳补报未核实”；2027未公告，不复用2026日期保证。
- 收尾：更新product、README、handoff的赛事补充、decision-log、source-register；保留Logo／VI和商业计划的同期状态，不改其文件与资产。核对链接、JSON、文号、日期、人数和组员信息，[验证记录](output/qa/2026-09-16-world-vocational-registration/closeout-validation.json)。
- 剩余：用户联系Marco，学校确认机构／组别／国籍学籍、可用届次与安排。未对外发送、拨号、登录、报名、签署、创建公司或定时任务；没有应用／硬件测试。


## 2026-09-16 至2027年7月底参赛阶段计划

- 目标：按用户未来时间窗，重新整理适合Group2的高认可度、有现金优先赛事，逐项说明报名、作品提交和决赛所需成熟度。
- 阅读：沿用本赛事任务33份Markdown全读及历次补读记录，复核当前AGENTS、handoff、product相关变化、四份已有赛事报告和最新日志；记录新清单、读取范围与排除项于[阅读记录](output/qa/2026-09-16-competition-plan-to-2027-07/reading-record.json)。
- 研究：再次核对Techathon2027正式日期／简报／奖金、香港大学生赛分阶段交件和实物FAQ、海峡两岸报告／演示要求、中美创客选拔原型与奖额、YPEC实物可选；新取得VTC广东赛完整文章及国家创新赛香港大专创意组入口。2027未知不以2026代替。
- 原件：三份现有官方PDF不改动；补渲染并查看YPEC第3页和HKEPC第7页，复核中美第14–15页奖金；其它已通过的相关页视觉核对继承，不重复渲染。年报只用官方索引的举办周期段落，未声称全文视觉阅读。
- 交付：[2027年7月底前阶段计划](research/2026-09-16-competitions/plan-to-july-2027.md)与[来源表](research/2026-09-16-competitions/plan-2027-source-register.json)，主选5项、省级训练路线1项、较晚赛程候选6项，并有准备月份和作品成熟度说明。
- 收尾：更新product、README、handoff赛事信息和四份旧报告当前排序／访问状态，追加decision-log；[验证](output/qa/2026-09-16-competition-plan-to-2027-07/closeout-validation.json)核对本地链接、JSON、明确年份、原件哈希和当前品牌状态。
- 剩余：用户最终选择组合，学院确认学生身份／支持／省赛训练，主办方确认中美作品顺序；其它2027公告尚未核到。未对外联系、报名、签署、注册公司、创建监控或实施软件硬件。

## 2026-09-16 基于Measured的Logo修订R2

- 目标：承接用户选择旧VI第1版并认为Logo一般般的反馈，保留整体工作基准，改进符号；不重选名字或将旧Logo标为批准。
- 阅读：继承品牌任务全读，补读当前入口、VI说明、旧manifest、世界赛路线和同期至2027年7月底赛事计划；[记录](output/qa/senplate-logo-refinement-2026-09-16/reading-record.json)。
- 生成：查看并实际附加Measured原图，内置ImageGen独立生成三张R2黑白／反白／图标研究；实际显示顺序1 Rim Fold、2 Poise、3 Contour S，各展示一次。原生成文件及项目副本保留。
- 交付：[R2说明](planning/2026-09-16/senplate-logo-refinement-r2.md)、[映射与三图](output/brand/2026-09-16-senplate-logo-r2/manifest.json)、三个提示词；旧VI manifest仅更新基准选择，旧JSON存QA快照。
- 视觉复核：文字可读，三种符号与旧圆形不同；记录G形误读、上部叶片联想、S独特性较弱和缩小路径一致性等取舍。没有把小图示意当真实24px验证；未变化配色不重复测试。
- 收尾：更新product、README、V1选择状态、软件路由、decision-log及handoff；[核对](output/qa/senplate-logo-refinement-2026-09-16/closeout-validation.json)验证文件、顺序、选择层级、JSON和保护文件。同期赛事及商业成果保留。
- 剩余：用户选R2符号或继续反馈，再做修订与可复用资产。没有购买、注册、对外发送、代码、硬件或模型测试。

## 2026-09-16 Logo R3重整与候选筛选

- 用户否决R2全部三张，并明确不足为太普通、缺少高级感和辨识度。关闭旧候选，保留原VI基准，未要求用户再从已否决组选择。
- 读取Creative Production produce、logos、board-runtime及来源／精确内容参考；按其明确委派条款安排四个限定图像任务，每个恰好一次ImageGen，无模型覆盖。四个代理已完成、结果已消费并调用中断接口确认结束；接口无销毁句柄功能，不声称销毁。
- 三个方向依据代理图像审阅报告筛除，保留字标稿；主代理另生成新图形，发现透明低对比度失效后用ImageGen修复一次。只做元数据读取及不改像素的文件复制，未用Python／SVG绘画。总共六次生成。
- 交付：[R3说明](planning/2026-09-16/senplate-logo-reset-r3.md)、[清单及A／B](output/brand/2026-09-16-senplate-logo-r3/manifest.json)，原始提示词和无效／筛除结果保留并标明。没有原生创意画板或Figma，不冒称完整VI／独特性已完成。
- 阅读和工具边界见[记录](output/qa/senplate-logo-reset-2026-09-16/reading-record.json)，继承本品牌任务全读；[收尾](output/qa/senplate-logo-reset-2026-09-16/closeout-validation.json)检查PNG／来源／状态／链接和保护文件。R2更新前JSON保留，其他图片和正式文档未覆盖。
- 当前待用户判断字标路线或图形路线的气质是否接近；尚无Logo选择、矢量母版、实际字体、24px或印刷验证、App还原，未购买、注册、对外联系或部署。

## 2026-09-16 Logo真实标记审美校准

- 目标：回应用户认为后续稿越来越丑，撤下R3候选，改变连续生成普通符号的做法；原VI基准保留，当前没有Logo获批。
- 阅读：继承本品牌任务完整阅读并补读当前入口、R3；Visualize技能初次组合输出截断后，以1–155和156–252行完整补读。[记录](output/qa/logo-reference-calibration-2026-09-16/reading-record.json)。
- 研究：查看Oura／Withings／Ooni等公开入口，最终可视对照采用Polestar、Linear、Stripe、Notion的固定版本单色图形；记录库元数据和品牌来源，不手绘或重排原标志轮廓。
- 交付：[校准说明](planning/2026-09-16/logo-reference-calibration.md)、[来源记录](research/2026-09-16-logo-references/reference-sources.json)，以及任务可写可视化目录中的senplate-logo-references.html响应内容。不是Senplate网页App、公开网站或新的品牌方案。
- 验证：浏览器看到四个真实图形；修正初版按钮内标签被挤断的布局。检查选择、最多两个、空状态禁用，360px和320px均无水平溢出；取消分支已接线但未单独验收，未执行提交，清除测试选择并恢复视口，临时预览／服务器已关闭。
- 收尾：更新product、README、VI／R3路由、软件下一步、decision-log及handoff；[核对](output/qa/logo-reference-calibration-2026-09-16/closeout-validation.json)检查来源、HTML、链接、R3撤下及保护文件。未生成／编辑新Logo、部署、采购、注册或对外联系。
- 下一步：用户指出接近的真实参照，随后提取设计原则并重新设计原创Logo；没有合适参照时继续校准，不恢复旧草稿强制选择。

## 2026-09-17 Senplate原创矢量Logo

- 目标：响应用户选择Polestar／Linear并保留深绿、米白的要求，先归纳精简形状、统一斜切及负形原则，再做原创符号；不恢复被否决的候选。
- 阅读：继承品牌任务全量记录，补读当前根规范、校准、VI、软件路由及日志；Figma技能与gotchas分段补齐，见[阅读记录](output/qa/senplate-vector-logo-2026-09-17/reading-record.json)。
- 制作：新建Figma草稿文件Senplate — Logo Studies，只有一个计划可选，无需额外询问。检查空白文件与字体后直接定义向量，制作Interval与Balance；后者由助手筛除。A因向量原点归一化造成初始重叠，修正第二块偏移并重新截图。
- 交付：[规范](planning/2026-09-17/senplate-vector-logo-studies.md)、[评审图与资产清单](output/brand/2026-09-17-senplate-vector/manifest.json)，Figma评审5:2／紧边界组合8:2。三SVG保留透明背景，组合字标转路径，Figma源文字可编辑；三个小尺寸PNG直接保存Figma字节。
- 验证：主组合、反白和24／32／64px实际画布预览，拼写、切口、尺寸及无占位状态；[收尾](output/qa/senplate-vector-logo-2026-09-17/closeout-validation.json)核对SVG、PNG、内部链接、原交付物哈希和状态同步。
- 同步：product、README、校准与来源、VI及软件当前路由、decision-log、handoff均更新。原学校文档、竞赛、商业计划、身份和旧品牌图片保留。
- 剩余：用户评价本稿；尚无Logo批准、图形近似检索、最终字体归档、物理打样或完整VI。未写App、训练、购买、注册、发送或部署。

## 2026-09-17 Interval图形商标近似初筛

- 目标：在用户初步认可气质后检索相似品牌／商标，保留当前图稿，不预先宣布独特性或可注册。
- 阅读：承接同一品牌任务的全读，补读当前入口、矢量规范、旧名称初筛及修改区段，见[记录](output/qa/senplate-logo-similarity-2026-09-17/reading-record.json)。
- 检索：公开网页／图片及3454个固定版本图标作候选排序，人工查看38项；排序只是发现工具。Aqua Security纯图形在TSDR实时核为有效，90678592／6622466，9／42类具体为云／容器安全软件。另核OPNsense现行官网及RustDesk官方源码；没有把图库或品牌使用当注册证明。
- 交付：[报告](research/2026-09-17-logo-similarity/similarity-review.md)、[对照图](research/2026-09-17-logo-similarity/comparison.jpg)、[来源](research/2026-09-17-logo-similarity/source-register.json)、算法与排序、官方页面观察与截图。
- 香港后段完成：用户明确同意条款及查询后，页面已到上传页，代理未解验证码。原样导出192px PNG并查询，系统300候选含重复，审阅前50条资料／37个不同编号，核两条第9类详情：303321710机械革命所属公司图形、307039215 meterytech。保存[香港记录](research/2026-09-17-logo-similarity/hk-query-and-records.json)、观察和截图；先前独立权利人检索失败不当零记录。WIPO／内地／欧盟缺口仍记录。
- 收尾：同步product、README、Interval、校准、软件路由、decision-log、handoff；[核对](output/qa/senplate-logo-similarity-2026-09-17/closeout-validation.json)检查原图及正式文档保护、链接、来源和PNG。研究对照HTML不是产品App，未运行应用测试或修改品牌图像。
- 剩余：香港本次查询已完成。建议下一稿改变双折面方框结构并保留气质，尚未开始修订、申请、购买、发送或部署。追加香港对照页因跨域原图无法加载未交付，保留完整官方详情截图与国际品牌对照图；浏览器截图字节实为JPEG，已按实际格式命名，没有转码或重绘。

## 2026-09-17 Profile R4结构修订

- 目标：按用户要求调整近似的Interval，保留已认可的色调与字标气质，制作结构不同的可编辑图稿。
- 阅读：继承连续品牌任务全读，补读当前入口、Interval与近似报告、修改区段；初次较长输出截断后补齐，见[记录](output/qa/senplate-logo-r4-2026-09-17/reading-record.json)。Figma技能与API沿用完整阅读，重新应用关键规则；未派代理。
- 制作：Figma原生路径创建三个开放轮廓，随后把下端错开，减少柱形图联想。齐底稿及旧Interval归档，保留几何和旧图；最终所有组合／反白／小图同步同一母稿。
- 对照：固定图库3454项候选排序，最终人工看21项；另检查Pillar Konstruksi实际图样。算法只辅助筛选，没有官方新稿图形查询或权利核准。
- 交付：[R4规范](planning/2026-09-17/senplate-logo-profile-r4.md)、[主图](output/brand/2026-09-17-senplate-r4/profile-review.png)、3份SVG、4份原生PNG与[清单](output/brand/2026-09-17-senplate-r4/manifest.json)。初次输出超过工具长度上限后拆分重导，一次只读脚本语法错误修正后成功；没有部分截断文件当成有效交付。
- 验证：主图／反白／24、32、64px查看，SVG解析、像素尺寸、内链及旧资产保护见[收尾](output/qa/senplate-logo-r4-2026-09-17/closeout-validation.json)。对照浏览器与临时服务器关闭；原学校文档、组员资料、商业／赛事与软件业务规格保留。
- 剩余：用户评价本稿，采用后补官方图像检索与VI。没有App工程、模型训练、注册、购买、对外联系或部署。

## 2026-09-17 R5餐食计量与GPT网页提示词

- 目标：在R4视觉尚可的基础上强化项目意义，交付新图稿及可独立使用的提示词MD。
- 阅读：继承连续品牌任务全读并补读当前入口与R4，截断资产段另补；沿用已完整阅读的Figma流程，见[记录](output/qa/senplate-logo-r5-2026-09-17/reading-record.json)。
- 制作：新增浅盘／份量块／基准带，表达“餐食＋计量”的设计意图；R4保留为视觉参考，原几何与导出不变。R5评审28:2、母稿26:3、紧边界组合32:2。
- 交付：[R5规范](planning/2026-09-17/senplate-logo-measured-plate-r5.md)、[评审图](output/brand/2026-09-17-senplate-r5/measured-plate-review.png)、3份SVG、4份原生PNG与[清单](output/brand/2026-09-17-senplate-r5/manifest.json)；[ImageGen简报](Senplate_Logo_ImageGen_Brief.md)含主提示词、后续细化及选择标准。
- 验证：主图／反白／小尺寸查看，SVG／PNG、提示词完整性、内链与原文件保护见[收尾](output/qa/senplate-logo-r5-2026-09-17/closeout-validation.json)。初次合并脚本语法错误未执行，拆分后成功；未把尝试写成完成。
- 范围：未操作用户GPT页面、提交或代其在网页生成图片；没有声称使用特定网页版图像模型。Figma为实际交付，无新稿近似查询、App代码、购买、申请或对外联系。
- 剩余：用户比较R5和其网页版候选，选定视觉与语义方向后再精修及做最终几何的近似检查。

## 2026-09-17 采用用户选定的A细化版并整理素材

- 目标：执行用户“用这个吧”，将其上传的餐盘／份量／圆点Logo设为当前品牌；保留原图和历次稿件。
- 阅读：继承连续品牌任务完整阅读记录，补读入口、R5、提示词、当前软件状态及需修改文件；压缩后精简恢复，见[本轮记录](output/qa/senplate-selected-a-2026-09-17/reading-record.json)。
- 制作：原图逐字节复制；上方主色版按3个符号部分、8个字母提取轮廓，清理像素噪声后生成曲线路径，未替换字体。初期描摹毛刺及合并复合路径导入丢字已修复；按独立字母导入、保留原位置，并统一各配色与图标几何。Figma当前母版41:2／43:77，品牌板36:6；本轮失败试描节点已清理，历史稿保留。
- 交付：[brand.md](brand.md)、[素材目录说明](output/brand/2026-09-17-senplate-selected-a/README.md)、[ZIP](output/brand/Senplate_Brand_Assets_v1.zip)。共7份SVG、13份Figma原生导出PNG及1份原始参考PNG；不是重新生成候选。
- 检查：已查看主色／黑白／图标组合及24、32、64px小样。24px盘沿偏细，建议32px起、优先48px以上。一次超过5张的图像返回被工具截为5张，按实际字节长度核对并分批导出其余文件；PNG尺寸／透明度、SVG结构与同轮廓、原图／73项受保护文件哈希和内链见[收尾检查](output/qa/senplate-selected-a-2026-09-17/closeout-validation.json)。
- 同步：product、README、handoff、decision-log、当前软件状态、R5／网页提示词／审美参照状态。品牌板文字与原图口号不作为正式文案。没有App代码、实物验证、购买、商标新查询／注册或对外联系。
- 下一步：按选定Logo与配色设计第一组iPhone关键页面供审阅；字体来源及新图形近似核对保持独立待办，不将旧查询当成新稿权利证明。

## 2026-09-17 A版曲线重建与大小写对照

- 目标：修复用户指出的图形和字标毛边，并回答首字母大小写；保留已选A构图。
- 阅读：延续上一轮品牌细化，沿用完整阅读链，补读入口、当前品牌规范／素材说明、最新决定／工作记录及软件状态。补读被截断的product区间；见[记录](output/qa/senplate-refined-a-v2-2026-09-17/reading-record.json)。
- 制作：使用明确的少量Bezier控制点、圆形轮廓、水平／垂直边重新构建3个符号部分和8个字母；保留小写、单层a及图文位置，统一主色／黑白／图标。没有换字体或把AI位图再自动描摹；制作脚本只写矢量路径，PNG全部Figma原生导出。
- 对照：首字母大写仅为比较，默认小写不变；[大小写](output/brand/2026-09-17-senplate-refined-a-v2/capitalization-comparison.png)、[V1/V2毛边对照](output/brand/2026-09-17-senplate-refined-a-v2/edge-comparison.png)已实际查看，确认旧版起伏和新版连续轮廓的差别。不是仅以文件扩展名证明光滑。
- 交付：[V2素材ZIP](output/brand/Senplate_Brand_Assets_v2.zip)、[规范](brand.md)，8份SVG、16份原生PNG及原始参考PNG。主Logo53:2／符号53:15／品牌板55:2／大小写56:2；V1 Figma品牌板标记历史，几何与本地资产保留。
- 验证：2056px主图、黑白／图标板、大小写、边缘放大及24／32／64px查看。小图仍建议32px起、优先48px；文件尺寸、透明度、同轮廓配色、原图及97项受保护文件、内链和规范同步见[收尾检查](output/qa/senplate-refined-a-v2-2026-09-17/closeout-validation.json)。
- 状态：上一轮称V1已清理合格的判断被本轮质量修正取代；用户选定A构图仍有效。无App代码、字体识别结论、新商标检索或对外行动。

## 2026-09-17 A版黄金分割V3

- 目标：按用户要求使用黄金分割调整当前Logo，并延续中途“继续刚刚的工作”的指令；不重新选择品牌或开始App代码。
- 阅读：继承连续品牌任务完整阅读链，补读AGENTS、product、handoff、brand、最新日志、软件状态及V2制作依据，见[阅读记录](output/qa/senplate-golden-a-v3-2026-09-17/reading-record.json)。
- 构造：先计算φ，再确定符号宽高、份量宽高、感知点分割位置、图文间距与文字主竖笔高度，使用少量平滑曲线生成SVG。V2并非黄金比例稿，本轮没有倒推美学叙事；字母路径保留V2，仅整体缩放和定位。
- 核对：除参数计算外，独立读取[Figma实际尺寸](output/qa/senplate-golden-a-v3-2026-09-17/figma-geometry.json)核对比例，记录浮点差异。已查看2036pxLogo、[构造图](output/brand/2026-09-17-senplate-golden-a-v3/golden-ratio-construction.png)、[前后对照](output/brand/2026-09-17-senplate-golden-a-v3/proportions-before-after.png)、主色／黑白／图标板及24／32／64px小样。
- 交付：[V3素材ZIP](output/brand/Senplate_Brand_Assets_v3.zip)、[品牌规范](brand.md)，9份SVG、16份原生PNG及原始参考PNG；Figma主Logo60:2、符号60:15、品牌61:2、构造62:2、对照63:2。PNG为原生导出，像素整数取整与矢量比例分开记录。
- 验证：[收尾检查](output/qa/senplate-golden-a-v3-2026-09-17/closeout-validation.json)包含五项实际黄金比例、字母路径保持、配色几何一致、SVG／PNG、原图和125项受保护文件、内链及规范同步。
- 边界：黄金比例不是更美观的实证，大小写未自动改选，无新商标检索／注册、应用代码、硬件测量、购买或对外联系。

## 2026-09-17 盘沿共享椭圆V4

- 目标：处理用户指出的左右弧度不一致，保留食物监测语义，结合黄金分割重新构造；必要时才更换象征。
- 阅读：继承连续品牌任务阅读链，补读当前入口、品牌与V3依据、最新日志及软件状态；截断的最新日志已补读。用户截图已查看并保存在QA，见[阅读记录](output/qa/senplate-ellipse-a-v4-2026-09-17/reading-record.json)。
- 制作：以一对同心同轴椭圆建立盘沿，使用同角度镜像圆角与内外边相切。比较过平切、收尖和圆角的局部处理，最终采用镜像圆角；本轮临时试稿已移除，历史V1–V3保留。整体外框不再强制φ，外／内椭圆高度等仍按黄金比例。份量位置上移，圆点与餐盘更接近；字母路径保持。
- 验证：解析椭圆722组成对采样核对位置与曲率；单独原生导出盘沿作左右翻转数值比较，并记录抗锯齿边缘差异。实际查看主Logo、整体／仅盘沿对照、构造图、黑白／图标及24／32／64px。详见[收尾](output/qa/senplate-ellipse-a-v4-2026-09-17/closeout-validation.json)。
- 交付：[V4 ZIP](output/brand/Senplate_Brand_Assets_v4.zip)、[规范](brand.md)，10份SVG、18份Figma原生PNG及原始参考PNG。主Logo68:2、符号68:15、品牌69:2、整体对照70:31、仅盘沿71:2、构造72:2。
- 工具修正：构造图首次脚本在移除网格后访问了缓存中的旧节点，工具回滚；后续读取确认新板不存在。改为先取得所需节点、再替换网格，完成构造图，未把失败尝试当成果。
- 收尾：更新当前入口、品牌、软件状态与handoff，核对原图和154项受保护文件、SVG／PNG、镜像与相切、字母路径、同色几何、内部链接与ZIP。几何对称不代表已获审美批准；无App实现、注册、采购或新商标查询。

## 2026-09-17 实体碗重新设计V5

- 目标：执行用户明确重新设计的要求，解决V4不再像碗的问题；停止旧开口环路线，不再以几何测试维持被用户否决的方向。
- 阅读：继承连续品牌任务完整阅读链并补读当前入口、品牌及软件状态。使用内置ImageGen技能和提示词指引；Creative Production的Logo指导作为参考，未启动其看板工作流或代理，见[阅读记录](output/qa/senplate-bowl-redesign-v5-2026-09-17/reading-record.json)。
- 制作：一次全新ImageGen生成＋一次针对同图的背景／平面化编辑，形成清楚的椭圆碗口、完整碗身和底脚，口沿有阶梯形留白。原先的圆点和开口环未保留；候选字标采用Senplate。第一张返回透明背景，第二张实际不透明米白底；两次原生文件均保留，未用Python改图。
- 交付：[当前概念](output/brand/2026-09-17-senplate-bowl-redesign-v5/bowl-01-concept.png)、[首次生成原稿](output/brand/2026-09-17-senplate-bowl-redesign-v5/bowl-01-generated.png)、[生成及编辑提示词](planning/2026-09-17/senplate-bowl-redesign-v5.md)和简短清单。没有扩展整套VI、生成SVG或制作App图标。
- 检查：实际查看新图、碗体和Senplate拼写，读取PNG尺寸／透明度，保留轻微生成纹理及细线待精修的说明；未宣称实际黄金比例或32px已验证。旧186项资产／学校文件／身份保护、内链与规范同步见[收尾](output/qa/senplate-bowl-redesign-v5-2026-09-17/closeout-validation.json)。
- 旧Figma的V4品牌板及三个对照／构造框已标记HISTORICAL，节点69:2、70:31、71:2、72:2；原几何不改，新候选未导入矢量稿。
- 状态：新候选尚未被用户选择，旧V4的几何通过不能覆盖本次用户否决。下一步依据新造型反馈精修，再进行矢量、小尺寸与新图形近似核对；无App代码、注册、购买或对外联系。

## 2026-09-17 实体碗黄金比例矢量V6

- 目标：执行用户“开始吧”，把V5实体碗做成可编辑、可量度的黄金比例矢量稿，不再只依赖ImageGen提示词。
- 阅读：继承连续品牌任务全读记录，补读入口、V5规范及当前软件状态；采用既有Figma流程，核对可用字体与官方Manrope OFL文本，见[记录](output/qa/senplate-bowl-golden-v6-2026-09-17/reading-record.json)。
- 构造：先计算φ尺寸系列，使用椭圆口沿、半圆碗身、底脚和阶梯负形，通过布尔减法形成透明留白；未描摹生成纹理。建立Figma新页76:2，保留布尔构造77:8与文本76:3，导出生产轮廓78:9和主组合78:10。字标采用Manrope Bold，字体来源已记录。
- 验证：直接读取最终矢量路径，解x=160的曲线交点，区分碗口、碗身底和脚底，再以外轮廓竖边测底脚宽；没有把输入参数当成测量结果。五项实测比值误差均小于0.0001，最大尺寸偏差约0.000608单位。574点外轮廓镜像采样最大距离约0.000001单位，口沿量位切口保留偏置。
- 视觉：查看主稿、实际构造图、黑／反白和32／64／128px样本。口沿、碗身和底脚仍清楚，32px细节更弱，因此细节场景建议48px以上；不宣称真实用户识别率或已实机验证。
- 交付：[V6说明](planning/2026-09-17/senplate-bowl-golden-v6.md)、[素材包](output/brand/Senplate_Bowl_Golden_Vector_v6.zip)、7份SVG、8份原生PNG及V5参考PNG、参数／实测JSON与字体许可。不是完整VI或App实现。
- 导出复核：另从交付SVG文件重新解析曲线，最大尺寸误差约0.000824单位。检查器最初误设字标为单path，实际为8个字母path；修正检查器后通过，不改动图稿来适配假设。
- 收尾：更新当前品牌、入口、软件状态、V5历史状态及handoff；旧190项文件原样保留。SVG／PNG、路径测量、配色几何、内链与ZIP见[收尾检查](output/qa/senplate-bowl-golden-v6-2026-09-17/closeout-validation.json)。新图形近似查询、视觉最终选择及后续界面仍未完成。

## 2026-09-17 V6保留与刻度小修试稿

- 目标：按用户要求完整保留V6，并独立试做刻度替代阶梯口沿的局部改动。
- 阅读：沿用连续品牌任务全读记录，补读当前入口、V6规范与制作依据及最新日志；截断的work-log末段补齐，见[阅读记录](output/qa/senplate-v6-tick-study-2026-09-17/reading-record.json)。截图已查看并存入QA。
- 制作：克隆V6布尔源稿，移除副本的阶梯内开口／连接缺口，补完整椭圆内口和三条右对齐圆端刻线。试稿84:3／84:22，组合85:2，预览85:6，上下对照85:13。原V6节点未重命名或修改。
- 验证：8个V6源稿／预览节点状态指纹前后一致；公共外轮廓、口沿线、脚底线源路径一致，字标路径与组合尺寸／间距一致。960×680透明PNG对照显示指定口沿和刻度区域外差异为0；实际查看整体对照及32／64px，32px刻度较弱。
- 交付：[试稿说明](planning/2026-09-17/senplate-v6-tick-study.md)、[对照图](output/brand/2026-09-17-senplate-v6-tick-study/tick-comparison.png)、独立预览／SVG和小样；没有重复打包整套VI。原V6包、源稿、规范和QA均保留。
- 收尾：更新当前状态、决定、handoff及软件视觉状态；227项受保护文件与内链检查见[QA](output/qa/senplate-v6-tick-study-2026-09-17/closeout-validation.json)。刻度版未被用户选用，不替换V6，无App代码或新商标查询。

## 2026-09-18 碗沿微刻度局部优化

- 目标：回应刻度突兀反馈，保留V6及V6.1，减少独立装饰感。
- 阅读：沿用连续品牌任务完整阅读链，补读入口、当前刻度说明、品牌、相关软件状态和日志，截断处补读；见[阅读记录](output/qa/senplate-v6-rim-tick-study-2026-09-18/reading-record.json)。
- 完成：克隆布尔源稿，移除副本三条碗壁刻线，按椭圆法线添加三处内沿刻痕；新布尔89:3、符号89:23、组合89:24、对照89:33。原Figma节点不改。
- 交付：两份SVG、整体／对照／放大／透明符号PNG及32／64px原生样本。已实际查看全部构图及小样，小样细节较弱。
- 验证：15个旧节点指纹一致，四个公共构造部件、字标路径及主要排版一致；保护文件、PNG局部变化与内链检查见[收尾QA](output/qa/senplate-v6-rim-tick-study-2026-09-18/closeout-validation.json)。
- 光栅复核：改动区外18个边缘像素有差异，均在内口轮廓1px内、透明度差≤16／255，源椭圆不变；未把光栅差异写成0。245份保护文件不变，382条局部文件链接有效。
- 收尾：同步brand、product、README、两份软件状态、decision-log和handoff，新增[聚焦说明](planning/2026-09-18/senplate-v6-rim-tick-study.md)。仍待用户视觉反馈，未设默认或展开App／VI。

## 2026-09-18 提高刻度可见性

- 目标：回应V6.2过于隐蔽的反馈，在保留旧版基础上增强量位线。
- 阅读：继承连续任务完整阅读链，补读当前品牌、handoff、V6.2说明和更新正文，见[本轮阅读记录](output/qa/senplate-v6-visible-ticks-2026-09-18/reading-record.json)。
- 完成：克隆源稿，三条弧形负形从右侧轮廓伸入；布尔93:3、符号93:23、组合94:2。交付整体／对照／放大及32／64px、透明PNG和两个SVG，实际查看正常尺寸与小样。
- 验证：23个旧Figma节点保持，公共构造源部件、字标和排版一致；局部轮廓变化是预期设计。文件保护、SVG、PNG范围与链接结果见[QA](output/qa/senplate-v6-visible-ticks-2026-09-18/closeout-validation.json)。
- 收尾核对：263个旧文件及23个旧Figma节点保持，379条本地链接有效；PNG额外11个边缘像素差异已检查并说明，未伪称完全相同。
- 收尾：更新brand、product、README、handoff、两份软件状态及日志，新增[V6.3说明](planning/2026-09-18/senplate-v6-visible-ticks.md)。新稿未选用，原V6及两次试稿均保留，无App代码或完整VI扩展。

## 2026-09-18 刻线曲率贴合碗形

- 目标：只增加V6.3刻线弧度，保留位置锚点、线宽及长短节奏。
- 阅读：沿用连续任务完整阅读链，补读当前入口、品牌、V6.3说明和最新日志／变更正文，见[记录](output/qa/senplate-v6-curved-ticks-2026-09-18/reading-record.json)。
- 完成：平移碗口椭圆弧、三次贝塞尔近似与等宽圆端轮廓化；发现并修正轮廓化坐标异常，错误临时节点已删除。布尔97:3、符号97:36、组合97:37、对照97:46。
- 交付：独立SVG、整体／对照／放大／透明PNG和32／64px样本；整体、放大和小样均已查看。
- 验证：31个旧节点保持，共同构造部件、字标路径和排版一致；文件保护、SVG和内链见[QA](output/qa/senplate-v6-curved-ticks-2026-09-18/closeout-validation.json)。未用完全相同像素作为曲率变更的要求。
- 收尾：同步当前品牌、product、README、软件状态、handoff及日志，新增[V6.4说明](planning/2026-09-18/senplate-v6-curved-ticks.md)。仍为试稿，所有旧版保留，下一步接收曲线观感反馈。

## 2026-09-18 解决刻度划痕感的内壁试稿

- 目标：用户从“仍怪”进一步澄清为刻度像划痕、与碗不融合；同一轮补充，没有重启全库阅读。
- 阅读：沿用连续任务完整阅读链，补读当前规范／V6.4说明与最新变更，见[阅读记录](output/qa/senplate-v6-inner-scale-2026-09-18/reading-record.json)。
- 完成：外侧缺口取消，嵌套内口减去三个量位条，产生与内壁相接的深绿标记；主符号100:25、新旧对照102:2。纯碗只作诊断控制，用户澄清后展示聚焦内壁方案。
- 交付：符号SVG、对照／放大／透明PNG及32／64px；实际查看构图和小尺寸。未重复新制横向字标包或完整VI。
- 验证：39个旧Figma节点保持；共同构造与原椭圆尺寸／路径复核，文件保护、SVG和内链见[QA](output/qa/senplate-v6-inner-scale-2026-09-18/closeout-validation.json)。
- 收尾：同步brand、product、README、handoff及决定日志，新增[V6.5说明](planning/2026-09-18/senplate-v6-inner-scale.md)。软件规格上一轮已改为引用brand，无过期版本号，本轮不改。试稿尚未选用。

## 2026-09-18 选定无刻度纯碗V7

- 目标：落实用户不用刻度、只保留碗形的决定，结束刻度迭代。
- 阅读：沿用连续品牌任务完整阅读链，补读当前入口、V6.5及变更正文，软件状态和下一步段落补读后同步；见[阅读记录](output/qa/senplate-plain-bowl-v7-2026-09-18/reading-record.json)。
- 完成：克隆无刻度源和路径为V7，组合原字标并导出SVG、透明PNG、米白预览、64px样本及既有字体许可副本。源106:2、符号106:8、组合106:9、预览106:13。
- 验证：纯碗路径与101:17一致，字标及图文排版一致；48个旧Figma节点保持，源码只含碗身／口沿线／底脚线／完整内口四部分。完整预览及64px已查看。
- 收尾：更新brand、product、README、两份软件状态、handoff与决定日志，新增[V7说明](planning/2026-09-18/senplate-plain-bowl-v7.md)。[QA](output/qa/senplate-plain-bowl-v7-2026-09-18/closeout-validation.json)含原文件保护、SVG／内链／ZIP核对。所有旧稿保留为历史，当前请求完成，没有启动应用工程。

## 2026-09-18 Senplate VI V1完整制作与字体核查

- 目标：保持V7纯碗，提供独立图形／字标和完整VI；用户在本轮澄清不是.ai文件。
- 阅读：继承连续品牌任务全读链，补读当前规范、V7说明和最新变更；新研究与交付说明完整编写，见[阅读记录](output/qa/senplate-vi-v1-2026-09-18/reading-record.json)。
- 核查：从Figma确认Manrope Bold700，读取官方Manrope、Inter、Noto TC／SC的OFL与SIL FAQ；下载三种原始字体和许可证，记录来源与SHA-256。
- 制作：Figma页110:2建12个基础版本、可编辑文字、VI总览及App图标／封面／菜单／标贴。源图形不变；主标矢量与V7一致，配色副本几何一致。
- 导出：12SVG＋12透明PNG，应用SVG／PNG、JSON／CSS令牌和字体原件。临时SVG下载返回空202，改用带整体哈希核对的分段原生SVG导出，短期URL已从临时清单清理。
- PDF：按PDF技能一次运行作者操作标记，生成11页规范和4页资产总表；全部15页逐页渲染查看，中文和版式正常。默认Helvetica／Times资源无实际文字绘制，可见文字均使用核查过的字体实例。
- 收尾：更新brand、product、README、软件状态、handoff及日志，新增[VI说明](planning/2026-09-18/senplate-vi-v1.md)、[字体报告](research/2026-09-18-font-licences/font-licence-audit.md)。包与验证见[QA](output/qa/senplate-vi-v1-2026-09-18/closeout-validation.json)。未创建App工程、购买、提交或新商标申请。

## 2026-09-18 V7纯碗与Senplate名称商标初筛

- 目标：查找当前纯碗的类似商标，结合装置／App／软件业务判断关注点；保留V7与VI。
- 阅读：本轮完整读取78份原有项目Markdown、6719行；大批输出截断处改为小批补齐，文件在阅读期间未变化。[阅读记录](output/qa/senplate-v7-trademark-2026-09-18/reading-record.json)。
- 香港：用户手动完成验证，使用绿色V7独立符号成功查询300条候选；6页元数据去重227编号，筛得15项9／42类候选。查看10幅原始图／8个编号，展开BASAO与两项OpenRice的商品说明。另行eSearch详情受验证码／记录不可得限制，未刷新香港文字或确认届满日期。
- 美国与公开使用：USPTO三个拼写查询均无结果；BOWL 97231717／7431298核为EPICNPOC有效9／42类注册，页面未显示图像。新发现并直接阅读作者资料中的历史同名Senplate iOS原型，未推断为发行或注册；SensePlate与SensoPlate保持名称使用线索层级。
- 交付：[报告](research/2026-09-18-senplate-trademark/trademark-review.md)、[原图对照](research/2026-09-18-senplate-trademark/comparison.html)、查询转录JSON、15项类别候选及10幅官方原图来源。原图通过浏览器素材下载保存，不重绘；浏览器查询不是认证副本。
- 验证：对照页四幅图均加载，实际查看中文与版式；229条当前文档本地链接有效，320项品牌／VI及身份保护文件哈希保持，JSON数量和图像来源哈希一致。[QA](output/qa/senplate-v7-trademark-2026-09-18/closeout-validation.json)。一次UTF-8脚本与一次原子patch失败均未作成功记录，后用正确方式完成。
- 收尾：更新brand、product、README、handoff、VI说明、旧名称报告的后续提示及decision-log；没有改Logo、字体或Figma。下一步先评审真实对照，尚未授权重画、申请、购买、联系或App实现。内地／WIPO、全球图形与香港文字刷新仍为明确缺口，不称全球通过。

## 2026-09-18／19 P0软件开发与英／简双语

- 目标：落实用户开发授权，以V7及VI构建首条可运行补餐链；中途按最新指令改为默认英文／可切换简体中文。
- 阅读：79份原有Markdown、6834行完整阅读；[记录](output/qa/development-p0-2026-09-18/reading-record.json)。语言消息、压缩和跨午夜沿用本轮记录，只补相关变更。
- 实现：apps/ios、apps/operations-web、services/api、tools/simulator、scripts/dev.py、tests；私有PostgreSQL与生成凭据。原生四入口、账户／身份、语言持久化、厨房任务／建议／事件、Web设备显示／CSV、模拟异常输入和共享状态均已接入。
- 规则：同操作幂等、并发只建一张任务、版本与领取权限、乱序包不倒退、移盘不算取用、原始测量和未来供应分开、有效增重关联不重复加量；补上单调事件sequence及早期调试表追加迁移。
- 实际联调：iPhone处理任务至等待补入，CLI模拟+1000g，Web核对，1700g及完成状态回到iPhone。CDP只拦截本地Fetch决定响应，200提交后丢弃回复，原键核查恢复无重复；已清除拦截。viewer无处理／导出，个人身份独立空状态，离位显示未知和最后有效700g。
- 验证：15项pytest通过（8.43s，2条上游弃用提示）、Ruff通过；Web TypeScript和production build通过。iPhone17Pro英／简、重开恢复、任务主链通过；SE3与最大辅助字号通过。原生UI层snapshot工具不可用时用XCTest及XCResult全分辨率附件验证；没有把编译通过当交互验证。
- 修复：资源包遗漏、模拟器签名导致Keychain未存、登录键盘焦点、图表时间／大字截断、窄屏任务筛选、StrictMode旧连接重连及同时间事件乱序。一个文档patch和一次错误工作目录命令失败后已重试；未把失败当成功。Vite配置格式化触发重启后重新加载，最终控制台无新错误。
- 视觉：两张ImageGen英文参考、原VI资产、实际字体；1536×1024厨房、390×844窄屏、402×874与375×667手机。用view_image直接比较，保留原生底栏／字号／业务状态差异；[QA记录](output/qa/development-p0-2026-09-18/verification.md)。
- 收尾：更新product、brand、README、四份软件规格、[P0记录](planning/2026-09-18/development-p0.md)、decision-log及handoff；[保护哈希／链接／交付检查](output/qa/development-p0-2026-09-18/closeout-validation.json)。保留API／Web和700g演示供用户审阅，历史run、学校原件、建议书与VI未覆盖。
- 未完成：P1顾客菜单／扫码／订单、个人餐食、学校汇总，M2硬件与模型，真实iPhone／最低OS、iPhone特定网络丢包注入及持续运行压力。没有外网部署、购买、提交、对外联系或Git初始提交。下一步细化P1菜单与订单／预留契约。

## 2026-09-19 M1.1菜单、订单与预留履约

- 目标：承接用户“继续下一批工作”，完成顾客App到工作App／厨房Web的菜单、下单、接单、配出和取餐；硬件仍使用明确模拟输入。
- 开工：80份Markdown、7017行、51批全读，无阅读期间变化；[记录](output/qa/development-p1-orders-2026-09-19/reading-record.json)。建立P0数据库与代码本地备份，332项原件保护哈希；本轮未派代理。
- 后台：追加菜单／订单／历史／预留／履约分配及迁移、菜单QR、报价与管理版本、个人订阅／操作权限、服务方式版本、整单事务、取消竞争、单盘测量窗口、多次舀取、经理偏差和取餐码限流。保留P0，不把在制或释放预留重复计入实测量。
- 客户端：SwiftUI个人四入口、菜单／详情／购物车／改价复核／本人订单／取餐码／手动回退及系统链接；工作App订单分栏。React菜单管理／QR／订单队列／实测关联／取餐，英／简与窄屏导航。生成并检查三张菜品示意图，[实际提示词／哈希](assets/menu/manifest.json)保留。
- 验证：33项pytest通过（含15项P0＋18项订单），取餐码改为ASCII后针对1项通过；Ruff、Web类型及生产构建通过。8个分阶段XCTest通过，覆盖Pro／SE3、英／简持久化、大字、顾客和员工流程、私人隔离及系统链接；真机SDK无签名构建通过，相机硬件未测。
- 跨端：手机购物车保留90元，Web改价后手机明确复核91元并下单。Web接单200响应扣留到客户端超时，原操作恢复后只预留300g一次；模拟100＋200g两次减重，核对及取餐后1700g不再扣，人工沙拉12→11。另用工作App核对第二单100g，最终1600g、002待取餐。QR从实际网页截图由Vision成功解码，解析器13个输入检查通过。
- 修复／限界：步骤按钮自动化标识、Simulator空相机视图、旧事件选择过滤、错误提示与恢复版本、窄屏菜单导航断行、菜单入口自动收起、辅助文字对比度；浏览器截图像素比例纠正，临时覆盖和拦截已清除。Xcode AX翻译不可用时用XCTest与截图验证，初始失败记录保留。未把UI通过写成硬件性能或全FYP完成。
- 收尾：更新product、README、四份当前软件规格、[M1.1契约](planning/2026-09-19/menu-orders-contract.md)、decision-log、handoff和本日志；[QA](output/qa/development-p1-orders-2026-09-19/verification.md)／[收尾检查](output/qa/development-p1-orders-2026-09-19/closeout-validation.json)。API／Web保留运行，历史数据、学校DOCX/PDF、V7／VI及身份原件保留，没有Git初始提交或外部动作。
- 剩余：M1.2个人配对／份量／参考营养及学校匿名样本，M1.3完整目录配置与报告，M2实物／模型；真实iPhone、最低OS17、VoiceOver、原生丢包注入和长期压力。下一步只有M1.2共用契约及实现。

## 2026-09-19 M1.2个人餐食／匿名学校样本实现

- **目标：**承接“继续下一批”，完成个人短时配对、逐项重量、版本参考营养、学校匿名样本与设备界面，保留M1.1。
- **恢复：**81自有Markdown／7136行／66批完整阅读；第25／26批截断内容单独补全；无阅读期间变化。QA目录output/qa/development-m1-2-meals-2026-09-19记录清单／范围／时间。M1.1数据库及代码私有备份。
- **实现：**FastAPI meal_schemas／meals_domain／meals_routes／nutrition、6张业务与设备表；SwiftUI配对、份量、营养、来源／历史；Web /device独立会话及School samples、CSV；默认英文／简体中文。USDA官方4条资料原JSON、hash与CC0来源另存research/2026-09-19-nutrition。
- **数据保护：**原演示新增#003未完成订单，另建senplate_meals_qa／8800／localhost5178及QA账户；原run和#001／#002／#003保持collected／ready／submitted。未新增物理设备、未重置用户记录。
- **验证：**55后台测试通过（34.02s），Ruff与Web构建通过；6次iPhone分阶段运行通过，覆盖双端配对、450g三项、350g总余量、477.5kcal参考、英／简、SE3及最大字号。真实网页QR解码、4合法／12非法解析通过；Generic iphoneos无签名编译成功。数据4hash／20值核对。UI第一次营养断言因AX合并标签失败，修正测试后独立夹具重验通过。
- **异常：**称重抖动禁用／恢复、漏包／迟到／校准／皮重／移盘保护；设备完成回复丢失后刷新仍用原操作恢复，只有1完成历史；参考目录超时持续提示，恢复后可操作。React hooks新增时HMR发生暂态错误，完整重载后恢复并重新检查，不归为已验证生产故障。
- **匿名样本：**450g已知餐／300g余量与250g未知混合／余量null，汇总2份、700g提供、300g已知剩余、1有余量／1未知；导出明确simulated与未审核示范计划，无浪费率或儿童身份。
- **交付：**餐食契约、资料核查、QA与检查点／截图／CSV；product、README、四份当前软件规格、decision-log和handoff同步。品牌／学校原件与身份份额保留，链接及保护hash收尾记录在本批QA。
- **未完成：**M1.3完整食物／配方／审核计划／角色与餐末去向、实物注册／校准／Pi／模型、真机扫码、OS17、VoiceOver、原生故障与长时压力。没有真实营养／硬件精度／减损证明，没有外网发布、对外联系、购买、签名、学校提交或初始Git提交。


## 2026-09-21 学校Project Proposal制作与检查

- **目标：**按AY26指南与两份样本制作英文正式proposal；最新消息将9月28日列团队提交目标，Moodle截图为9月29日23:59、DOCX与PDF两种格式。开发M1.3本轮未继续。
- **开工：**83份项目自有Markdown／7292行／73批全部读取，第32／33批输出截断后完整补读，无阅读期间变化。[阅读记录](output/qa/proposal-2026-09-21/reading-record.json)；本轮压缩后沿用记录，仅恢复当前规范与要修改文件。
- **附件：**指南1页、sample1全部8页（末页空白）、sample2全部6页（末页空白）逐页查看。提取七项必需内容，采用指南的ITE4116M，未沿用旧样本ITP4913M。三份原文件只读并保留hash，Moodle截图另存QA。
- **研究：**刷新EPD2024厨余统计、卫生署学校午膳资料、Metafoodx、Controliza Buffet、Pi5、Gemini2、PyTorch迁移学习／MobileNetV3和USDA FDC官方资料。9条链接进入参考文献，来源与用途见[来源登记](output/qa/proposal-2026-09-21/source-register.json)。厂商自述不转换成当地试点成效或竞争领先证明。
- **内容：**痛点、受众、竞争、单盘位三配置、硬件／架构、功能／数据、视觉训练和补餐基线、营养估算边界、非功能指标、可行性／风险、团队里程碑、交付、40／30／30、资源与外部／AI协助。19Sep软件结果与拟议实物／模型目标分别表达，没有虚构访谈或试点。
- **制作：**[英文源稿](planning/2026-09-21/proposal-content.md)、[规范](planning/2026-09-21/proposal-spec.md)、[构建脚本](scripts/build_school_proposal_20260921.py)及可编辑架构SVG；最终[DOCX](<output/docx/AY26_ProjectProposal_Group 2.docx>)／[PDF](<output/pdf/AY26_ProjectProposal_Group 2.pdf>)均10页。Word正文与10张表格原生可编辑，架构1图，9条超链接。
- **验证：**初稿渲染后修复标题边框／主题字体、图中连线遮字、编号接续与签名栏空间；最终render-02全部10页以原始分辨率检查。身份／课程／日期／页码、表头重复、签名留空、无跟踪修订核验；a11y高／中／低问题均0；3份学校原件及332项旧文件hash未变。[成稿验证](output/qa/proposal-2026-09-21/final-validation.json)。
- **收尾：**同步product、README、handoff、decision-log、proposal-spec和本日志；链接、保护hash及成稿存在性另记[收尾验证](output/qa/proposal-2026-09-21/closeout-validation.json)。一次原子patch因同一路径同时删除／新增被拒，未改变文件，改为独立更新后成功。未改应用代码、运行服务、重做已通过的软件测试、派代理、改品牌、签名、联系导师或提交Moodle。
- **剩余：**接收组员／Marco反馈后修订，签署与正式提交由相应人员完成；最终课程日程尚未提供，文内2027-03-19只是团队技术完成目标。唯一下一步为proposal审阅修订。

## 2026-09-21 相机必要性与番茄炒蛋营养复核

- **目标：**回应Marco的两点反馈，解释廉价RGB＋称重的替代、混合／遮挡的观测限制及可验证营养流程；不把假设改主线误写为用户决定。
- **阅读：**本轮85份项目自有Markdown／7600行／41批全读；2–4组合输出截断后逐批重读，8批尾部补读，27批product在开头已完整读取并记范围。阅读期间无文件变化；[阅读记录](output/qa/marco-camera-nutrition-2026-09-21/reading-record.json)。
- **研究：**重新读取Orbbec Gemini2和Pi Camera Module3官方规格、FAO配方计算／数据评估及Nutrition5k作者README。CameraModule3 US$25起只为海外官方起价；没有淘宝SKU或Pi实测。FAO方法作为配方参考依据，不伪装真实成分检测。
- **完成：**新增[技术复核](planning/2026-09-21/marco-camera-and-nutrition-review.md)，包含功能—传感器对应、混合菜总量不唯一、原料／得率／损耗、整锅与分份、少量油盐精度、单盘时序、误差层次及下版英文文字。假设500g／500kcal→150g／150kcal只是算术例子。
- **同步：**product、README、handoff、decision-log、proposal-spec，以及当前采购／询价入口、持续监测、相机比较和单盘可靠性提示；旧正文保留历史条件。已交付Proposal DOCX／PDF及源稿、品牌、身份、旧BOM／RFQ未覆盖。
- **验证：**[收尾核对](output/qa/marco-camera-nutrition-2026-09-21/closeout-validation.json)记录文件链接、338项保护hash、研究出处及假设算术。未运行不相关软件测试，未生成新版DOCX／PDF，未训练、采购、上电、联系或提交。
- **唯一下一步：**明确能否取得真实配方／接受备料记录，并确定营养是否作为主评价，据此修订proposal。研究建议不等于导师批准或准确性已经达标。

### 同轮补充：直接回答学生每日维生素C达标能力

- 用户表示前述估算说明未回答精度，进一步给出学生一天营养标准和维生素C场景。直接澄清当前设备无法保证满足该精确目标，不能把“有配方可估算”写成已解决。
- 沿用85文件／7600行全读，补读当前规范、相机营养复核和最新日志；组合输出截断后重读handoff／日志相关段。刷新NIH ODS维生素C热／储存损失及National Academies个体膳食评估资料。
- 补充复核第8节、product、handoff、decision-log及本记录：实际含量、实际吃下量、全天覆盖、摄入参考与营养状态分别解释。未指定某国数值为学校采用标准，未提供儿童补充剂剂量。
- 原Proposal与338保护文件保持，链接与来源登记见本QA的adequacy-followup-validation.json；没有新Word／PDF、代码、训练、硬件测试、对外联系或提交。

### 同轮补充：Metafoodx痛点与可交付价值

- 延续Marco反馈与营养可行性讨论，沿用85文件全读记录；补读竞品研究、最新营养复核／当前交接，核对公开资料，没有重做已通过软件测试或全库阅读。
- 刷新Metafoodx首页、Metron产品、AI运营与预测、Freshness Alert、移动介绍、Pomona厂商案例及校方报道。最终重点引用公开流程及客户采用，未把营销准确率当化学营养精度，未移植54%等成果为本项目指标。
- 追加复核第9节、product当前依据、handoff和decision-log；原10页Proposal及338保护文件保持。检查来源、内部链接及10－3＝7、3＝2＋1的假设口径；证据为metafoodx-pain-followup-validation.json。
- 未创建新Word／PDF、应用代码、实物／模型实验、购买、对外联系或提交。用户尚未决定改主线；工程启示是围绕可测经营问题论证社会价值。

### 同轮补充：已有成熟采购时是否需要Senplate

- 用户继续检验痛点成立条件；沿用Marco反馈讨论的85文件全读及补读链，本次补读当前交接、复核和最新决定。
- 刷新Metafoodx／Illumia集成及Controliza Buffet官方资料。明确补充已存在的运营系统，不能预设采购落后或人人需要设备。
- 追加复核第10节及product、handoff、decision-log，记录适配／不适配情形、餐中时间算例、现有流程基线与现场验证建议。600÷150＝4分钟是明确假设，不是测试结果。
- 原Proposal及338项保护文件保持，内部链接／算例验证见mature-procurement-followup-validation.json；无新正式文档、代码、实物实验、购买、联系或提交。

## 2026-09-25 智能工作台／AI电子日历转向研究

- **目标：**执行用户推翻 Senplate 并研究组员新想法的指令；用户补充适用家庭或办公室桌面，并明确 Chrome 中已打开指定 OpenAI 视频。
- **开工阅读：**按 AGENTS 完整盘点和读取86份项目自有 Markdown、7847行、69批；批次截断处逐项补读，记录显示阅读期间无文件变化。[阅读记录](output/qa/new-concept-2026-09-25/reading-record.json)。两份组员原文件只读提取；DOCX两页结构与页面渲染核对，渲染环境缺中文字体，故正文判断依据结构提取。原件SHA-256、旧Proposal哈希留在本轮QA。
- **公开研究：**核对 Echo Show 存在感知、Skylight Calendar、Microsoft Viva、Upright GO 2、Razer AVA、Pi官方规格、Google日历API、OpenAI GPT-Live官方技术／价格、微软提醒时机研究、OSHA／NIOSH，以及情绪推断与AI情感使用研究。Chrome 实际播放指定约55秒X视频，查看0:06、0:16、0:21、0:30、0:39、0:51画面／可见字幕，再与OpenAI官方完整技术文章交叉。未声称观看所有音轨或复现视频装置。
- **研究结论：**电子日历、存在感知、姿态反馈和语音角色已存在；“更有硬件／功能”本身不是差异。首选可测命题是基于日程紧迫度、在桌状态和用户专注设置减少不合时宜提醒，同时守住重要事件的及时性；用用户确认构成闭环。情感障碍治疗和自动情绪诊断不在可承诺范围；LCD角色可做，反射影像和小云台仅作可选实验。GPT-Live语音按需开启，官方按活跃会话秒数收费，后端另计。
- **交付：**[新方向完整分析](research/2026-09-25-desk-companion/feasibility-review.md)，含竞品矩阵、四种定位、商业假设、硬件与语音架构、验证、六个月分工和英文Proposal表述。重写[product.md](product.md)，将旧全文保留在[product-senplate-historical.md](product-senplate-historical.md)；README、brand、旧软件总规范、商业计划、RFQ入口与旧Proposal规范标历史，更新decision-log与handoff。
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

## 2026-10-09｜全身3D女性二次元伙伴

- **目标与要求：**按用户需求加入类似AVA的全身3D角色，用户选择先用二次元女性；保留坐姿、日历、事务、受限操作与英文默认／简中。
- **开工：**修改前127份MD／11,994行／47块全读；18块截断单独补发，入口早期截断由完整分块覆盖。22:53:28+08:00完成，[阅读范围](output/qa/2026-10-09-3d-avatar/reading-record.json)。压缩恢复沿用本轮记录，没有重启或继承其他轮正文覆盖。
- **完成：**新增VRM场景／骨骼动作／眨眼、实际播放音量与300ms超时、同源浏览器桥、动作与合成元音预览、自包含模型替换、暂停／减少动态、英简、常亮集成及独立纯黑／镜像。固定pixiv模型来源与许可，未复制Razer角色。修复fallback副作用误报WebGL失败、暂停留开口、替换模型错误许可链接与恢复样本的预览清理；更新source-map-js传递依赖后npm审计0项。
- **验证与证据：**[本轮QA](output/qa/2026-10-09-3d-avatar/verification.md)含22前端、26定向后端、构建、npm、真实浏览器输出RMS与嘴部变化／归零、暂停镜像、简中390×844、桌面1280×800、常亮1024×600、非法模型拒绝／本地替换、WebGL丢失／重试与准确截图。IAB截图尺寸／CDP拦截行为差异均记录；拦截已清除。未将模拟音量称为自然对话或Pi成绩。
- **规范与保留：**新增[角色契约](desk-companion/docs/avatar.md)并同步product、两个README、架构／操作／设备规范、第三方许可、decision-log与handoff。107保护项与七条事件和原备份一致；账号／运行库保留忽略目录。当前功能分支 `codex/full-body-3d-avatar`，未自动合并main；GitHub实际交付回读在QA补记。
- **剩余：**正式角色美术、跨设备／Python音量桥、逐音素口型、真实语音与目标Pi／iPhone／光学硬件性能；通用PC与RIG原未完范围不变。无收费调用、真实音视频采集、硬件运行、采购、外部联系或学校提交。

- **实际GitHub交付：**软件提交`c866d32`已推送私人仓库功能分支，[PR #4](https://github.com/tantalum666/FYP/pull/4)建立并附加本聊天，未合并main；收尾提交只补QA关闭、PR回读与日志空白处理，不改已测试应用。主8831／5190继续运行，QA8833／5191已关闭。

## 2026-10-09至10｜女性全身角色美术研究

- **目标：**按用户要求先研究目前受欢迎的二次元角色，为现有3D伙伴整理原创美术方向；不提前改模型。
- **开工阅读：**128份项目Markdown／12,096行／48块全文，2／3组合截断后分别完整补读；00:50:21+08:00完成，阅读期间hash不变。[阅读范围](output/qa/2026-10-09-avatar-art-research/reading-record.json)沿用同轮跨午夜／压缩进度，没有机械重启。
- **研究：**核对Anime Corner10月5日季度社区投票与Anime Trending3月公布的2025年度结果；实际看爱蜜莉雅、芙莉莲、猫猫、海梦官方图，取样流萤／芙宁娜官方视频画面，检查HoYoverse署名的星见雅主图及Razer当前产品资料。未把视频播放量／个人Agent of the Year当全球人气名次；视频只检查关键画面，未声称全部连续观看。
- **交付：**[中文研究与三方向](research/2026-10-10-avatar-art/popular-character-study.md)、[8项图文参考板](research/2026-10-10-avatar-art/reference-board.html)、[来源表](research/2026-10-10-avatar-art/source-register.json)。建议A银雾柔科技优先、B墨青都市伙伴强对照、C暖金开朗日常；目前是原创文字／色板，未生成概念或选定角色。
- **实际检查：**参考板1280px宽、8图全部加载、无横向溢出、浅／深切换和原图比例已检查，浏览器截图保留。正文链接、来源、资产hash／应用与学校保留及Git交付读回见[本轮QA](output/qa/2026-10-09-avatar-art-research/verification.md)。无应用代码／DOCX变化，不重跑旧业务测试或文档渲染。
- **同步：**product、根README、角色契约、decision-log、handoff和本日志。107保护项、pixiv模型及应用源码保持；正式美术、Pi并发、自然语音／逐音素、远端声音、物理光学、PC／RIG原未完成范围保留。
- **下一步：**制作同规格A/B原创全身、脸部和表情概念对照；本轮没有ImageGen生成、模型替换、采购、付费服务、硬件动作、对外联系、学校提交或main合并。

- **实际Git交付：**研究提交`876d89e`已推送，`git ls-remote`与连接器均读回同一head；PR #4保持open且补充研究范围，main仍`ccfac48c`。564条本地链接、107项保护hash、原模型／应用保持、8图显示与staged Gitleaks零结果通过；最后收尾提交只更新交付状态与证据。

### 2026-10-10 同一美术任务补充：A/B服装研究

- **用户补充：**同意A/B继续设计，要求研究丝袜及轻微性感服装；最终服装和角色未定，C暂不推进。
- **阅读：**继承同一角色研究128份／12,096行全读记录，盘点当前129份项目Markdown，补读入口、当前研究、角色契约及README／决定／日志变化范围；[补读记录](output/qa/2026-10-10-avatar-wardrobe/reading-record.json)明确不冒称重新全库阅读。
- **研究与产物：**[服装研究](research/2026-10-10-avatar-art/wardrobe-study.md)、[4项服装参考＋4套简报板](research/2026-10-10-avatar-art/wardrobe-reference-board.html)、[来源表](research/2026-10-10-avatar-art/wardrobe-source-register.json)。实际查看2B原图、卡芙卡官网、申鹤官方文章／全身GIF和Myethos授权卡芙卡礼服图；核Wolford／FOGAL。只把人气和服装关系写为假设。
- **建议：**A1短外套短裙半透黑丝／B1都市剪裁哑光黑丝优先，A2肩颈烟灰丝／B2非对称裙装对照。角色设为成年外观，约25岁仅是原创简报建议；丝袜D数不映射成材质alpha，贴图与裙摆变形分别验收。
- **同步与验证：**product、根README、角色契约、首轮研究／参考板、决定、handoff及日志更新；[本次QA](output/qa/2026-10-10-avatar-wardrobe/verification.md)记录图片加载／浅深切换、链接、保护hash、原模型与代码保留及Git交付。没有代码／学校文件变化，不重跑既有应用套件或DOCX渲染。
- **下一步：**按四套简报先制作A1/B1同规格原创全身与脸部概念。没有生成角色图、制作VRM、采购、付费服务、实体运行、对外联系、学校提交或main合并。

- **服装补充实际Git交付：**`b4e7589`推送并由远端ref／PR head双重读回，PR #4保持open、main未变；说明补入服装范围。最后收尾只更新本条、handoff与QA交付状态，不改已检查的服装板、模型或应用。

### 2026-10-10 同一美术任务补充：A1/B1角色图生成

- **目标：**执行用户开始生成角色图的明确授权，按A1/B1首组简报交付可直接看的全身图。
- **阅读与路线：**继承美术全读128份／12,096行及服装补读，盘点当前130份MD、补读入口／服装／角色契约及当前变化。应用系统ImageGen与Creative Production技能，后者明确要求两张未缓存原生图交给工作代理；两项各一次调用，完成后立即消费结果并调用中断接口确认完成，未声称销毁不存在的句柄。直接Creative Production UI工具未在当前调用表暴露，按其禁止嵌套转发的要求未通过functions.exec挂载，交付原生图。
- **产物：**[概念入口](research/2026-10-10-avatar-art/character-concepts.md)、[两张原图／完整提示词／manifest](design/desk-companion/characters/2026-10-10-concepts/README.md)。1024×1536 PNG逐字节复制，A1为1,819,525字节、B1为1,798,005字节；无输入参考图、CLI/API回退、后期改像素或重生成。
- **审阅：**全身、手鞋和服装清楚；实际半写实风格、留白、A1鞋跟及B1短裤／强调色偏离已记。两图未被用户选定，A2/B2与模型工程未做。
- **同步／验证：**product、README、角色契约、两份研究及参考板状态、decision-log、handoff和本日志更新；[本次QA](output/qa/2026-10-10-character-concepts/verification.md)记录阅读、技能限制、图片尺寸／hash、保护文件、代码与原模型保持和Git交付。无代码／学校文件变更，不重跑应用套件或DOCX渲染。
- **下一步：**根据用户对方向与半写实程度的反馈精修，再补三视图／表情与VRM；本轮没有替换应用角色、运行新硬件、消费语音模型、采购、对外联系、学校提交或main合并。

- **角色图实际Git交付：**概念提交`3cd7976`已推送，远端ref与PR head双重读回；PR #4保持open且描述已更新，main未变。最后收尾只记录交付，不更改两张原图／提示词或应用。

### 2026-10-10 同一美术任务补充：A1二次元V2

- **用户反馈：**选择A1方向，首轮过于写实；沿用同一美术阅读链，补读入口、当前资产说明与决定，截断尾部另补。记录在[本次QA](output/qa/2026-10-10-a1-anime-v2/reading-record.json)。
- **实际完成：**查看原A1后，内置ImageGen一次编辑，参考图仅为本组A1 V1；V2更鲜明的眼型、简化鼻口、平滑皮肤／成组发束／衣物赛璐璐明暗，原服装与全身构图保持。没有派新代理、CLI回退、重生成或像素后期。
- **交付：**[A1 V2原图与完整提示词](design/desk-companion/characters/2026-10-10-concepts/README.md)，1024×1536、1,710,378字节，原生文件逐字节保留；A1/B1 V1不覆盖。A1为已选工作方向，V2仍待风格反馈。
- **同步／检查：**product、README、角色契约、研究／资产入口、决定、handoff与日志更新；[验证](output/qa/2026-10-10-a1-anime-v2/verification.md)记录图片、来源／hash、链接及应用／模型／学校保护。无代码或学校正文变化，不重跑既有应用套件或文档渲染。
- **下一步：**据V2反馈继续精修A1，再补三视图／表情和模型工程；本轮未替换运行角色、动硬件、用语音API、采购、对外联系、提交学校或合并main。

### 2026-10-10 同一A1美术迭代：平涂二次元V3

- 用户要求进一步减少写实；沿用美术全读／补读链，完整补读入口与资产说明，查看V2编辑目标。
- 内置ImageGen一次编辑，V3为1024×1536／1,350,646字节；实际更平涂、硬边明暗，减少衣物、丝袜与鞋的渐变，脸型接近V2。无CLI、重试、代理或像素后期，原生结果已显示。
- [原图／提示词与版本](design/desk-companion/characters/2026-10-10-concepts/README.md)已保存；原稿保持。产品、README、角色／研究／资产入口、决定与handoff同步，[本次QA](output/qa/2026-10-10-a1-anime-v3/verification.md)记录图片／hash、链接和保留检查。
- 当前V3待风格反馈，下一步继续定向精修A1，再补视图／表情；未替换运行模型、改代码／学校正文、动硬件、消费语音、采购、对外联系、提交或合并main。

### 2026-10-10 A1同轮小修：V4

- 用户要求再轻微降低写实；沿用同一美术全读／补读，补读当前handoff、资产说明及决定，并实际查看V3。
- 内置ImageGen一次编辑，原生V4已显示；实际小幅压平上衣／布料／丝袜，五官和姿态接近V3，背景仍有轻微渐变。无重试、代理、CLI或像素后期。
- [V4原图／提示词与版本](design/desk-companion/characters/2026-10-10-concepts/README.md)已保存，产品／当前入口／handoff／决定同步；[QA](output/qa/2026-10-10-a1-anime-v4/verification.md)记录尺寸／hash、链接、旧图和原模型／代码保护。
- V4待风格反馈，下一步定向精修A1，再补视图／表情；未改程序／学校正文或运行硬件，不重复旧套件，不合并main。

### 2026-10-10 保留五版与日本动画形象／刻画研究

- **目标：**执行“先保留这几版，再研究日本动漫人物的形象与刻画”，A1方向保持，本轮停止改图。
- **实际保留：**A1 V1–V4与B1、五份完整提示词hash一致；资产manifest原有五项来源条目完全一致，只有当前工作状态更新。没有V5、像素编辑或模型替换。
- **研究产物：**[完整研究](research/2026-10-10-avatar-art/japanese-character-study.md)、[图文板](research/2026-10-10-avatar-art/japanese-character-board.html)、[13来源记录](research/2026-10-10-avatar-art/japanese-character-sources.json)。六角色、官方设定／实际观察、配音／导演／CG制作人员原始访谈分开；没有把宣传立绘当实时3D、不同作品版本混用或声称完整观看剧集。
- **结论与建议：**A1下一轮先明确身份、性格及六种表情，再有针对性地调整中性脸、发束、姿态和状态转换。安静、敏锐、可靠及轻巧幽默是建议，尚未由用户最终选定。保留不等于否定V4。
- **检查与同步：**[本轮QA](output/qa/2026-10-10-japanese-character-study/verification.md)沿用128文件／12,096行全读和补读链；图文板八图实际加载、完整截图查看通过，五PNG／五提示词／107保护文件／程序路径／原VRM保持，当前文档本地链接通过。product、入口／角色规范、资产索引、历史研究入口、决定与handoff同步；纯研究不重复旧软件套件或学校文档渲染。
- **交付：**继续既有功能分支／PR #4，实际远端读回另存本轮QA。不合并main，不改学校正文或运行数据，不动硬件或调用语音服务。
- **唯一下一步：**先评审一页A1性格／外形简报与六种表情规则，再按明确反馈制作视图／表情。

- **本轮实际Git读回：**研究内容`9b9effb`已推送，远端ref与PR #4 head相同；说明已同步、open且未合并，main保持`ccfac48`。[交付记录](output/qa/2026-10-10-japanese-character-study/git-delivery.json)保留；其后收尾仅写核验记录。
