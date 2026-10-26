# Group 2 品牌命名与视觉方向 V1

日期：2026-09-16。状态：HISTORICAL_EXPLORATION — UNSELECTED。本文件保留此前的三张命名概念图。用户随后选定 **Senplate**，完成[名称初筛](../../research/2026-09-16-senplate-name-check/senplate-trademark-and-domains.md)，现又明确要求[Senplate Logo与VI](senplate-logo-vi-directions.md)。本文件旧图都不是Senplate的已选视觉，其编号与新组无关。

## 1 设计目标

品牌应承接餐厅持续监测与补餐、学校匿名样本配餐、成年个人餐食记录三种用途。核心表达为“理解份量与变化，帮助作出合适的供餐／用餐决定”。不用“零浪费”“精准营养诊断”等尚无证据的效果承诺，也不让名字限定为垃圾识别工具。

一套身份覆盖同一iPhone App的个人／工作模式、厨房／管理Web及单台设备。标志需要在App图标、页面页首、设备机身小面积单色印刷上成立。正式英文项目题目仍为现有Food and Nutrition Monitoring System，候选品牌尚未替换建议书或RFQ。

生成方式：Product Design ideate流程＋内置ImageGen，三次独立调用。没有用API CLI、没有新建Figma文件。实际附加的参考是[Metafoodx公开App截图](../../research/2026-09-16-metafoodx-app/screenshots/official-populated-screens.png)，仅用于功能背景，提示词明确不沿用其标志、蓝色界面和扫描工作流。

## 2 三个候选

编号在三张原生生成结果全部出现后，按本次对话的实际显示顺序确认。不能按并发提交次序推断；本轮观察到的顺序如下，机器记录见[manifest](../../output/brand/2026-09-16/manifest.json)。

| 显示编号 | 候选名称 | 命名与视觉主张 | 当前概念图 |
|---|---|---|---|
| 1 | Portemi · 食度 | portion的命名联想；对食物份量和分寸心中有数。深绿、米白、柔和橄榄色，双份量／碗形抽象标志，食物照片与余量同屏 | [原图](../../output/brand/2026-09-16/portemi-v1.png) |
| 2 | Traysen · 餐序 | tray与sensing的命名联想；持续感知、供餐有序。深墨青、浅柠绿，餐盘／刻度式几何标志，大数字和趋势优先 | [原图](../../output/brand/2026-09-16/traysen-v1.png) |
| 3 | Melsori · 餐伴 | meal与餐食记录的命名联想；亲近的日常餐食理解。陶土橙、梅紫、暖白，m与碗形结合的柔和标志，个人餐食照片和逐项份量 | [原图](../../output/brand/2026-09-16/melsori-v1.png) |

上述构词是本项目的设计联想，不是词典释义或对现有名称词源的声明。中文名用于比较气质，不代表商标已核准。设计建议倾向Portemi，理由是个人亲和感和供餐专业性较均衡；这不是用户决定，selected_option仍为空。

三张均为1536×1024的单品牌概念板，包含名字、标志、App图标及一个代表页面。前两张展示工作模式补餐，第三张展示个人记录；它们不是三套不同功能的产品，也不是已完成全部角色页面。

## 3 画面数据与视觉复核

工作页沿用P0设计算例：当前700g、补餐建议1000g，标“示範資料”；Traysen的1500→1200→700g折线只表示示例变化，不提供实测时间轴或性能证据。个人页为逐项装盘200g米饭、100g鸡肉、150g蔬菜，共450g，不表示相机从一张混合餐照片推得准确分项重量或摄入。

已直接查看三张生成结果：名称和关键重量可辨，主动作与来源标签存在，未加入热量／健康评分或已验证减损数字。三张图仅通过“足以比较方向”的检查，未通过生产视觉、字体、可访问性或交互验收。

选定后必须处理的细节：

- Portemi大标与页首的小标形态需统一；当前形状仍容易被看作叶片，需要判断是否加强份量／碗的识别。底栏有简繁字形混用，正式稿全用繁体中文。
- Traysen生成的托盘外观只是品牌应用示意，不是新的整机结构或硬件交付图；不能替换既有立柱、相机、屏幕和称重平台方案。大标、图标与硬件示意上的负形也需一致。字体样张“Satoshi”是图片上的设计表达，未核验实际字体文件。
- Melsori的参考色标生成成了#EFD1B8，提示词目标是#EFD1BB；正式色值以选定后设计规范为准，不能从概念图OCR直接入库。细字仍需在真实手机尺寸核对。
- 概念图没有严格保证手机内容为390×844；还原前应重新定稿单页、字号、按钮尺寸、长文本和安全区。三张都是栅格图，不是可直接用于所有尺寸的矢量Logo或可运行界面。

不要机械复制生成时自行补出的英文宣传语或说明段落。页面行为、权限、份量和状态仍以[页面规格](app-pages-and-permissions.md)、[业务与API](software-workflows-and-api.md)为依据。

## 4 初步公开同名检索

本轮做了引号精确词与food／app／software组合的公开网页初筛。Portemi、Traysen、Melsori的本轮结果未发现明确同名餐食监测软件；Portemi有语言／歌曲结果，Traysen有人名使用，Melsori有非产品结果。这只是本轮有限检索观察，不能推导名称唯一、域名可注册或商标可用。未做正式商标、应用商店全区或域名注册核验。

已排除或未采用的候选有明显现成使用，例如[Mealume餐食软件](https://mealume.com/)、[Serviqo软件](https://serviqo.io/)、[Cibelo建筑公司](https://www.cibelo.com/servicios/)、[Trayvia零售](https://trayvia.com/)；这些仅支持同名使用观察，不对对方的商业效果作判断。Traysen现有人名示例见[World Athletics资料](https://worldathletics.org/athletes/united-states/traysen-thomason-15283287)。

## 5 文件与下一步

- [原图与显示映射](../../output/brand/2026-09-16/manifest.json)：保留每张原生成路径、项目副本、哈希和待选择状态。
- 原始完整提示词：[Portemi](../../output/brand/2026-09-16/prompts/portemi-v1.txt)、[Traysen](../../output/brand/2026-09-16/prompts/traysen-v1.txt)、[Melsori](../../output/brand/2026-09-16/prompts/melsori-v1.txt)。
- [阅读记录](../../output/qa/brand-directions-2026-09-16/reading-record.json)与[收尾核对](../../output/qa/brand-directions-2026-09-16/closeout-validation.json)。

原“选图或组合后直接出调整图”的下一步已取代，名字后来确定为Senplate；本文件没有当前执行步骤。后续按用户安排进行Senplate的视觉工作，不自动重用这些旧图。以后进入还原时仍保留iPhone原生方向，不因设计技能默认模板而擅自改成面向用户的网页。
