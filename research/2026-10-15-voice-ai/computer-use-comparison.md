# Group 2：跨应用 Computer Use 模型比较

核对日期：2026-10-15。状态：公开官方资料与评测口径复核；没有模型调用、桌面录屏、执行器安装或最终选型。用户明确想比较类似computer use的跨应用操作能力。语音能力继续见[语音报告](voice-model-comparison.md)。

## 结论与适用范围

**工程建议，非用户决定：**首轮把Claude Sonnet5.5作为日常桌面GUI基线，与GPT-6.1 Sol对照；复杂任务再比较Claude Opus5.5和GPT-6 Astra。Gemini3.8 Flash／4 Argon是当前挑战者。此顺序来自公开能力、桌面证据和价格；没有同一执行器、同一任务的本组实测，不能宣布跨厂商冠军。

**同日新增约束：**用户明确程序要运行在树莓派Linux，最终希望操作Pi自身和另一台电脑，并询问先只做Linux是否更简单、是否需VPN及能否单模型兼顾语音与电脑。下文Linux优先和Qwen Omni单模型试验是工程建议，用户尚未冻结首版系统范围或选定模型。

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

## 树莓派Linux、网络与单模型补充

**Linux优先建议：**先验证一个固定Pi OS／桌面版本、两款指定应用和有界目录，随后在另一台Linux主机接同一执行协议，再扩展Windows／macOS。可减少安装、窗口、输入和权限适配组合；不能按OS数量推算节省百分比。Pi本机与远端电脑两种愿景保留，远端仍需目标机执行服务、配对、授权和断线恢复。

Pi运行界面、音频、日历、JobService和执行器，云端运行所选托管模型。Linux／ARM64本身不要求VPN；网络可达、服务地区／账号资格和桌面执行兼容分别验证。GPT-6.1 Sol接受文字／图像并输出文字，不是直接语音模型。[官方模型卡](https://developers.openai.com/api/docs/models/gpt-6.1-sol)。

截至本次核读，OpenAI直连API支持名单未列香港或中国大陆，Google Developer Gemini API名单也未列香港。VPN改变出口不建立官方服务资格，因此不把依赖VPN作为交付前提。[OpenAI地区](https://developers.openai.com/api/docs/supported-countries)、[Google地区](https://ai.google.dev/gemini-api/docs/available-regions)。Microsoft Foundry官方目录已上架6.1 Sol，但尚未验证本人订阅、配额、地区、费用或其computer-tool契约；这是可调查的正式渠道，不是已可用回执。[Foundry目录](https://ai.azure.com/catalog/models/gpt-6.1-sol)。

**单模型可以组成“听说＋看屏幕＋工具调用”的循环，不强制每个点击再接第二个LLM。**下列公开能力支持该工程设计，但不构成专用computer工具或本组GUI成功证据：

| 单模型候选 | 已核能力 | 仍需本组完成 |
|---|---|---|
| GPT-Realtime2.1 | 文字／音频／图像输入，文字／音频输出，函数和MCP工具 | 本地屏幕输入、受限动作执行、审批与核验；不能继承6.1 Sol桌面成绩。[模型](https://developers.openai.com/api/docs/models/gpt-realtime-2.1)、[工具](https://developers.openai.com/api/docs/guides/realtime-mcp) |
| Gemini3.8 Live／Extended Thinking | 图像、音频和视频输入／语音输出、异步函数；Extended侧重多步后台推理 | 自定义桌面动作；Live函数不等于3.8 Flash的computer-use接口。[Live](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live)、[Extended](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live-extended-thinking) |
| Qwen3.8 Omni Flash Realtime | 流式音频／连续图像帧输入、文字／音频输出、自定义函数和远程MCP | 新协议适配、截图定位与动作可靠性；不是现有Qwen Audio适配器换model字符串即可。[型号文档](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash-realtime) |

**按“学生原型、Pi、中文、尽量一模型”约束的工程建议：**先核验Qwen3.8 Omni新加坡SKU及实际账户，再与可获准使用的Realtime／Gemini单模型配置对照。Qwen型号页目前仅列北京／新加坡；有香港workspace不等于此SKU在香港部署。地区、workspace key、模型和服务部署scope须对应。[地区与端点](https://www.alibabacloud.com/help/en/model-studio/regions)。此建议补充先前专用GUI候选，不否认复杂任务可按需委派Sonnet／Sol，也不宣称Qwen的GUI质量领先。

Raspberry Pi OS当前默认Wayland／labwc；具体截图和输入执行器必须适配图形栈及ARM64。官方配置文档已不建议切到停止开发的X11，因此不把全机切换X11作为默认方案。Playwright浏览器路线与任意桌面应用控制分别验收；本次未安装、改系统或验证目标Pi。[Pi配置文档](https://www.raspberrypi.com/documentation/computers/configuration.html)、[官方默认桌面说明](https://www.raspberrypi.com/news/a-new-release-of-raspberry-pi-os/)。

单模型减少第二个LLM交接，但截图／历史、动作步数与思考仍影响延迟和费用；不能直接保证5秒。普通日历查询沿直接工具，复杂作业沿持久任务；音频／姿态／浏览器并行负载和回声在目标Pi另测。[补充QA](../../output/qa/2026-10-15-pi-voice-computer/verification.md)。
