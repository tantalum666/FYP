# Group 2 Current Handoff

更新：2026-10-12后续。当前：**用户最终要求换回完整2D A1并去掉分割感；Web／独立设备页已接入，连续缩放、拖动和贴边收起可用。** 分块SVG、2.5D变形和3D衍生稿均已被否决。

## 当前实现与证据

- 用户入口：[Web](http://localhost:8832/)／[Linux目标布局](http://localhost:8832/?surface=device)，Mac回环服务PID89265，独立`.runtime/user-preview-20261012`。真实AI／后台AI未启用，未启动音视频／硬件代理；专用笔记仍需逐项本人批准。凭据只在聊天提供。
- [页面契约](desk-companion/docs/page-companion.md)：单张完整睁眼PNG，轻微整体刚性回应，无关节切块／局部变形／透视；滚轮／拖角／1%滑条连续缩放，三边半身／露头／隐藏与召回、偏好记忆、键盘／暂停／减少动态和弹窗暂避。
- [最终QA](output/qa/2026-10-12-a1-page-companion/verification.md)：28项前端测试、类型／构建、实际单图／零mask／零canvas、点击／缩放／贴边／刷新召回、面板保护与桌面／窄屏／设备布局。中间尝试另标superseded，Mac布局不等于Pi／Linux实机。
- [透明原图／实际prompt](design/desk-companion/characters/2026-10-12-a1-interface/README.md)保留，闭眼稿仅历史；[3D失败尝试](design/desk-companion/characters/2026-10-12-a1-3d/README.md)只存历史源工程及证据，新3D运行GLB／深度渲染已移除，原pixiv许可VRM入口保持。
- [九套服装包](output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)、[六视角／四细节](design/desk-companion/characters/2026-10-12-a1-turnaround-details/README.md)、学校与原主工作区保持。默认服装未选。沿既有`codex/full-body-3d-avatar`／[PR #4](https://github.com/tantalum666/FYP/pull/4)保存，不自动合并main。

## 剩余事项

当前二维反馈不是独立挥手／点头／行走，大动作需完整姿势帧。长期缺口仍按[17模块清单](planning/2026-10-12/software-function-inventory.md)：真实PC执行、长期记忆／作业归档、真实语音／真人姿态、Pi／iPhone／光学／机械验证。被否决3D稿不算原创模型完成，学校提交状态本轮未核实。

## 唯一下一步

**用户刷新两个测试入口，以完整2D为基线检查原画完整性、大小及收起行为并反馈具体问题。** 后续大动作先制作和审阅完整姿势帧，不继续当前被否决3D路线。
