# Group 2 Current Handoff

更新：2026-10-09。状态：**全身女性二次元3D角色已在本地实现并验证；[PR #4](https://github.com/tantalum666/FYP/pull/4)／功能分支 `codex/full-body-3d-avatar`已推送，main仍为已完成的Dot整合**。

## 当前结果

用户要求类似Razer AVA的全身3D形象，并选择先用二次元女性角色。以可替换VRM升级原SVG：骨骼状态动作、眨眼、实际播放音量驱动开口、本地动作／合成元音预览、文件替换、英／简、纯黑与只镜像角色输出。常亮页保留大时间、近期日程及姿态状态，助理增加独立角色入口。正式角色美术未定；pixiv官方样本、固定来源／SHA／版权／完整许可和嵌入设置已保留。

[角色契约](desk-companion/docs/avatar.md)区分浏览器显示与物理光学、音量开合与逐音素唇形、同源标签页桥与跨设备声音。默认语音服务仍未配置；没有新增收费调用或硬件动作。

## 验证与入口

[本轮QA](output/qa/2026-10-09-3d-avatar/verification.md)：22项前端、26项定向后端语音／工具回归、TypeScript／Vite、npm审计，以及真实浏览器模型加载、动作／口型复位、暂停、镜像、简中390×844、1280×800独立角色、1024×600常亮、文件拒绝／替换和WebGL丢失后重试。模型渲染单独懒加载；上游Clock弃用提示、较大按需chunk及原Starlette测试提示有记录，未隐藏。

主预览仍在[管理界面](http://127.0.0.1:5190/)／[全身3D角色](http://127.0.0.1:5190/?surface=avatar)／[常亮页](http://127.0.0.1:5190/?surface=device)，API8831。原owner凭据留在忽略的`desk-companion/.runtime/credentials.json`。原7条日程与107项学校／身份／旧工程保护文件不变；QA使用独立虚构工作区，不改主偏好；QA8833／5191与测试标签已关闭，临时浏览器覆盖／拦截已清除，主预览保留。

[本轮全文阅读](output/qa/2026-10-09-3d-avatar/reading-record.json)覆盖修改前127份项目Markdown／11,994行，47块与截断补读，压缩继续同一记录。产品、两个README、架构／操作／设备规范、第三方声明、决定与日志已同步。学校Proposal／logsheet未改或提交。

此前Dot整合已通过[PR #2](https://github.com/tantalum666/FYP/pull/2)及[PR #3](https://github.com/tantalum666/FYP/pull/3)合入main，软件基线149后端／15前端和[当轮证据](output/qa/2026-10-09-dot-integration/verification.md)保留；本轮26项不能冒称重跑149项。

## 未完成

正式角色美术、逐音素口型、跨设备／Python语音输出桥、真实自然语音／AEC／费用、Pi／iPhone原生3D性能及物理显示效果仍需验证。通用PC／LCU、长期记忆管理、作业归档／备份、真人姿态标签、RIG／清洁模块与物理停止仍按原契约待接入。没有采购、系统权限变更、收费模型、成员邀请、学校提交或自动合并本轮新视觉功能。

## 唯一下一步

**在目标Pi5上运行这版角色与姿态／音频并发，记录帧率、内存和温度，据实决定模型复杂度与渲染尺度。** 无实机时不能把30帧调度目标写成Pi成绩。
