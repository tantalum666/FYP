# Senplate Brand Assets V2 — Smooth Reconstruction

2026-09-17。在已选A方案上修复V1自动描摹带来的毛边。V1素材包和原始参考板保留，当前使用V2。

## 本版内容

- `senplate-logo-green.svg`：默认全小写横向Logo；另有black／white同轮廓版本。
- `senplate-mark-*.svg`：独立符号；`senplate-wordmark-green.svg`：独立字标路径。
- `senplate-logo-*.png`：2056×340透明PNG；`senplate-mark-green/black/white.png`：1300×680透明PNG。
- `app-icon-*-1024.png`：三个1024×1024方形图标源图，默认forest深绿底。
- `capitalization-comparison.png`：全小写与首字母大写对照；当前建议Logo用小写，报告／正文／产品名称用Senplate。
- `senplate-capital-s-comparison.svg/png`：首字母大写对照，尚未选作默认Logo。
- `edge-comparison.png`：修复前后的放大对照；`brand-preview.png`：精修版全套预览。
- `senplate-mark-24.png`、`senplate-mark-32.png`、`senplate-mark-64.png`：小尺寸样本。
- `source-selected-a.png`：用户选中的原始参考板，字节不变；`manifest.json`：版本、来源、尺寸、节点与哈希。

## 使用说明

主色#163F35，米白#F3F1E7。图形、圆点和图文字距等比例缩放，不单独拉伸。符号建议至少32px宽、优先48px以上；24px虽已清理轮廓，盘沿仍因宽扁比例而偏细。

V2使用明确的少量Bezier曲线、圆形轮廓及水平／垂直边重建，保留原选定构图。字母按原图结构重新整理，保持小写和单层a；没有宣称识别到原图字体，也没有自动替换为历史字体。与V1存在有意识的轮廓修正，并非逐像素复制。

用于缩放和加工的优先文件是SVG。PNG为Figma原生导出的像素图，放大超过原始尺寸仍会看到像素。图标源图未裁圆角；预览圆角只表示使用效果。

[Figma品牌板](https://www.figma.com/design/UyYjnTFGWO0r1lj4uvghGp?node-id=55-2)／[大小写对照](https://www.figma.com/design/UyYjnTFGWO0r1lj4uvghGp?node-id=56-2)。本版没有新的商标检索或应用实现；原图口号未定为正式文案。
