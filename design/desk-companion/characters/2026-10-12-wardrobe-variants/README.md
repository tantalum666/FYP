# A1 V4 与 C1 V1 · 服装再设计六版

Group 2 · 2026-10-12。状态：**FIRST_ROUND_PRESERVED / A1_CHARACTER_SELECTED / OUTFIT_SELECTION_PENDING**。用户后续已确定A1为形象，C1转为历史参考；服装入口见[第二轮六套A1](../2026-10-12-a1-wardrobe-round2/README.md)及[A1九套总索引](../a1-wardrobe-index.md)。以下记录第一轮六图及当时建议。

用户要求为A1 V4与C1再设计几版服装，探索不同风格，不局限都市上班族。两位角色各完成三张独立全身图；脸、头发、眼睛、配饰、表情及站姿以各自原稿作连续性参考，服装、袜子和鞋型允许完整重设计。所有原稿及提示词保留。

[六版并排预览](review-board.html)为共享Creative Production renderer生成的静态检查页，点击图可打开完整原图；它不保存或代替用户选型。原生创意画板的直接工具入口本轮不可用，因此没有经禁止的嵌套路径挂载画板。

| 编号 | 方向与原图 | 实际轮廓 | 提示词 |
|---|---|---|---|
| A1-W1 | [柔科技机能](a1-w1-soft-tech.png) | 立领无袖机能裙、斜向裹片与分离袖；青灰滚边、小腰包、半透袜及短靴。 | [完整实际 prompt](prompts/a1-w1-soft-tech.txt) |
| A1-W2 | [轻户外](a1-w2-light-outdoor.png) | 浅沙色短风衣、工装短裤、不透明打底裤与越野运动鞋。 | [完整实际 prompt](prompts/a1-w2-light-outdoor.txt) |
| A1-W3 | [星旅轻奇幻](a1-w3-astral-fantasy.png) | 象牙白与暮蓝交叠裙、小披肩、垂片腰带、深灰袜及及膝靴。 | [完整实际 prompt](prompts/a1-w3-astral-fantasy.txt) |
| C1-W1 | [音乐舞台](c1-w1-music-stage.png) | 酒红／炭黑不对称舞台裙、单侧长袖、露肩、侧层片及及膝靴。 | [完整实际 prompt](prompts/c1-w1-music-stage.txt) |
| C1-W2 | [运动休闲](c1-w2-sport-casual.png) | 奶油白短运动外套、酒红短上衣、弧形边运动短裤、罗纹袜及运动鞋。 | [完整实际 prompt](prompts/c1-w2-sport-casual.txt) |
| C1-W3 | [现代和风](c1-w3-modern-wa.png) | 梅紫短羽织、米白交领内搭、青灰腰封、不对称褶裙、深灰袜及短靴。 | [完整实际 prompt](prompts/c1-w3-modern-wa.txt) |

## 视觉判断与差异

助手建议优先继续细化 **A1-W3星旅轻奇幻**和**C1-W3现代和风**：前者的披肩与蓝白交叠裙延续安静气质，后者用腰封、袖形与褶裙建立清楚身份。若偏日常常驻，可比较A1-W2与C1-W2。以上是本轮视觉判断，没有用户最终选型或人气／效果测量。

- **A1-W1：**分离袖长至上臂，扣件多于简报；鞋跟为适度方跟。
- **A1-W2：**衣摆出现短调节绳环；不影响服装结构。
- **A1-W3：**外层下摆及腰带垂片稍长，层次较简报复杂；靴子仍有小方跟。
- **C1-W1：**侧裙片较长，额外出现米白裙片；仍有材质渐变。
- **C1-W2：**短上衣留少量腰部，与完整运动穿搭协调；未见明显结构问题。
- **C1-W3：**右袖几何边饰比目标更宽，短靴跟高于很低跟目标。

六张均由协调代理使用view_image实际查看：单图单人、成年观感、头／双手／双鞋完整，衣物层次和结构可读，主要身份特征稳定。材质和背景仍有柔和渐变，不称严格两级赛璐璐或完全逐像素锁定脸部。没有发现需重生成的无效图，保留每张首次成功结果。

## 来源与保存

- A1三版唯一参考：[A1 Anime V4](../2026-10-10-concepts/a1-silver-mist-anime-v4.png)。
- C1三版唯一参考：[C1 Plum Dusk V1](../2026-10-10-c1-concept/c1-plum-dusk-v1.png)。
- 六次内置ImageGen编辑；三个限定图像工作代理各顺序生成两张。每张1024×1536、1次尝试；无第三方IP参考图输入、CLI/API回退、裁切、拼图、重绘或其他像素后期。
- [资产清单](manifest.json)保存精确输入／输出／prompt哈希与原生路径；各receipt保留工作代理的原始检查。原生与工作区PNG逐字节一致。
- [六份实际提示词](prompts/)及[生成任务](generation-jobs.json)保留；[本轮QA](../../../../output/qa/2026-10-12-wardrobe-variants/verification.md)记录全文恢复、工具边界与保存检查。

这是第一轮服装概念探索。当时未制作侧背面；当前另用原V4服装完成[A1六视角／四细节](../2026-10-12-a1-turnaround-details/README.md)。九套变体各自背部、原创VRM／衣物绑定仍待，学校文件与运行样本保持。

用户最新要求先保存服装再做角色视图，已完成[九套原图包](../../../../output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)及[A1视角／细节](../2026-10-12-a1-turnaround-details/README.md)；下一步统一角色可制作参考，服装选型和E1反馈保留。
