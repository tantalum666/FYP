# Group 2 Current Handoff

更新：2026-10-03。状态：**主动事务首版已实现；本轮UI／UX审查及修复完成，本地可验证**。

## 当前状态

用户明确要求先增强软件、再做交互逻辑审查。Desk Companion现有S1–S10基础上新增Tasks、跨会话进展、截止／下一步／步骤、一次待处理检查、暂停／延后／本人确认完成／恢复、助理事务草稿、可选Qwen／Gemini文字适配和业务备份扩展。见[产品契约](product.md)、[事务契约](desk-companion/docs/task-tracking.md)、[本轮QA](output/qa/task-enhancement-ux-2026-10-03/verification.md)。同日Dot研究已标历史基线，不能再据“尚未实现”回退。

UI保持英文默认／简体中文可切，手机／电脑管理与Linux常亮大时钟／月历分别构图。触摸和常亮入口已有事务数量／待跟进提示；没有替换坐姿必做主线或品牌决定。开发名仍Desk Companion。

## 本轮结果和证据

- 101项后端、11项前端检查、Ruff、TypeScript／生产构建及iPhone模拟器构建安装启动通过。
- 实际UI核对创建、日期、步骤、进展、助理确认、暂停／恢复、本人确认完成／恢复、并发冲突、取消保护、21步输入不截断、偏好退出、断连／重连、英简、320px手机、1024×600常亮和日夜。
- 调度实际在保存的检查时间产生一次提示，设备和iPhone均看到。没有新依据时不反复累加；已有提示保存在SQLite。
- [手机](output/qa/task-enhancement-ux-2026-10-03/09-mobile-tasks-320.jpg)／[常亮](output/qa/task-enhancement-ux-2026-10-03/14-device-day-checkin.jpg)／[iPhone详情](output/qa/task-enhancement-ux-2026-10-03/16-iphone-task-detail.png)。107项旧代码／学校／身份保护文件未变，主7条日程内容与重启前相同。
- 本轮完整阅读沿用同一增强阶段的[117份覆盖记录](output/qa/task-enhancement-ux-2026-10-03/reading-record.json)，压缩后只补读修改与聚焦资料。更早历史和已完成检查见work-log，不重复全库或重跑旧验证。

## 可运行入口

- [主管理／事务](http://127.0.0.1:8831/?page=tasks)／[主常亮](http://127.0.0.1:8831/?surface=device)，开发前端5190。主库7条原示例、0条测试事务。
- 账号owner，原密码在`desk-companion/.runtime/credentials.json`，不复制到日志。主API／Vite已重新启动到新版本。
- QA8832／5191用`.runtime/completion-qa/`，保留9条旧日历、2条本轮测试事务，1个已批准的iPhone。iPhone Simulator继续连接此库；QA样例不是用户真实任务。
- iPhone工程`desk-companion/frontend/ios/App/App.xcodeproj`、scheme App、bundle `dev.group2.deskcompanion`；本地构建目录`.runtime/ios-build`。
- [软件说明](desk-companion/README.md)／[操作](desk-companion/docs/operator-guide.md)／[架构](desk-companion/docs/architecture.md)／[评价](desk-companion/docs/evaluation.md)。

源码交付：[事务与UI／UX版](<output/software/Group 2_DeskCompanion_Tasks_UX_2026-10-03.zip>)，旧版包保留。

## 已知边界

文字默认本地规则，Qwen／Gemini文字与语音分别配置；自动文字建议默认关闭、启用后每日最多20次尝试。没有调用付费模型或证明自然语言准确率／自然度。模型不能确认修改、提交报告或任意移动机械。主机离线不继续调度，iPhone事务未做远程锁屏推送，Google仍是只读日历而非邮件。

真实相机、固定机位、个人标定和人工标签；Pi并行负载／常亮／触摸／音频；真实API与AEC；机械型号／角度／供电／物理停机及显示光学；Google本人OAuth、Apple真机签名和学校DGX配额均待外部条件。未代替用户授予权限、采集真人、采购、提交学校或对外联系。

单API worker；`.runtime`含私有凭据和数据，不删除或打包。模型依赖用`uv sync --frozen --extra vision --extra audio`，检查用`--no-sync`。iOS每次cap sync后按操作指南运行configure-ios-features和prepare_ios验证官方框架。没有借用其他项目账号／发布权限。

学校Proposal和逐人列工作的团队日志保持原样；40／30／30仍是计划份额，不把AI辅助代码归为学生已核实际贡献。

## 唯一下一步

**在目标设备与获准真实语音服务到位后，按既有操作／评价脚本完成坐姿→反馈→复测及语音事务确认的实机闭环，记录准确率、时延和错误操作；本轮无需用户参与的软件增强与交互审查已完成。**
