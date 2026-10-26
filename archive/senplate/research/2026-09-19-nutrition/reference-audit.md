# Senplate 首批参考营养资料核查

2026-09-19，Group 2。当前用途为M1.2受控餐食的已提供重量换算，不是食物化验、个人实际摄入测量或医疗建议。

## 来源与授权

本轮从USDA FoodData Central官方API读取下列4条记录，原始JSON保存在sources目录，文件hash、读取时间和原文描述见[provenance.json](provenance.json)。使用官方允许的公开DEMO_KEY做少量查询，没有申请账号或使用用户私钥。官方[API Guide](https://fdc.nal.usda.gov/api-guide/)声明数据为public domain并按CC0 1.0发布，可用于本地软件；本项目保留USDA和具体记录归属。

四条记录均属于SR Legacy，API返回publicationDate为2019-04-01；SR Legacy是历史参考集，并非2026年新测的食物数据。官方[Foundation Foods文档](https://fdc.nal.usda.gov/Foundation_Foods_Documentation/)区分SR Legacy及后续Foundation数据。当前版本写成“SR Legacy final release / API record ID”，不把读取日期写成营养测定日期。

## 纳入记录

每列营养均按100g可食用部分；能量kcal，其他为g。

| 显示名称／官方记录 | 能量 | 蛋白质 | 脂肪 | 碳水化合物 | 膳食纤维 | 匹配条件 |
|---|---:|---:|---:|---:|---:|---|
| [熟白米饭 169757](https://fdc.nal.usda.gov/food-details/169757/nutrients) | 130 | 2.69 | 0.28 | 28.17 | 0.4 | 长粒白米、未强化、煮熟且未加盐 |
| [烤鸡胸肉 171477](https://fdc.nal.usda.gov/food-details/171477/nutrients) | 165 | 31.02 | 3.57 | 0 | 0 | 仅肉、去皮去骨、熟且烤制；另加酱汁／油不计入 |
| [水煮西兰花 169967](https://fdc.nal.usda.gov/food-details/169967/nutrients) | 35 | 2.38 | 0.41 | 7.18 | 3.3 | 煮熟、沥水、未加盐 |
| [香蕉 173944](https://fdc.nal.usda.gov/food-details/173944/nutrients) | 89 | 1.09 | 0.33 | 22.84 | 2.6 | 生的可食用部分，不含皮 |

另有一个项目自定义“未明确的混合食物”，来源、食物组、生熟及5项营养均明确未知；它不是USDA记录。早期搜索结果里的其他食物没有纳入目录。

## 处理与核验

[运行资料](../../services/api/senplate_api/data/food_references.json)保留来源ID、原文、状态、每100g单位、读取日期及源hash。归一化按nutrient.id匹配：1008能量、1003蛋白、1004脂肪、1005碳水、1079纤维。4个文件hash和20个数值已经逐项与官方原始响应核对。

用Decimal按“本项克数 × 每100g参考 ÷ 100”换算，再在展示边界四舍五入到两位。示例200g米饭＋100g鸡肉＋150g西兰花，总450g，对应477.5kcal、39.97g蛋白、67.11g碳水、4.75g脂肪、5.75g纤维。单位／换算测试与跨端结果一致；这些数值只适用于所选参考假设。

每个份量保存当时参考快照，后续更换资料不重写历史。缺任何项目某营养值时，该整餐营养总量保持null，另显示已知项小计和覆盖克数；全未知时不显示0。食物选择错误可以留原因纠正，克数及旧参考保留审计。

## 解释限制

当前目录由人确认，不是视觉识别结果；做法、得率、含水量、品种及额外油盐会产生现实差异。总剩余350g不能说明每项吃了多少，因此不按比例减去营养，也不把100g总重差称为摄入或浪费。

学校200g谷物／100g蛋白类／150g蔬菜模板是便于验证三项操作的示范计划，标记illustrative_unreviewed；它不是USDA或香港学校营养指引，也不是给儿童的推荐克数。实际计划维护与审核留后续。相关软件验证见[本批QA](../../output/qa/development-m1-2-meals-2026-09-19/verification.md)。
