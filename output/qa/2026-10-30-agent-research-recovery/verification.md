# Group 2 · Research recovery and current product mechanism audit

30 October 2026. User request: revisit Grok Bot, Muse and Dot, recover prior rounds and explain why the previous answers did not use them. This is a documentation/research correction on `codex/personal-agent-research-20261030`, based on application milestone `44aa2c7100ac9e072090cf25c10b4315de885670` / PR68.

## What was recovered

The 3 October Dot study, 6 October personal-agent plan, 14–15 October product/architecture notes and 29 October permission study existed in the current tree. The most detailed six product/gap reports existed only on open draft PR5, verified head `11dc2b84cebe6e8250b28ca4442fc91f0dfec676`. Current PR metadata and the local remote ref agreed. The old architecture index linked four Muse/Dot files but omitted the two Grok files; the recent handoff had no route back to this research.

Restored six reports, 1,304 original lines / 205,227 original bytes. [Manifest](historical-inventory.json) records exact original Git blobs/SHA-256 and recovered hashes. Changes are a historical banner, 25 links pinned to old supporting code/documents and trailing-whitespace normalization. Original narrative is retained; one equivalent prose rewrite removes a scanner false positive and is explicitly listed in the manifest. Full blob recovery is distinct from full re-reading; exact focused reading is in [reading record](reading-record.json). The old API/pricing corpus is not silently re-certified as current.

Only research is recovered. PR5's 832-file implementation diff, separate kernel, old avatar, CI files and private runtime were not merged. Existing application source stays at the PR68 baseline.

## Current findings and corrections

- The active references are Grok Bot, Meta Muse and OpenAI Your dot. New Computer's Dot remains a dated historical aside, not a new interpretation of the owner's target.
- [Fifteen primary pages](primary-sources.json) were retrieved for the product mechanisms, model/harness boundary and mail-event implementation options. Vendor claims are identified as such; no competitor account or end-to-end behavioral benchmark was run.
- Grok separates persistent shared account computer, connected-app actions, skills, scheduled/event routines, action review and Vault. A connected mailbox is not itself a watch. Its current own-inbox background-send rule keeps mail in draft until Send. Current chat-driven approval cards are not on a timer; background/routine cards expire after 30 minutes, superseding the older study's approximate 10-minute statement.
- Muse publishes a dedicated VM and separated runtime/credential/permission/browser services. The announcement was accessible in this round, resolving the older fetch limitation. Its documented purchase path calls for per-purchase review, including stored-card websites and merchant/amount/time-scoped Link cards. Grok's saved-card use and Link one-time-payment approval must be described separately.
- Dot's persistent responsibility, saved schedules, supported events, context/notes and read-only proactive research are different mechanisms. A call can end while assigned work continues. No dot-specific embedding API is claimed.
- The previous answer was too narrow in centering Linux Codex installation. The recovered Dot report already discussed managed Agents API, SDK and Responses alternatives. The current Agents API overview was re-read; reusable harness/session services are not the complete consumer product. Account access, cost and integration compatibility were not tested.

The [canonical entry and implementation map](../../../research/personal-agent-research-index.md) connects these findings to existing source and three concrete journeys: email tracking/advice; voice-led everyday purchasing; travel/booking state. Current source has task/permission/job/notification primitives and actual bounded office execution. It has no verified real mailbox monitoring, merchant/payment integration or flight ticketing. The static-source absence search and known tool/scope contracts support this bounded conclusion; no claim about unrelated installed apps follows.

## Documentation corrections

Root AGENTS/START/product/handoff/README now route to one research entry. Older product and architecture notes are explicitly historical, Dot identity wording is corrected, and the missing Grok links are added. Product goals and delivery gates distinguish already implemented execution from still-missing personal-agent outcomes. Decision log and work log record the correction and one next implementation gate.

The next gate is email change → same task → sourced advice/draft → meaningful notification with resumable model turns. Offline data is development support, not final real-mail acceptance. User/mail connection, sending, payment, service access and actual fees remain separate from a research request.

## Checks

This is a documentation-only change. Original/recovered SHA-256 and narrative-preservation checks pass for all six reports. All 339 local references in 19 changed Markdown files resolve. Application backend/frontend/scripts/tests are byte-unchanged against PR68. Diff whitespace and staged-secret checks pass; exact results are in [checks.json](checks.json) and the scan log. Preserve earlier 524/89/73 test evidence at its original milestone; do not run or claim another application suite merely for copied research.

No email was read from the user's accounts, no monitoring schedule created, no message sent, no purchase/booking made, no model charge incurred and no hardware or deployment changed. One guessed Dot documentation route returned 404 and is excluded from evidence; the valid official overview/task/control routes were used. No CI was created or run. Publication readback is recorded separately.
