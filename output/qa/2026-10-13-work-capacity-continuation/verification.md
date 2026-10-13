# Retained Work capacity — frozen integration verification

2026-10-13 08:13 UTC. Source and audit complete; Git publication and actual browser acceptance remain separately recorded.

- Full software command: `UV_CACHE_DIR=/workspace/shared/fyp-uv-cache npm_config_cache=/workspace/shared/fyp-npm-cache bash desk-companion/scripts/check_software.sh`, terminal exit 0
- 909 backend tests passed; 194 frontend tests passed, zero failures; Ruff, TypeScript, Vite build and original asset checks passed
- 271 source/test/config/lockfile hashes before and after exactly equal; see release-source-stability.json and paired manifests
- Existing two Starlette/httpx deprecation warnings and large Vite chunks remain; no new target-performance claim
- [Backend implementation](../2026-10-13-work-capacity-backend/verification.md), [interface verification](../2026-10-13-work-capacity-interface/verification.md), [independent audit](../2026-10-13-work-capacity-audit/report.md): 69 implementation backend + 20 independent backend and 33 independent interface cases
- Actual SQLite, HTTP owner boundaries, unchanged admission/recovery, corruption, authority races, full-capacity existing-operation recovery and React hooks/SSR were exercised. No mounted browser, paid provider, physical hardware or real-account acceptance is claimed

The independent audit found and rechecked literal-NUL JSON parity and stale captured linked-review callbacks after a capacity permission denial. Both fixes are included in this frozen test run. An earlier executor disconnect interrupted a type/build process; it was rerun successfully and is not counted as a pass by inference.

Current remote base is 2ad00700bcf80a2f9e7d2e12410f3d6cbf43087a; its exact PR/push CI both succeeded. No merge/deploy, credentials, quota lift, file deletion, external notification or live model call. Ongoing Mac approval remains pending rather than cancelled.

Updated product.md, handoff.md, work-log.md, decision-log.md, desk-companion/README.md, docs/architecture.md and docs/work-capacity.md. Reading inherits the same ongoing 186-document intake with focused supplements; compression did not start a new intake. Final candidate secret/link/mode/tree verification is recorded separately before publication.
