# Third-party visual assets

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
- 当前A1工作稿使用下述已披露许可的3D样本改作，完整2D备用图来自此前项目原生ImageGen输出；旧SVG占位角色属于历史。未使用Razer／Metafoodx角色、品牌或产品图作为应用资产。原Senplate字体／品牌清查不替代当前项目的商业权利核查。

工程不包含账户秘密或原始个人音视频；姿态／唤醒权重通过固定来源校验下载。角色许可样本与已披露的改作随本分支分发。当前是学校原型的软件交付，不据这些说明声明全部商业发行手续已完成。

## 2026-10-17 A1 3D study

Three.js0.186.1 is MIT; [licence](licenses/three-LICENSE.txt) is retained and served in public/licenses. The pinned original pixiv sample, full VRM licence and embedded permissions remain in frontend/public/avatars. A1 GLB is an explicitly modified adaptation of that anatomy/face/rig, with AI-assisted new hair/garments/fit/motion; [source/settings](frontend/public/companion/source.json) retain copyright and the same restrictions. This is not wholly original student art or a Razer asset.

A selected CMU Motion Capture Database subject14/trial26 upper-body excerpt is retargeted for Gesture. Source ASF/AMC, frame/rate bounds, hashes and acknowledgement remain in the [asset manifest](../design/desk-companion/characters/2026-10-17-a1-3d/source.json). [CMU terms](https://mocap.cs.cmu.edu/) permit all uses/inclusion in products, but not direct resale of data, including converted data. Finger/thumb convenience channels are ignored. This is public capture, not user data collected by this project.
