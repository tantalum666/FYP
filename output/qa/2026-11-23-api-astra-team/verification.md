# Group 2 · Parallel API development

## Source and scope

Restored the project from the 22 November calendar-aware flight release at `412721b2`. The source review covered AGENTS.md, product.md sections on ordinary chat, flight reviews and shopping, handoff.md, the 22 November flight decision, the flight conversation specification, scoped commerce reviews, existing calendar storage and the ordinary conversation view. Deployment on the previous day and closed provider trials retain their existing evidence. The API contributor and the integrating engineer use separate worktrees.

## Booked flight to local calendar

[API Astra PR 143](https://github.com/tantalum666/FYP/pull/143) contains the private itinerary projection at `e06c5149`. The OpenAI Responses receipt returned model `gpt-6.2-astra`, reasoning effort `max`, standard service, and a completed response with implementation and tests. The first bounded request ended on its output limit and supplied no code. The integrating engineer corrected the Python package imports and reused the provider's existing PNR validator. All 33 projection cases passed in the API worktree, including a transfer crossing the date line, a desk DST fold, an uncertain airport time, an approved fare increase and exclusion of private receipt details.

In ordinary chat, the integrating branch reopened the supplier record before preview and before saving. The five added HTTP journey tests passed with an isolated desktop database, authenticated owner and synthetic LetsFG transport. A 19:00 Hong Kong departure and 22:10 Tokyo arrival became 19:00–21:10 on the Hong Kong calendar. The preview wrote zero events. Confirmation produced one private event with no reminders, and repeat confirmation found the same event. Deleting the saved event, then replaying the request, returned the removed status. An expired or dismissed draft, a changed capture, a privacy switch during the supplier read, a second login and forgetting the original conversation all prevented an unauthorized new write. The existing flight had one original submission. Frontend TypeScript and the focused Python lint checks passed.

Cost and credential evidence are retained privately by the operator. Published changes contain no owner credit amount, credentials, actual account identifiers or production database.
