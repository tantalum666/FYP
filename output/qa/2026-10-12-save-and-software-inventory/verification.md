# Group 2 · 保存与软件功能盘点 QA

2026-10-12，Asia/Hong_Kong。用户要求先保存现有成果，再列软件功能、已完成与待完成。范围为当前Desk Companion，不恢复旧食品项目为当前要求。

## 保存

[保存前清单](preservation-before-save.json)记录194文件、57,566,785字节、原HEAD和每项hash。第2份v5日志、两轮换装、A1视角／细节及原prompt／研究／QA已提交`e45afd2700e87f07c7e8044a7f67ce3b09237cae`并推送；[读回](preservation-git-delivery.json)核对194项当前字节与提交blob、远端分支一致及main不变。GitHub connector另回读PR #4 head一致、open／未合并；gh GraphQL因令牌PR权限失败，没有扩权。

第一次默认staged空白检查返回2，来自20份实际prompt与自动原始证据。原始字节／hash保持；其余174文件通过，见[诊断与例外](preservation-whitespace-check.json)。未把默认失败写为全量通过，也未为通过检查修改实际输入。首次[Gitleaks](gitleaks-preservation.json)为零发现，真实私有运行目录／凭据／缓存仍受Git忽略。

## 阅读与功能依据

[本轮记录](reading-record.json)继承当前FYP任务139份／12,884行完整阅读、上一阶段144份补读链，并逐项复核当前正文未变。补读AGENTS／product／handoff、协作说明、软件核心聚焦规范、S1–S10、旧架构审查及10月9日整合／3D证据。全库目录／hash仅用于变化检查，没有将其作为全文阅读替代。

源码交叉核对当前API路由、默认关闭配置、LocalNotesExecutor允许范围与独立验证、文字模型配置、前端管理／设备／角色入口、iOS工程及安装／评价脚本；检查当前无`.github/workflows`文件。[软件清单](../../../planning/2026-10-12/software-function-inventory.md)列17模块及待开发／待真实验证；没有新应用代码或测试。

引用历史验证：10月9日整合149后端／15前端与真实浏览器文件闭环；其后3D阶段22前端／26定向后端、构建及浏览器验证。数目不混加，不称本轮重跑，不把模拟、Mac／Simulator、目标Pi／真机／自然语音／真人指标混用。

## 规范与收尾

更新product、两README、架构入口、handoff、decision-log、work-log并新增17模块清单。只保留一个当前建议下一步：先确定一个目标OS与1–2个应用任务，完成有批准与独立结果的执行闭环；A1默认服装／原创VRM及角色细化继续保留。原图／prompt／学校文件／应用源码不变。

[最终本地检查](final-validation.json)记录本地链接、身份／组号、交付物、图片／学校保护、源码无变化及本轮变更读回。后续软件清单／规范和QA沿现有角色分支保存；实际推送与PR状态的最后读回见[收尾交付](inventory-git-delivery.json)。没有合并main、发布应用、付费模型、硬件动作、成员消息／邀请或学校提交。
