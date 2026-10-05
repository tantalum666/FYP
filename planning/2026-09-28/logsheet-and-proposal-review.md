# Group 2 首份团队日志与提案复核

日期：2026-09-28。用途：记录本次学校文档的依据、改动及交付范围。

## 学校要求与最新澄清

用户确认记录期为2026-09-14至2026-09-27，填表日期为2026-09-28，并最新转述老师要求**每组交一份log sheet**。这一明确要求取代此前从个人姓名栏和平台文件名推断每人一份的判断。用户进一步明确：同一份中要分别列每位成员的工作。新版表头列三人姓名及学号，Part I、II、III各按Yuan、Xu、Li和共同工作组织，Not Done也分别列待完成领域。平台文件名仍用Yuan作为代表；不是三份日志。用户未提供已完成工作逐人归属，回复“你直接安排”，本版因此按既定角色整理为成员核对稿，备注明确individual attribution arranged under planned roles，不把规划当已核验个人贡献。

本轮只读核对[课程页](https://moodle2627.vtc.edu.hk/course/view.php?id=7481)与[Log sheet #1作业页](https://moodle2627.vtc.edu.hk/mod/assign/view.php?id=444246)：日志截止2026-09-28 17:00，需DOCX和PDF；Proposal截止2026-09-29 23:59，也需双格式。查看时日志作业显示尚未提交，本轮未上传或点击提交。

学校Proposal Guidelines列七项：问题、背景、方案及范围、适切性、阶段、交付物和组员职责；不要求市场问卷或调查访问。Project Guide的版式要求为A4、正文12pt、单倍或1.5倍行距、左边至少1.5英寸其余至少1英寸，封面后连续页码。本轮保留学校原件和所有旧提案。

## 团队日志的记录口径

- 学校原始一页横向表格保留，填Part I、II、III与Remark，Project ID为Group 2，Log Sheet No为1。
- 如实覆盖两周中的旧食物方案需求与模拟软件、Marco对混合菜营养和相机成本的反馈、9月25日改题、桌面坐姿／日历要求及语音／显示资料比较。
- 旧食物软件55项后端测试来自既有验证记录，明确为模拟输入，不能证明新桌面设备性能。
- 新设备的相机机位、姿态精度、语音API和角色控制时延均写为未测。没有编造访谈、用户样本、机械臂测试、独立个人编码或导师批准。
- 下周期先定姿态与数据协议，再做Mac上的视觉／日历流程，核对显示可编程接口。每两周整组交一份，提交表内必须直接列每人的工作、发现、未完成项和下阶段计划，并另保留可追溯贡献与AI辅助记录。

## Proposal相对中文第二版的主要修改

1. 保留持续坐姿判断、具体提示及复测为必做核心；将前倾限定为已校准机位下可见的头肩变化，明确遮挡拒判和不能依赖被桌子遮挡的髋部关键点。
2. 把AVA式角色呈现写成待验证显示路线：反射成像和带罩旋转LED按接口、可读性、噪声与延迟择一；区分程序切换预置片段与连续逐帧输入，HDMI不是唯一方式，未宣称已知AVA内部光路。
3. 机械臂仍列计划硬件，限定2至3自由度轻载提示、固定相机、独立电机供电、限位与停机；不扩大到抓取任务。
4. 增加可检查的拟议评价：6名自愿成年参与者、开发／测试各3人、两次录制；宏平均F1目标0.80、正常工作段误报目标不超过2次／小时、持续条件满足后的本地反馈95%不超过2秒。所有目标均未实测，属于待团队／导师审阅的工程建议。
5. 日历至少30个用例、40条普通话／英语命令和10条含糊／禁止动作；语音正确执行目标90%，所有写入确认用例必须通过。声音、角色、机械动作与用户调整分别计量。
6. 按Moodle实际学校节点重排至2027年4月，保留约6个月核心开发；纳入每组一份双周日志和学校AI作为组员的公告，不杜撰AI评分占比。
7. 新生成对应的英文提案，学校七项结构完整；旧Senplate英文稿与桌面中文v1／v2保留作历史。

## 交付入口

- [Group 2团队日志DOCX](<../../output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.docx>)与[PDF](<../../output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.pdf>)。
- [新版英文Proposal DOCX](<../../output/submission/2026-09-28/AY26_ProjectProposal_Group 2.docx>)与[PDF](<../../output/submission/2026-09-28/AY26_ProjectProposal_Group 2.pdf>)。
- [中文版第三版DOCX](<../../output/docx/Group 2_DeskCompanion_ProjectProposal_ZH_Review_v3.docx>)、[中文正文](desk-companion-proposal-zh-v3.md)与[英文正文](desk-companion-proposal-en.md)。
- [日志构建脚本](../../scripts/build_logsheet_20260928.py)、[提案构建脚本](../../scripts/build_desk_proposal_20260928.py)与[本轮检查记录](../../output/qa/logsheet-proposal-2026-09-28/validation.json)。

## 三人明细修订记录

2026-09-28按老师进一步要求新增member-breakdown-v2，保留前一版DOCX／PDF字节不变。Yuan安排统筹、需求、AI／语音与提案；Xu安排硬件、显示接口、供电与机械臂可行性；Li安排日历、TimeTable、隐私／冲突与交互需求。已完成列只取既有团队研究与方案记录，个人归属供成员核对；9月28日新增的触摸屏／手机／电脑讨论只进入下阶段计划，没有回填到9月14至27日的完成项。新版1页已渲染检查，证据见[修订QA](../../output/qa/logsheet-members-v2-2026-09-28/validation.json)，[构建脚本](../../scripts/build_logsheet_member_breakdown_20260928.py)。

## 后续仍需验证

具体显示模块的开放控制能力、最终摄像头机位、树莓派并行负载、机械臂型号与实际动作仍未确定或实测。语音仅保留Qwen、Gemini、OpenAI Realtime、GPT-Live的候选顺序，未开通或测试API。新设备代码、采购、导师签字、学校批准及Moodle提交均不是本次文档交付已完成事项。
