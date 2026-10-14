# 拥有者记忆

2026-10-14，Group 2。这是 Desk Companion 的长期事实，不是聊天全文，也不是电脑作业。

英文：the owner saves, corrects, and deletes facts. The model may read active facts and prepare a draft. A draft does not write. Deleted facts are omitted from later model context. A paired display cannot open this list.

## 行为

- 拥有者在「记忆」页直接保存、更正或删除。每次写入带版本；版本不符返回 `VERSION_CONFLICT`。
- 本地规则无需模型密钥：`记住：…`／`Remember: …` 只准备草稿；`忘掉：…`／`Forget: …` 仅在文字与某一条活动事实完全相同时准备删除草稿。确认前不写库。
- 模型工具是 `memory_query`、`memory_save_draft`、`memory_replace_draft`、`memory_delete_draft`。没有确认工具。确认仍走既有助理草稿接口。
- 发给托管模型的上下文由 `desk/context.py` 的 `pack_conversation` 组装，最多 40 条仍有效的事实。删除后的正文不再出现。密钥、相机帧和笔记文件内容不在这个包里。
- 活动事实最多 200 条，每条折叠空白后不超过 500 字。达到上限是 `MEMORY_LIMIT`，不会静默丢掉旧事实。
- 配对显示屏访问 `/api/memory` 得到 403。常亮屏不展示这些事实。

## 与电脑作业的关系

受限笔记作业和拥有者指定的一个文件夹共用同一套作业：批准全文，执行器只新建 `<作业ID>.txt`，独立读回字节数和 SHA-256，取消不会假装回滚。见 [computer-jobs.md](computer-jobs.md)。记忆不代替这项作业，也不新开第二套任务系统。

## 尚未完成（按顺序）

1. 本文件所述的记忆、草稿和上下文打包。已实现，并用模拟／本地规则测试，没有付费模型。
2. 已在 main 上的专用笔记作业：批准、独立读回、取消。默认关闭。
3. 拥有者指定一个真实文件夹，沿现有作业契约保存、独立读回和取消。已实现，见 [computer-jobs.md](computer-jobs.md)。模型不能提交路径。
4. 文字和语音共用一份可编辑人格文本。已实现，见 [persona.py](../backend/desk/persona.py)。模型不能改这段文字。工具协议仍由程序附加，避免删掉确认限制。
5. 关闭单项跟进后，已经排队的可选文字建议不再发给模型，事务本身保留。已实现。
6. 安静时段推迟新的跟进，同一次检查最多放出 3 条，避免提醒堆积。已实现。
7. 下一步：有花费上限之后，才用同一套工具比较托管供应商。供应商仍未锁定。在那之前不要开通模型账号。
8. 不在这一步：合并 PR #4／#5、通用浏览器、收件箱、自称姿态准确率或减损效果。
