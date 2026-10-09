# Group 2 Current Handoff

更新：2026-10-10。当前任务：**A1/B1两张首轮全身概念已生成并实际检查，待用户审阅／选择。** 当前分支`codex/full-body-3d-avatar`／[PR #4](https://github.com/tantalum666/FYP/pull/4)；概念提交`3cd7976`已推送并读回，PR保持open；main保持Dot整合。

## 当前产物

用户在同意A/B与丝袜／适度性感服装后明确要求生成。当前[A1银雾／B1墨青](research/2026-10-10-avatar-art/character-concepts.md)各1024×1536、内置ImageGen一次调用。两图成年女性、单人全身，原PNG逐字节保留；[原图、实际提示词、来源与SHA](design/desk-companion/characters/2026-10-10-concepts/README.md)均在仓库。无IP参考图输入、CLI/API回退、像素后期或重生成。

A1为银灰长发、象牙白外套、叠片短裙与黑丝；B1为深色肩长发、灰青外套、结构短裤与黑丝。实际更偏半写实3D，顶部／底部留白紧，A1鞋跟较高、B1短裤较短且暖色小点缀不明显。两者未由用户选择；A2/B2、三视图、表情表与VRM未制作。参考／[服装研究](research/2026-10-10-avatar-art/wardrobe-study.md)已补当前路由，C仍保留历史。

现有pixiv样本与应用代码保持；[角色契约](desk-companion/docs/avatar.md)的音量口型、同源桥、固定姿态和工具确认边界不变。PNG概念不是可运行3D资产，真实语音仍未配置。

## 证据与入口

[本次QA](output/qa/2026-10-10-character-concepts/verification.md)记录同一美术任务的阅读继承／补读、两项生成、实际画面／参数偏离、PNG尺寸／hash、107保护项和原模型／代码保持。Creative Production技能要求两图委派，已完成并消费两个结果；当前只暴露嵌套板工具且技能禁止转发，因此未挂载rich board，直接交付原图。无新应用／学校文档变化，不重复旧套件／DOCX渲染。

软件证据仍为[3D QA](output/qa/2026-10-09-3d-avatar/verification.md)22前端／26定向后端与[Dot QA](output/qa/2026-10-09-dot-integration/verification.md)149后端／15前端，不是本次新成绩。主[管理](http://127.0.0.1:5190/)／[3D角色](http://127.0.0.1:5190/?surface=avatar)／[常亮](http://127.0.0.1:5190/?surface=device)与API8831保持；原七条日程不操作，凭据在忽略的`.runtime`。原服装参考板5192仅loopback预览，未扩大服务目录或发布公网。

## 未完成

最终角色／风格、三视图／表情、可运行VRM／衣物、逐音素口型、跨设备／Python声音桥、真实语音／AEC／费用、Pi／iPhone与光学效果仍待完成或实测。PC／LCU、长期记忆、作业归档／备份、真人姿态、RIG／清洁与物理停止继续保留；未采购、消费语音、改权限、对外联系、提交学校或自动合并main。

## 唯一下一步

**依据用户对A1/B1方向与半写实程度的反馈做一次定向精修，再补选定角色的三视图／表情。** 生成授权已经完成，不重复要求确认已同意的A/B方向；未经选择不把任何一张设为正式角色或默认应用模型。
