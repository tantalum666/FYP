# Group 2: voice-model refresh QA

Date: 15 October 2026, Asia/Hong_Kong. Scope: the user's new public-source comparison after Grok Voice3.0 and Gemini updates. Work is isolated from the original A1 checkout in the existing managed worktree, on codex/voice-model-comparison-20261015, based on main a663d83d28ce9209849cedc332bf7ed107a5a13d.

## Reading and evidence

- [Reading inventory](reading-inventory.json) inherits the completed [full FYP read](../2026-10-15-grok-review-merge/reading-inventory.json) and [remote supplements](../2026-10-15-grok-review-merge/supplemental-inventory.json) from this ongoing session, as allowed by AGENTS.md same-round and compaction recovery. It does not claim a second fresh full read.
- Current inventory before edits: 132 project-owned Markdown files, 12,721 lines. 116 exact document versions match previously observed reads. Current contracts and voice-focused files were read again. For other changed versions, only byte-exact matching source lines inherit prior coverage; 97 emitted supplement lines (including file/range labels) were then observed without truncation in supplement-current.txt.
- Fingerprints detect changes; they are not proof of reading. Read ranges and their previously observed source versions are recorded separately. The original branch's additional A1/kernel documents remain on that branch; their absence from main is not an exclusion by age or length.
- [Comparison](../../../research/2026-10-15-voice-ai/voice-model-comparison.md) and [source register](../../../research/2026-10-15-voice-ai/source-register.md) distinguish provider claims, benchmark observations, architecture, model/API availability and engineering recommendations. The register contains 73 official/provider-author or benchmark source references, including official indexes and search-body excerpts; it does not claim 73 full-page reads.
- Access gaps are explicit: Jarvis/EVA gave no readable current board, OpenAI Audio overview returned a challenge, Doubao's numbered protocol redirected, and exact Doubao3.0 price mapping remains open. The StepFun overseas price page and public original HTML confirm the current limited-time-free Preview item.

## Arithmetic

[calculate_costs.py](calculate_costs.py) uses Decimal and no network, and produces [calculations.json](calculations.json). It was executed successfully and its rows were checked against the report. Common scenario: 300 active session minutes, 150 user-speech minutes and 150 assistant minutes per 30 days. Qwen uses Singapore USD rates. Hypothetical input meters are clearly separated; all figures exclude historical context, text/reasoning, transcription, tools/backend, retries, taxes and discounts.

Confirmed base examples: Gemini about4.20; Grok24.00; OpenAI Realtime full14.40/mini4.50; Qwen AudioPlus3.42/4.14 and Flash0.315/0.419625; Omni0.268965/0.327555; Higgs vendor estimates2.445/2.79; Live15 plus backend; Eleven Creator24 plus LLM; Deepgram Standard22.50 under its configuration. StepPreview is temporary-free, not a permanent zero projection.

## Documentation checks and delivery

Document-link and whitespace checks passed. The link inventory checks 135 Markdown files including this QA report, with 1,285 local references: 1,284 resolve, and the existing desk-companion README link to .runtime/credentials.json is an explicitly expected install-generated target absent from this isolated worktree. No credential file was created or copied. Staged Gitleaks8 scan passed with no leaks across approximately156KB. Remote receipts are recorded at closeout. No application code changed, so the earlier182/17 application results were not rerun or presented as new voice evidence.

The report, source register, product, handoff, README, decision log, work log, companion architecture and two historical voice reports are the intended updated documents. Publication will stay on a feature branch and draft PR; this research request does not merge that PR into main.

No account, key, trial, model call, audio collection, model download, school-server login, hardware action, deployment or school submission occurred. Providers remain none. The next gate is exact candidate/voice/backend configurations, actual account eligibility and a total test-spend cap before a shared short listening/tool trial.

Reproduction: python3 output/qa/2026-10-15-voice-model-refresh/check_documents.py; git diff --staged --check. The application-source diff is empty. The staged secret scan exited0 with no leaks. Remote-delivery receipts follow.
