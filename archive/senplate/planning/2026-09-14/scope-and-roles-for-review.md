# Group 2 项目定位与分工 V1 历史记录

HISTORICAL：本文件对应保留的 V1。Marco 讨论后的当前范围见[多场景 V2](multi-scenario-suggestion-v2.md)及[product.md](../../../../product.md)；下文保留当时的题目、导师拼写和状态供追溯。

建议以 AI 与 IoT 补餐决策和食物减损为主线，面向自助餐及批量备餐的自选快餐。扫码电子菜单和点餐是需要实现的辅助功能，用于把顾客可见信息、待处理需求和后厨供应状态连在一起。

这份文件保存详细范围与分工；英文 Project Suggestion Form 已据此填写并完成 DOCX/PDF 逐页核对。导师尚未口头确认，拟议导师和分工不表示已经获批。

技术修订说明：已明确为餐盘在供餐期间一直留在设备上的持续实时监测。借鉴 Metafoodx 的硬件外形和布置，不采用共享扫描站为主流程。优先验证 Raspberry Pi 5 单机采集和计算，已有 Arduino UNO R4 WiFi 为可选的采样／调试备选；详见[持续监测架构与硬件选择](continuous-monitoring-architecture.md)。相机型号、主机与预算尚未确认，角色比例仍为建议。

## 已提供的基本资料

- Group number：2
- Programme / Class：Higher Diploma in AI and Smart Technology (IT114124) / Class AIST-2B
- Proposed supervisor：Macro，姓名拼写按提供内容保留，口头同意待确认。
- Group leader：Yuan Yuchen

| 成员 | 学号 | 学校邮箱 | 预计工作占比 |
|---|---|---|---:|
| Yuan Yuchen | 250342840 | 250342840@stu.vtc.edu.hk | 40% |
| Xu Ziqian | 250137555 | 250137555@stu.vtc.edu.hk | 30% |
| Li Wenhua | 250329909 | 250329909@stu.vtc.edu.hk | 30% |

邮箱按已明确提供的“学号＋@stu.vtc.edu.hk”规则生成。比例表示预定工作分配，不是保证的最终评分或已经完成的贡献。

## 建议题目

**AI and IoT Based Food Replenishment and Waste Reduction System**

中文工作名称：**基于 AI 与 IoT 的餐品补充与食物减损系统**。

电子菜单写入范围与功能，不让标题变成扫码点餐平台。普通餐厅的纯按单现做流程可以作为后续扩展，核心评价先围绕自助餐和批量备餐自选快餐。

## 要解决的问题

前台餐盘余量、近期取餐速度、已确认未配餐的订单和后厨在制批次可能分散在不同位置。员工若过晚补餐，会出现空盘、等候和不可兑现的点单；若过早补餐或重复制作，餐末会剩下过量食物。顾客侧的菜单信息也可能落后于实际供应，需要反复询问还有没有、多久能好。

拟议系统将实际供应、需求和制作进度统一为可核对的状态，为员工提供可接受／调整的补餐建议，并把适当的可售、热度和等待信息反馈到电子菜单。不是依据传感器直接判断食物安全，也不以生成宣传式“热销”作为目标。

具体问题发生频率、损失金额及采用意愿仍需真实场景验证。现有 Metafoodx、Controliza 及相关点餐生态已经覆盖不少功能，因此提案应陈述参考与拟议整合目标，不宣称市场首创或已全面优于商用品。

## 两种主要用餐模式

| 模式 | 顾客如何使用菜单 | 订单与传感器怎样衔接 |
|---|---|---|
| 自助餐 | 查看菜单、供应状态、近期取用趋势、补餐等待；现制／加点项目可以扫码下单 | 普通自取菜以餐盘变化为主要供应／取用信号，不要求每取一道菜都下单；现制订单单独进入厨房队列 |
| 批量备餐自选快餐 | 扫码选菜并下单，查看确认与配餐／取餐状态 | 已接受但未配餐的订单形成待履约数量，结合餐盘可用量及在制批次计算可承诺供应，防止重复计量 |

普通菜单浏览、收藏或未提交的选菜不等于已确认需求；已提交订单也不等于已经完成出餐。系统应保存这些状态的区别。

## 核心与辅助功能

| 范围 | 功能 | 首版完成条件 |
|---|---|---|
| 核心必做 | 原位持续监测与餐盘物理事件采集 | 厨师端上菜后原位供餐，持续称重和视觉观察；首个完整餐位验证后扩展 2–3 个；处理去皮、稳定读数、换盘／移盘、取用和加料，识别无效或陈旧数据 |
| 核心必做 | AI 短期需求与补餐建议 | 使用有效余量、近期消耗、营业时段、待处理订单及在制批次，给出补做时机和数量范围；数据不足时可使用基线方法 |
| 核心必做 | 后厨任务与人工确认 | 建议可接受、修改或拒绝；制作任务有待处理、制作中、可出餐、已补充、取消等状态，避免重复任务 |
| 核心必做 | 餐末剩余与运营评价 | 分开记录可避免剩余、空盘分钟、订单履约状态和人工改动；可以导出用于测试的记录 |
| 辅助必做 | 动态 QR 电子菜单 | 菜名、图片、价格／套餐说明、店方维护的描述、可供应状态、热度／取用趋势、预计等待与更新时间 |
| 辅助必做 | 基础扫码点餐 | 自选快餐和自助餐现制／加点的点单、确认、取消规则、后厨队列与取餐状态；处理重复提交和余量变化 |
| 平台基础 | 双语与角色管理 | 英文和繁体中文界面；顾客、厨房员工、经理／管理员的权限与界面不同 |

首版不承诺完整集团采购、供应商发票 OCR、财务 ERP、多地区经营系统、自动烹饪机器人或独立食品安全判定。支付先按现场原有方式处理，是否加入支付集成留待主线稳定后决定。这些边界已写入当前建议书。

## 菜单上的实时信息必须有依据

| 显示内容 | 数据依据与规则 |
|---|---|
| 供应中／余量较少／补餐中／暂不可售 | 有效传感器读数、已接受待配餐订单、制作任务及人工状态；数据失效时不能假装正常 |
| 热销 | 在点餐场景按明确时间窗口的已完成订单统计，排除取消与重复订单 |
| 近期取用趋势 | 在自助场景按校准后的餐盘消耗趋势显示；不把不同菜的克数直接当成人气高低 |
| 预计等待 | 根据已确认的制作任务与预计完成时间，显示估计或范围；不是保证送达时间 |
| 价格与餐品说明 | 由经理维护；不让 AI 推测不存在的菜品事实、营养或安全结论 |

若采用“热销”排序，仍需保留顾客选择，不把待清空的菜伪装成最受欢迎的菜。菜单推荐效果与后厨补餐算法的效果应分开测试。

## 三个项目目标

1. 分析并实现一个低成本 IoT 采集与状态管理系统，为自助餐／自选快餐提供可靠的餐盘余量、消耗、补充和剩余记录。
2. 开发并评价 AI 辅助补餐逻辑，结合短期需求、有效供应、待处理订单和在制批次，在空盘、等待与餐末剩余之间形成可人工审核的建议。
3. 集成双语员工操作界面和辅助 QR 菜单／点餐，验证菜单、订单、传感器和厨房任务的一致性，以及系统可靠性和使用体验。

正式表格已将这三个目标写成简洁英文，没有加入未经测试的节省百分比、预测准确率或商业收益保证。

## 建议分工

### Yuan Yuchen 40%

**Proposed role：Project Leader and Backend AI Lead**

**Responsibility wording：**

Lead requirements analysis, system architecture and project coordination. Develop backend APIs, the shared data model, food recognition, short-term demand forecasting and replenishment decision logic. Integrate the IoT, kitchen workflow and digital menu subsystems, and coordinate end-to-end testing and evaluation.

具体主责：定义业务和数据规则；设计后台与数据库；实现预测、补餐决策、订单和在制状态之间的接口；协调需求、进度、集成与整体测试。组长的 40% 有明确技术产出，不能仅依靠管理工作。

建议占比分解：需求／架构／协调 8%，后台与业务状态 12%，预测与补餐决策 14%，集成评价和报告统筹 6%，合计 40%。

### Xu Ziqian 30%

**Proposed role：IoT Hardware and Edge Processing Developer**

**Responsibility wording：**

Design and integrate the sensing nodes and edge communication. Implement Raspberry Pi acquisition services, calibration, signal processing, tray-event detection and reliable data collection; add microcontroller firmware only if required. Test hardware accuracy, disconnection recovery and abnormal conditions, and document the device setup and maintenance procedures.

具体主责：持续称重模块、供电与结构、Pi 采集服务；校准、滤波、去皮、取餐和换盘状态；通信、缓存和去重；测量与故障测试、安装说明。已有 UNO 固件仅作为需要独立采样时的备选。

建议占比分解：硬件与采集服务 14%，校准／物理事件处理 8%，通信与故障恢复 5%，模块测试记录和文档 3%，合计 30%。

### Li Wenhua 30%

**Proposed role：Web Application and User Experience Developer**

**Responsibility wording：**

Develop the staff dashboard and the supplementary customer QR menu and ordering interface. Implement real-time availability, popularity, preparation and order-status views with bilingual support. Integrate the interfaces with backend services, conduct frontend and usability tests, and prepare user documentation.

具体主责：员工餐台状态／补餐任务界面、菜单维护界面；顾客扫码菜单、基础点单和取餐状态；实时更新、双语、手机适配和错误状态；前端／可用性测试及使用说明。

建议占比分解：员工操作与管理界面 10%，顾客菜单／点餐 10%，实时整合与双语 5%，可用性测试和用户文档 5%，合计 30%。

所有成员都参与调研、系统设计讨论、集成测试、日志和报告。主责表示归属，不代表其他成员完全不参与；最终贡献应按真实工作记录说明。

## 技术路线建议

- Hardware：Raspberry Pi 5、load cells 与合适 ADC（HX711／NAU7802 等待验证）、顶部相机、温度模块、显示／提示及固定结构；餐盘原位持续监测。Pi 单机优先，UNO 为可选；型号和预算待验证。
- Acquisition：Pi 上的 Python 采集服务；只有启用可选微控制器时才需要 C++ 固件。
- Backend and AI：Python、相应 RGB-D SDK、图像识别模型、FastAPI、pandas、scikit-learn；限定菜品，比较 RGB 与 RGB-D 的实际收益，同时保留短期预测和补餐决策基线。
- Web：TypeScript、React，响应式网页；实时更新可采用 WebSocket。
- Data and messaging：PostgreSQL、MQTT／Mosquitto；区分传感事件、订单、制作任务及餐期记录。
- Deployment：复用电脑开发／训练，优先验证 Pi 5 单机独立装置；实测不满足要求时再考虑独立采样器或小型电脑。Docker 用于适合的服务部署，本地核心优先。
- Localization：英文／繁体中文为首版；时间、币种、语言及部署配置独立，作为以后适配大中华地区的基础，不宣称已完成跨境合规部署。

这些是拟采用工具，不代表已建成或已采购。硬件以复用电脑和少量节点为前提，预算需在选定元件及结构后核算。

已有研究中的元件单价可作为参考；原共享扫描架构的整套预算已不适用于当前持续监测结构，需要按实际餐位数和复用硬件重新计算。

## 评价与关键异常

算法至少与固定余量阈值和简单消耗速度方法比较。自助餐评估空盘分钟、可避免剩余及员工干预；点餐流程另评估菜单状态滞后、重复提交、确认后缺货和订单状态一致性。

对已确认订单与实际取餐进行对账，避免先把订单计为消耗，之后传感器又重复扣一次。移动餐盘、同盘加料、网络中断、临近收餐、后厨已在制、订单取消和顾客没有取餐，都需要明确处理。

下面是一个说明一致性的假设例子，份数假设已经按该菜品标准份量换算，实际设备仍需校准：

| 时点 | 实际在盘 | 已确认待配餐 | 可再承诺数量 |
|---|---:|---:|---:|
| 尚未配餐 | 20 份 | 8 份 | 12 份 |
| 为其中订单配出 3 份后 | 17 份 | 5 份 | 12 份 |

两次事件需要正确关联。已经配出的同一份不能在订单和传感器两个来源里重复扣除；还没制作完成的食物也不能显示为当前已有供应。

模拟或回放数据可用于功能测试；若没有实际试点，不得把它们写成已实现商业减损。导师应能看到各成员的模块测试、整合过程和实际贡献。

## 正式 suggestion 的填写状态

原模板三页，填入内容后为四页；成员资料集中在同一页，问题／范围、技术和签批分别清楚排布。原件没有修改，组号为 Group 2。完成副本位于[DOCX](<../../output/docx/AY26_ProjectSuggestion_Group 2.docx>)和[PDF](<../../output/pdf/AY26_ProjectSuggestion_Group 2.pdf>)。

模板要求先取得导师口头同意，并在 14 September 2026 的 FYP 课堂提交 DOCX 和 PDF。Macro 仍未确认；所有签名／日期和导师审批留空，文件未上传或提交。相机／ADC 选型、预算、场地与实验细节属于后续验证项。
