# Group 2 Current Handoff

更新：2026-10-10。当前任务：**用户已同意A/B继续设计，服装研究与四套文字简报完成；最终角色／服装尚未定稿。** 当前分支`codex/full-body-3d-avatar`／[PR #4](https://github.com/tantalum666/FYP/pull/4)，本次补充沿此协作分支保存；main保持Dot整合。

## 当前结果

[服装研究](research/2026-10-10-avatar-art/wardrobe-study.md)与[服装参考板](research/2026-10-10-avatar-art/wardrobe-reference-board.html)纳入用户的丝袜和轻微性感偏好。A1短外套短裙半透黑丝／B1都市剪裁哑光黑丝为首组建议，A2肩颈烟灰丝／B2非对称短裙为对照。四套为成年原创角色文字简报，约25岁是工程美术建议；具体脸、服装、名字、色板和最终模型未选定，也未生成新概念图。A/B已同意推进，C保留历史、暂不推进。

实际检查2B、卡芙卡、申鹤及授权礼服商品图；[来源表](research/2026-10-10-avatar-art/wardrobe-source-register.json)区分官方／授权图、D数指南与美术推断。没有把角色受欢迎归因于丝袜，也不把D数映射为模型透明度。首轮[人气研究](research/2026-10-10-avatar-art/popular-character-study.md)及[旧参考板](research/2026-10-10-avatar-art/reference-board.html)已补当前路由。

现有pixiv样本与应用代码保持：骨骼动作、眨眼、音量口型、局部替换、英简、黑底／镜像与常亮集成。[角色契约](desk-companion/docs/avatar.md)仍限制同源浏览器音量桥与物理显示；默认真实语音未配置。

## 证据与入口

[本次QA](output/qa/2026-10-10-avatar-wardrobe/verification.md)记录继承上一美术任务128份／12,096行全读、129份当前盘点及受影响文件补读、四张图实际加载、浅深切换和原资产／代码／学校文件保留。无代码／学校正文变化，不重跑旧应用套件或DOCX渲染。

软件证据仍见[3D角色QA](output/qa/2026-10-09-3d-avatar/verification.md)22前端／26定向后端，以及[Dot整合QA](output/qa/2026-10-09-dot-integration/verification.md)149后端／15前端。它们不是这次新跑或Pi／自然语音成绩。

主预览：[管理](http://127.0.0.1:5190/)／[3D角色](http://127.0.0.1:5190/?surface=avatar)／[常亮](http://127.0.0.1:5190/?surface=device)，API8831；凭据留在忽略的`.runtime`。服装板有[本地预览](http://127.0.0.1:5192/research/2026-10-10-avatar-art/wardrobe-reference-board.html)，复用仅loopback且限制到原美术研究／QA目录的临时服务器；未发布公网。原七条日程不操作，107项保护文件保持。

## 未完成

原创概念／最终VRM与衣服、逐音素口型、跨设备／Python声音桥、真实语音／AEC／费用、Pi／iPhone原生并发与物理光学仍待完成或实测。PC／LCU、长期记忆、作业归档／备份、真人姿态、RIG／清洁与物理停止继续保留。未采购、消费模型、变更权限、联系他人、提交学校或自动合并main。

## 唯一下一步

**按服装研究制作A1/B1同一构图、站姿、光照与尺寸的原创全身和脸部概念。** A/B方向无需重复确认；具体服装和角色还需看实际概念。模型复杂度与衣物动画随后在目标Pi及真实骨骼中验证。
