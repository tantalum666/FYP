# Senplate Brand Assets V4 — Shared Ellipse Curves

2026-09-17。针对用户指出的左右盘沿弧度不同，在A构图基础上重新构造盘沿。V3与更早素材保留，当前使用V4修正版。

## 本次修正

盘沿的外边和内边分别来自同心、同轴的两条完整椭圆，左右关于x=160镜像；两个开口用镜像的圆角连接，并与椭圆边界相切。左右对应位置的厚度一致，前缘稍厚于两侧。份量形状和感知点保留偏置；镜像要求适用于盘沿，不是整个符号。

黄金比例用于构造尺寸：外椭圆320×122.2291，宽高比为φ²≈2.618；外／内椭圆高度122.2291／75.5418=φ；份量高度75.5418／圆点直径46.6874=φ。完整构造椭圆的尺寸与裁去开口后的可见外接框不同。整体符号外框不再强制为1.618。

## 使用文件

- `senplate-logo-green.svg`：默认小写横向Logo；black／white为同几何配色。
- `senplate-logo-*.png`：2036×360透明PNG；独立符号三色PNG为1280×720。
- `senplate-mark-*.svg`、`senplate-wordmark-green.svg`：独立符号与字标路径。
- `app-icon-*-1024.png`：1024×1024完整方形图标源图，默认forest。
- `brand-preview.png`：主色、黑白与图标版。
- `curves-before-after.png`：V3／V4整体对照；`bowl-before-after.png`：仅盘沿的放大对照。
- `ellipse-construction.png`、`ellipse-construction-grid.svg`：共享椭圆与镜像构造说明，不作日常Logo使用。
- `bowl-only.svg/png`：用于单独检查盘沿，PNG为1280×489；日常应用优先使用完整符号。
- `senplate-capital-s-comparison.svg/png`：大写S对照，未选为默认。
- `senplate-mark-24.png`、`senplate-mark-32.png`、`senplate-mark-64.png`：小尺寸检查样本。
- `source-selected-a.png`：用户选择的原始参考板；`manifest.json`：构造、验证、节点及文件哈希。

颜色为深绿#163F35、米白#F3F1E7、黑#000000、白#FFFFFF。Logo仍用senplate，iOS显示名称、App名称及正文写Senplate。字母路径保持，不因修盘沿更换字体或拉伸字形。

等比缩放；建议符号至少32px宽，优先48px以上。SVG用于缩放和加工，PNG在过度放大时仍有像素。图标源图不预裁圆角。数学镜像、PNG边缘抗锯齿差异和视觉评价分别记录；黄金比例不自动证明更美观。

[Figma品牌板](https://www.figma.com/design/UyYjnTFGWO0r1lj4uvghGp?node-id=69-2)／[仅盘沿对照](https://www.figma.com/design/UyYjnTFGWO0r1lj4uvghGp?node-id=71-2)。无新商标查询、注册或App实现。
