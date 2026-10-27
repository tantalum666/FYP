# Group 2 Current Handoff

更新：2026-10-27。当前分支在代理循环之上加只读查询。文字循环那一片仍然有效，不是这一支的全部。下面 2026-10-26 的归档交接仍然有效。

## 只读查询

- `owner_search`、`plate_summary`、`owner_clock` 都是 `read`。检索不读任意目录。今日／本周和时钟都用拥有者时区。配对会话不能调用。
- 副作用仍只准备草稿。契约见 [agent-loop.md](desk-companion/docs/agent-loop.md)。

更新：2026-10-27。文字代理循环、语音共用工具策略、离线场景和工具失败处理仍在上一支。

## 代理循环那一片

- 文字回合走 `desk/agent_loop.py`。语音不跑多步循环，但和文字一样走 `desk/tool_policy.py`：注册表、风险、审计、每工具超时，以及同一操作只接受一个副作用结果。草稿和作业准备仍要拥有者批准。
- 无法使用的模型回复最多试 3 次，然后给拥有者一句说明，不执行工具。超时后晚到的未批准草稿或待审作业会被取消。
- 离线场景覆盖提醒、记忆回忆、拒绝越界、待批准的电脑笔记、步数和时间上限，以及文字／语音同一次拒绝。不联网。见 [agent-loop.md](desk-companion/docs/agent-loop.md)。
- 每次工具调用写入 `tool_calls`，含一句说明。拥有者在助理面板和 `GET /api/assistant/tool-calls` 查看。配对屏 403。本机 Chrome 打开过面板。
- 验证：`pytest -q` 193 通过，Ruff 通过，前端 `npm test` 19 通过，`npm run build` 通过。没有付费 API。
- 未做：任意电脑或应用控制；合并 PR #4／#5／#15／#16；真实模型试听。

## 这一支的下一步

先合并代理循环 PR，再合并这一支的只读查询。若同时改 `handoff.md`、`decision-log.md`、`work-log.md`，保留两边的条目。

## 2026-10-26 仓库归档交接

当前任务是仓库归档与组员PR整合。**硬件PR #17已审查修订并合并；Senplate集中归档与运行验证已完成。**Git交付：[硬件PR #17](https://github.com/tantalum666/FYP/pull/17)／[整理PR #18](https://github.com/tantalum666/FYP/pull/18)。

## 当前状态与证据

- [PR #17](https://github.com/tantalum666/FYP/pull/17)合并提交`4417e3656959bd3deb7e0d42a2e42654723dfba4`，审查头`0f7fbb19b17ab4801e5f3d8d621c022a85197e1d`。修正Pi记录混用、硬件目标归属、轴长和报价币种，补命令去重／期限／停止／完成证据；[审查QA](output/qa/2026-10-26-repo-cleanup/pr17-review.md)。没有新增硬件测试或部署。
- [archive/senplate](archive/senplate/README.md)集中退役食品代码、规划／研究、品牌、采购、旧学校交付和QA；[原路径清单](archive/senplate/archive-manifest.json)记录迁移校验。当前代码在`desk-companion/`，学校原件、桌面Proposal／Log sheet和身份入口继续保留。
- 本轮[完整阅读记录](output/qa/2026-10-26-repo-cleanup/reading-record.json)覆盖176个文件版本／16,752行；继承只用于同一轮已读的完全相同文本。验证与合并收尾见[QA](output/qa/2026-10-26-repo-cleanup/verification.md)。
- 最新AliceChan／统一Omni／语音计时／Linux工作保存在软件本地工作区，未被本次归档覆盖或批量上传；main的实现边界见[product](product.md)。Pi继续暂停，旧API测试预算已关闭。
- 其余开放PR #4、#5、#15、#16是拥有者较早分支／草稿；#4冲突，#5依赖#4，#16依赖#15且包含已否决人物。只核对依赖与状态，未声称完成它们的独立代码审查，也未盲合旧美术。

## 2026-10-26 的下一步（不是本片）

单独整理并审查最新本地AliceChan／Omni软件增量。保留当前未发布成果，按当前角色和统一模型方向拆出可审阅提交，不直接合并旧A1造型栈。真实人体／声学与目标Pi验收仍是独立后续事项。
