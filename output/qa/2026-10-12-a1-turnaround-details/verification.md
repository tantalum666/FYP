# Group 2 · A1全方位与细节 QA

2026-10-12，Asia/Hong_Kong。同一美术任务补充：先保存九套服装，再完成A1全方位与细节。

## 阅读与路由

继承[首轮139份／12,884行全文](../2026-10-12-wardrobe-variants/reading-record.json)及[上一阶段收尾补读](../2026-10-12-a1-wardrobe-round2/closeout-reading.json)。[本轮记录](reading-record.json)开工盘点142份，补读入口／角色聚焦资料与最新决定。压缩恢复补读AGENTS、product、handoff、当前规范／修改源文件和有关决定，没有机械重启全库全文。收尾新增视图规范／素材README，最终144份自有Markdown；实际修改范围和读回见[updated-markdown](updated-markdown.json)、[closeout-reading](closeout-reading.json)。

ImageGen及Creative Production技能沿本任务继续，补读shots／source-preservation规则。复用三名限定图像代理，无新增句柄；终态已消费并用interrupt确认，工具没有销毁句柄接口，不冒称销毁。仅嵌套画板工具可见而技能禁止该路径，未挂载原生画板；使用共享renderer静态预览，见[工具记录](tool-route.json)。

## 先保存服装

[九套原图包](../../../output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)含九PNG、九实际prompt、原V4身份参考、index.json、README.md，共21项。CRC、每项原字节及hash读回一致，[保存记录](wardrobe-preservation.json)保留来源；原素材目录不覆盖。默认服装未选，原V4衣服仅为本轮一致工作参考。

## 十图来源与实际查看

[六全身＋四细节](../../../design/desk-companion/characters/2026-10-12-a1-turnaround-details/README.md)全部逐张view_image实际检查。[image-validation](image-validation.json)与[manifest](../../../design/desk-companion/characters/2026-10-12-a1-turnaround-details/manifest.json)核对十张原生／项目字节、IHDR尺寸、实际prompt与初始prompt、参考hash和依赖；T06第二次实际提示词没有误记成初始计划。

- 六全身、D02／D03为1024×1536；D01／D04为1254×1254，接受原生尺寸。
- 11次内置ImageGen，T06首稿头身方向不一致由工作代理拒绝，追加明确指令重试一次。拒绝图／receipt／初始prompt均保留，其他九张首次成功；协调代理只声称实际查看十张最终图，没有声称查看拒绝稿。
- T01检查后才用于侧背面，T03检查后才用于T06／D02。发扣固定人物自身左侧；左右侧面远侧肢体自然遮挡，不称各图双手皆可分别检查。
- T05／T06实际斜视较浅，不称精确45度；后发／外套后缝／裙后片为新设计提案。D02／D03取景略宽，D04鞋头分片／光泽增强，均记录。
- 原生PNG未裁切、缩放、拼图、重绘或像素后期；二维图不是共用精确三维几何、原创VRM或已绑定衣服。

共享Creative Production renderer的image-wall预览使用明确单图清单，不生成contact sheet。[实际浏览器检查](preview-verification.json)十图全部加载，676像素面板三列、无水平溢出，完整截图已查看；图与标题／原图链接对应，输出标签页已保留。

## 收尾与保留

22份当前规范／路由更新：product、两README、avatar契约、A1简报／表情／服装／视图规范、六资产README、五研究入口、decision-log、handoff和work-log。历史研究保留原日期与来源，当前顺序以保存服装后制作视图为准；唯一下一步为统一发束／后背衣缝／裹裙的可制作参考。

[最终检查](final-validation.json)核对71项旧保护文件、服装归档hash／CRC／成员字节、内部链接、组号／成员资料、交付物存在性、保留的四条性格规则及空白检查。旧A1／B1／C1／E1和服装原PNG／prompt／manifest、学校文件与许可VRM保持；本轮没有应用源码变化，不重复旧应用套件或学校DOCX／PDF渲染，没有Git写入或硬件／语音／学校提交动作。
