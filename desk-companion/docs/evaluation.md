# 坐姿与集成验证流程

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**现行规范／入口**。已按本轮保存状态核对；最新软件、GitHub main 和 Pi 部署分开，Pi 暂停、旧 API 预算关闭。 [新聊天入口](../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

本文件是可执行的评价安排，不是已达到的准确率报告。当前已运行合成数据与模型冒烟检查；没有采集真人视频或运行真实机械臂。

## 数据准备

1. 获得参与者同意，固定摄像头，使用不含姓名的participant编号。标记session及开发／测试组，同一人不能同时出现在两组。
2. 单独记录三项个人标定，再记录自然坐姿、短暂动作、持续偏移、遮挡、离桌和光线变化。相机移动后另建session并重新标定。
3. 标定帧不能计入分类成绩。人工参照原视频标注时间区间，不用模型预测充当真实标签。
4. 原视频保存在本机受限目录，工作软件不会自动上传视频。可在评价结束后按团队已同意的保留政策处理；不要擅自删除未获授权的数据。

导出关键点（仅读取给定视频，不开相机）：

```sh
PYTHONPATH=backend .venv/bin/python scripts/extract_landmarks.py /path/to/consented-video.mp4 --participant p01 --session desk-a --split test --source recorded --output .runtime/data/p01-unlabelled.jsonl
```

合成视频必须使用`--source synthetic`。输出中的`expected`与`calibration_pose`为空，不能直接用于成绩报告。

标注CSV的列为：

```csv
start_seconds,end_seconds,expected,calibration_pose
0,6,,reference
6,12,,forward
12,18,,side
18,35,within_reference,
35,55,forward,
55,65,unknown,
65,95,absent,
```

这些仅说明格式，不是你的视频标签。时间区间为左闭右开，需覆盖每个采样点且不重叠。应用人工标签：

```sh
.venv/bin/python scripts/apply_labels.py .runtime/data/p01-unlabelled.jsonl .runtime/data/p01-labels.csv --output .runtime/data/p01-labelled.jsonl
.venv/bin/python scripts/evaluate_posture.py .runtime/data/p01-labelled.jsonl --split test --output .runtime/data/p01-report.json
```

评价器检查participant分组泄漏、标签及完整个人标定。默认只评价test，开发数据需明确`--split development`。输出混淆矩阵、各类支持量／F1、无法判断比例，以及相同冷却条件下单帧基线与持续判断的提示统计。帧分类与提示时机分开，不能把减少短暂动作提醒说成分类模型准确率提高。

`macro_f1_over_present_classes`只针对该文件实际存在的类别；缺失类别时不能直接用于提案完整场景目标。短片中的每小时误报归一化可能非常不稳定。先检查数据来源、覆盖和支持量，再分析数值。

## 实物评价

原提案中的6名成年人、开发／测试各3人、宏平均F1目标0.80、误报不超过2次／小时和满足持续条件后95%本地反馈不超过2秒仍是待验证目标。真实试验需另外完成：

- 参考、持续前倾／侧偏、遮挡／多人／离桌各类及不同身材、衣着和光线。
- 标定成功率和失败原因，不能只挑易识别的片段。
- 两种桌面位置各2小时连续运行；在Pi上并行启用视觉、显示及语音，测CPU／内存／温度、掉帧和响应时间。
- 固定间隔活动提醒、单帧阈值与持续判断分别观察；固定间隔是活动提示基线，不等同于姿态分类。
- 姿态提示后实际调整、未调整、遮挡和断流，核对复测结果。
- 自然语音中的犹豫、插话、改期、中英、噪声、工具失败与重复请求；记录端到端时延及实际用量。
- 确认机械包络、脉宽、限位、独立断电和100次预设动作。仅有驱动回执不能证明实际角度。

## 本轮软件证据

合成回放的三步标定、持续前倾、仍偏离复测已在浏览器操作；HTTP、事务、隐私、重启、配对、草稿与协议测试在隔离库执行。MediaPipe用空帧推理，唤醒模型用合成静音推理。评价脚本另运行404个标注的合成评分帧，并验证分组泄漏会被拒绝。

这些结果用于验证代码路径，不构成真实准确率、唤醒成功率、医疗效果或商业收益。详细证据见[本轮QA](../../output/qa/software-completion-2026-10-02/verification.md)。
