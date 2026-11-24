# Alice 能否替用户用卡付款

2026 年 11 月 19 日，香港。评估基线为已部署的 `85e6aa94`，仓库基线为 `da11c62f`。本次工作核对产品能力、香港适用性及本地 SDK 兼容性。钱包接入仍是工程方案，用户询问可行性并未授权消费。

## 三款产品如何付款

| 产品 | 官方资料确认的流程 |
| --- | --- |
| Grok Bot | 在 Link 路径上，订单卡展示商户、商品和总额。用户选择付款并在 Link 完成授权后，Bot 可使用一次性卡结账。产品也有已存卡路径。[Grok Bot Vault](https://docs.x.ai/grok-bot/vault) |
| OpenAI 的 dot | 在 dot 对话里，用户审阅购买请求并逐笔通过生物识别，然后 dot 使用关联虚拟卡结账。帮助中心列出的上线范围为分批开放的合资格美国 Pro 用户，须满足美国居住、账单地址和信用卡条件。[ChatGPT Wallet](https://help.openai.com/en/articles/20001654-making-purchases-with-chatgpt-wallet) |
| Meta Muse | Muse 使用 Stripe 的 Link，在用户明确批准购买后使用一次性卡。Meta 也说明，使用商户已存付款资料时会把订单详情交还用户审批。[Muse 安全设计](https://muse.ai/security-and-privacy) · [Muse 的结账设计](https://muse.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse) |

## Alice 能复用的接口

Link 提供本机 CLI/MCP 和托管应用 SDK。Alice 可以沿用 OpenAI Sessions、Functions、既有报价和拥有者审批。钱包适配层使用用户授权的 Link OAuth 身份创建一笔消费请求，绑定商户、最终金额、币种和稳定的操作键。托管接入还需要向 Link 注册 OAuth 客户端及回调地址。银行或钱包要求的验证由用户在对应界面完成。一次性凭据交给专用结账组件，模型、普通聊天记录和诊断日志只接收状态和订单引用。虚拟卡可用于普通商家收银表单，具体交易仍取决于商户接受该卡及验证结果。[Link 托管接入](https://docs.link.com/guides/add-payments-to-your-agent) · [Link OAuth](https://docs.link.com/authentication/oauth) · [凭据类型](https://docs.link.com/)

对于一次性购买，收到钱包批准后还要完成商户结账。支付状态不明时用原操作标识查状态。商户改价则重新让用户批准。支付回执、商户订单号和机票票号分别读回。周期采购只有在用户另行授权了用途、金额和周期时才适合采用周期额度。OpenAI 的公开 Commerce 指南介绍的是商家网站怎样承接 ChatGPT Wallet 的付款，目前查到的消费者钱包接口属于 dot 产品。[Link 消费请求与状态](https://docs.link.com/concepts/spend-requests) · [OpenAI 商户侧指南](https://developers.openai.com/commerce/guides/accept-payments)

Link 的托管接入指南明确列出美国和加拿大客户。其 FAQ 还列出其他市场，两处均未列香港。商家所在地与客户钱包资格是两项条件。香港用户能先使用商户支持的本地收银方式，钱包或 3-D Secure 提示交还本人完成。若要求香港本地卡由 Alice 在授权后提交付款，需要确认相应发卡行和支付伙伴给予该应用的生产接入资格。香港已有 Visa 与中银香港的代理支付测试，以及 Mastercard Agent Pay 与本地银行完成的实际接送订单。[Link 资格 FAQ](https://docs.link.com/faq) · [Visa 与中银香港](https://www.visa.com.hk/en_HK/about-visa/newsroom/press-releases/visa-advances-the-next-phase-of-agent-initiated-card-payments-in-hong-kong.html) · [Mastercard 香港实单](https://www.mastercard.com/news/ap/en-hk/newsroom/press-releases/en-hk/2026/mastercard-completes-its-first-live-agentic-transaction-in-hong-kong/)

## 本地证据与下一项验收

FYP 后端的 Python 3.14.5 从临时目录载入 PyPI 上的官方 `stripe-link-sdk 0.2.0` wheel，核对了发行文件 SHA-256。实际 SDK 通过 HTTPX 模拟传输创建一笔 `test=True` 的虚构商户消费请求，同一购买的重试带相同操作键，随后请求审批并读回模拟的待批与拒绝状态。测试禁用了网络连接，没有读取钱包、申请卡凭据或产生扣款。这证明 SDK 与当前后端及该部分请求契约兼容。真实 Link 测试账户审批、商家测试收银、资金回执和出票仍需各自验证。[官方 SDK](https://pypi.org/project/stripe-link-sdk/0.2.0/) · [官方测试模式](https://docs.link.com/quickstart/overview)

本轮聚焦阅读 AGENTS.md、product.md 当前约定、handoff.md、decision-log.md 最新决定、研究索引的竞品与购物旅行章节、历史竞品资料的产品识别部分、纸巾采购卡契约、已上线航班验收及相应执行入口。现有采购卡的金额和改价核验可复用。Kiwi 会话的工具名单只有 `search-flight`，供应商返回旅客可打开的预订链接。上轮 HK$2,006 的报价高于 HK$1,500 预算，20 公斤含费总价也未核实，这个案例应止于报价。首个合适的付款验收是任选一个有测试收银和订单查询能力的合作商户，用测试钱包分别核对同额批准、拒绝和超时后的订单读回。[部署验收](../2026-11-19-flight-ledger/verification.md) · [Kiwi 官方连接器](https://www.kiwi.com/stories/kiwi-mcp-connector/)
