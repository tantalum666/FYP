# Group 2 Current Handoff

更新：2026-10-05。状态：**RIG-Arm研究完成；机械臂仍为候选，未采购／接入**。

## 当前任务与结果

用户转述Marco推荐RIG-Arm，要求判断整机可用性及更换AI的二次开发范围。[完整评估](research/2026-10-05-rig-arm/secondary-development-review.md)／[来源](research/2026-10-05-rig-arm/source-register.json)核对官方网页及两个固定固件commit：可以改模型／工具／表情／动作／IK，也有官方MCP和local局域网控制实现。推荐本组主机处理AI／日历／坐姿，现成控制器处理小幅机械表达；不是已批准采购或已实现新驱动。

整机页面标价US$124，套件US$109不含打印外壳，当前预售且有节日发货延迟。小智是框架，文字模型换接口和完整自然实时语音接入是不同工作。随臂相机／240×240小屏不替代固定姿态相机／常亮触摸屏。omni与local示教、微动默认行为不同，动作接受不等于到位；统一停止、失联、完成反馈与到货固件仍须台架核对。omni声明Apache2，local整体许可和机械SDFL-C分别处理，上游源码／STL留在Git忽略缓存，不纳入本仓库。

## 完成项与证据

- [全文阅读](output/qa/2026-10-05-rig-arm-feasibility/reading-record.json)：122份／11,376行，36批及截断补读至EOF，期间无变化；压缩沿用记录。
- [本轮QA](output/qa/2026-10-05-rig-arm-feasibility/verification.md)：官方可见正文、商品截图、源码静态追踪、链接与保护文件核对。没有执行厂商代码、付费AI、刷机或实物动作。
- product／README／架构／操作已同步候选与接入缺口；学校Proposal／团队日志、身份、旧Senplate和应用源码保持。

## 已有工程与仍待验证条件

Desk Companion包含日历、独立常亮／触摸、坐姿标定／判断／反馈复测、配对、助理、Qwen／Gemini语音适配、受限输出、交换／分享／备份和iPhone；主动事务及UI／UX修复完成。[产品](product.md)／[软件README](desk-companion/README.md)／[事务](desk-companion/docs/task-tracking.md)／[操作](desk-companion/docs/operator-guide.md)。101后端、11前端及三端交互等[既有QA](output/qa/task-enhancement-ux-2026-10-03/verification.md)未在本轮重跑，不代表真人准确率、语音自然度或机械性能。输出仍默认停机，尚无RIG驱动。

[私人tantalum666/FYP](https://github.com/tantalum666/FYP)已建仓、默认main，原全项目推送核验完成；旧令牌403已解决，仅增加FYP范围且其余权限保持。成员邀请未发送，按[CONTRIBUTING](CONTRIBUTING.md)由Yuan用组员GitHub用户名邀请。本轮研究分支／PR实际状态见本轮QA；不把研究上传当作应用部署或PR已合并。

本轮未重启／核实预览8831／5190；原账号owner、私有凭据在desk-companion/.runtime/credentials.json，不进Git。真实摄像头／标签、Pi常亮与触摸／负载、音频与AEC／费用、机械供电／停止／包络、光学、Google本人OAuth、Apple真机签名及DGX配额仍需对应实物或账号条件。学校正式双格式、三人明细日志和40／30／30计划份额保持，不代签、不提交。

## 唯一下一步

**取得候选RIG-Arm的实际SKU／板型、出厂固件与可调用工具清单；先做只读连通，再确定受限驱动及停止／回执台架方案。** 本轮已列可供核对的问题，尚未对外发送；没有把购买意向记成采购决定。
