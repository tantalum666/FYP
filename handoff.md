# Group 2 Current Handoff

更新：2026-10-05。状态：**私人 FYP 协作仓库已创建；全项目已推送并完成远端文件核验**。

## 当前任务与状态

用户授权新建暂名FYP的GitHub仓库并上传全部项目工作。[tantalum666/FYP](https://github.com/tantalum666/FYP)现为Private、默认main，当前工程、历史Senplate、学校文件、研究、设计、交付和QA均已推送。首次远端核验6,005个文件，每一路径、文件类型、模式和Git内容哈希与本地提交一致；本轮收尾材料随后纳入同一仓库，最终回读使用同一验证脚本。

用户已明确同意仅给现有GitHub令牌增加FYP，且完成邮箱验证；该范围已保存生效，其他仓库、代码 / 工作流权限、账号权限及有效期未改。没有生成或保存新令牌、没有注册SSH密钥。旧403阻塞已经解决，不能按旧快照继续等待验证。

[建仓QA](output/qa/2026-10-05-github-bootstrap/verification.md) / [远端核验检查点](output/qa/2026-10-05-github-bootstrap/remote-verification-checkpoint.json) / [协作说明](CONTRIBUTING.md)。本地origin为 `https://github.com/tantalum666/FYP.git`，main跟踪origin/main；Git身份仅在本仓库配置为Yuan Yuchen及GitHub noreply邮箱。成员邀请方法已提供，未发送邀请。

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

**Yuan获取Xu Ziqian和Li Wenhua的GitHub用户名，在仓库Settings → Collaborators发送邀请；两人接受后按CONTRIBUTING克隆、运行当前desk-companion，并各自用分支 / PR协作。** 本轮建仓、上传和核验已完成；真实硬件 / 服务集成继续保留为后续独立验证。
