# Link Agent Wallet 测试卡拒绝原因

2026 年 11 月 20 日，香港。从 `69d9b95f` 恢复，使用已批准的 180 天额度及原 US$1.00 纸巾结账单。**Link 接口返回的完整卡号逐位等于其官方 CLI 1.6.0 README 第 595 行公布的测试示例。该公开示例和实际返回值均未通过 Luhn 校验。** 此前 Stripe Checkout 的卡号输入框已对这笔订单给出无效提示。查到的另一处故障是本地权限解析，已修复。[机器可读观测](observations.json) · [固定版本的官方示例](https://github.com/stripe/link-cli/blob/06d97214935160aa26c848f090ac0d27eaeb5842/README.md#L595)。

## 首次分歧

| 检查点 | 实际操作与结果 |
| --- | --- |
| 上游发行物 | 从 npm 核对当前 `@stripe/link-cli` 1.6.0 的发布压缩包、安装锁文件及本机 `dist/cli.js`。SHA-512 校验一致，已安装的 CLI 文件与发布包内文件逐字节相同。官方 Git 标签指向 `06d97214`，其 README 与本机安装版本也逐字节一致。 |
| Link 接口 | 用官方 Python SDK 0.2.0 对原授权执行了一次带 `include=card` 的 HTTPS GET。在 SDK 解析之前检查响应 JSON，确认 HTTP 200、同一个已批准的授权、同一 FYP 商户及 US$500 月额。卡号原本就是 16 位 ASCII 数字字符串。接口原值与 SDK 结果、与官方公开示例分别做了完整比较，两者都一致。比较在内存内完成。 |
| 独立校验 | `python-stdnum` 2.2 和 FYP 校验器均拒绝这份原值。独立库对已知正例和反例也给出预期结果。通过 Stripe 官方文档命令读取的银行卡品牌成功付款示例表包含 22 个不同号码，里面没有这个 Link 示例。结论来自原值本身的校验失败，示例表比对提供旁证。[独立校验库](https://arthurdejong.org/python-stdnum/doc/2.2/stdnum.luhn) · [Stripe 的测试卡说明](https://docs.stripe.com/testing#cards)。 |
| CLI 写文件 | 用完全公开的示例和本地模拟响应走过原版 CLI 的 `retrieve --include card --output-file`。受保护文件中的数字与输入逐位相同，文件模式为 `0600`，标准输出和错误输出均未出现完整号码。此项回放没有外部网络请求，临时文件已删除。[官方写出路径](https://github.com/stripe/link-cli/blob/06d97214935160aa26c848f090ac0d27eaeb5842/packages/cli/src/commands/spend-request/index.tsx#L75)。 |
| 原收银台 | 复用上次的实机浏览器证据。输入框中已有 16 位、校验为假、`aria-invalid=true`。第二次签发读回的末四位与输入框相同。历史完整凭据已删除，所以历史比对只引用已经核实的字段。本轮的接口原文与官方示例使用了全部 16 位。 |
| 商户状态 | 独立的 Stripe GET 在 21:29 香港时间返回原 Checkout 为 `open/unpaid`，没有挂接 PaymentIntent。按同一订单引用检索的付款记录数为 0。模拟扣款、模拟退款、真实支出均为 US$0.00。[此前的页面与商户记录](../2026-11-20-overseas-shopping-sandboxes/receipts.json)。 |

## 一处会误报授权失败的本地缺陷

原先的设备授权保存为以空格分隔的两个权限。随后 FYP 配置内的同两项权限以逗号分隔。Link 文档允许这两种格式。旧版额度状态命令用 `.split()` 解析，在本地权限检查处退出。FYP 的两个钱包操作入口现在共用精确的权限词元解析，兼容逗号、空白和混合形式，并拒绝仅前缀相同的权限名。[Link OAuth 参数](https://docs.link.com/authentication/oauth#scopes) · [共用检查](../../../desk-companion/scripts/link_wallet_test_allowance.py)。

修前和修后使用同一个授权配置。修后实际状态命令在 21:44 返回 `approved`、每月 50,000 美分、截止 2027-05-19 15:15:07 香港时间。对照期间保存的访问令牌相同，也没有申请新的设备配对。修复后的另一条真实状态入口也能正常读回旧的一次性请求为 `canceled`。卡号问题发生在已授权的接口返回之后，权限解析修复不会改变上游测试卡。[针对性测试](../../../desk-companion/tests/test_link_wallet_test_allowance.py)。

检查同类取卡入口时，还发现旧的一次性测试程序只检查数字和长度。用公开示例离线回放，旧程序会写出“已可交付”的回执。现在两个取卡入口共用同一个检查，验证钱包请求、商户、卡号校验位和有效期，只保存商户对账所需的掩码字段。相同回放在写出回执前拒绝了无效示例，并清理了临时凭据文件。有效的公开对照仍成功。此次运行了七个新增权限用例、一个新增凭据交接用例及一个受影响的有效期用例，Ruff 通过。没有重跑既有购物旅程。

## 可公开复现与兼容范围

无需登录、虚拟卡文件或交易记录即可独立复现公开示例的校验结果。在仓库根目录执行下面的命令。脚本仅下载固定提交的公开 README，核实其 SHA-256 后打印长度和校验结果。加入 `--readme /path/to/README.md` 可在已有相同发行文档的机器上离线运行。

```sh
uv run --no-project output/qa/2026-11-20-link-wallet-diagnosis/reproduce_public_fixture.py
```

已观察到 `public_example_length=16` 和 `luhn_valid=false`。这说明本次 Link 测试夹具和现有 Stripe 卡片收银台存在兼容性问题。公开资料不足以判定该示例号的内部设计意图，也不足以推及正式卡或其他商户。现有额度可以保留。继续验收这条链路需要提供方确认兼容的测试虚拟卡或受支持的对应测试收银方式。Link Pay Token 当前不支持测试模式。Link 的 Shared Payment Token 测试走商户 HTTP 402 挑战及对应的授权，属于另一条集成。[Link 测试凭据指南](https://docs.link.com/quickstart/overview) · [Link Pay Token](https://docs.link.com/guides/link-pay-token) · [HTTP 402 支付](https://docs.link.com/guides/machine-payments)。

本轮阅读了 AGENTS、product 的现行购物段、handoff、最新决定、研究索引、上次验收、两个实际钱包操作入口、保护性取卡代码以及相关官方 SDK/CLI 源码。自审只覆盖权限修复及本次诊断工具。此前通过的订单、退款和本地测试沿用原记录。更新了项目入口、产品状态、决策、工作日志和交接。公开产物只包含发行物散列及脱敏比较结果。
