# Group 2 Current Handoff

更新：2026-09-28。状态：**LOG_1_MEMBER_BREAKDOWN_V2_READY_FOR_MEMBER_REVIEW — SOFTWARE_SCOPE_PLANNED**。

## 当前任务和最新指令

用户再次澄清老师要求：一份log sheet中列三个人各自的工作，不能仅备注三名成员。用户对个人归属追问回复“你直接安排”。已按既定职责制作[一页三人明细DOCX](<output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.docx>)／[PDF](<output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.pdf>)；表头列三人，Part I／II／III与Not Done按人分开。既有团队研究被按角色安排，备注明确member-review draft，个人实际归属尚未核验。原学校模板、前一版团队概述和Proposal均保持；[修订QA](output/qa/logsheet-members-v2-2026-09-28/validation.json)。

用户要求梳理新桌面助理的软件类型、平台、跨端、功能及显示内容。已确认手机与电脑都能控制，设备希望触摸屏直接操作；日历与角色是否同一显示区仍未定。关于Linux的追问已解释：现成Raspberry Pi OS运行本组本地应用，不是自制OS；React界面可由Chromium开机全屏呈现，Python后台处理视觉、日历、音频与硬件。

当前聚焦稿：[软件范围与跨端方案V1](planning/2026-09-28/desk-software-scope-v1.md)。必须保留持续坐姿判断、具体反馈及复测、日历、免按键设备语音和计划轻载机械臂。语音候选顺序Qwen、Gemini、OpenAI Realtime、GPT-Live。Senplate食品方案已退休，不沿用其餐厅／顾客角色或品牌作为新产品。

## 已完成与建议状态

- 已全量读取99份项目自有Markdown、9198行、71批，截断部分已补读，阅读期间文件无变化。[阅读记录](output/qa/desk-software-scope-2026-09-28/reading-record.json)。另重读组员原DOCX正文。
- 方案包含三端功能矩阵、Today／Calendar／Posture／Assistant／Records／Settings页面、首次设置／姿态复测／跨端改期三条旅程、角色六状态、局域网与未来远程同步区别、离线与并发处理以及分阶段实现顺序。
- **工程建议未锁定：**React＋TypeScript＋Capacitor手机App、电脑浏览器、Pi kiosk；Python／FastAPI／SQLite本地核心，摄像头／音频／驱动独立工作。官方Flutter也有多平台支持，是备选，不宣称Pi部署已测。
- **显示尚未决定：**软件先分开日历和角色场景；第一阶段同一触摸屏可验证，最终“触屏操作＋独立悬浮角色”更符合兼顾可读性与AVA偏好的建议。没有批准追加第二屏或确定风扇／反射SKU。
- **网络尚未决定：**用户确认平台覆盖，未明确离开局域网后仍须控制。先做局域网为建议；外网入口、云同步、手机后台推送和应用上架分别开发验收。云Qwen不替代设备远程连接。
- 官方资料已复核Pi kiosk／Touch Display 2、Capacitor、Flutter、FastAPI、MediaPipe、Qwen、PWA安装条件；只有纸面可行性，没有新软件构建、相机、API或Pi负载测试。[本轮QA](output/qa/desk-software-scope-2026-09-28/validation.json)。

## 已有学校文件

[一页Group 2团队日志DOCX](<output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.docx>)／[PDF](<output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.pdf>)，记录9月14至27日、填表9月28日，老师要求整组一份且表内逐人列工作；新版表头列三人，文件名仍由Yuan代表。[11页新英文Proposal](<output/submission/2026-09-28/AY26_ProjectProposal_Group 2.docx>)／[PDF](<output/submission/2026-09-28/AY26_ProjectProposal_Group 2.pdf>)及[12页中文v3](<output/docx/Group 2_DeskCompanion_ProjectProposal_ZH_Review_v3.docx>)本轮未改。上轮只读Moodle所见日志#1截止9月28日17:00、Proposal截止9月29日23:59；本轮没有刷新提交状态、上传或代签。三人计划40／30／30不变。

## 尚未完成与唯一下一步

没有启动新题目应用工程、安装包、局域网配对、云端同步、语音API、姿态采集、显示／机械臂或Pi并行验证。技术栈、双屏与Android首版范围均是待讨论建议；旧食品测试不能算新设备验证。

**下一步：三位成员核对新版日志的个人工作归属。**文档结构和双格式已经完成；软件规划仍保留，后续可继续细化触摸屏首页、手机首页及电脑日历布局。若用户直接授权编码，先做同一核心数据的日历三端同步与姿态输入边界；不重复生成学校文件或恢复已取消的食品开发。
