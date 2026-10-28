# HISTORICAL — A1 custom head rejected; work stopped

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**HISTORICAL · 人物源与比较**。当前常驻已选 AliceChan；本页旧选择／精修下一步不再自动执行。原画、服装、失败源及各自许可保留。 [新聊天入口](../../../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

Group 2 · 2026-10-18。用户用新的实际截图明确否决这套头部，要求停止自行做3D人物，改用开放完整模型换装／捏脸。本目录只保留失败源与证据，**停止继续打磨或当作当前候选**。当前路线见完整模型改装 (local historical material: `design/desk-companion/characters/2026-10-18-existing-model-adaptation/README.md`; not included in this checkpoint)。旧v3／Galaxy否决继续有效。

## 实际产物与查看

- Blender 可编辑源 (local historical material: `design/desk-companion/characters/2026-10-18-a1-head-study/a1-head-study.blend`; not included in this checkpoint)：默认场景 `A1_Head_Study`，真实脸、独立眼球、牙／舌、曲面发束、发夹与头部支点，贴图已打包。原 CC0 Anna 进口场景保留来源结构。
- 历史GLB (local historical material: `design/desk-companion/characters/2026-10-18-a1-head-study/a1-head-study.glb`; not included in this checkpoint)／否决来源记录 (local historical material: `design/desk-companion/characters/2026-10-18-a1-head-study/source.json`; not included in this checkpoint)：保留失败头部与基本面部形变；没有完整身体骨架、衣服或发骨物理。
- 本机[已否决历史页](http://localhost:8832/?surface=head-history&lang=zh)：保留旧头部多角度／表情和原画对照，明确标为已否决。原`?surface=head`现进入完整模型页。
- 实际 QA (local historical material: `output/qa/2026-10-18-a1-likeness-motion/head-study/verification.md`; not included in this checkpoint)：原生与网页截图、失败试验、模型校验、浏览器事件及保存核查。

本历史页在工作空间Provider之前独立挂载，无需登录／语音。当前`?surface=avatar`和常驻层已切换完整模型；本头部没有接入完整人物，旧全身文件也保留历史。

## 本轮还原方法与改动

以 A1 原画为检查基准：先校准头部姿态和取景，比较眉眼、鼻、嘴、下巴，再检查正面／30°／侧面。`reference-landmarks.json` 是人工近似取点，`reference-fit.json` 仅用于姿态／取景，残差**不是相似度分数**，不能反推原画真实摄影机。

从经过许可和拓扑检查的 CC0 半脸提取真实表面，镜像并焊接中线，保留形变。调整眼睑倾向、鼻梁／嘴位置、下颌宽度、下巴与额头；统一细分 Basis 和每个形变，避免顶点顺序错位。眼睛使用单独灰蓝虹膜。新发束由手工布置的曲线引导曲面形成，重排侧分、遮眉刘海、鬓发、后发与波浪，减少重复细束；没有复用被否决 v3 的头发几何。

原生 ImageGen 制作面部／虹膜／发束材质，二次面部和头发贴图改为更清楚的卡通线条与大明暗层次。前投影只作为绘制坐标；随后在 Blender 解出独立 `A1_SurfaceUV`，把连续正面／侧面肤色烘焙为 albedo (local historical material: `design/desk-companion/characters/2026-10-18-a1-head-study/textures/a1-face-albedo.png`; not included in this checkpoint)，消除脸／耳的硬材质接缝及投影重叠。网页另处理卡通色阶、细面部轮廓、金属高光与闭眼线条。继承底模的闭眼几何已遮住眼球，但原睁眼贴图会拉成黑块，因此闭眼时淡出该区域并画细眼睑线；这是网页材质修正，不是新的人体实测或完整身体绑定。

**已撤回的试验：**直接把原画颜色投到整个脸上，会在侧面复制下颌线，不能作为还原捷径。`build_head.py` 内对应块明确禁用；原生失败截图 (local historical material: `output/qa/2026-10-18-a1-likeness-motion/head-study/pass6-failed-projection`; not included in this checkpoint)保留。`a1-head-pass1.*`、`a1-head-pre-likeness.*`、早期贴图只作历史，不由保留状态推断美术合格。

## 来源与再现

[Anna 原始来源与内嵌许可](base-source.json)固定 ToxSam/open-source-avatars 目录 commit `0f9a1b2fd99894736563d55b2c9dc9125700d081`、100avatars-r3 / Anna1.1。原 VRM SHA256 `8694d2a0c09014524d5bc7fdf870f55b6efb8dbd5b399d91bde353b779502779`；目录和内嵌条款均声明 CC0、允许改作／再分发。只取脸、眼、牙舌、颈部构件，不采用其整个人物身份。新几何与贴图是 AI 辅助改作，不能称全部学生手工作品；未使用米哈游游戏角色文件。

以下命令仅为历史失败试验的复现说明，不再是当前制作路线。用户已要求停止继续制作本头部。

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --disable-autoexec --python design/desk-companion/characters/2026-10-18-a1-head-study/prepare_base.py
/Applications/Blender.app/Contents/MacOS/Blender -b --disable-autoexec --python design/desk-companion/characters/2026-10-18-a1-head-study/build_head.py
/Applications/Blender.app/Contents/MacOS/Blender -b --disable-autoexec --python design/desk-companion/characters/2026-10-18-a1-head-study/fit_reference.py
/Applications/Blender.app/Contents/MacOS/Blender -b --disable-autoexec --python design/desk-companion/characters/2026-10-18-a1-head-study/render_reference.py
```

实际使用 Blender5.1.2。准备脚本仅能在后台运行；缺少缓存时从固定公开 URL 下载并核 SHA，导入到被忽略的 `.runtime`。不会打开或覆盖 GUI 中已有工程。构建会重建本目录当前派生文件与 QA 原生视图，请先另存需要保留的手工修改。网页副本在 `desk-companion/frontend/public/companion/`；完成复制后需运行前端构建。

所有五次原生 ImageGen 的完整提示词、输入角色和输出路径见 [imagegen-prompts.json](imagegen-prompts.json)。没有使用 CLI/API fallback 或本轮新的 Qwen 付费会话。

## 尚未完成

A1 的眼神与成熟气质仍有差距；发根汇合、发束连接、发夹露出、耳廓和局部线条还不够精细。现在的基本领口只是头部衬底，不是服装选择。头部外形达标后才接身体及最小互动集；Pi／Linux 负载、真实声音口型和硬件不在此次美术检查内。

**制作已停止。下一步采用完整现成模型及其原生换装／捏脸流程，不继续本目录的头／发雕形。**
