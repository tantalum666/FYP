# Group 2 · Current handoff

19 November 2026, Hong Kong. Continue in `/Users/tantalum/.codex/worktrees/proactive-agent-merge-20261117/FYP`, branch `codex/shopping-flight-quotes-20261119`. [PR 134](https://github.com/tantalum666/FYP/pull/134) targets [PR 133](https://github.com/tantalum666/FYP/pull/133). [Product](product.md) · [decisions](decision-log.md).

## Shopping and flights

Implementation `48aec0e6` connects the existing Alice draft, owner approval, hosted browser and verified readback to a shopping or flight quote. A live Wellcome result gave HK$34 for two selling units. Delivery and the final total remained unknown. The corrected GPT‑6.2 Sol follow-up used the stored receipt without another browser job. Both live hosted airline pages returned no usable fare. First-party HTML and Simulator Safari independently exposed a promotional price. Public lookup stops before checkout, reservation or ticketing. [Acceptance and residual gaps](output/qa/2026-11-19-shopping-flight/verification.md) · [receipts](output/qa/2026-11-19-shopping-flight/receipts.json).

## Running release and spending

The normal Web and iPhone 17 Pro Simulator still use `00780e44`, GPT‑6.2 Sol for text, managed browser and Live reasoning, and GPT‑Live 1 with A3 v9 for audio. The usual Web service was restored using its existing release and launcher on port 8831. Its health and exact build were read back. The isolated Simulator test installation was removed. The Pi remains deferred at `c607759e`; its previous release package is retained. [Running release](output/qa/2026-11-18-sol62-deployment/verification.md).

FYP OpenAI use is authorized through 24 November inclusive with US$20 per Hong Kong day. Mac and Simulator share a US$9 ledger, Pi has a separate US$9 allocation, and US$2 is unallocated. On 19 November the Mac ledger conservatively accounted US$8.96 with US$0.04 available. All nine test Sessions returned 404. Billing did not itemize the hosted browser runs. Background inference stays off.

**Next step** — Obtain a dated public airline result for the exact route, party and checked baggage through the official hosted browser. Start with the documented gap in the current evidence and compare the returned fare to the carrier's own page before describing it as bookable.
