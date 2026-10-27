# Group 2 Current Handoff

更新：2026-10-26。当前任务是仓库归档与组员PR整合。**硬件PR #17已审查修订并合并；Senplate集中归档与运行验证已完成。**Git交付：[硬件PR #17](https://github.com/tantalum666/FYP/pull/17)／[整理PR #18](https://github.com/tantalum666/FYP/pull/18)。

## 当前状态与证据

- [PR #17](https://github.com/tantalum666/FYP/pull/17)合并提交`4417e3656959bd3deb7e0d42a2e42654723dfba4`，审查头`0f7fbb19b17ab4801e5f3d8d621c022a85197e1d`。修正Pi记录混用、硬件目标归属、轴长和报价币种，补命令去重／期限／停止／完成证据；[审查QA](output/qa/2026-10-26-repo-cleanup/pr17-review.md)。没有新增硬件测试或部署。
- [archive/senplate](archive/senplate/README.md)集中退役食品代码、规划／研究、品牌、采购、旧学校交付和QA；[原路径清单](archive/senplate/archive-manifest.json)记录迁移校验。当前代码在`desk-companion/`，学校原件、桌面Proposal／Log sheet和身份入口继续保留。
- 本轮[完整阅读记录](output/qa/2026-10-26-repo-cleanup/reading-record.json)覆盖176个文件版本／16,752行；继承只用于同一轮已读的完全相同文本。验证与合并收尾见[QA](output/qa/2026-10-26-repo-cleanup/verification.md)。
- 最新AliceChan／统一Omni／语音计时／Linux工作保存在软件本地工作区，未被本次归档覆盖或批量上传；main的实现边界见[product](product.md)。Pi继续暂停，旧API测试预算已关闭。
- 其余开放PR #4、#5、#15、#16是拥有者较早分支／草稿；#4冲突，#5依赖#4，#16依赖#15且包含已否决人物。只核对依赖与状态，未声称完成它们的独立代码审查，也未盲合旧美术。

## 一个下一步

**单独整理并审查最新本地AliceChan／Omni软件增量。**保留当前未发布成果，按当前角色和统一模型方向拆出可审阅提交，不直接合并旧A1造型栈。真实人体／声学与目标Pi验收仍是独立后续事项。

## 2026-10-27 记忆与主动检查切片

拥有者记忆现在会去重、保留更正前的文字、到期，并把相同文字的停用交给既有草稿确认。姓名和偏好只产生草稿；托管提取默认关闭，且必须同时配置开关和正的每日上限。早晨简报与可选晚间检查沿用安静时段和同一份偏好，跟进写明触发原因。契约见 [memory.md](desk-companion/docs/memory.md) 与 [task-tracking.md](desk-companion/docs/task-tracking.md)。本切片不合并 PR #4／#5／#15／#16，也不改硬件或 archive。合并前先看该 PR 的测试命令和已知缺口。
