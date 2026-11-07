# Group 2 - Current continuation

7 November 2026. This review branch is `cursor/conversation-work-reshow-verified-b9a2`, synced with current main after #94. It re-shows one verified offline Work result when a later turn in that same conversation asks about the work. It does not run the executor again and does not call a provider. Codex reviews and merges #95, then #96. Drafts #73, #87, and #88 stay untouched. Read [handoff](handoff.md), [product](product.md), latest [decisions](decision-log.md), [browser contract](desk-companion/docs/computer-use.md) and [live QA](output/qa/2026-11-07-live-agent-eval/verification.md).

Pi source d40457fe is activated. Real OpenAI controlled shopping/flights, calendar followup and cancellation passed; 31 generations, USD0.37970163 conservative accounting, USD1 ledger closed. JD stopped at verification; Cathay did not load. One FYP-drafted test email was sent/read back through Codex Gmail, not a native Pi sender.

Main's separate next step remains same-browser owner takeover and deliberate return, grounded in the real JD verification barrier. This pull request does not implement it. No CI; only red-LED diagnosis is deferred. PR94 is merged; its full tree matches the reviewed head. [Publication receipt](output/qa/2026-11-07-live-agent-eval/publication-receipt.json) and runtime activation are separate.
