# Group 2 · 外壳 V3 与 H2D 首轮打印

[下载本次 12 件 ZIP](FYP_H2D_print_package_12_parts.zip) · [可编辑 Blender](FYP_enclosure_320x200x200_V3_six_panels.blend) · [爆炸图](six_panels_exploded.jpg) · [装配预览](six_panels_preview.jpg) · [五码图案](aruco_preview.png)

## 单色结构件

| 单件 | 数量 | 建议热床投影（mm） |
| --- | ---: | ---: |
| 前板，合并斜屏框及回座口 | 1 | 309.6 × 204.2 |
| 后板 | 1 | 309.6 × 193.6 |
| 左、右侧板 | 2 | 各 200 × 200 |
| 顶板 | 1 | 309.6 × 104.6 |
| 底板 | 1 | 309.6 × 200 |
| 可拆 Qi 发射支架 | 1 | 70 × 17 |

STL 已按建议朝向摆放，单位毫米、100% 原尺寸。前板斜屏外侧朝下，切片预览核对折角的支撑。H2D 单喷嘴标称 325 × 320 × 325 mm，双喷嘴共同范围为 300 × 320 × 325 mm。将 309.6 mm 的板沿单喷嘴 325 mm 方向排版，预览确认实际可用区域及裙边。[H2D 厂家规格](https://cdn1.bambulab.com/documentation/h2d/zh/H2D_AMS_Combo_20250305.pdf)

六板装配外廓 320 × 200 × 200 mm。试样连接为 Ø3.4 mm 通孔和 M3 螺母槽。先装底板、两侧及 Qi 支架，再装前、后板和顶板。左顶孔 Ø22 mm 用于机械臂走线。显示窗、安装和承力按实物尺寸核验。车尾 RX 与车位 TX 沿用 [V2 回充留位](../enclosure_320mm_v2/dimensions-and-qi-dock.md)。

## 黑白定位牌

同盘 3MF 包含 ID 0–3 四枚桌角码（含白边 80 × 80 mm）及 ID 4 一枚车顶码（53.3 × 53.3 mm）。白底 1.0 mm，黑图案 0.4 mm。对象列表中 White base 用白色，Black pattern 用黑色。车顶 ID 4 按预览图上边朝车头。先试印一枚，用相机确认识别。

在 Bambu Studio 选择学校的 H2D 配置，核对实装喷嘴、热床板与耗材。切片预览确认后，用“导出已切片盘”生成 `.gcode.3mf` 拷入 U 盘。[Bambu Studio 操作说明](https://www.polyu.edu.hk/u3dp/-/media/department/u3dp/content/download/bambu-studio-guideline_2026.pdf?hash=8AAF44910A30F9BC817F549AB6041286&rev=d323b234c96a4b9d8548e7020cda8328)
