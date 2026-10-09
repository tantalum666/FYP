# Group 2 Current Handoff

更新：2026-10-10。当前任务：**角色美术研究已本地完成，原创概念／最终角色未定；研究沿功能分支 `codex/full-body-3d-avatar`／[PR #4](https://github.com/tantalum666/FYP/pull/4)整理，待本轮推送读回。** main仍为已完成的Dot整合。

## 当前结果

用户要求先研究目前受欢迎的二次元角色，为现有女性全身3D伙伴做美术优化。[研究与方向](research/2026-10-10-avatar-art/popular-character-study.md)区分近期季度社区投票、2026公布的2025年度结果和官方视觉参照；[8项图文参考板](research/2026-10-10-avatar-art/reference-board.html)可切浅／深背景，[来源与访问范围](research/2026-10-10-avatar-art/source-register.json)保留。工程建议先比较A“银雾·柔科技”和B“墨青·都市伙伴”，A优先；C“暖金·开朗日常”为对照。它们目前只有原创文字简报／色板，未生成角色图、未选定造型或品牌。

既有VRM功能、许可样本和应用代码保持：全身骨骼状态动作、眨眼、播放音量开口、本地预览／替换、英简、纯黑／镜像与常亮集成。[角色契约](desk-companion/docs/avatar.md)仍限制音量口型、同源浏览器桥及物理光学；默认真实语音未配置。

## 证据与入口

[本轮QA](output/qa/2026-10-09-avatar-art-research/verification.md)记录128份Markdown／12,096行／48块全读、截断补读、来源、8图加载／浅深背景／无横向溢出，以及应用／模型／学校文件保留。任务10月9日开始、10日收尾，QA目录沿用任务起始日。没有应用或学校文件变更，不重跑之前通过的软件套件／DOCX渲染。

软件验证仍见[3D角色QA](output/qa/2026-10-09-3d-avatar/verification.md)的22前端／26定向后端及实际浏览器检查；Dot基线149后端／15前端见[整合QA](output/qa/2026-10-09-dot-integration/verification.md)。这些不是本轮新跑或Pi／自然语音成绩。

主预览：[管理](http://127.0.0.1:5190/)／[3D角色](http://127.0.0.1:5190/?surface=avatar)／[常亮](http://127.0.0.1:5190/?surface=device)，API8831；私有凭据仍在忽略的`.runtime`。研究参考板有[临时本地预览](http://127.0.0.1:5192/research/2026-10-10-avatar-art/reference-board.html)，仅loopback且限制到本轮研究／QA目录，不是公网部署。原七条日程不操作；学校／身份／旧工程107项保护文件保持。

## 未完成

原创全身／脸部／表情概念与最终VRM、逐音素唇形、跨设备／Python音量桥、真实语音／AEC／费用、Pi／iPhone原生3D性能与光学效果仍需完成或实测。通用PC／LCU、长期记忆管理、作业归档／备份、真人姿态、RIG／清洁模块与物理停止继续保留，不因美术研究取消。未采购、开收费服务、改权限、发邀请、提交学校或自动合并新视觉功能。

## 唯一下一步

**按A/B简报制作同一构图、光照与尺寸的原创全身和脸部／表情概念对照，再决定具体3D美术。** 本轮研究不等于用户已选A；后续模型复杂度仍须目标Pi并发实测后确定。
