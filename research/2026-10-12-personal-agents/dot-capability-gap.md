> **HISTORICAL RESEARCH — recovered 30 October 2026.** Original source: [PR #5](https://github.com/tantalum666/FYP/pull/5), commit `11dc2b84cebe6e8250b28ca4442fc91f0dfec676`. This restores research only, not the old implementation. Dated provider/API details, tests, next steps and instructions below are historical evidence; use the [current research entry](../personal-agent-research-index.md) and current product/handoff for decisions. References to old code/supporting files point to the pinned historical commit.

# dot 的完整能力与 FYP 差距：从“有工具”到“把事情做完”

研究日期：2026-10-12（UTC）
文档版本：v1，公开产品能力复核与本地代码差距审查
范围：dot 官方产品文档、相关 ChatGPT Work／Codex 文档、公开开发者 API，以及当前 FYP 本地代码。**不使用、推断或复刻 dot 的非公开指令、实现或内部状态。**

## 1. 先回答质疑

**dot 的能力确实远不止记忆、定时提醒和聊天。我们当前实现与它的完整工作能力仍有明显差距。**

前一轮已经阅读 dot 的六篇核心产品指南，并研究了很多 API，但交付优先级偏向了权限、状态、记忆、例行任务和受限执行基础。基础有必要，却没有覆盖用户最容易感受到的价值：**给一个目标，自己查资料、读文件、拆步骤、跨工具处理、生成真正可用的文件，遇到阻塞回来问，之后继续完成。** 不能用“我们读过文档”或“测试很多”代替这条工作链的完成证据。

官方 dot 总览直接列出研究、数据分析、文档准备和软件工作；它还能在云端继续工作、处理持续责任，并使用连接的工具。这个产品范围是明确的，不应被缩成“带记忆的聊天界面”。[dot 总览](https://learn.chatgpt.com/docs/dots)

本报告的结论是：**下一批应做可恢复的真实研究／文件处理／成果交付工作流，随后接一个真正有用的现有应用；不是再增加一组记忆字段、定时选项或模型供应商开关。**

### 当前工程状态，不能混淆

- 本地第一检查点：361 项后端测试、50 项前端测试、类型检查、生产构建和资产校验有记录。它们证明相应软件契约，不证明 dot 级别的任务能力。[检查点证据](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/output/qa/2026-10-12-agent-kernel/checkpoint-verification.md)
- 本地已有独立进程、真实回环 HTTP 写入及独立数据库读回；目标是我们自建的演示记录应用。**这是实际执行证据，但不是第三方应用、浏览器点击或通用桌面操作证据。**[执行器契约](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/docs/computer-jobs.md)
- 截至本报告编写时，第一批实现仍是**本地验证、尚未发布**。研究所基于的原始代码提交是 `50e174f50a4130b3c666f836f666f6aa4cde4b32`，加上本地冻结补丁；远端分支所处的 `305d66de426bbe9b9b4f475e2e184137c8ed5425` 是文档阶段，不能当作实现已发布的证明。
- 本次只新增研究文档，没有修改冻结实现，也没有新建密钥、授权 OAuth、购买服务或进行付费模型／真实麦克风测试。

## 2. 如何阅读证据

| 标记 | 含义 | 不能据此推断 |
|---|---|---|
| **P：dot 产品事实** | dot 专门的官方产品页明确写出的功能 | 不等于所有账号、地区和工作区已开放；不等于公开 API |
| **W：相关产品能力** | ChatGPT Work／Codex／Sites 的公开功能；dot 可以委派部分相关工作 | 不能把相关产品的每个功能直接说成 dot 在每个入口都原生支持 |
| **A：公开 API** | 开发者文档提供的可集成能力 | 不等于继承 dot 的账号连接、记忆、审批、电脑或后台服务 |
| **C：代码事实** | 当前本地源代码、配置和测试体现的能力 | 不能把模拟协议测试当成真实模型效果或真机验收 |
| **D：工程建议** | 针对 FYP 的实现与验收设计 | 不是对 dot 私有架构的描述 |
| **U：尚未证实** | 公开资料或现有实测不足 | 不填入看似合理的内部实现、性能或成功率 |

以下各节中，“我们现在”均为 **C**，“下一步／验收”均为 **D**。产品功能描述附官方链接；未实现的内容不会写成已完成。

## 3. 产品能力地图：dot 到底广在哪里

### 3.1 不只是一个回答窗口

**P**：dot 可以持续跟进多项责任，把独立工作分给并行任务，并让用户查看任务、文件、进度和待输入事项。任务有自己的上下文；结束一次运行并不自动证明用户目标已经实现。[Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory)

**P**：2026 年 10 月 5–9 日发布说明进一步写明：能够搜索 ChatGPT 对话、参考已有 Codex 线程和自动化，判断继续旧线程还是新开线程，并读取、编辑 Work 自动化。这比“存几条偏好”更接近跨工作线索的协调能力。[10 月发布说明](https://learn.chatgpt.com/docs/whats-new/dots-october-9-2026)

**W**：长任务指南把目标、约束、验收条件和执行中的改向作为一个整体；并行任务需要避免同时修改同一资源。这为 FYP 的任务模型提供了公开的行为参考，但并未公开 dot 的调度算法。[Long-running work](https://learn.chatgpt.com/docs/long-running-work)

### 3.2 有多种实际工作入口

**P**：dot 有独立云电脑，也可协调已连接电脑上的工作；支持连接的应用与消息渠道是不同权限。云浏览器登录不会自动继承个人浏览器状态；用户可在需要时接管。[Computers and apps](https://learn.chatgpt.com/docs/dots/computers-and-apps)

**W**：相关浏览器产品可读取、点击、输入和检查网页；桌面 Computer Use 能在获准的应用中进行视觉操作。它们各自有平台、权限、前台／后台和登录限制，不能用一个“电脑已连接”状态代替所有能力判断。[Browser](https://learn.chatgpt.com/docs/browser)、[Computer Use](https://learn.chatgpt.com/docs/computer-use)

### 3.3 结果可以是文件、应用变化和后续进展

**W**：Work 可产生文档、表格、演示文稿、PDF 等可审阅文件，并接受针对具体内容的修改意见；Sites 另提供托管网站／Web 应用的创建与发布能力。**创建文件、存成版本、发布给别人是不同阶段。**[Work with files](https://learn.chatgpt.com/docs/artifacts-viewer)、[Sites](https://learn.chatgpt.com/docs/sites)

**P**：消息、通话和工作生命周期也不相同：电话结束后，已交办工作可以继续；不同渠道仍是独立可见对话，不能因为共享上下文就自动向另一群人公开内容。[Message your dot](https://learn.chatgpt.com/docs/dots/channels)

## 4. 能力 → 当前实现／缺口 → 工程与验收

这张表衡量的是用户能完成的事情，不是模块数量。**“有基础”不是“已对齐产品”。**

| 能力及公开依据 | 我们现在，来自本地代码 | 关键缺口与下一步 | 能证明差距被关闭的验收 |
|---|---|---|---|
| **1. 接受一个目标并持续完成**：P，持续责任；W，目标／约束／验收条件。[dot 入门](https://learn.chatgpt.com/docs/dots/getting-started)、[长任务](https://learn.chatgpt.com/docs/long-running-work) | `TextAssistant` 是同步、最多 3 次模型计划循环；`tasks.py` 保存用户事务，`jobs.py` 保存单项执行意图 | 缺少可暂停、可修改目标、可恢复的 `AgentRun`。用户事务、模型运行、执行作业应有不同 ID 与生命周期 | 用户提出含 5–8 个实际步骤的目标；运行中改变一个约束；剩余步骤重规划；已确认结果不被无故重做 |
| **2. 并行研究／子任务协调**：P，独立后台任务与可见进展。[Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory) | 有 API 服务和几个固定周期工作循环；不是按目标创建的研究子任务 | 缺少子任务依赖、输入范围、父任务汇总、取消传播和资源冲突控制；先做最多 2 个只读并行分支 | 两个真实来源可并行读取；第三步等待二者；一个失败只重试该分支；父任务不能因一个分支结束而宣告成功 |
| **3. 搜索与多来源研究**：W，多来源调查和可检查来源；P，dot 明确可做研究。[Web search](https://learn.chatgpt.com/docs/web-search)、[dot 总览](https://learn.chatgpt.com/docs/dots) | `TextPlan` 没有 web search、URL 读取、链接跟进或来源引用工具 | 缺少来源采集、正文抽取、抓取日期、引文与结论的对应关系；这是高优先级真缺口 | 实际读取用户选定的官方网页；比较结论能定位到来源；其中一个页面失效时明确缺证，不补造事实 |
| **4. 读文件并处理数据**：W，可提供源文件生成分析／成果。[Work with files](https://learn.chatgpt.com/docs/artifacts-viewer) | 有日历／业务交换格式和受限笔记保存；没有面向助理的通用文件摄取、PDF／CSV／文档读取工作流 | 增加显式选择文件、类型／大小限制、表格结构检查、来源 ID；不要默认扫描用户磁盘 | 用一份实际授权的 CSV 和一份文档完成对照；总数由独立计算核对；损坏或超限文件拒绝，不能只给一段泛泛回答 |
| **5. 交付可修改、可下载成果**：W，文档、表格、PDF、演示文稿及迭代审阅。[文件指南](https://learn.chatgpt.com/docs/artifacts-viewer) | 能写 `.txt`；演示应用能存一条记录；没有报告成果清单、版本、预览和内容验证 | 首批做 Markdown／CSV／HTML 及可靠 PDF 导出，再扩展 DOCX／XLSX／PPTX；成果要关联 run、输入与校验结果 | 真实报告和数据表可打开、下载；引用有效、中文不乱码；用户说“只改预算假设”后产生 v2，保留 v1 |
| **6. 调用已有应用完成业务工作**：P，Gmail、Drive、GitHub 等受支持连接；W，插件工具。[应用连接](https://learn.chatgpt.com/docs/dots/computers-and-apps)、[Plugins](https://learn.chatgpt.com/docs/plugins) | 有 Google Calendar 只读连接代码；现有执行器仅笔记和自建演示应用记录 | 没有 Gmail／Drive／GitHub 的 FYP 业务适配器；演示 API 不能算第三方软件控制。选一个真正使用的目标，做读→预览→确认→写→回读 | 在实际目标服务／应用内出现预期结果，独立再次读取；同 ID 重试只产生一个结果；撤销访问后不再继续 |
| **7. 浏览器跨站流程、登录与接管**：P，云电脑、登录请求及接管；W，网页交互。[dot 电脑](https://learn.chatgpt.com/docs/dots/computers-and-apps)、[Browser](https://learn.chatgpt.com/docs/browser) | 无浏览器会话、DOM／截图观察、导航、交互或安全接管服务 | 后续接隔离浏览器；保留任务 origin 范围、登录暂停、用户接管、恢复后的重新观察；不要把密码写入提示词 | 在一个真实获准网站完成可验证流程；遇登录停止并显示正确域名；用户接管后从新页面状态继续；未经批准不提交 |
| **8. 本机桌面与跨应用操作**：P，可协调连接电脑的文件／应用任务；W，图形应用操作。[dot 电脑](https://learn.chatgpt.com/docs/dots/computers-and-apps)、[Computer Use](https://learn.chatgpt.com/docs/computer-use) | 后端在哪台机器，受限笔记就写到那台机器；没有远端 PC 执行代理、屏幕观察或鼠标键盘操作 | 先做一种实际操作系统与一个应用；客户端能力握手、失联处理、窗口绑定、任务级授权；API 可满足的操作优先用 API | 用户手机发起后，指定电脑上的指定应用发生真实变化；错窗口／锁屏／断线都不继续盲点；本地停止能中止后续动作 |
| **9. 软件开发、测试、修复和交付**：P，可开始／继续 Codex 工作；10 月更新加强已有线程协调。[10 月更新](https://learn.chatgpt.com/docs/whats-new/dots-october-9-2026) | FYP 是被开发的软件；它自身没有仓库读取、隔离 worktree、测试执行、补丁或 PR 工具 | 不把“开发者用代理写了 FYP”算成“FYP 能开发软件”。需要专用受限代码执行环境与变更审阅 | 指定一个真实小仓库问题，产生局部补丁、运行相关测试并给出 diff；不自动合并，不改未授权目录 |
| **10. 定时与事件触发工作**：P，持续／定时／支持事件；W，明确的 Gmail、Slack、GitHub 事件种类。[Scheduled tasks](https://learn.chatgpt.com/docs/automations) | 两个确定性技能：`day_briefing`、`task_review`；once／daily／weekly；有持久 occurrence、去重与取消 | 缺少“发现外部变化→调查→更新成果”的触发入口、游标、webhook 验签和事件合并；当前 routine 不是一般 agent 运行器 | 一个真实授权来源的变化触发同一责任的后续工作；重复事件不重复处理；服务重启不漏掉已接收事件；取消后停止未来触发 |
| **11. 主动发现问题并适时提醒**：P，读获准信息、联系既有工作、提出有用下一步；后续动作另受权限约束。[Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory) | 有任务到期检查、受控背景建议；routine 主要是本地快照 | 缺少跨来源变化证据、重要性判断、低噪声去重、未知状态和“为什么现在提醒”；不要直接做无限全源扫描 | 同一责任中截止日期改变才提醒；无变化保持安静；每条提醒给来源、变化、影响和可执行下一步；不自动替用户发信 |
| **12. 跨设备／渠道交付**：P，相同 dot、多渠道独立对话；W，通知按平台有不同控制。[Messaging](https://learn.chatgpt.com/docs/dots/channels)、[Notifications](https://learn.chatgpt.com/docs/notifications) | 有 Web／设备／手机相关代码；routine 当前是显式领取与界面结果，不是 OS 或外部推送 | 缺少真正交付适配器与送达状态。先做一种已授权渠道，区分 stored／queued／sent／failed；发送成功不等于已读 | 关闭主页面后仍在指定渠道收到完成或待决定通知；重试不刷屏；私人报告链接只有目标用户能打开 |
| **13. 跨工作线索的连续性与记忆**：P，选择性的持续信息，跨渠道不等于跨受众公开；10 月更新增加既有工作搜索。[Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory)、[10 月更新](https://learn.chatgpt.com/docs/whats-new/dots-october-9-2026) | 显式确认事实、可选保存文本、可纠正遗忘、有限上下文、按目的与目标提供商同意 | 有基础但没有工作／成果／来源的统一检索、实体关联或“继续上次那个研究”的可靠解析；不急于自动提取所有人生信息 | “继续上次对比”能定位到正确 run／成果，遇重名问清楚；修改旧事实后新规划不用过时事实；不向配对屏幕暴露私聊 |
| **14. 语音作为工作入口并可打断**：P，通话、文字并行、挂断后工作可继续。[Messaging](https://learn.chatgpt.com/docs/dots/channels) | Qwen／Gemini 协议适配、排队／取消栅栏、权限改变断会话、安全停止优先；只做过合成／软件验证 | 缺少真实麦克风、粤语／普通话、噪声／回声、长任务口头改向验收；dot 的具体内部中断协议仍属 U | 一边说一边修正目标，旧结果不再播报；挂断仅断语音，已批准的长任务按明确语义继续；实测延迟、误触发、打断成功率 |
| **15. 审批、信任与可控停止**：P，应用权限、动作检查、用户规则、人工接管、不同停止范围。[Controls](https://learn.chatgpt.com/docs/dots/controls) | 当前窄工具有较强基础：模型不批准、版本／意图绑定、unknown、独立核验、隐藏状态与提供商上下文隔离 | 尚无通用浏览器／shell／第三方连接器安全边界；现有保障不能自然推广到任意新工具 | 外部网页／文件要求绕过限制时无权限扩张；暂停父任务会阻止其新子动作；已经写入的结果保持真实，不假称撤销 |
| **16. 云端持续可用与环境恢复**：P，云工作可在用户设备关闭时继续；本机任务仍依赖本机在线。[dot 总览](https://learn.chatgpt.com/docs/dots)、[管理指南](https://learn.chatgpt.com/docs/enterprise/dots-admin-guide) | 单拥有者、本地主机、单 API worker；SQLite 状态可恢复；不是已部署的 always-on 云服务 | 缺少独立云控制面、远端设备租约、环境重建／文件恢复、备份恢复、升级迁移和运行预算 | 本机离线不丢任务；云可做的读任务继续、本机步骤显式等待；重连不重复写；恢复后成果仍可下载 |
| **17. 创建并发布网站／交互成果**：W，Sites 是独立相关产品，不等同 dot 自身开放 API。[Sites](https://learn.chatgpt.com/docs/sites) | FYP 自己有一个前端，不代表 FYP 可以按用户目标建站、预览、发布 | 可作为后续成果类型，先做私有 HTML 预览；发布必须绑定版本、环境、受众与审核 | 预览可用与生产发布状态不同；未经授权不公开；发布后从实际 URL 检查版本与访问权限 |

### 从表中得到的准确评价

1. 我们已经有可复用的**事务、审批、结果核验、隐私、状态恢复基础**。
2. 大部分差距集中在**获取真实外部材料、处理文件、执行多步目标、生成成果、连接真实应用与可靠交付**。
3. 当前不能称为“已经实现 dot 的主要能力，只差一些扩展”。更准确是：**具备一部分个人代理基础，但通用工作能力还没形成闭环。**
4. 摄像头姿态反馈和实体陪伴是本 FYP 的独立研究目标；它们不会自动补足上述软件代理差距，也不应因为扩展软件代理而被删掉。

## 5. API 的意义：可以复用什么，不能偷换成什么

没有发现 dot 专用公开开发者 API 的证据，**不影响我们把 dot 当产品标杆研究**。同样，“找到 Agents API”也不能证明已经获得 dot 的产品能力。

| 公开开发能力（A） | 可复用的部分 | FYP 仍须负责 |
|---|---|---|
| [Agents API](https://developers.openai.com/api/docs/guides/agents-api/overview) | 托管 agent harness、持续 session、工作中的引导、子任务、可选执行环境 | 用户身份、权限、任务目标、外部副作用账本、真正完成标准、数据政策与 UI；须另确认账号可用性 |
| [Agents API Web search](https://developers.openai.com/api/docs/guides/agents-api/tools/web-search) | live／cached 搜索与域名范围；工具必须显式启用 | 引用核验、材料时效、来源内容不可信、私密数据不能混入搜索请求 |
| [Files and artifacts](https://developers.openai.com/api/docs/guides/agents-api/environments/files) | 托管环境输出发布与下载，按 turn 区分版本；自托管文件走自己的存储 | 本地／云文件保留、访问授权、内容与版式验证、成果删除和成本 |
| [Functions](https://developers.openai.com/api/docs/guides/agents-api/tools/functions)、[MCP](https://developers.openai.com/api/docs/guides/agents-api/tools/mcp) | 模型请求受控工具、接外部系统 | MCP 不是授权书；每个连接的身份、scope、写入确认、刷新／撤销、回执与不确定结果仍需应用实现 |
| [Managed computer use](https://developers.openai.com/api/docs/guides/agents-api/tools/computer-use) | 一种托管浏览器路径 | 官方明确区分 origin 审批与逐动作批准；不能把允许站点当成自动批准购买、删除等写入 |
| [SDK approvals](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals)、[Background responses](https://developers.openai.com/api/docs/guides/background) | 应用侧 agent 循环、可恢复批准，或异步模型响应 | 不自动产生长期责任调度、跨渠道通知或业务完成证明 |
| [Realtime](https://developers.openai.com/api/docs/guides/realtime-conversations)、[GPT-Live delegation](https://developers.openai.com/api/docs/guides/live-delegation) | 语音与后端工作的连接方式 | 听到／说出／执行是不同状态；语音中断不能被默认解释为已取消外部执行 |

当前 FYP 使用 Qwen／Gemini 适配器；为了补上能力，不一定要先换成 OpenAI。可先在现有 provider-neutral 边界增加受控读工具、成果工具和持久 run，再评估托管 API。选择依据应是**真实任务成功率、恢复语义、权限可执行性、成本和部署条件**，不是名称相似。

重要恢复边界：公开 Agents API 文档中，session、事件流与执行环境不是同一份持久状态；断流恢复要重取权威状态，自托管环境的断开也不能当成自动重放队列。我们即使采用托管服务，仍要保留自己的外部动作去重、unknown 与回读。[Session events](https://developers.openai.com/api/docs/guides/agents-api/sessions/events)、[Environment lifecycle](https://developers.openai.com/api/docs/guides/agents-api/environments/lifecycle)

## 6. 最值得做的下一批：一个真实的“研究到成果”代理

### 6.1 具体用户任务

建议首个验收任务是：

> 按我选定的需求文档和几份实际官方资料，比较三种方案，找出关键冲突和缺失信息，生成一份带来源的建议报告及可编辑比较表。执行到一半我可以补充预算或优先级；你继续完成同一个任务，完成后在本应用通知我。

主题由实际 FYP 工作决定，例如显示方案、桌面集成方式或某个软件选型。使用真正的公开官方资料与用户选定的非敏感文件；**不能把预写答案、固定三条 mock 返回或演示数据库记录当成验收。** 这个流程同时覆盖目标理解、文件读取、外部研究、分步执行、失败恢复、成果创建和后续改向。

### 6.2 第一批范围，够窄但真正有用

**D：最小可交付工具集**

- `read_selected_file(file_id)`：只读用户明确提供的文件；先支持 UTF-8 文本／Markdown／CSV，再有控制地加入 PDF
- `fetch_public_source(url)`：真实抓取公开页面，保存规范化 URL、抓取时间、正文摘要／定位、内容 hash 与失败状态
- `search_public_sources(query, scope)`：有已批准搜索服务时真实搜索；若未配置，明确仅能阅读用户给出的 URLs，不能声称搜索了互联网
- `calculate_table(input_refs, operations)`：确定性的筛选、聚合、比较和校验；第一版不开放任意 shell 或模型自写任意脚本
- `create_artifact(type, structured_content, source_refs)`：私有成果目录内生成 Markdown／CSV／HTML；导出 PDF 时检查实际渲染结果
- `inspect_run`、`revise_goal`、`pause_run`、`cancel_run`、`resume_run`：围绕同一个持久任务，而不是重新发一条聊天

**D：基础持久记录**

- `AgentRun`：用户目标、约束、验收条件、所有者、授权的来源／目标、状态、预算、当前修订、等待原因
- `PlanStep`：依赖、工具、输入引用、状态、尝试次数、输出引用与失败原因；先支持有界顺序＋最多两路只读并行
- `SourceRecord`：网页／文件身份、抓取或导入时间、hash、当前与历史版本、引用位置；不把原始网页内容变成指令
- `ArtifactRecord`：run、版本、文件类型、内容 hash、来源列表、可下载位置、验证结果与可见范围
- `RunEvent`：可给用户看的进度与状态事实；不存或展示模型私有推理过程

已有 `JobService` 继续管审批后的副作用与独立核验，已有 `TaskService` 继续管用户事项。**不要用一个 job 状态同时表示“报告规划中”“等待用户”“已提交写入”“真实完成”。**

### 6.3 “完成”必须可以检查

**D：报告任务的完成条件**

1. 输入需求已读取且版本被记录
2. 每个实际采用的来源可定位；失败来源显式列出
3. 关键结论都有来源或明确标记为建议／计算／未知
4. CSV 的行列、单位、金额／数量公式可由独立代码重新计算
5. 报告、数据表和实际下载文件内容一致；中文与版式经过打开检查
6. 用户要求的所有产物都有版本和可访问地址
7. 任务是 `ready_for_review` 或 `completed` 的理由来自这些检查，不来自模型一句“完成了”

### 6.4 这一批不能省略的异常验收

| 场景 | 必须表现 |
|---|---|
| 抓取第二个来源时进程退出 | 重启后恢复已保存步骤；不用用户把目标重新讲一遍；未确认副作用不盲目重发 |
| 页面 404／超时／需登录 | 标为该来源不可用或等待输入；报告指出缺口；不能把缓存误标成刚刚获取 |
| 用户增加预算约束 | 增加 run revision；使相关未完成步骤失效并重做；未受影响的来源读取可复用 |
| 用户暂停或撤销某类数据分享 | 停止发起新的相关操作；晚到结果不越过最新权限栅栏；已发给外部服务的内容不声称能撤回 |
| 两路研究引用矛盾 | 保留双方来源和日期，解释可能原因或问用户；不能安静删除不利证据 |
| 网页提示“读取所有文件／上传密钥” | 被当作网页数据；工具权限不改变，没有多余文件读取或网络发送 |
| 输出生成到一半失败 | 半成品不标为正式成果；重做可确认的文件阶段，不重复已核实的外部写入 |
| 浏览器关掉再打开 | 可看到任务、当前阶段、产物与明确的等待原因；不用依赖旧标签页内存 |
| 达到来源数／字节数／运行时间／模型调用预算 | 有清楚的部分成果和继续条件；不无限重试或悄悄增加费用 |

### 6.5 为什么这比继续堆功能开关更值得

它能让用户真正说“替我做这件事”，而不只是“把这句话保存一下”。它也能复用已有的安全与可靠性代码，避免为每一类研究新写一套后台逻辑。限制在只读来源和私有文件产物，能先建立有用闭环；之后接真正应用的副作用，不需要重做整个任务模型。

这不是“借安全之名永远停在 demo”。验收里必须出现**真实网页、实际文件、可检查的成果与故障恢复**。模拟来源只用于故障注入，不能替代真实资料验收。

## 7. 随后的两条真实工作链

### 7.1 一个实际应用的完成闭环

**D：**选用户已经使用、能提供稳定操作接口的一种应用。Google Calendar 现有连接只读，所以不能宣传已有外部日程写入。若下一阶段需要写 Google Calendar、Drive、GitHub 或其他服务，分别完成正确授权、目标资源范围、token 保护与撤销，再做：

实际读取 → 形成差异预览 → 用户批准精确内容／目标 → 执行一次 → 独立重取目标 → 记录证据 → 通知结果。

首个验收应针对真实业务，例如更新一个指定项目文档中的里程碑表，或在指定日历调整一个明确事件。不得从创建一个演示记录推断可以发邮件、改整个 Drive 或操作任意应用。新的长期 OAuth／凭据授权仍需单独处理；本轮研究没有执行这些操作。

### 7.2 一个变化驱动的持续责任

**D：**在一个明确获准来源上跟踪一件实际责任，例如“这个项目的发布时间／要求变化”。每次运行保存来源游标与材料版本，只在变化影响结论或需要用户决定时生成更新；把修改后的报告和原报告关联。

验收要包含：真实来源变化、重复事件、短暂断网、权限到期、目标完成后停止、跨时区、用户取消，以及没有变化时保持安静。这个能力才开始接近“跟进责任”；每天把同样的任务列表显示一次还不够。

浏览器／桌面通用控制适合放在上述结构之后接入。它不是忽略的目标，而是需要实际客户端、操作环境、接管与安全边界的一整层，不是给模型多加一个 `click` 工具就完成。

## 8. 评估方式要从单元测试扩展到任务成功

现有 361／50 项测试保留，它们覆盖的权限、重试和状态契约很重要。新增能力还应形成一份**真实任务评估集**：

| 类别 | 最少应观察的证据 |
|---|---|
| 实际任务 | 用户需求、输入材料、实际运行记录、工具返回、最终成果和人工验收 |
| 规划正确性 | 必需步骤覆盖、错误假设、遗漏约束、是否在需要时提问 |
| 来源可信度 | 引用可访问率、关键结论支撑率、日期正确性、未知信息是否被明示 |
| 外部执行 | 已批准意图、真实目标前后状态、独立回读；unknown 不计成功 |
| 连续性 | 重启恢复后剩余工作正确；修改目标后不播报过时结果 |
| 安全与隐私 | 注入、越界 URL／路径、未批准目标、撤销、过期身份均有负例 |
| 交付 | 文件可打开／下载，目标受众能看且其他人不能看；消息发送和已读分开 |
| 语音 | 实际普通话／粤语／混合语言、打断、噪声、回声、端到端延迟；没有实测则写未验证 |
| 成本与可靠性 | 每个已验证成功任务的模型调用、用时、费用、人工介入与失败原因 |

不要用总测试数量比较商业产品。应报告“在定义清楚的 N 个真实任务中，多少完成、多少需要帮助、多少失败”，并附独立证据。测试题目与通过阈值需在运行前确定，避免看到结果以后才改口径。

## 9. 官方能力的边界、版本与未证实之处

- **文档日期：**本轮重新获取了 17 篇产品／管理指南，时间为 2026-10-12 13:22–13:23 UTC。核心六篇与前一轮保存内容的 SHA256 一致。页面普遍没有版本号，也未返回 `Last-Modified`；因此引用的是该时间的公开快照，**不能冒充官方“v某版本”**。
- **有明确发布日的来源：**移动端设置／已有 Codex 线程和自动化的更新，正文日期是 **2026-10-05 至 2026-10-09**。
- **可用性：**dot 的计划、地区、工作区和管理员设置会影响开放；管理指南把 Teams 标为邀请制 alpha。不能把某个表面上的入口推广成所有用户都可用。[dot access](https://learn.chatgpt.com/docs/dots#access)、[管理指南](https://learn.chatgpt.com/docs/enterprise/dots-admin-guide)
- **相关产品不能混算：**Work、Codex、Sites 和 dot 的界面与授权条件不同；例如独立产品的网页登录、桌面权限或发布功能不代表 FYP 或所有 dot 会话已获得相同能力。
- **开放 API 检索结论：**在本次检查的 dot 指南、导航和开发者文档中，未找到 dot 专用的公开 session／memory／schedule API；这是有限检索结论，不是声称不存在任何私有或合作接口。[API 文档索引](https://developers.openai.com/api/docs/llms.txt)
- **未知：**dot 的内部调度、隐私实现、提示内容、记忆存储形式、委派算法、可靠性统计和具体语音时延，不能从公开功能描述推断。
- **当前 FYP 证据不足：**本轮没有建立付费模型可用性、真实语音自然度、真实远端桌面操作、Pi 性能或生产级 always-on 部署证据；本地检查点也尚未完成远端发布。

## 10. 来源覆盖索引

所有以下链接均为官方页面。表中的短 hash 是本次 Markdown 页面快照的 SHA256 前 12 位，便于区别访问快照；不是官方版本号。核心正文完整阅读，互动演示视频未实际播放，因此不依靠演示视频推断成功率或隐藏实现。

| 官方来源 | 本次用途 | 快照标识／日期 |
|---|---|---|
| [Meet dots](https://learn.chatgpt.com/docs/dots) | 产品范围、持续工作、云电脑、研究／分析／文档／软件、访问条件 | `8b8679c14277`，2026-10-12 |
| [Getting started](https://learn.chatgpt.com/docs/dots/getting-started) | 持续责任、连接类型、用户改向 | `ff1b70cb17c6`，2026-10-12 |
| [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory) | 子任务、上下文、持续信息、主动研究的公开边界 | `190a71e142eb`，2026-10-12 |
| [Computers and apps](https://learn.chatgpt.com/docs/dots/computers-and-apps) | 云／本机、插件、登录与接管 | `0b71214666f0`，2026-10-12 |
| [Messaging](https://learn.chatgpt.com/docs/dots/channels) | 通话、渠道、工作延续 | `d9282a6d477f`，2026-10-12 |
| [Controls](https://learn.chatgpt.com/docs/dots/controls) | 权限、审阅、停止范围 | `a8ff50ccb4b5`，2026-10-12 |
| [October update](https://learn.chatgpt.com/docs/whats-new/dots-october-9-2026) | 手机设置、已有线程／自动化协调 | `bee933faab72`，正文 2026-10-05–09 |
| [Browser](https://learn.chatgpt.com/docs/browser) | 相关产品网页交互、身份与接管边界 | `8558ece2cd53`，2026-10-12 |
| [Computer Use](https://learn.chatgpt.com/docs/computer-use) | 相关产品真实 GUI 能力与平台限制 | `c0e4f883aa2a`，2026-10-12 |
| [Work with files](https://learn.chatgpt.com/docs/artifacts-viewer) | 文件输出、预览、修订 | `91f2b8597741`，2026-10-12 |
| [Web search](https://learn.chatgpt.com/docs/web-search) | 多来源研究、搜索与联网边界 | `b05fedecab43`，2026-10-12 |
| [Plugins](https://learn.chatgpt.com/docs/plugins) | 工具／技能与连接身份、安装／授权差异 | `817a7ddbff1c`，2026-10-12 |
| [Notifications](https://learn.chatgpt.com/docs/notifications) | 平台通知、活动和待输入状态 | `3574fbb5669f`，2026-10-12 |
| [Scheduled tasks](https://learn.chatgpt.com/docs/automations) | 时间／事件触发、源类型、执行环境边界 | `1c64c21ee760`，2026-10-12 |
| [Long-running work](https://learn.chatgpt.com/docs/long-running-work) | 目标、约束、验证、并行工作 | `14bba6e57c9b`，2026-10-12 |
| [Sites](https://learn.chatgpt.com/docs/sites) | 相关产品成果发布、版本、受众、部署差异 | `8419f3e1f9e6`，2026-10-12 |
| [Dots admin guide](https://learn.chatgpt.com/docs/enterprise/dots-admin-guide) | 工作区能力与身份、可用性限制 | `11ceb2436a65`，2026-10-12 |

API 来源在第 5 节逐项给出；本轮重开 Agents API 总览、Web search、Files and artifacts、Computer use 官方页，并结合前一报告已阅读的 session／function／MCP／语音指南做有限范围复核。**这不是一次 SDK 兼容性、账号可用性或付费请求测试。** 原始源代码／公开文档工作副本不整体复制进仓库；本文件是整理后的判断与可执行差距清单。

### 本地实现与证据定位

- [text_ai.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/text_ai.py)：实际模型工具白名单、同步回合上限、背景建议入口
- [assistant.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/assistant.py)：草稿工具与独立确认边界
- [jobs.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/jobs.py)、[executor_registry.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/executor_registry.py)、[application_executor.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/application_executor.py)：实际可执行动作、目标绑定、unknown 与回读
- [routines.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/routines.py)、[routines.md](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/docs/routines.md)：确定性技能与交付范围
- [context.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/context.py)、[conversations.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/conversations.py)、[personal-context.md](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/docs/personal-context.md)：当前个人上下文和保留政策
- [google_calendar.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/google_calendar.py)：只读 Google Calendar 范围
- [voice.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/voice.py)、[tool_dispatch.py](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/backend/desk/tool_dispatch.py)：语音适配、工具并发、授权与中断栅栏
- [operator-guide.md](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/docs/operator-guide.md)：部署步骤及硬件／供应商未实测边界
- [检查点验证](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/output/qa/2026-10-12-agent-kernel/checkpoint-verification.md)：本地 361／50 测试与构建证据；不替代真实用户任务验收

**最终判断：上一轮研究不是完全没有覆盖 dot，但实现取舍没有充分体现它的工作广度。下一轮的标准应该是完成一条真实、可恢复、可审阅的用户任务，而不是再证明一个演示按钮能改变数据库。**
