# Retained Work narrow-title integration

13 October 2026. Production delta is only one CSS declaration and its comment: `.agent-run-choice { flex-shrink: 0; }`. A capped vertical flex list now retains each card intrinsic height instead of compressing its clipped goal row. Existing width, title clamp, list height/scroll, translations, selection and privacy behavior remain unchanged.

## Evidence

The [actual Mac report](../2026-10-13-mac-4e508411/report.md) pins the earlier 4e508411 source: narrow English measurements recorded goal strong boxes of 0px and 66px-high cards, with missing titles visually confirmed in both languages; desktop Chinese title boxes were 42px. No computed flex-shrink or list client/scroll height was captured. This confirms the observed failure, not the new rendered fix. [Implementation QA](../2026-10-13-narrow-work-titles/verification.md) and [independent review](../2026-10-13-narrow-work-titles-audit/verification.md) record the minimal patch, four source/SSR tests and expected prepatch failure.

Full `check_software.sh` completed with exit0: 1,380 backend / 242 frontend, Ruff, TypeScript, Vite and A1/VRM provenance checks pass. Existing Python/npm/Vite advisories remain. No source changed during verification. The initial manifest command omitted its required path argument; corrected 303-file snapshot was taken shortly after test startup, and matches the final snapshot. Do not mislabel it as a valid pre-command snapshot. Worker-frozen CSS/test hashes independently match.

Actual patched mounted 390px/desktop EN/ZH title height, scroll reachability, long-word overflow, selection and A1 behavior remain for the existing Mac task on the exact new commit. No live model, paired identity, public MCP/capture, real StackEdit or CSV Save acceptance is inferred. No user runtime migration, credential, security bypass, merge or deployment.

Parent shared product/handoff/work-log records the actual older-source checkpoint and keeps newer-source acceptance separate. Publication and exact commit CI are recorded only after remote verification.
