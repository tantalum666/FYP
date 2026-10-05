# RIG-Arm研究核对｜2026-10-05

状态：公开来源研究、文档／静态检查及研究分支上传完成；Draft PR已创建，未合并。未进行实体设备验证。

## 阅读与来源

开工122份项目自有Markdown、11,376行、36批全文至EOF；截断的第8批重读，第11批中间表格补读。范围、排除和15:31:24+08:00完成时间见[reading-record.json](reading-record.json)，阅读期间原文件没有变化。上下文压缩后沿用已读范围，未重做研究或测试。

Chrome核对MakerWorld、商城SKU、Arm开发／MCP／版本／下载／原理图索引；后续Web工具对部分站点提取失败，使用实际渲染的可见正文补足，转录保存在本目录。两个GitHub仓库只读缓存到忽略的.runtime，完整commit和相关源码哈希见[research-checkpoint.json](research-checkpoint.json)与[来源表](../../../research/2026-10-05-rig-arm/source-register.json)。没有执行厂商源码或下载机械模型。

[整机截图](rig-arm-full-unit-shop.jpg)可见Hand-built Full Unit选中、US$124和预售；[MakerWorld截图](rig-arm-makerworld.jpg)为真实网页。二者已视觉查看，未生成／编辑验证图片。装配视频链接仅定位，未观看完整视频，未用作实现证据。

## 收尾检查范围

- 本组Markdown与JSON链接、围栏、组号及来源路径。
- 源码可定位性：Arm工具、local MCP构建／Start、流式文字工具回填、分支微动／示教差异、Opus握手与现有FYP驱动选项。
- 既有107项学校／身份／旧代码保护哈希，以及当前应用代码未变。
- 当前规范与handoff同步，学校DOCX／PDF未覆盖，不重跑既有业务测试或渲染。
- Git分支只包含本组研究、规范与自动QA证据；上游源码、STL／3MF、凭据／运行数据排除。待提交Gitleaks检查通过：两个初始命中均为同一公开源码SHA256，已与固定仓库字节核对；只为两个确切记录路径／这个确切值补精确例外，提供商规则和其他内容继续扫描。

[validation.json](validation.json)：539条本地链接有效、107项保护哈希不变，当前应用源码未改，固定源码快照／接口位置和JSON检查通过。新研究正文及全部修改diff已读回。

检查命令：`python3 output/qa/2026-10-05-rig-arm-feasibility/validate_research.py`、`git diff --cached --check`、`gitleaks git --pre-commit --staged --redact --max-archive-depth 2`。均通过；新添的.gitleaks例外仅匹配经核实的公开校验值。

## Git协作状态

本轮使用codex/rig-arm-research，基于main的5b8ce5b，研究提交761ae78已推送，远端ref和Git tree与本地一致，见[remote-verification.json](remote-verification.json)。已通过登录Chrome创建[Draft PR #1](https://github.com/tantalum666/FYP/pull/1)，页面回读标题／分支／提交与完整正文，且已附加到当前聊天。CLI现有令牌没有PR权限，未扩大令牌，使用已登录页面完成；不自动合并main，不发送供应商／成员消息。收尾材料继续提交到同一分支，最后以git ls-remote和tree回读核对最新提交。

## 未进行的检查与下一步

没有采购、联系供应商、编译／刷写、操纵实体关节、开收费会话、运行学校服务器或采集真人音视频。真实SKU／版本、MCP入口、供电／负载、动作完成／停止／失联、自然语音与原机音频网关仍需设备条件。唯一下一步是取得候选整机的准确版本与工具清单，再确定只读连通及受限驱动台架方案。
