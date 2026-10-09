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
- 全身角色采用pixiv官方未修改的VRM1_Constraint_Twist_Sample v1.0.1，© 2022 pixiv Inc.。它按VRM Public License 1.0及嵌入许可设置分发，不能称为MIT或本组原创美术。许可允许everyone使用、corporation商业用途、再分发和修改再分发；禁止anti-social／hate用途。[完整来源与嵌入设置](frontend/public/avatars/source.json)、[许可原文](frontend/public/avatars/VRM-Public-License-1.0.txt)及[使用说明](docs/avatar.md)随模型保留。未使用Razer角色、品牌或产品图作为应用资产。
- Three.js、React Three Fiber与three-vrm软件为MIT，副本位于[Three.js](licenses/three-LICENSE.txt)、[React Three Fiber](licenses/react-three-fiber-LICENSE.txt)及[three-vrm](licenses/three-vrm-LICENSE.txt)，并在public/licenses分发。模型许可与软件许可分开。原Senplate字体／品牌清查不替代当前项目权利核查。

工程不包含账户秘密或原始个人音视频；姿态／唤醒权重通过固定来源校验下载。10月9日起，获准再分发的pixiv示范VRM随frontend/public/avatars打包，固定commit／SHA／版权／许可和元数据同时保留；本地替换的用户模型不自动入库。当前是学校原型的软件交付，不据这些说明声明全部商业发行手续已完成。
