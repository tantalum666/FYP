# Group 2: useful voice-response latency QA

Date:15 October2026. User request: next-week meeting answers should arrive within10 seconds; around5 seconds feels more natural. This follow-up records the requirement, inspects the current path and measures only the existing local calendar tool. No application source was edited.

## Read coverage and scope

[Inventory](reading-inventory.json) inherits the ongoing session's full-project read and exact text supplements via the previous voice-model-refresh record.134 exact current Markdown versions were already observed; the new [latency contract](../../../planning/2026-10-15/voice-response-latency.md) was authored/read here. Root AGENTS/product/handoff were reread. Fingerprints detect change and refer to existing observed ranges; this is not a second independent full read.

Code inspected: AssistantService.tool and local-message routing, Store.snapshot/data and event cap, ToolDispatcher, VoiceService setup/receive/tool-result loops, browser VoiceAudio and40ms AudioWorklet capture. Calendar reads do not call a model or external refresh. Two ordinary-tool slots can queue; connection limits are failure ceilings, not fixed sleeps. Browser capture drops frames before ready; per-turn useful-reply timing and10s timeout handling are not implemented. The day-only local text rules are not used as a claimed next-week fast path.

## Actual offline measurement

Executed: desk-companion/.venv/bin/python output/qa/2026-10-15-voice-latency/benchmark_calendar.py

[Script](benchmark_calendar.py), [raw timing record](calendar-tool-timings.json). Real ToolDispatcher -> worker thread -> calendar_query -> SQLite snapshot/recurrence/privacy -> JSON serialization. Validated synthetic100/500-event fixtures, including daily/weekly recurrence;500 is the current app limit. Each case100 timed queries, plus one hidden-title query per case. All returned33 occurrences in the correct19-26 October2026 Hong Kong range, serializing7,188 bytes. Private-title projection passed. Temporary fixtures were removed.

| Event rows | p50 ms | p95 ms | Maximum ms |
|---|---:|---:|---:|
|100|1.949|2.391|3.931|
|500|5.213|6.002|6.254|

Mac26.5.2 arm64, Python3.14.5. Repeated local-process samples after seeding. First measured query is not an OS cold boot. No microphone, provider connection/network/inference, synthesis, browser playback, Pi, real calendar, occupied tool slots or writer contention is included. The measurements do not establish a5-second voice SLA.

## Acceptance and source distinctions

The user's approximate5-second preference is recorded separately from engineering p50<=3s/p95<=5s criteria and10s failure handling. First audio/preamble, first grounded spoken result, complete list and long-job completion are separate metrics. Data freshness, privacy and correct next-week boundaries remain mandatory.

Official source passages: [OpenAI evaluation](https://developers.openai.com/cookbook/examples/audio/voice_agent_evaluation) allows qualifying preambles in its generic response-latency metric; our grounded-content measure is deliberately separate. [Live backend latency](https://developers.openai.com/api/docs/guides/live-delegation#reduce-backend-latency) recommends stage measurement and connection/model optimization. [Google streaming](https://ai.google.dev/gemini-api/docs/live-api/best-practices) recommends small audio chunks/buffers; the current code's40ms chunks are recorded, not claimed as new optimization.

## Closeout checks

Document checks passed: 137 Markdown files, 1304 local references, 1303 resolved and one explicitly expected install-generated credential link absent from this isolated worktree. Whitespace and the empty application/protected-file diff passed. Staged secret and remote receipts are verified during publication. Application code and protected school/art/runtime files remain unchanged. No paid API, account/key/trial, audio capture, hardware or school submission. Existing182/17 tests were not rerun or presented as new end-to-end evidence.

Updated norms: product, handoff, decision log, work log, current comparison and companion architecture; added the focused latency contract. This extends draft PR15 and does not merge main or PRs4/5. Exact configuration/spend and actual latency integration/trial remain next.
