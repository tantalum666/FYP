# 2026-10-06 云端软件审查与核验

## 结果

最终代码：**147项后端测试、15项前端测试、Ruff和TypeScript／Vite生产构建通过**。这是云端实际运行的结果，不使用停止前的37项中间测试代替。受限笔记文件实际写入临时目录并独立读回；Qwen／Gemini使用假传输与虚构内容。尚未完成通用桌面／LCU或实机验收。

| 检查 | 实际结果 | 证据 |
|---|---|---|
| Python 3.12.14，锁定依赖 | uv sync --frozen成功 | pyproject／uv.lock未修改；普通基础依赖，无vision／audio extras |
| 全后端 pytest -q | 147 passed，1 warning，42.85秒 | [日志](cloud/pytest-final.log) |
| ruff check backend scripts tests | All checks passed | [日志](cloud/ruff-final.log) |
| Node v24.19.0／npm 11.9.0锁定依赖 | npm ci --ignore-scripts成功 | package-lock未修改，未运行依赖安装脚本 |
| npm test | 15 passed，0 failed | [日志](cloud/frontend-tests-final.log) |
| npm run build | TypeScript和Vite 8.3.1成功，1925模块 | [日志](cloud/frontend-build-final.log) |
| 独立代码复核 | 具体问题已修复，最终限定范围复核无剩余问题 | 根因与修复见[架构审查](../../../planning/2026-10-06/software-architecture-audit.md) |
| 真实浏览器交互 | **未通过／未完成** | 独立Chromium含获准重试仍遇socket Operation not permitted；受支持云浏览器访问环回报ERR_BLOCKED_BY_CLIENT。未改用用户Mac |
| 远端CI | **无workflow** | 推送后核对精确提交Actions／checks／status；无检查不等于通过 |

唯一后端warning来自当前锁定Starlette测试客户端对httpx的弃用提示，不是业务测试失败；本轮未为消除warning擅自变更锁文件。测试并不运行真实模型、采集音视频或安装LCU。

## 针对新增代码的实际覆盖

- Unicode实际文件字节／SHA256独立读回；未批准不写；同键重试不重复保存／参数冲突拒绝
- 拥有者审阅和批准、未登录／错误Origin拒绝、模型无批准／shell／任意文件工具
- 拒绝目录穿越、路径／URL参数、符号链接目录／目标和硬链接；已有文件不覆盖；文本里的命令只保存为数据
- 审批／执行前事务版本变化，待审和已批准排队过期，取消及重复取消
- 执行前取消与写后取消分别验证；迟到回执保持真实状态；关闭／进程重启后不盲目重放
- 写成后崩溃、核验暂不可用、文件被修改；仅只读对账，原文件时间和内容不重写
- 严格校验verified类型、文件名、字节数、SHA256、执行器和范围；伪回执不能成为成功
- 201条其他作业历史不隐藏旧任务的相关或未解决作业
- 工具并发／待处理／结果队列有界，普通配额满仍可Stop；背压时不遗失未结束生产者
- 慢工具期间provider音频和打断继续处理；重复调用参数冲突；断开后迟到草稿清理
- 客户端通知阻塞与provider结果发送阻塞两个取消窗口；取消后无旧response.create，缓存重复结果和错误结果保留代次栅栏
- UI纯逻辑测试：新鲜且未过期才可批准、状态取消范围、恢复操作只清同一任务的同一草稿；TypeScript／生产打包通过

后端整套同时覆盖已有日历、事务、坐姿、配对、数据交换和Google／语音假协议。不是对所有代码的形式化证明，也不代表浏览器UI、真实云协议、自然度或Pi性能通过。

## 交接、阅读与范围

- 基线main `5b8ce5b81dd075cae3cef6787c964bf0406591e2`，讨论提交`597cfe7e90aec8d12a2f68963d2b8f4e1ff54220`
- 单次获准交接包SHA256：`54d6d938ce5da80de19cbd0ac73a6131626cff5276f58e92ec1d1a0c27075b3b`。先核包，再核两补丁重建的19项工作及10项讨论文件，29项逐字节一致
- 云端物化123个相关基线文件，每个Git blob SHA一致；依赖／运行数据／缓存不进入提交
- [阅读记录](reading-record.json)保留停止任务的实际范围，并区分同轮继承的122份Markdown／13份QA报告、库存与云端新补读。没有取得历史逐文件范围，不能称为本执行者重新完整阅读全库
- 继承原改动后增加缺陷修复及回归。更新handoff、README、架构、操作、事务契约、[笔记作业说明](../../../desk-companion/docs/computer-jobs.md)及decision-log。按用户最新缩小发布范围的确认，product.md／work-log.md保留原远端版本，本轮状态另见[独立交接](../../../planning/2026-10-06/cloud-software-delivery.md)
- 只使用临时测试目录和虚构文本。临时环回服务已停止；没有留下测试服务作为用户可用部署

## 发布验证口径

原已核验36项候选中，排除product.md与work-log.md，保留其远端原blob；发布其余34项并增加一份只含本轮结果的独立交接，共35项相对讨论基线的变动。代码、测试和构建结果未改变；本次仅修正文档发布范围，不复制受阻历史内容。

独立分支`codex/fyp-cloud-software-20261006`基于真实远端讨论提交构造Git树／提交；使用base tree保留未物化的其余文件，不提交虚假本地稀疏历史。发布后逐项核对变动blob SHA、精确提交、分支head及全树差异，main与RIG分支保持不变。最终SHA由该文档所属提交与交付链接定位；本文件不把计划中的远端核验预先当成成功。

## 仍未完成

[当前缺口矩阵](../../../planning/2026-10-06/software-architecture-audit.md#4-完成度与证据矩阵)覆盖通用PC／LCU、远端执行权限和云传输范围、长期记忆管理、作业归档／备份、真实语音／AEC／费用／恢复、Pi／触屏／RIG／清洁模块、真人姿态及学校评价。当前可运行的软件基础有实测证据；不能据此宣称全部FYP或个人Agent已完成。
