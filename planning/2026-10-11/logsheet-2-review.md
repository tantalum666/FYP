# Group 2 第二份双周日志制作记录

2026-10-11。状态：**LOCAL_DOCUMENT_COMPLETE / MEMBER_REVIEW_PENDING / NOT_SUBMITTED**。

## 本轮指令与记录期

用户要求先填写新提供的学校《Final Year Project - Log Sheet (Bi-weekly) v5 AY26.docx》。本轮优先完成日志，不推进角色选型或新的软件／硬件功能。按[首份日志记录](../2026-09-28/logsheet-and-proposal-review.md)中明确的下周期，编号为2，记录期为2026年9月28日至10月11日，填表日期为10月11日；下一计划期为10月12日至25日。具体上传期限未在本轮重新核实，不把记录期或26日Progress I准备目标称为日志上传期限。

保留每组一份、分别列三人工作的既有明确要求。姓名／学号按[group-2-details.json](../2026-09-14/group-2-details.json)，专业班级为IT114124 / AIST-2B，导师Marco，Project ID为Group 2。

## 新模板与填写范围

v5的Part III为 **Declaration of AI-Assisted Technologies Used**，与首份v4中的研究结果栏目不同。末行是 **Supervisor's Feedback**，留给导师填写，不用它存放成员备注或生成导师意见。

- Part I：Yuan的软件／AI工作与角色／仓库成果；Xu及Li共同整理的材料购买清单。
- Part II：Yuan的受限PC任务、坐姿与语音评价准备；Xu的Pi／固定相机／音频／供电核对；Li的显示／RIG／安装和停机核对；团队贡献检查与Progress I演示准备。
- Not Done：真人相机／自然语音试验及通用PC控制仍待完成，采购／装配／台架状态仍待成员确认。
- Other：当前及下周期、26日Progress I准备目标、成员工作归属和拟议计划复核。
- Part III：分别声明研究／文稿、代码／调试、界面及角色概念图、此次日志的AI辅助用途。任务1、2、4为OpenAI ChatGPT / Codex，任务3为OpenAI ImageGen。Qwen／Gemini适配器没有被写成已使用的真实语音服务。

## 事实与归属

本轮追问两位硬件成员是否有实际新增进展，用户回复“有列出材料购买清单”。据此写为两人共同的清单工作；没有收到清单细目、个人撰写占比、订单、接线、装配或台架记录，不补造这些内容。

用户10月6日已明确自己负责软件／AI、另外两人负责硬件。日志按此组织，并披露AI辅助开发，不将助手全部代码与测试自动写成学生独立编码贡献。两位硬件成员下一期的具体核对范围是本轮建议分配，提交前应由成员复核，不改学校提案的40／30／30计划比例或宣布新的正式评分。

软件事实依据[当前产品规范](../../product.md)、[完成计划](../2026-10-02/software-completion-plan.md)、[作业契约](../../desk-companion/docs/computer-jobs.md)、[角色契约](../../desk-companion/docs/avatar.md)和[工作记录](../../work-log.md)。已完成本地软件检查、浏览器／模拟器验证与Git保存，不等于真人姿态准确率、自然语音质量、Pi／RIG／光学实测、原创角色建模或通用电脑控制完成。概念图与运行许可样本分开。

## 交付与检查

- [可编辑DOCX](<../../output/submission/2026-10-11/AY26_Logsheet_No2_Group 2_YuanYuchen_250342840.docx>)。
- [对应PDF](<../../output/submission/2026-10-11/AY26_Logsheet_No2_Group 2_YuanYuchen_250342840.pdf>)。
- [构建脚本](../../scripts/build_logsheet_20261011.py)、[模板契约](../../output/qa/2026-10-11-logsheet-2/artifact.md)、[成稿验证](../../output/qa/2026-10-11-logsheet-2/document-validation.json)。

原件SHA256为`d3a9d16189057467a94cc6114e260e23c22f03c2f44e881649dde95c66af57f8`。原模板经打包LibreOffice渲染为一页表格加一页空白尾页，均已查看；仅将表格后必须保留的空段改为1pt，消除空白尾页，正文页像素与修正前完全相同。最终DOCX／PDF均一页，最终渲染页已直接查看，所有填写文字在PDF中可提取且完整。

ZIP包仅`word/document.xml`变化，原节、页式、表格网格、单元格宽度／合并／边框／行属性、原标签和空白导师栏保持。学校原件与首份日志哈希不变。只有填写内容使用局部字号／行距；不重建学校表格或使用通用设计主题。原有直接格式／非Heading式表格标签在样式审查中保持，不为消除提示而改版。

本轮完成138份项目自有Markdown、12,819行全文恢复，49批均已观察并记录区间，阅读期间无变化；[本轮阅读记录](../../output/qa/2026-10-11-logsheet-2/reading-record.json)和[收尾QA](../../output/qa/2026-10-11-logsheet-2/verification.md)保存实际范围与检查。应用源码未改，不重跑既有应用测试。文件在本地完成，未签署、填写导师意见、上传Moodle或对外联系；成员归属复核与正式提交仍由相应人员完成。
