# 软件章节草稿

> HISTORICAL — 2026-10-27基于main46ac167的软件章节草稿。下文“未合并／未实现”与测试数只适用于该快照，不是当前软件状态，也不是本轮改写或提交的Progress Report I。当前实现与验证见[产品](../../../product.md)和[整合QA](../../../output/qa/2026-10-28-grok-review-merge/verification.md)。

Group 2。日期：2026-10-27。这是 FYP 报告的软件章节草稿，只写 `main` `46ac167` 里已经提交的 Desk Companion 代码，以及 [decision-log.md](../../../decision-log.md) 里已经记下的决定。开放 PR 单独放在第 3 节，不能写成已经合并。没有实测的数字不写成设备准确率、时延或商业收益。

更细的模块说明见 [architecture.md](../architecture.md)（2026-10-15）。本草稿不取代那份说明，也不把研究假设升成已批准功能。

## 1. 架构

软件在 `desk-companion/`。界面是 React／TypeScript／Vite，API 是单个 FastAPI 进程，数据是本机 SQLite。浏览器、常亮屏和 iPhone 共用这一份业务数据，版式分开。姿态时间窗、输出停止和语音会话在该进程的内存里，所以生产服务必须是一个 worker。

现场数据流：

1. 拥有者或已配对设备调用 `/api`。变更请求还要带 `X-Desk-Request: 1` 和操作 ID。
2. 日历、事务、记忆、人格、配对和作业写入 SQLite。相同操作 ID 和相同请求返回原来的回执；相同 ID 配不同请求则拒绝。
3. 四个后台循环做规则检查、天气、可选文字建议和电脑作业。循环失败只记下 `ready` 或 `retrying_after_error`，不把异常原文交给界面。
4. 文字和语音适配器把 Qwen 或 Gemini 的报文转成程序自己的工具调用。模型不能调用确认接口。
5. 电脑作业先进入 review。拥有者批准后才写入专用笔记目录，或拥有者事先保存的一个文件夹。写完后另一次打开文件，核对字节数和 SHA-256。

`main` 上的文字和语音仍是两套适配器。用户后来选择的 Qwen 3.8 Omni Flash Realtime，以及本地工作区里的 AliceChan，都还没有进入 `main`。见 [product.md](../../../product.md)。

## 2. 安全不变量

这些是当前代码里的限制，不是目标说明书。

| 不变量 | 代码中的做法 |
| --- | --- |
| 拥有者会话 | 8 小时。`expires` 必须晚于时钟；到期整点即失效。退出只删除该令牌 |
| Cookie | `HttpOnly`、`SameSite=Strict`、路径 `/api`。`Secure` 只在请求本身是 HTTPS 时设置 |
| 登录 | 同一 IP 60 秒内 10 次失败后返回 `TRY_LATER`。成功会清空计数。响应体只有错误码 |
| 来源 | 默认只接受本机 Host。`DESK_PUBLIC_ORIGIN` 必须是单个没有路径和用户信息的 HTTPS 源 |
| 记忆 | 活动事实最多 200 条，进入模型的最多 40 条。模型只能准备草稿 |
| 人格 | 正文最多 4000 字。文字和语音共用这一段，模型不能改它 |
| 事务跟进 | 安静时段默认 22:00–07:00。一次 tick 最多新建 3 条跟进。关闭跟进后，到期的检查和安静推迟会被清掉 |
| 文字建议 | 背景建议默认关闭。`purpose='followup'` 从当前 UTC 日期前缀起最多 20 行；时钟不往未来写时，这就是当天 |
| 电脑作业 | 全文批准，review 5 分钟，执行期限 60 秒。未知结果不自动重试。取消不删除已写文件。作业成功不把事务标成完成。笔记正文最多 32000 字节 |
| 工具调度 | 普通工具同时 2 个、未完成 8 个；另给停止输出一个名额。普通调用保留 32 个 |
| 语音 | 单次会话 600 秒，或空闲 45 秒。不把原始音频写入业务库 |
| 日历容量 | 事件 500。展开超过 3000 次发生时，快照返回 `NARROW_DATE_RANGE`，而不是未捕获的 500 |
| 恢复 | JSON 备份校验 SHA-256，只补缺失记录。对备份使用替换会得到 `RESTORE_KEEP_EXISTING`。已有单次例外的系列不能被替换 |
| 分享 | 忙闲分享只有时间区间。可展示分享不含私人字段 |

模型不获得批准、路径或 GPIO。配对身份、分享令牌和拥有者会话彼此分开。

## 3. 测试证据

### 已合并的 `main`

2026-10-15 审查 QA 和 2026-10-26 整理 QA 记录的是 **182 项后端、17 项前端**，另有 Ruff、类型检查和构建。那是合并当时的本地结果，不是本轮重跑，也不是 GitHub Actions 绿。

2026-10-27 在 `46ac167` 上用一次性的 `coverage.py` 测量了 `backend/desk`：**4620 条语句，1016 条未执行，约 78%**。前端的 Node 测试只统计被测试导入的文件，所以它的百分比不是整个界面的覆盖率。`dates.ts` 里按日判断、时间和私人标题当时没有测试。这次测量没有把 `coverage` 写进锁文件。

### 本轮打开、尚未合并的 PR

这些数字都是本机命令的结果。私人仓库的 GitHub Actions 在更早的 CI PR 上因账户账单失败，步骤没有开始。下面没有一项可以写成 CI 已通过。

| PR | 本地结果 | 行为变化 |
| --- | --- | --- |
| [#36](https://github.com/tantalum666/FYP/pull/36) | `pytest` 193 通过；前端测试 20 通过 | 读回时，笔记路径若被换成目录，`read_artifact` 会在 `fdopen` 前拒绝。`main` 上这个路径会抛出 `IsADirectoryError`。修复只在该 PR |
| [#42](https://github.com/tantalum666/FYP/pull/42) | `pytest` 187 通过；前端测试 19 通过；`npm run build` 通过 | 新增 JSON 日志脱敏、拥有者只读诊断，以及运行目录内最多 7 份 SQLite 副本。浏览器登录后看到诊断页，页面上没有配置的 API key 和本机口令 |
| [#49](https://github.com/tantalum666/FYP/pull/49) | 前端测试 20 通过；构建通过 | 拥有者和常亮屏各有一份 manifest。服务工作者不把 `/api` 写入 Cache API。无头 Chrome 中两份页面分别链到对应 manifest |

更早仍开放的 [#21](https://github.com/tantalum666/FYP/pull/21)、[#22](https://github.com/tantalum666/FYP/pull/22)、[#24](https://github.com/tantalum666/FYP/pull/24)、[#25](https://github.com/tantalum666/FYP/pull/25)、[#27](https://github.com/tantalum666/FYP/pull/27)、[#28](https://github.com/tantalum666/FYP/pull/28)、[#30](https://github.com/tantalum666/FYP/pull/30) 也是从 `main` 拉出的独立切片。它们的本地测试记录在各自 PR 中。本草稿不把它们的差异算进 `main` 的行为。

## 4. 局限

- 这是一名拥有者的本机原型，不是多租户系统。
- 电脑作业只写一个新的 UTF-8 文本文件。它不是任意 GUI、shell 或浏览器控制。
- JSON 业务备份不含口令、会话和保险库密钥。SQLite 文件副本含口令哈希和会话哈希，只能留在受限运行目录。
- 登录和配对次数限制在进程内存里，重启后清空。
- README 的 uvicorn 示例写了 `--no-access-log`，`scripts/dev.sh` 的启动行没有这个参数。两处不一致。本轮没有改脚本。
- `main` 的读回在目标是目录时会抛异常，而不是返回未核验回执。这是 [#36](https://github.com/tantalum666/FYP/pull/36) 要修的缺陷，现在还没合并。
- 坐姿使用二维关键点。没有真人标签，就不能写准确率。无法判断不会被当成恢复或已经休息。
- 学校提案里的 F1、误报、反馈时延、两种桌面各 2 小时和 100 次机械动作，都还是待测目标。见 [product.md](../../../product.md)。

## 5. 后续工作

按已经写下的决定，而不是新开范围：

1. 审阅并合并上面的软件 PR。交接若与 [#24](https://github.com/tantalum666/FYP/pull/24)、[#30](https://github.com/tantalum666/FYP/pull/30) 冲突，保留较新的一份。
2. 单独整理尚未发布的 AliceChan／统一 Omni 增量。不要把旧的 A1 造型栈直接合并。PR #4、#5、#15、#16 仍是较早草稿。
3. 真实人体姿态、声学、Pi 和机械停机仍要分开验收。硬件 PR #17 已合并，那是资料和契约，不是整机测试。
4. 没有新的模型花费授权，就不能跑会扣费的提供商试验。可选的冒烟脚本若存在于未合并 PR，也必须默认跳过。

## 6. 未验证，不能写进结果

- 没有硬件准确率、端到端时延或减损效果。Senplate 用餐试点已归档，不属于当前 Desk Companion。
- 没有付费模型的识别质量、有用答案时延或账单。产品文档里的合成播放样本不是本轮重测。
- GitHub Actions 没有在本轮跑绿。
- 没有在真机上完成 PWA 安装、iOS 主屏幕或离线后的整页操作。
- 没有导师批准、Moodle 上传或学校正式提交。
- 诊断页和 manifest 链接有本机浏览器查看；这不等于 Pi 触控或常亮屏验收。
