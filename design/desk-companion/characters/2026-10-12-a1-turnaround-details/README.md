# A1 · 六个全身视角与四张细节图

Group 2 · 2026-10-12。**A1角色身份已确定；九套服装已单独保存；本轮十张二维参考图完成并逐张检查。**

用户要求先保存服装，再制作全方位形象图与细节图。[九套服装原图包](../../../../output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)含九张原PNG、九份实际prompt、原V4身份参考及索引，21项逐字节读回一致。原素材目录和历史版本保留。

[十图并排预览](review-board.html)／[工作规范](../a1-turnaround-spec.md)／[A1简报](../a1-character-brief.md)／[九套服装索引](../a1-wardrobe-index.md)／[本轮QA](../../../../output/qa/2026-10-12-a1-turnaround-details/verification.md)。预览点击任一图可看完整原PNG，由共享Creative Production renderer生成，无派生拼图。

## 本轮工作参考

沿用[A1 Anime V4](../2026-10-10-concepts/a1-silver-mist-anime-v4.png)原服装，以一致衣物研究视角和结构；这是工程参考选择，**用户未选定九套中的默认服装，也未把原服装定为最终款**。保留约25岁成年脸型、银灰侧分长发、灰蓝眼、开环发扣及既有性格。

左右均按人物自身区分。发扣固定在她的左侧：正面出现在画面右，背面在画面左；右侧面会被头发／头部自然遮住。全身站姿改为平衡、手臂小幅离身的中性参考，便于看结构。

## 六个全身视角

| 编号 | 原图 | 实际提示词 | 观察 |
|---|---|---|---|
| A1-T01 | [正面全身](a1-t01-front.png) | [prompt](prompts/a1-t01-front.txt) | 平衡站姿，完整头／双手／双靴；手臂分离幅度低于目标15度 |
| A1-T02 | [人物左侧面](a1-t02-left.png) | [prompt](prompts/a1-t02-left.txt) | 鼻子朝画面左，近侧发扣正确；远侧手自然遮挡 |
| A1-T03 | [背面全身](a1-t03-back.png) | [prompt](prompts/a1-t03-back.txt) | 无回头，完整头手鞋；后发、外套背缝和裙后片为新增推演 |
| A1-T04 | [人物右侧面](a1-t04-right.png) | [prompt](prompts/a1-t04-right.txt) | 鼻子朝画面右，左发扣在远侧；远侧手／部分鞋自然遮挡 |
| A1-T05 | [前斜视](a1-t05-front-three-quarter.png) | [prompt](prompts/a1-t05-front-three-quarter.txt) | 完整头手鞋；角度比四分之三目标浅，脸较接近正面 |
| A1-T06 | [后斜视](a1-t06-back-three-quarter.png) | [第二次实际prompt](a1-t06-back-three-quarter.attempt2.actual-prompt.txt) | 头身同向朝远处，无眼口；角度比45度目标浅，较接近正背面 |

六张均为1024×1536原生PNG。T05／T06按实际标为斜视，不宣称精确45度；侧视允许远侧肢体自然重叠，不能声称每个视角都能分别检查双手。

## 四张细节图

| 编号 | 原图 | 实际提示词 | 尺寸与观察 |
|---|---|---|---|
| A1-D01 | [脸部与发扣](a1-d01-face.png) | [prompt](prompts/a1-d01-face.txt) | 1254×1254；完整头顶、灰蓝眼、鼻口、左侧发扣和耳钉清楚 |
| A1-D02 | [后发及发扣侧后](a1-d02-hair-back.png) | [prompt](prompts/a1-d02-hair-back.txt) | 1024×1536；完整发尾，取景延伸至上裙和袖部；后背缝比全身更明确 |
| A1-D03 | [上衣、腰带与叠裙](a1-d03-outfit.png) | [prompt](prompts/a1-d03-outfit.txt) | 1024×1536；头部按用途排除，近正面构图；袖口、五金和裙层清楚 |
| A1-D04 | [短靴与裤袜材质](a1-d04-boots-tights.png) | [prompt](prompts/a1-d04-boots-tights.txt) | 1254×1254；两靴完整，带扣／鞋底／方跟清楚；鞋头分片与高光较原稿更明确 |

细节图按指定区域取景，不是裁切全身原图，头／躯干不入镜不代表缺图。十张均由内置ImageGen独立生成，协调代理实际逐张查看。

## 依赖、来源与限制

先生成并查看T01，再以T01＋原V4制作T02–T05；查看T03后才以T03＋原V4制作T06／D02。D01／D03／D04直接从原V4制作。[manifest](manifest.json)记录原生路径、尺寸、输入／输出hash、完整实际prompt和逐图观察；[生成任务](generation-jobs.json)保留初始计划，各receipt保留实际执行。

共11次原生调用，保留十张成稿。T06[首稿](a1-t06-back-three-quarter.attempt1-rejected.png)因回头、头身方向不一致，由工作代理检查后拒绝；[首稿receipt](a1-t06-back-three-quarter.attempt1-rejected.receipt.json)和[初始prompt](prompts/a1-t06-back-three-quarter.txt)保留，第二次追加头身同向的明确指令后完成。其他九张首次成功，没有重做已合格图。所有原生PNG与项目副本逐字节一致，无裁切、缩放、拼图或像素后期。

原V4没有完整背面。本轮后发流向／长度、外套简单后缝、裹裙后片和部分鞋侧结构属于**新增设计提案**。跨视角的大轮廓已核对，发束、衣褶和五金的细微差异仍需后续统一；这些图不共享已测量的三维几何，不是建模正交工程图、原创VRM或已绑定服装。原服装及九套变体、E1、C1、学校文件与运行许可模型保持。

当前下一步：依据本套视角统一A1的发束、后背衣缝和裹裙结构，整理可制作参考；默认服装选择及E1精修保留为独立后续事项。
