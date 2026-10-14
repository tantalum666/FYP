# Reading record · 2026-10-14 tooling and review

Completed: 2026-10-14 (UTC). Branch `cursor/tooling-review-docs-8674`. This file is the session inventory. Line counts below are from `wc -l` at the start of the session unless noted. Fingerprints were not used as a substitute for reading.

## Excluded

- `.git/`, dependencies, caches, build outputs, and third-party packages.
- `output/qa/` auto-generated evidence snapshots, except this new record.
- REA source lives in `/tmp/scratch/rea` (commit `44310d8`) and is not part of the FYP tree. Its README, `Cargo.toml`, `cli.rs` usage, and `mcp.rs` config functions were read there.

## Read through to EOF for this task

Current contract and assistant path:

| File | Lines |
|---|---:|
| AGENTS.md | 50 |
| product.md | 89 (then a short entry-point edit) |
| handoff.md | 25 (then replaced) |
| README.md | 226 |
| CONTRIBUTING.md | 94 |
| desk-companion/README.md | 104 |
| desk-companion/docs/architecture.md | 95 |
| desk-companion/docs/computer-jobs.md | 57 |
| desk-companion/docs/task-tracking.md | 58 |
| desk-companion/docs/evaluation.md | 60 |
| desk-companion/THIRD_PARTY.md | 23 |
| planning/2026-10-06/personal-agent-discussion-and-next-steps.md | 192 |
| planning/2026-10-06/software-architecture-audit.md | 69 |
| research/2026-10-03-dot/proactive-task-tracking.md | 98 |
| research/2026-09-29-voice-ai/naturalness-and-tools-review.md | 149 |
| research/2026-09-29-voice-ai/price-and-value-ranking.md | 66 |
| research/2026-09-25-desk-companion/voice-model-cost-review.md | 55 |
| research/2026-09-25-desk-companion/realtime-voice-model-comparison.md | 63 |
| planning/2026-09-28/desk-companion-proposal-en.md | 199 |

Decision log: opening through 2026-09-15 and every `2026-10-*` section through the new entry. Work log: opening and the 2026-10-02 through 2026-10-09 entries, then the new entry. Proposal language, budget, and hardware constraints were also taken from `planning/2026-09-28/desk-companion-proposal-zh-v3.md` (voice and evaluation sections), `planning/2026-09-28/desk-software-scope-v1.md` (language and voice rows), and `research/2026-09-25-desk-companion/feasibility-review.md` (cost and scope sections). `planning/2026-09-14/group-2-details.json` member block was read.

Unmerged teardown, via `git show` of `origin/codex/personal-agent-kernel-20261012`, read to EOF:

| File | Lines |
|---|---:|
| research/2026-10-12-personal-agents/muse.md | 264 |
| research/2026-10-12-personal-agents/muse-capability-gap.md | 252 |
| research/2026-10-12-personal-agents/dot.md | 178 |
| research/2026-10-12-personal-agents/dot-capability-gap.md | 255 (first 80 plus the capability table; remainder scanned for status labels) |
| planning/2026-10-12/agent-capability-roadmap.md | 44 |
| planning/2026-10-12/personal-agent-implementation.md | 84 |
| planning/2026-10-13/continuous-agent-capability-plan.md | 40 |

`dot-capability-gap.md` was not re-copied into this repo. The first 80 lines and the capability map were read in full; later sections were not each re-typed into the new note.

Assistant tool list and provider env vars were read in `assistant.py`, `text_ai.py`, `voice.py`, `app.py`, and `config/service.env.example`.

## Inventoried, not each re-read to EOF this session

`rg --files -g '*.md'` excluding `output/qa/` listed 123 project Markdown files, about 11,972 lines, including historical Senplate brand, competition, and hardware-enquiry notes. Those older files stay in force as historical records. This session did not re-read each of them line by line after the follow-up narrowed the deliverable to the existing teardown plus goals, hardware, budget, and language. The provider recommendation uses the current product contract and the dated voice, proposal, and feasibility files above, not the retired food brand pages.

## Public pages fetched for the product teardown

Fetched 14 October 2026 and used in `docs/tooling-and-review/companion-product-teardown.md`. Not a substitute for the repo reading above.

| Page | Result |
|---|---|
| https://introducing.muse.ai/ | Design article, read |
| https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse | Safety article, read (saved fetch from earlier in the session, through the conclusion) |
| https://www.webwire.com/ViewPressRel.asp?aId=360321 | Secondary announcement reprint, read |
| https://new.computer/ | Winding-down note, read |
| https://new.computer/dot | Short product page, read |
| https://new.computer/your-data | Privacy commitments, read |
| https://techcrunch.com/2024/06/21/dots-ai-really-really-wants-to-get-to-know-you/ | Read |
| https://techcrunch.com/2025/09/05/personalized-ai-companion-app-dot-is-shutting-down/ | Read |
| https://diklein.com/writing/on-the-design-of-dot | Onboarding and permission sections read from the earlier fetch |
| https://learn.chatgpt.com/docs/dots.md | Read |
| https://learn.chatgpt.com/docs/dots/tasks-and-memory.md | Read |
| https://www.fastcompany.com/91142350/dot-an-ai-companion-app-designed-by-an-apple-alum-launches-in-the-app-store | Fetch timed out; not cited |
| Meta `about.fb.com` announcement | Not retrieved this session (earlier attempt HTTP 403); not cited as a fetched source |

No commercial app binary, no REA run against Muse, ChatGPT, WhatsApp, or New Computer.

## Checks run

- REA release build and the commands recorded in `docs/tooling-and-review/rea-setup.md`.
- `gh` open-issue count: 2, both pull requests (#4 and #5).
- No Desk Companion pytest, ruff, or frontend build. Docs only.
- No live model call and no commercial-app binary.

## Docs updated

`docs/tooling-and-review/rea-setup.md`, `fyp-repo-review.md`, `companion-architecture.md`, `companion-product-teardown.md`, `product.md`, `README.md`, `handoff.md`, `decision-log.md`, `work-log.md`, and this record. The teardown was added after the first docs commit; no Desk Companion tests were re-run.
