# Group 2 Current Handoff

更新：2026-10-05。状态：**私人 FYP 仓库已创建；全项目首次提交完成；推送等待新仓库 GitHub 授权**。

## 当前任务与状态

用户授权新建暂名 FYP 的 GitHub 仓库并上传全部项目工作，方便三人协作。已通过登录 Chrome 创建 [tantalum666/FYP](https://github.com/tantalum666/FYP)，网页确认 Private；本地首次提交 `fc5c7c9` 收录6,003文件。当前 GitHub 令牌没有新仓库读写权限，HTTPS推送403，仓库仍为空。

已请用户在 Chrome「📦 FYP协作」完成 GitHub 邮箱验证，并确认仅将 FYP 加入现有令牌的仓库范围，保持其他权限不变；用户已在本轮明确同意仅增加FYP；邮箱验证仍在等待完成。令牌设置页已标为 handoff，仓库页标为 deliverable。不要自动扩大权限、生成新令牌或注册SSH密钥。获确认及验证完成后继续推送，不重做本轮内容整理。

[建仓QA](output/qa/2026-10-05-github-bootstrap/verification.md)记录实际结果及认证尝试；[协作说明](CONTRIBUTING.md)说明成员邀请、克隆、运行及分支 / PR。`origin` 当前为 `https://github.com/tantalum666/FYP.git`，本地分支main；Git身份只在本仓库配置为Yuan Yuchen及GitHub noreply邮箱。尚未发送邀请。

## 本轮完成与证据

- [全读记录](output/qa/2026-10-05-github-bootstrap/reading-record.json)：119份 / 11,237行 / 51批至EOF；新组员原MD已补读，压缩沿用范围。
- 当前 / 退役源码、学校各版、需求、研究、采购、设计、品牌、交付包及QA全部纳入；[输入原件清单](inputs/manifest.json)补14份明确附件，与Downloads原件逐字节一致。
- Gitleaks目录 / 待提交扫描通过；104初始告警全核为校验值 / 公开编号 / 存储键。13个已知私有配置值对比无剩余匹配，107项学校 / 身份 / 旧代码哈希不变，9个ZIP无私有运行文件，无超限文件或剩余软链接。
- 两份旧二进制iOS测试记录只隐去本机测试密码；原件在 `.runtime/github-upload-private-evidence/`，不上传。[清理记录](output/qa/2026-10-05-github-bootstrap/evidence-sanitization.json)。凭据、数据库、已安装依赖、缓存及本机字体链接均留在本地。
- README / product / 软件启动路径和协作入口同步；未改应用行为或学校DOCX / PDF，因此没有重跑旧业务测试 / 渲染。

## 已完成的软件与未验证条件

Desk Companion包含日历、独立常亮 / 触摸入口、姿态标定 / 判断 / 反馈复测、配对、助理、语音适配、输出预设、交换 / 分享 / 备份及iPhone；主动事务首版和UI / UX修复已完成。[产品](product.md) / [软件README](desk-companion/README.md) / [事务契约](desk-companion/docs/task-tracking.md) / [操作](desk-companion/docs/operator-guide.md)。101项后端、11项前端、构建和三端交互是[上一软件阶段QA](output/qa/task-enhancement-ux-2026-10-03/verification.md)，不是本轮新测试或硬件表现。

上一轮本地预览地址为8831 / 5190、隔离QA为8832 / 5191，本轮没有重启或重新核实运行状态。账号owner；原密码在 `desk-companion/.runtime/credentials.json`，不复制到Git或日志。iPhone工程 `desk-companion/frontend/ios/App/App.xcodeproj`、scheme App、bundle `dev.group2.deskcompanion`。私有运行目录不删除。

真实相机与人工标签、Pi常亮 / 触摸 / 并行负载、实际语音 / AEC / 费用、机械角度 / 供电 / 物理停机 / 光学、Google本人OAuth、Apple真机签名及DGX配额仍需外部条件。模型默认未启用；不监控邮箱 / 全电脑、不代替用户确认动作。学校Proposal和逐人列工作的团队日志保持原样；40 / 30 / 30仍为计划份额。

## 唯一下一步

**用户完成 GitHub 邮箱验证并确认仅增加 FYP 的令牌仓库范围后，推送main，核对远端HEAD与全部文件树，再将上传状态收尾为已验证。** 后续实机闭环仍未完成，不被此次建仓替代。
