# Senplate 品牌基准 · A构图曲线修正版

更新：2026-09-17。状态：**LOGO_SELECTED_A — V4_CURVE_REPAIR_READY**。

用户已选A构图，最新指出V3盘沿左右弧度不同，要求继续结合黄金分割调整，必要时重设计。当前V4保留餐盘、份量与感知点，重新构造整个盘沿；修正版已交付，等待实际视觉反馈，不将几何校验写成审美批准。

![当前预览](output/brand/2026-09-17-senplate-ellipse-a-v4/brand-preview.png)

## 当前识别与写法

Logo默认小写 **senplate**；iOS显示名称、App名称、项目标题与正文写 **Senplate**。大写S只保留为对照，用户没有明确改选。中文名和正式口号未定；原参考板说明文字不是正式产品文案。

餐盘对应真实餐食，盘内形状对应份量，圆点表达感知。这是设计意图，不是用户识别或产品能力验证。份量和圆点仍有偏置；此次镜像约束针对盘沿，不是整个符号。

## 盘沿构造与黄金比例

V3的数值比例虽符合φ，上半盘沿仍左右分别绘制，端点又一尖一圆，因此不协调。V4由同一对同心、同轴椭圆构造左右两边；两端圆角的控制点互为镜像，并与内外椭圆边界相切。

| 构造项 | 当前规则或尺寸（矢量设计单位） |
|---|---|
| 镜像轴与共同中心 | x=160；两椭圆中心均为(160,118.8233) |
| 外椭圆 | 320×122.2291；宽／高=φ²≈2.618 |
| 内椭圆 | 284.3340×75.5418；外／内椭圆高度=φ≈1.618 |
| 份量与感知点 | 份量122.2291×75.5418；份量高度／圆点直径46.6874=φ |
| 图文间距 | 28.8544；圆点直径／间距=φ |
| 盘沿厚度 | 前缘23.3437、两侧17.8330；左右对应位置一致，不宣称全程等厚 |
| 开口收尾 | 同角度、同控制点关系的镜像圆角，与椭圆相切 |

上表的外椭圆是**完整构造椭圆**；切出开口后，可见盘沿的外接框高度不同。整体符号320×179.9379，不再强制整体宽高等于φ。黄金比例负责尺寸关系，左右弧度由共享椭圆和镜像保证，两者不能互相替代。

[共享椭圆构造](output/brand/2026-09-17-senplate-ellipse-a-v4/ellipse-construction.png)／[仅盘沿前后对照](output/brand/2026-09-17-senplate-ellipse-a-v4/bowl-before-after.png)／[完整Logo对照](output/brand/2026-09-17-senplate-ellipse-a-v4/curves-before-after.png)。参数见[构造记录](output/qa/senplate-ellipse-a-v4-2026-09-17/ellipse-construction.json)。

字母路径沿用V2/V3，继续保持平滑曲线、直边和单层a；本轮不替换字体、不单独拉伸字形。原图字体来源没有确认，现有字标为可编辑轮廓，不是可直接打字的文本。

## 配色

| 用途 | 色值 |
|---|---|
| 主色深绿 | #163F35 |
| 辅助米白 | #F3F1E7 |
| 纯黑 | #000000 |
| 反白 | #FFFFFF |

各配色使用同一几何轮廓。默认App图标为深绿底、米白符号；源图是完整方形，预览中的圆角仅表示使用效果。

## 当前素材

- [V4完整ZIP](output/brand/Senplate_Brand_Assets_v4.zip)／[使用说明](output/brand/2026-09-17-senplate-ellipse-a-v4/README.md)／[清单](output/brand/2026-09-17-senplate-ellipse-a-v4/manifest.json)
- [主Logo SVG](output/brand/2026-09-17-senplate-ellipse-a-v4/senplate-logo-green.svg)／[透明PNG](output/brand/2026-09-17-senplate-ellipse-a-v4/senplate-logo-green.png)
- [符号SVG](output/brand/2026-09-17-senplate-ellipse-a-v4/senplate-mark-green.svg)／[字标SVG](output/brand/2026-09-17-senplate-ellipse-a-v4/senplate-wordmark-green.svg)
- [大写S对照](output/brand/2026-09-17-senplate-ellipse-a-v4/senplate-capital-s-comparison.png)
- [深绿图标](output/brand/2026-09-17-senplate-ellipse-a-v4/app-icon-forest-1024.png)／[米白图标](output/brand/2026-09-17-senplate-ellipse-a-v4/app-icon-ivory-1024.png)／[黑底图标](output/brand/2026-09-17-senplate-ellipse-a-v4/app-icon-black-1024.png)
- [Figma品牌板](https://www.figma.com/design/UyYjnTFGWO0r1lj4uvghGp?node-id=69-2)：主Logo68:2、符号68:15、品牌69:2、整体对照70:31、仅盘沿71:2、构造72:2。

原图1536×1024仍[逐字节保留](output/brand/2026-09-17-senplate-ellipse-a-v4/source-selected-a.png)，SHA-256为`cc98804614d8e0de4e15d1e5dd197550f3bef06a4569cc5c4c3b9f54e2929a61`。V1描摹、V2平滑重建、V3黄金比例稿及更早资料保留；旧版本不混入当前应用资产。

## 使用与检查

横向组合约1018.0588×179.9379，独立符号320×179.9379，均保持等比缩放。保护空间建议一个圆点直径约46.6874单位；内部图文间距另为28.8544。

已查看2036pxLogo、盘沿局部、构造、反白、图标及24／32／64px小样；建议符号至少32px宽，优先48px以上。SVG用于缩放和加工，PNG像素尺寸经过整数取整，过度放大仍能看见像素；印刷／加工最小尺寸需要按实际工艺打样。

[收尾检查](output/qa/senplate-ellipse-a-v4-2026-09-17/closeout-validation.json)分开记录解析曲线镜像、相切关系和原生PNG翻转后的边缘抗锯齿差异，不把PNG称为逐像素绝对对称。没有以单一比例或文件格式证明视觉质量。

## 状态边界

A的语义和名称仍保留，V4针对用户反馈修正盘沿。新的图形近似／官方商标查询尚未完成，旧Interval结果不能作为本版结论。没有新注册、App实现、上架或硬件验证。

当前下一步按用户对V4的反馈继续品牌细化；若用户要求进入界面设计，则依据本规范和现有软件规格执行，不机械重复已完成的Logo测试。
