# A1：GitHub 对照与局部精修依据

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**HISTORICAL · 人物源与比较**。当前常驻已选 AliceChan；本页旧选择／精修下一步不再自动执行。原画、服装、失败源及各自许可保留。 [新聊天入口](../../../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

**HISTORICAL 研究：**用户随后连同自制头部一起否决了自行建模路线，当前采用完整现成模型 (local historical material: `design/desk-companion/characters/2026-10-18-existing-model-adaptation/README.md`; not included in this checkpoint)保留原绑定与材质，进行原生换装／捏脸。下文“另做头部”目标和部件拼合建议已经被取代。

Group 2 · 2026-10-18。同一制作任务的补充。用户反馈“比上一版好很多，但还是差点意思”，允许继续精细化调整或比较更多 GitHub 项目。该反馈没有明确恢复先前被否决的 v3；本轮对照现成项目和素材，不重新发布该试稿。

**随后用户明确否决Galaxy-Chan，要求原神／铁道式人物质量并缩减动作范围。**当前以[精致卡通角色与最小互动规范](toon-quality-scope.md)为准；下文Galaxy源检查与18图比较页是该反馈之前的历史证据，不再作为人物基础建议。

## 结论

**继续保留 A1 原画身份与此前 Reira 卷发候选，采用合适的面部源、卡通材质与独立的表情／骨骼动画流程。没有找到可以直接换上、只改颜色就合格的免费 A1 整模。**

本轮核查 12 个仓库的固定版本、文件目录与聚焦文档／源码，不声称全量审计这些第三方仓库。实际使用 Character Studio 在线创建入口查看 Anata Female；索引 ToxSam 三批共 300 条目录记录，挑选并查看 12 项原始预览；另从创作者原页下载 Galaxy-Chan 的 Blender 源并实际渲染三个头部角度。仓库首页、宣传图、实际文件和运行效果分别记录。

本地比较页在 `http://127.0.0.1:8842/`，只绑定本机。HTML、原始预览和个人参考源保存在被 Git 忽略的 `desk-companion/.runtime/asset-screening-20261018/`；不会作为正式应用资源自动发布。原服务 localhost:8832 未替换模型。

## 最有用的项目

| 项目 | 实际核查与判断 | 对 A1 的用途 |
|---|---|---|
| [pixiv/three-vrm](https://github.com/pixiv/three-vrm) | 官方 VRM/Three.js 实现，代码 MIT；支持 MToon、表情和 SpringBone。工具许可不覆盖任意导入人物。 | **优先参考的网页角色运行层**。保留卡通材质和头发骨骼的语义，避免将完整 VRM 直接降为普通 PBR 外观。材质不能补救错误脸型。尚未替换现有 renderer。 |
| [moeru-ai/airi](https://github.com/moeru-ai/airi) | 固定版本的 display-models.ts 明列默认 VRM 为 AvatarSample_A/B；表情源码处理平滑过渡、口型与情绪的嘴部写入权、眼部表情冲突和回零。实际网页被服务配置引导挡住，未配置服务，未声称完成在线 3D 动态验收。 | **表情／视线／口型的组织参考**。它没有提供更接近 A1 的现成成熟脸。不能将默认样本当原创模型。 |
| [SanHsien/voxavatar](https://github.com/SanHsien/voxavatar) | 代码 MIT，Windows-only；素材清单独立列出官方样本与动作来源。核读动画加载／过渡实现及 manifest，另核读 Sachi、rerofumi 作者 CC0 页面。没有在本机运行 Windows 程序或评定动作自然度。 | **动作切换与可追溯 VRMA 候选**。13 段随库动作是后续待实播候选，不继承项目自评的分数或质量结论。Linux 不采用其 Windows 音频执行层。 |
| [saturday06/VRM-Addon-for-Blender](https://github.com/saturday06/VRM-Addon-for-Blender) | 官方仓库说明支持 Blender 2.93–5.2，提供 VRM 导入／导出、MToon 和 VRMA 工作流。当前机器 Blender 为 5.1.2。此次只核查，不安装新插件。 | **可编辑源到网页 VRM 的工作流参考**。需要实际导出后检查眼睛／嘴、发骨、侧背和运行材质，不能以保存 .blend 代替。 |
| [PaoloESAN/gacha-setup](https://github.com/PaoloESAN/gacha-setup) | README 明确目标为标准 Blender 5.2+，代码 GPL-3.0；无游戏人物模型随库。实际看了作者的 HSR 面部绑定截图，其眼、鼻、轮廓为完整卡通光影参考；不是 A1 脸型模板。 | **面部阴影、描边、眼部层次的参考**。本机 5.1.2 不直接安装假设兼容，也不把游戏角色素材当免费替代品。 |
| [dillongoostudios/goo-engine](https://github.com/dillongoostudios/goo-engine) / [Blender-StellarToon](https://github.com/festivities/Blender-StellarToon) | Goo Engine 是为 Eevee/NPR 改动的 Blender 分支；StellarToon 明确为 Goo Engine 着色器，主要针对指定游戏数据。源码开放不附带人物使用权。 | **材质质量和动画法线参考**。不能假设 Blender 专用节点原样进入当前网页 GLB；网页需自己的相应材质实现和验证。当前不迁移整个应用／引擎。 |

## 实际看过后没有选的路线

- **[M3-org/CharacterStudio](https://github.com/M3-org/CharacterStudio)**：实际进入 Create Character → Anata Female，等待模型完成加载并查看。当前演示是带头盔／武器的游戏装扮、T 姿态；没有看见更合适的 A1 成熟脸或自然待机演示。代码和资源包分开；关联 [loot-assets](https://github.com/M3-org/loot-assets) 根目录没有足够的逐素材许可说明，不把程序 MIT 套到所有部件。适合作为换装、合并网格／纹理图集实现参考，暂不采用人物。
- **[ToxSam/open-source-avatars](https://github.com/ToxSam/open-source-avatars)**：修复了先前 R3 目录获取失败的研究缺口，三批目录各 100 项均成功读取。仅实际查看 Rose、Olivia、Erika、Lydia、Samuela、Kate、Jennifer、Aesthetica、Juanita、Agnes、Eugenia、Anna 的 12 个预览；不是看过 300 个模型。它们分别偏低多边形、卡通／幼态、怪物或幻想战斗角色，无一作为 A1 整模首选。三批作者集合明示 CC0，不扩展为其他社区集合统一许可。
- **[hrabanazviking/Hamr](https://github.com/hrabanazviking/Hamr)**：首页图是概念宣传，不能作为可编辑模型质量证据。固定版本的 builder 在 `src/hamr/core/builder.py` 下寻找 `core/scripts/build_avatar.py`，实际脚本位于 `src/hamr/scripts/build_avatar.py`；入口还引用没有在其参数／局部定义的 `force_over_budget`。没有运行或安装它，不认为“headless／Pi-ready”描述已经解决高质量人物制作。
- **[pixiv/ChatVRM](https://github.com/pixiv/ChatVRM)**：README 明确以 2024-07-18 代码归档；使用 three-vrm，随库为官方 AvatarSample_B。可读其原始网页 VRM 交互结构，不作为新的美术资产来源或当前语音协议替换。
- **[AMETHYST / DillonGoo](https://dillongoo.gumroad.com/l/amethyst-anime-rig)**：专业脸／身体 Rig、动画法线与裙子控制的公开质量参考。作者当前标价 US$50+，个人／教育用途许可不等于免费下载；未购买或下载。它的版权角色身份也不能冒充 A1。

## HISTORICAL — Galaxy-Chan实际文件检查，随后被用户否决

[Pierre Schiller 的创作者原页](https://3dcinetv.com/download-galaxy-chan-free-3d-rigged-anime-girl/)直接提供下载并声明 CC BY-NC-SA 4.0，满足用户这次允许的免费个人参考范围。原页称为 Blender 3.5；实际下载的 .blend 元数据为 **3.6.13**，本轮用 **5.1.2** 打开，自动脚本执行关闭，内嵌 `rig.001_ui.py` 未运行。

- 原 ZIP 15,683,483 字节，内有 48,820,650 字节 .blend；源文件只读保留，hash 和来源在本地 provenance.json。
- 实际包含 Rigify 完整控制骨架；头网格 1,447 个顶点、66 个形变项（包含 Basis），两眼各 64 项，含眨眼、视线、眉、嘴与情绪。**有形变项不等于每个形变都正确或已动态验收。**
- 在原生材质下隔离人物、使用静止骨架和中性灯光，渲染正面、30°、90°三个头部近景，逐张实际查看；没有改原网格、贴图或保存覆盖源。
- 5.1.2 导入出现一个 Mask 驱动警告和旧特效材质混合模式转换警告；渲染中另出现网格边修正警告。未把它称为干净导入、完整绑定验收或网页可直接用。
- 实际脸部仍偏简化、眼型偏圆，嘴在静止基形下微张，短发体积和色块不符合 A1。**用户随后明确否决，退出人物／脸部基底候选；不继续围绕它改作A1。**原文件与渲染只作历史检查记录。

本地三个原生渲染是源模型的检查结果，不是新 A1 成品，也不是网页运行截图。未改作、分发或集成该 NC 源；后续若使用派生内容，保留作者、许可和改动记录，并按其 ShareAlike 条件处理。

## 下一轮局部精修的明确目标

| 部位 | 相对 A1 原画的目标 | 局部检查方式 |
|---|---|---|
| 脸型与成熟感 | 下脸轮廓利落但不针尖；保留颧颊体积，避免圆大眼／短下脸的幼态组合；侧面鼻唇下颏连贯。 | 同一头部、固定正面／30°／侧面相机；同时比较中性、轻笑、眨眼与张口。原画为倾斜视角，不能将二维像素距离当精确三维测量。 |
| 眼神与嘴 | 较长的杏眼、上眼睑和细睫毛；灰蓝虹膜、克制眼白与高光；放松的嘴角，而非长时间大笑或闭眼回应点击。 | 切换表情时检查眼睛与嘴的写入是否争抢，最终回到中性；点击反馈用注意／短招手与眼神回应。 |
| 卷发 | 银灰略带紫、侧分、发根蓬松；主发束形成不同尺度的 S 波，中发束打破齐边，少量细束修边。保留开口圆环发夹与耳钉。 | Reira 仍是第一后发候选，Jessair 强卷备用；需取得实际可编辑文件后检查前／侧／背与头转动。粗发片直接扭曲不能代替这些层次。 |
| 材质 | 柔和分区卡通阴影、局部轮廓线、发丝高光随发束走向；避免整块白头发或全头均匀塑料反光。 | 在实际网页使用同一近景、背景与灯光对照；Blender 专用 NPR 结果单独标注。 |
| 动作（按最新范围） | 轻呼吸／眨眼、注意／聆听、说话和一个简短回应；有适量头发滞后。 | 在合格头部／身体上检查少量动作与回中性；走路、伸展和动作库不再作为必做。AIRI／VoxAvatar仅为设计参考，当前无新的动作验收。 |

以上是工程／美术建议，未新增默认服装或角色决定。一次只检查合格头部与发型，再接身体和最小互动，保留现有连续缩放、拖动、边缘收起和单一助理输入。

## 固定版本与证据

| 仓库 | 本轮读取版本 |
|---|---|
| moeru-ai/airi | `266e8d9467197f9562279d6291eddae758b11fe2` |
| pixiv/ChatVRM | `b542aa00e19dccf9fc48ba340cf7eee011d2329a` |
| SanHsien/voxavatar | `2a757396fe85b995630385794ad0b8c196a29b9f` |
| PaoloESAN/gacha-setup | `44ae755812d701f7d53369c4895deb1e9ece80f7` |
| hrabanazviking/Hamr | `bff479d49a82d7e845b48791a39a669273cf0af0` |
| dillongoostudios/goo-engine | `8457395892beec33d4605ef9d894a1aff4a8d79f` |
| saturday06/VRM-Addon-for-Blender | `2e91302e366a06091c891465ceda8c1deab98ff8` |
| M3-org/CharacterStudio | `293182bf4a6087f4a4a7fd00e4fbdfb590029da7` |
| M3-org/loot-assets | `24e2d470149e6a3235cb0cce9135bea4abafb1a3` |
| ToxSam/open-source-avatars | `0f9a1b2fd99894736563d55b2c9dc9125700d081` |
| festivities/Blender-StellarToon | `ac33b3f65a4470ecaadcd7c0af2e150636e8e40e` |
| pixiv/three-vrm | `68c7d6b1f73b79568f81139be62831968bff7876` |

QA (local historical material: `output/qa/2026-10-18-a1-likeness-motion/verification.md`; not included in this checkpoint)与 github-comparison-validation.json 记录目录、原始预览、Blender 检查和本地比较页的实际结果。没有新增应用代码、AI 付费会话、真实采集、Pi 测试、采购、外部联系、Git 发布或合并。
