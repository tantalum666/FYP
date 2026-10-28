# Third-party visual assets

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**现行规范／入口**。已按本轮保存状态核对；最新软件、GitHub main 和 Pi 部署分开，Pi 暂停、旧 API 预算关闭。 [新聊天入口](../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

本应用没有使用旧 Senplate 标志，也没有把 ImageGen 图片当成可交互页面。图形图标来自 Lucide，字体本地打包，不请求第三方字体服务器。

- **Inter**：通过 `@fontsource-variable/inter` 5.3.0 分发，SIL Open Font License 1.1。保留 [Inter 许可原文](licenses/inter-OFL.txt)。OFL 允许使用、嵌入和随软件再分发，需保留许可；不把字体文件本身单独销售或宣称字体版权属于本组。
- **Lucide**：`lucide-react` 1.48.0，ISC；其中 Feather 派生部分附 MIT。保留 [Lucide 许可原文](licenses/lucide-LICENSE.txt)。

软件依赖的版本与供应来源见 `package-lock.json` 和 `uv.lock`；本文件针对直接分发的字体和图标，不代替每项依赖各自许可。

构建目录也包含 `public/licenses/` 分发的原文副本，随Vite打包到 `dist/licenses/`。

## 本轮软件、模型与公开数据

- React／React DOM／Capacitor：当前安装版本及精确依赖见`frontend/package-lock.json`，许可副本在`licenses/`。iOS框架取自Ionic官方8.5.2发布，校验值来自其官方Swift包；`scripts/prepare_ios.py`验证后引用，原压缩包不改写。
- FastAPI为MIT，httpx／websockets为BSD-3-Clause，cryptography为Apache-2.0或BSD-3-Clause；记录的是已安装包元数据，保留直接依赖许可副本。完整传递依赖仍以锁文件及各自发行包为准。
- icalendar为BSD-2-Clause；recurring-ical-events为LGPL-3.0-or-later，未修改其源码，作为独立Python依赖使用。保留[许可](licenses/recurring-ical-events-LICENSE.txt)与[对应上游源码](https://github.com/niccokunzmann/python-recurring-ical-events)。分发二进制包时仍需保留对应声明与可替换依赖结构。
- MediaPipe软件为Apache-2.0。姿态模型来自[官方Pose Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)，模型卡为[BlazePose GHUM 3D](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf)。来源与内容SHA固定在`config/models.json`。
- sherpa-onnx／core软件为Apache-2.0。唤醒权重来自[官方中英3M发布说明](https://k2-fsa.github.io/sherpa/onnx/kws/pretrained_models/index.html)，下载与各文件校验在`config/wake-model.json`。软件许可和权重／训练数据的声明不能混为一项；本工程保留下载来源，没有宣称训练数据或权重版权属于本组。
- 香港公众假期JSON来自[1823](https://www.1823.gov.hk/en/hong-kong-public-holidays-ical)，文件为2025–2027发布数据，保留英文及简体中文原文；不代表政府认可本项目。
- 天气读取[香港天文台开放数据](https://www.hko.gov.hk/en/abouthko/opendata_intro.htm)，保存观测及读取时间。没有把示例温度当成传感器或即时实测。
- 当前默认AliceChan按下述CC BY-SA4.0条款使用；历史A1工作稿使用已披露许可的3D样本改作，完整2D备用图来自此前项目原生ImageGen输出；旧SVG占位角色属于历史。未使用Razer／Metafoodx角色、品牌或产品图作为应用资产。原Senplate字体／品牌清查不替代当前项目的商业权利核查。

工程不包含账户秘密或原始个人音视频；姿态／唤醒权重通过固定来源校验下载。角色许可样本与已披露的改作随本分支分发。当前是学校原型的软件交付，不据这些说明声明全部商业发行手续已完成。

## 2026-10-22 selected AliceChan

Alice Chan (Uniform ver.), ©edisonlee55 (now yuna0x0), is distributed under **Creative Commons Attribution-ShareAlike4.0** from the [author’s release](https://github.com/yuna0x0/AliceChan/releases/tag/v1.0.4). [Full licence](frontend/public/avatars/alice/LICENSE.md), [source/SHA/changes](frontend/public/avatars/alice/source.json), and [unchanged original/reproduction](../design/desk-companion/characters/2026-10-22-alice/README.md) are retained. The release is v1.0.4, while the downloadable VRM0 is1.0.2. The runtime copy corrects three optional glTF skin-root references; its geometry/texture binary and all other model fields are identical. The compatibility copy is supplied under the same CC BY-SA4.0, with attribution in the UI and these bundled files. No creator endorsement or student-authored character claim is made. Future shared adaptations retain attribution/change notices and ShareAlike conditions.

The owner chose this complete character for initial use. Original appearance is the default; old Shino/Victoria assets below remain optional and keep their own licences. Private/reference-only candidates from the [GitHub screening](../design/desk-companion/characters/2026-10-21-ready-models/github-star-screening-20261022.md) are not bundled with Alice.

## 2026-10-18 complete-model runtime

The optional Shino and Victoria beta characters come from pixiv/VRoid Project under the original author's separate CC0 declarations: [Shino](https://vroid.pixiv.help/hc/en-us/articles/360013482714-Sendagaya-Shino), [Victoria/beta4](https://vroid.pixiv.help/hc/en-us/articles/360014900233). [Originals, runtime copies, SHA and embedded Hub settings](../design/desk-companion/characters/2026-10-18-existing-model-adaptation/source.json) are retained. The old beta names are not the modern restricted A–Z presets. Compatibility copies normalize normals and equivalent skin slots while preserving positions, topology, textures, expressions, skeleton and VRM metadata. Palette and bounded head scale are optional runtime presentation changes, not wholly original student characters or final A1 acceptance.

`@pixiv/three-vrm`3.5.5 and its matching pixiv modules use MIT; [licence copy](licenses/pixiv-three-vrm-LICENSE.txt) is also served in public/licenses. Native MToon/VRM permission is separate from application code and from future editable-source/outfit terms. VRoid2.14 native focus/input is restored; the separate current native adaptation is documented below. The assistant did not accept a legal agreement.

A separate original official AvatarSample_J `.vroid` was acquired for local authoring evaluation, under the [modern A-Z conditions](https://vroid.pixiv.help/hc/en-us/articles/4402394424089-VRoidPreset-A-Z), not CC0. [Source/permissions](../design/desk-companion/characters/2026-10-18-existing-model-adaptation/editable-source-j.json) retain its original hash. The original remains unchanged and is not a final A1 selection; a separately authored fixed-character VRM now has its own review page. It is not used to create a character-creation service. UnityPy1.25.4 (MIT) was installed only in an ignored authoring-tool environment to extract the licensed TextAsset; it is not an application dependency.

## HISTORICAL: 2026-10-19 rejected native A1 face/eyes/hair review

The rejected fixed character at`?surface=a1-history` is adapted in VRoid Studio2.14 from the complete official J source under the [A-Z conditions](https://vroid.pixiv.help/hc/en-us/articles/4402394424089-VRoidPreset-A-Z). It is not CC0 and has no face/hair-colour or body-proportion creation controls in the application. Source authoring remains in the native editor. The current plain high-neck native garment is temporary review clothing, not a chosen A1 outfit.

Hair uses **Wavy Hair V1 and Edited Bangs V1, Dahlia / Reira's Items**, downloaded by the owner from [the author's BOOTH item](https://booth.pm/ja/items/4138976). The linked [creator conditions](https://hub.vroid.com/en/characters/2503153150187103847/models/5733583802599684396) permit alterations and redistribution and require attribution. Both originals/SHA are preserved; the derived front group is flipped and recoloured. Attribution appears in the review UI, embedded VRM metadata and [source manifest](frontend/public/avatars/a1-native-v1/source.json).

[Editable source, raw export, packaged VRM and reproduction](../design/desk-companion/characters/2026-10-19-a1-vroid-refinement/README.md) distinguish native authoring from runtime metadata normalization. The final packaged asset only adds its version field to the native export; model/texture/material/morph/bone bytes are identical. Earlier input punctuation loss and dark base-hair failure are retained in QA/cache history. AI-assisted Group 2 adaptation does not transfer third-party copyright or imply endorsement. Final A1 likeness and Pi performance remain unaccepted/unverified.

## HISTORICAL: 2026-10-18 rejected custom head

The rejected historical head at`?surface=head-history` derived face/eyes/teeth/tongue/neck components from Anna1.1 in Polygonal Mind/ToxSam's CC0 collection. [Pinned original terms](../design/desk-companion/characters/2026-10-18-a1-head-study/base-source.json), [five ImageGen prompts](../design/desk-companion/characters/2026-10-18-a1-head-study/imagegen-prompts.json) and bake sources remain for preservation. It is not an active base. The older pixiv full-body study retains separate restrictions and is not reclassified CC0.

## 2026-10-17 A1 3D study

Three.js0.186.1 is MIT; [licence](licenses/three-LICENSE.txt) is retained and served in public/licenses. The pinned original pixiv sample, full VRM licence and embedded permissions remain in frontend/public/avatars. A1 GLB is an explicitly modified adaptation of that anatomy/face/rig, with AI-assisted new hair/garments/fit/motion; [source/settings](frontend/public/companion/source.json) retain copyright and the same restrictions. This is not wholly original student art or a Razer asset.

A selected CMU Motion Capture Database subject14/trial26 upper-body excerpt is retargeted for Gesture. Source ASF/AMC, frame/rate bounds, hashes and acknowledgement remain in the [asset manifest](../design/desk-companion/characters/2026-10-17-a1-3d/source.json). [CMU terms](https://mocap.cs.cmu.edu/) permit all uses/inclusion in products, but not direct resale of data, including converted data. Finger/thumb convenience channels are ignored. This is public capture, not user data collected by this project.

## 2026-10-21 local creator-made model preview

Reveria Lite1.5, ©NYOA24A, was downloaded unchanged from [the author’s free BOOTH listing](https://24a.booth.pm/items/7916400) and loaded through the browser-only local-file viewer. [Hash, metadata and source checks](../design/desk-companion/characters/2026-10-21-ready-models/source.json) retain a conflict: embedded VRM says CC0 and Hub permits redistribution, but the linked VN3 English reference terms prohibit original redistribution and require contact for modified distribution. Keep this candidate in Downloads/browser-local storage; no model bytes are vendored, published or bundled. Japanese terms prevail and were not independently reviewed here.

[SELESTIA](https://booth.pm/ja/items/4035411) and [RINDO](https://booth.pm/ja/items/3443188), STUDIO JINGO, are paid candidates only; author posters were viewed, no purchase/import or protected asset extraction occurred. Their listed formats and terms do not establish this app/Pi compatibility. RINDO’s author labels VRM/PMX as test formats. Local original/model-adaptation history does not imply redistribution permission for any new file.
