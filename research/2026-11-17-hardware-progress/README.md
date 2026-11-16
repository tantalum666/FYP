# Group 2 硬件进度（2026-11-17）

## 采购与预算

[老师审核版 Excel](FYP_hardware_procurement_teacher_review_20261117.xlsx)按机械臂、吸尘机、显示器和行走改装部件汇总，保留数量、预算、淘宝／天猫链接和选购依据。首批三件是 luwu rig arm 手搓整机、1400mAh Type-C 桌面吸尘器样机和亚博智能 7 寸 HDMI IPS 电容触摸屏无支架款。

| 首批预算 | 后续商品预算 | 预计合计 | HK$2,000 上限余量 |
| ---: | ---: | ---: | ---: |
| HK$1,077.12 | HK$867.31 | HK$1,944.43 | HK$55.57 |

统一供电套件、英标线、5A 线、随屏 HDMI 配件和手机 Qi 五项共调低 HK$210。亚博旗舰店所选 IPS 无支架款标价 ¥219，旧链接已失效。随屏 HDMI 线和 micro-HDMI 转接头计 HK$0，USB 触控线到货复核。预算汇率沿用 ¥1 ≈ HK$1.10。运费、替换电池和整壳打印实际成本未计，Rig 所选套餐仍按约 ¥700 预估。学校可借 Pi 5、电源和散热器，microSD 与 ESP32-CAM 已有。

## 320 × 200 × 200 mm 外壳 V2

- [分件组装版 Blender](enclosure_320mm_v2/FYP_enclosure_320x200x200_V2_panels.blend)与[爆炸图](enclosure_320mm_v2/panels_exploded.jpg)。14 块外板，25 个连接件及独立 Mini 回充支架。最大外板平放约 200 × 156.8 mm。
- [一体版 Blender](enclosure_320mm_v2/FYP_enclosure_320x200x200_V2_one_piece.blend)与[完整外观](enclosure_320mm_v2/one_piece_preview.jpg)。本体长度达到学校热床标称 320 mm，能否整件切片待核。
- [尺寸与 Qi 留位说明](enclosure_320mm_v2/dimensions-and-qi-dock.md)和[充电局部图](enclosure_320mm_v2/qi_dock_detail.jpg)。保留顶面手机 Qi 和独立 Mini 回充，Mini 从正面进入 150 × 160 × 100 mm 开口，车尾竖向 RX 对准泊位 TX。图中线圈高和间距是模型占位，实测后定导向和充电参数。
- [复现脚本](build_enclosure_v2.py)和[首轮实测表](enclosure-fitting-checklist.md)。屏幕开窗、安装耳孔距、机械臂承力和 Mini 吸口高度须以实物定稿。

## 桌面与车顶 ArUco

先用固定俯视相机在 150 × 65 cm 桌面验证四角标定和车顶位置、朝向。采用 `DICT_4X4_50`。ID 0–3 为桌角，ID 4 在车顶。名义桌角码中心为 `(5,5)`、`(145,5)`、`(145,60)`、`(5,60)` cm，以实测码心坐标为准。桌角黑框 60 mm、车顶黑框 40 mm，保留白边。可用[一页 A4 纸质测试模板](FYP_ArUco_150x65cm_A4_Print_Sheet.pdf)以 100% 打印验证识别，五块最终码可用学校免费双色 3D 打印。先确认连续同框和各处车顶码可读，再跑桌面路线。顶码离桌高度单独量，台板厚度不用于视差修正。车载本地防跌落和失联停车仍需测试。

## 当前验收边界

已完成采购审阅、几何模型和定位版式。下一步由团队核对首批套餐和实际到手价，拿到实物后量屏和接口、测并发电流及相机取流，再决定试印和后续配套。尚无实物试装、切片、台架行驶或连续回充验证。[本轮验证记录](../../output/qa/2026-11-17-hardware-progress/verification.md) · [10 月采购评审原稿](../2026-10-26-hardware-procurement-review/README.md)
