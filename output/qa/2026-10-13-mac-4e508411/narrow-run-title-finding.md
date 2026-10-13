# FYP mounted Mac finding — 4e508411

Exact source: `4e508411f973328e310721936b9e4d5cf224f8eb`.

At an actual 390×844 CSS viewport, open Assistant → Work tasks with four retained runs. The Saved work tasks list occupies a capped flex column (`max-height:18rem`). Its `.agent-run-choice` children retain default flex shrinking. The rendered button heights shrink to 66px and their goal `<strong>` boxes become 0px high; only state and timestamp remain visible. Accessible button text still contains the full goal. This makes visual selection of a specific goal difficult. The detail pane is readable after selection and no horizontal document overflow was measured (390px document width).

Evidence: `18-narrow-en-work.png`, `18-narrow-en-work.txt`; actual read-only DOM geometry: first goal strong height 0px, button width 314px/height 66px, visualViewport width 390/scale1. Native IAB screenshot sizing did not faithfully capture the emulated viewport; this evidence was captured directly from the same tab through CUA's documented CDP screenshot capability at 390×844, without image editing.

Likely narrow correction for the parent to review: prevent run cards from shrinking inside the scroll container, e.g. `.agent-run-choice { flex-shrink:0; }`, and verify multiple long English/Chinese goals still scroll. No local production source edit, push, merge or deployment was performed.

Independent accepted checks on this source: hidden-owner queued run `65718184922c4415b84cfd159f7e3c15` v2 → pause review/confirm → paused v3 → cancellation review/confirm → cancelled v4. No goal/source content was revealed, no model/tool calls or artifacts occurred. Real sign-out during delayed detail read closed the old workspace; a new owner session opened with empty chat and no old detail resurrection.

CSV file-save boundary: a single visible Download file action for existing Evidence register v1, run `b27bf6f0f0814f94ad32d1e5060295e0`, artifact `ee722fa47e944f1ea2a4e85d0fc6474c` (822 bytes), from `http://127.0.0.1:5190` produced no completed download event before controller timeout/reset. The parent reported an associated platform approval pending at 10:32 UTC; its exact manager identity was not provided locally. No consent/cancellation was inferred. The attempted normal native Save-state inspection in `/Applications/ChatGPT.app` was explicitly denied by Computer Use, so that route was stopped. No repeated download, denied Chrome history lookup, alternate app-control route or manufactured file was used.
