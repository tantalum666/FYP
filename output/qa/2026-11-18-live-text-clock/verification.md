# Group 2 · Live OpenAI text acceptance

On 18 November 2026 the existing FYP project key completed one real Agents Session using `gpt-6.2-sol` at Standard tier. The ordinary FYP HTTP message route used the real network, official session client, function dispatcher and local action audit. The isolated runtime imported only the normal desk's timezone, read from its SQLite settings with a read-only connection. The available function catalog was restricted to `owner_clock`. Scheduling and background inference were off. [Machine-readable receipt](receipt.json) · [OpenAI model and rates](https://developers.openai.com/api/docs/models/gpt-6.2-sol).

## Real user journey

| Turn | FYP and provider readback | Input tokens | Cached input | Output tokens |
|---|---|---:|---:|---:|
| 1. Ask Alice to read the desk timezone | `owner_clock({})` executed once. Alice answered “这台桌面当前使用的 IANA 时区是 `Asia/Hong_Kong`，UTC 偏移为 `+08:00`。” | 20,082 | 9,977 | 70 |
| 2. Compare the result with Singapore | Same local chat, same remote session, new root turn and no additional function. Alice answered “相差 0 小时，香港和新加坡现在都是 UTC+08:00。” | 10,301 | 10,099 | 23 |

The function result carried the provider's original call and first-turn identifiers. Both canonical final answers matched the actual FYP replies byte for byte after trimming. The zone database independently confirmed the zero-hour difference at the timestamp returned by the function. Both root turns completed and the provider reported 30,383 input tokens, 20,076 of them cached, 93 output tokens and 30,476 total. The per-turn totals matched the final session usage. The first session-level usage read was empty and the later read-only reconciliation supplied the total.

There was one successful create (HTTP 201), one logical function result and one follow-up input. The DELETE returned HTTP 200 with `deleted=true`. Three subsequent GETs for that same remote resource each returned 404, including a separate GET after the ordinary cleanup check. Only digests of session and turn IDs are published. [OpenAI Functions](https://developers.openai.com/api/docs/guides/agents-api/tools/functions).

## Budget and the service contract

The first creation request selected `gpt-6.1-sol` and asked the service for a 25-cent limit. The deployed beta endpoint rejected `spend_control` as an unknown parameter (HTTP 400). A fresh metadata-scoped lookup returned HTTP 200 with zero matching sessions. The initial request produced no turn, function execution or model answer. The SDK 3.53.0 type accepts the field. The live endpoint and the public create reference used by this project did not establish an available server-side cap. Omitting the required beta header also failed on a read-only request. [Session create reference](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/methods/create) · [SDK change](https://github.com/openai/openai-python/pull/4058).

The owner then explicitly accepted local budget control and selected the newly released GPT‑6.2 Sol. Its exact ID was accessible to the project key via HTTP 200. The local transport admitted one session, one clock result and one follow-up. It reserved US$0.08 for each stage, monitored available usage, and retained a US$0.19 early-stop threshold under the US$0.25 allowance. It checked the first turn before allowing the follow-up. This was a local spending guard; the provider did not enforce a hard monetary limit. The batch closed and the normal service configuration was not changed. [Release announcement](https://openai.com/index/introducing-gpt-6-2-astra-sol/).

At the published Standard rates, treating each uncached input as an ordinary input yields **US$0.0235516**. Charging every uncached input as a 30-minute cache write would give US$0.0287051, or US$0.0544726 at the 12-hour cache-write price. The service did not report a currency amount or a cache-write breakdown. The deliberately conservative local accounting, using the high cache-write price and a margin for every input token, was US$0.1681295. The reservations and these estimates are distinct from an invoice.

## Source, regression and scope

The tested source was based on `76077139` with the two-file patch identified in the receipt. The patch preserves the ordinary provider-cap request and recognizes a definitive budget-parameter rejection. Only a trusted, explicitly supplied local budget transport may substitute its own admission for that field. The clock trial exercised that opt-in. Afterward the denial path was tightened so a local refusal leaves no remote cleanup record. Two new regressions covered the streamed service error with no unlimited retry and binding/denial before dispatch. Both passed. No previously passing local suite was rerun.

Re-read the checkout's entry rules, current product requirements and handoff, latest decisions, the ordinary Sessions contract, the previous migration QA/design, request/response handlers, budgeting, credential loading and the read-only clock implementation. Reconciled the model's public rate sheet, the session create/reference and the official SDK spend/usage types. Updated the source contract, project entry points, decisions, work log and handoff. Only sanitized receipts and documentation are published. Raw wire receipts and private configuration remain outside Git.

The normal Mac service directly reported source `c607759e`, text `gpt-6.1-sol`, speech `gpt-live-1` and A3 version 9. Its configured voice reasoning backend is `gpt-6.1-sol`. No Nano model took part. This live acceptance covers ordinary text and the clock function. Voice, browser work and production rollout of 6.2 remain separate. The current managed-browser capability still checks the text model against `gpt-6.1-sol`. [Text contract](../../../desk-companion/docs/official-text-sessions.md).
