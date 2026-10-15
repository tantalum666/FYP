# Group 2：跨应用 Computer Use 模型比较

核对日期：2026-10-15。状态：公开官方资料与评测口径复核；没有模型调用、桌面录屏、执行器安装或最终选型。用户明确想比较类似computer use的跨应用操作能力。语音能力继续见[语音报告](voice-model-comparison.md)。

## 结论与适用范围

**工程建议，非用户决定：**首轮把Claude Sonnet5.5作为日常桌面GUI基线，与GPT-6.1 Sol对照；复杂任务再比较Claude Opus5.5和GPT-6 Astra。Gemini3.8 Flash／4 Argon是当前挑战者。此顺序来自公开能力、桌面证据和价格；没有同一执行器、同一任务的本组实测，不能宣布跨厂商冠军。

目标是看截图、识别窗口、点击／输入、在浏览器与本机应用之间切换、保存并独立核验结果。调用注册好的日历函数、操作网页、操作完整桌面和长任务自主完成是不同层次。模型、编排程序、电脑执行器和成品助理分别判断。

## 当前模型与执行契约

| 候选 | 当前官方证据 | 本组建议与实际限制 |
|---|---|---|
| Claude Sonnet5.5 | 支持桌面computer toolset；Anthropic的OSWorld2.1 partial为80.1%；标准输入／输出$2／$10每百万token | 日常有明确目标的GUI基线。部分得分不是整项成功率，也不是本组Mac／Linux成绩。[发布与价格](https://www.anthropic.com/claude-sonnet-5-5) |
| Claude Opus5.5 | 同一发布表OSWorld2.1 partial为81.8%；标准输入／输出$4／$20每百万token；厂商定位复杂、开放工作 | 困难任务对照；1.7分差没有充分不确定性资料，不能宣称显著优于Sonnet。[发布](https://www.anthropic.com/claude-opus-5-5) |
| GPT-6.1 Sol | 当前模型卡支持computer use；标准输入／输出$2／$10每百万token | 与Sonnet对照的通用后台，尤其需要混合代码、业务工具和GUI时。当前核读来源没有同口径OSWorld2.1对照，不据此宣布更快或更强。[模型卡](https://developers.openai.com/api/docs/models/gpt-6.1-sol) |
| GPT-6 Astra | 支持computer use；官方对Astra推荐代码执行控制PyAutoGUI／Playwright，structured computer工具仍支持；标准输入／输出$10／$50每百万token | 复杂规划和混合工具路线的质量对照，不未经测量就用于所有点击。[模型卡](https://developers.openai.com/api/docs/models/gpt-6-astra)、[指南](https://developers.openai.com/api/docs/guides/tools-computer-use) |
| Gemini3.8 Flash／4 Argon | 最新指南支持浏览器、移动端和桌面；3.8 Flash是指南推荐的computer-use型号，Argon为强推理候选；工具仍标Preview | 不沿用旧“Gemini仅支持浏览器”的结论。3.8 Flash与3.8 Live不同；Argon不是实时发声前台。动作处理及恢复由接入方实现。[指南](https://ai.google.dev/gemini-api/docs/generate-content/computer-use)、[Argon能力卡](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon) |

Anthropic的`computer_toolset_20260801`有截图、鼠标、键盘等17个成员工具，每项由接入应用在自己的环境执行。OpenAI支持代码执行与结构化动作；Google同样要求客户端执行并传回新状态。三个API均不自动取得电脑权限，也不保证任意macOS／Windows／Linux应用直接兼容。[Claude契约](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)、[OpenAI](https://developers.openai.com/api/docs/guides/tools-computer-use)、[Google](https://ai.google.dev/gemini-api/docs/generate-content/computer-use)。

单价仅为上述标准输入／输出，缓存、思考、截图、工具、长上下文、重试和执行环境另计。低token单价不一定代表低成功任务成本。本人的账户资格与具体地区SKU未验证。

## 评测口径

- Claude80.1／81.8是厂商报告的OSWorld2.1部分得分，不能当80%以上整项完成。
- Google发布表为OSWorld2.0离线子集部分得分：Argon69.2、Astra72.6。Argon方法为3次运行取最高，每次单次尝试、最多500步；不能与Claude2.1数字混排。[发布表](https://deepmind.google/models/gemini/)、[方法](https://deepmind.google/models/evals-methodology/gemini-4-argon/)。
- OSWorld作者推荐2.1，要求代码、任务、资产、网站和镜像固定同一release；作者网页静态正文的较早模型结果不能当最新版排行榜。[作者README](https://github.com/xlang-ai/OSWorld-V2/blob/main/README.md)、[项目页](https://osworld-v2.xlang.ai/)。
- 语音τ-Voice、接话偏好、业务API工作流、浏览器点击和桌面操作不测同一件事。长任务另受焦点、弹窗、状态跟踪、核验和恢复影响。

## Grok Voice与Grok Bot

本次核读的Grok Voice3.0公开语音工具为搜索、MCP和自定义函数；可让语音请求本组computer job，由后台模型／执行器完成。语音工具分数不能证明截图定位、跨窗口或桌面长任务能力。[语音工具](https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech)。Qwen Audio、Gemini Live、GPT-Realtime与GPT-Live也不按语音成绩排GUI榜。

Grok Bot是带持久云电脑、浏览器、命令行、文件和连接器的成品代理，本机电脑为另一项需启用和批准的能力。这不等于购买语音API便获得同款执行环境。[官方电脑说明](https://docs.x.ai/grok-bot/computer-and-apps)。成品可作体验参考，本次没有确认可嵌入FYP的成品控制API或本机GUI兼容性。

## FYP连接与验收

建议同一身份、人格、任务与批准记录：语音入口→现有JobService→可替换电脑规划模型→电脑侧有边界执行器→目标应用→独立读回。模型提出动作，程序负责权限、记录、取消和未知写入对账。当前仅有专用笔记与一个指定目录；通用GUI／远端PC仍未实现。不新建第二套队列，不合并PR #5来假称补齐。

[LCU](../../planning/2026-10-06/personal-agent-discussion-and-next-steps.md)仍为执行器候选，不是模型。本次未刷新其版本或安装，不声称跨模型或Raspberry Pi已验证。

“下周有什么会议”走本地日历工具，按[5秒要求](../../planning/2026-10-15/voice-response-latency.md)测有依据的语音答案。多个应用的修改／导出先迅速返回作业状态，再异步执行；接单与完成分别计时，不承诺所有GUI任务5秒完成。

**首轮计划，尚未运行：**限定目标系统、两个测试应用、允许目录和可传截图／文字，用同一执行器及相同虚构资料比较Sonnet5.5与6.1 Sol，确有困难才加Opus／Astra。指定provider/model、实际可用账户和总花费上限后才开始模型试验。

建议任务：从允许的测试页面读取三项会议信息，在指定本地文档应用整理并另存文件，独立检查内容、名称和位置。另测弹窗／焦点、执行前取消、保存后回执丢失、断线恢复和范围外目标拒绝。记完整正确率、误操作、重复写入、有效反馈／总完成时间、人工介入、步数和每成功任务费用。不能把现有文件夹验证记成跨应用成功。

阅读、来源限制与交付检查见[QA](../../output/qa/2026-10-15-computer-use-comparison/verification.md)。最终模型、目标系统、付费试验与执行器采用均未锁定。
