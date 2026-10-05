# Senplate Brand Assets V3 — Golden Ratio

2026-09-17。根据用户要求，在已选A构图与V2平滑轮廓基础上，使用黄金分割调整主要尺寸。V2没有按黄金比例构造；其文件与原图完整保留。

## 比例依据

φ = (1 + √5) / 2 ≈ 1.6180339887。下列数字是矢量设计单位，不是设备毫米。

| 关系 | 尺寸或位置 |
|---|---|
| 符号整体宽／高 = φ | 320／197.7708764 |
| 盘内份量宽／高 = φ | 122.2291236／75.5417528 |
| 感知点中心的左右分割 = φ | x = 197.7708764，即总宽的61.8034% |
| 圆点直径／图文间距 = φ | 46.6873708／28.8543820 |
| 符号高度／字母l主竖笔高度 = φ | 197.7708764／122.2291236 |

主要尺寸先由φ计算，再构建路径。曲线衔接与字母细节保留视觉调整；不是声称每个节点来自黄金螺线，也不把数学比例当作用户审美测试。字母路径延续V2，仅统一等比缩放及重新定位。

## 文件

- `senplate-logo-green.svg`：默认全小写横向Logo；black／white为同轮廓单色版。
- `senplate-mark-*.svg`、`senplate-wordmark-green.svg`：独立符号与字标。
- `senplate-logo-*.png`：2036×396透明PNG；三种颜色的独立符号PNG为1280×792。
- `app-icon-*-1024.png`：1024×1024完整方形图标源图，默认forest。
- `golden-ratio-construction.png`：实际构造网格与比例说明；`construction-grid.svg`：无文字的矢量构造网格，不作日常Logo使用。
- `proportions-before-after.png`：V2原比例与V3黄金比例的实际对照。
- `brand-preview.png`：主色、黑白与图标预览。
- `senplate-capital-s-comparison.svg/png`：大写S备选对照；未改为默认Logo。
- `senplate-mark-24/32/64.png`：24、32、64px小尺寸样本。
- `source-selected-a.png`：原始参考板；`manifest.json`：来源、实际尺寸、构造参数与文件哈希。

主色#163F35，米白#F3F1E7。Logo目前仍为senplate；iOS显示名称、正文和项目标题用Senplate。保留餐盘、份量、圆点及单层a，不改变品牌名称。

SVG按矢量设计尺寸缩放；PNG像素尺寸经整数取整，因此其宽高整数比不会与φ完全相同。图标源图不预裁圆角。建议符号至少32px宽，优先48px以上；24px只保留作检查样本。

[Figma品牌板](https://www.figma.com/design/UyYjnTFGWO0r1lj4uvghGp?node-id=61-2)／[构造图](https://www.figma.com/design/UyYjnTFGWO0r1lj4uvghGp?node-id=62-2)。本版未做新商标检索、注册或App实现。
