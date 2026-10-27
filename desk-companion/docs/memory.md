# 拥有者记忆

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**现行规范／入口**。已按本轮保存状态核对；最新软件、GitHub main 和 Pi 部署分开，Pi 暂停、旧 API 预算关闭。 [新聊天入口](../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

更新2026-10-24，Group 2。这是 Desk Companion 的长期事实，不是聊天全文，也不是电脑作业。

英文：the owner saves, corrects, and deletes facts. The model may read active facts and prepare a draft. A draft does not write. Deleted facts are omitted from later model context. A paired display cannot open this list.

## 行为

- 拥有者在「记忆」页直接保存、更正或删除。每次写入带版本；版本不符返回 `VERSION_CONFLICT`。
- 本地规则无需模型密钥：`记住：…`／`Remember: …` 只准备草稿；`忘掉：…`／`Forget: …` 仅在文字与某一条活动事实完全相同时准备删除草稿。确认前不写库。
- 模型工具是 `memory_query`、`memory_save_draft`、`memory_replace_draft`、`memory_delete_draft`。没有确认工具。确认仍走既有助理草稿接口。
- 发给托管模型的上下文由 `desk/context.py` 的 `pack_conversation` 组装，最多 40 条仍有效的事实。删除后的正文不再出现。密钥、相机帧和笔记文件内容不在这个包里。
- 活动事实最多 200 条，每条折叠空白后不超过 500 字。达到上限是 `MEMORY_LIMIT`，不会静默丢掉旧事实。
- 配对终端访问 `/api/memory` 得到 403，助理草稿列表、确认接口和文字／语音工具也执行相同的拥有者边界。配对文字请求不打包事实，回复缓存绑定调用权限；语音只向拥有者或已启用的本地语音工作进程开放记忆工具。常亮屏不展示这些事实。

## 与电脑作业的关系

受限笔记作业和拥有者指定的一个文件夹共用同一套作业：批准全文，执行器只新建 `<作业ID>.txt`，独立读回字节数和 SHA-256，取消不会假装回滚。见 [computer-jobs.md](computer-jobs.md)。记忆不代替这项作业，也不新开第二套任务系统。

## 现有能力与剩余验证

1. 本文件所述的记忆、草稿和上下文打包。已实现；本次已用真实Omni与虚构事实跑完建立、更正、删除、取消、重复确认、版本冲突及新连接重问。
2. 已在 main 上的专用笔记作业：批准、独立读回、取消。默认关闭。
3. 拥有者指定一个真实文件夹，沿现有作业契约保存、独立读回和取消。已实现，见 [computer-jobs.md](computer-jobs.md)。模型不能提交路径。
4. 文字和语音共用一份可编辑人格文本。已实现，见 [persona.py](../backend/desk/persona.py)。模型不能改这段文字。工具协议仍由程序附加，避免删掉确认限制。
5. 关闭单项跟进后，已经排队的可选文字建议不再发给模型，事务本身保留。已实现。
6. 安静时段推迟新的跟进，同一次检查最多放出 3 条。推迟保存在库里，重启和改保存的时段之后仍按当前偏好执行。已实现。
7. 拥有者配置Omni时，输入框与语音共用同一实时模型；备用文字适配器仍可替换。测试预算与日常使用配置分开。
8. 本轮累计预算经用户授权从10提高至15元，已覆盖真实完整链：Aurora→新连接读取→同ID更正星穹蓝→新连接读取→删除→再问明确未知。假设与取消不写，版本冲突409不覆盖，最新中午偏好读回正确。真人措辞泛化和供应商侧历史擦除未验证。
9. 不在这一步：合并 PR #4／#5、通用浏览器、收件箱、自称姿态准确率或减损效果。

人格重置会保存新的递增版本，旧编辑不能因恢复默认而重新生效；已有配置追加迁移保留正文。保存失败／冲突保留本地草稿，只有明确选择加载当前文本才放弃。记忆、人格及作业尚未包含在现有业务JSON备份中；删除事实不保证从已有提供商会话或历史操作记录中擦除。

2026-10-23续轮已实现：拥有者配置Omni后，文字和语音共用实时会话、短期上下文及本服务的长期事实。前文只在有界RAM缓存和当前面板，不是聊天全文永久存储；旧HTTP文字适配器仍独立保留。记忆变更会结束旧连接、清除短期缓存，下次明确输入加载最新事实，避免重放已删除内容。完整链记录在自动验收QA (local historical material: `output/qa/2026-10-23-ai-acceptance/verification.md`; not included in this checkpoint)。测试发现删除后编造代号、将取消草稿当已保存，已补memory_query要求、零事实提示、排除历史确认记忆回执，并在新连接重测通过；不代表任意自由对话都不会幻觉。详见[统一对话契约](omni-conversation.md)和[场景清单](../../planning/2026-10-23/ai-validation-plan.md)。

充值后续轮完成缺信息／伪指令／语音接续补测，未新增真实用户事实；记忆完整链不重复执行。当前最新QA (local historical material: `output/qa/2026-10-23-ai-acceptance/resumed/verification.md`; not included in this checkpoint)与[交接](../../handoff.md)取代访问拒绝的旧下一步。
