# Group 2 · Interface copy and disclosure

2 November 2026: [desktop conversation](desktop-conversation.md) is the primary Web page, superseding the old modal/docked layout. Test zoom and window height in a separate QA tab.

1 November 2026. Owner feedback: pages contain too much explanatory text. This is an ongoing product requirement across web, phone and shared app components, not permission to remove Alice or the controls needed for informed actions.

## Default view

Show the user's content, the current state, useful results and the next available action. A heading does not need a paragraph that repeats it. Prefer “New work”, “Download” and “Results ready” to descriptions of persistence, verification infrastructure or output quality. Do not imply the whole goal is finished merely because a file exists.

Put operation IDs, hashes, call counts, versions, detailed activity, storage management and implementation explanations behind named disclosures. Optional configuration belongs in “More options”; empty optional sections need not appear. Avoid repeating the same caveat on every card. Keep errors, a necessary question, a blocked reason and its recovery action visible when relevant.

On a phone, selecting Work opens its detail in place of the list; “All work” returns through the existing guarded navigation. Desktop can retain a two-column list/detail. Alice and the phone's Plan/More navigation remain intact.

## Action-time information

Keep the affected item/destination and action clear before approval. Exact content remains reviewable. Explicit provider sharing and local retention are unchecked until selected; disclose that saved Work cannot currently be deleted. AI charges and retry consequences stay concise and visible when starting/retrying model work. Full access retains an explicit save action and its supported scope.

Import/share/backup details appear with the relevant controls. Sharing's recipients and expiry must be visible before creating a link. Privacy and permission policy, source identities, version checks, cancellation, unknown-result recovery and backend validation are unchanged by shorter labels.

## Implementation and checks

Reuse the current components, services, draft guards and request lifecycle. Native `details` keeps fields mounted while collapsed, so input survives disclosure changes. Do not add parallel state machines, extra polling, generic CSS that hides important content, or replace user-authored values to make a screenshot cleaner.

Review actual English desktop and Chinese phone rendering, keyboard disclosure, draft retention/closing, actionable errors, and the approval path. A lower text count is supporting evidence, not proof that the whole product is easy to use. The current [UI QA](../../output/qa/2026-10-31-ui-copy-cleanup/verification.md) records exactly which surfaces and flows were inspected. Native touch and software-keyboard acceptance remain separate.
