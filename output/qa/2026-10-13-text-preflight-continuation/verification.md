# Offline text-trial preflight — frozen integration

2026-10-13 08:35 UTC. Full software command `UV_CACHE_DIR=/workspace/shared/fyp-uv-cache npm_config_cache=/workspace/shared/fyp-npm-cache bash desk-companion/scripts/check_software.sh` exited 0.

- 955 backend tests passed, 194 frontend tests passed, zero failures
- Ruff, TypeScript/Vite and original asset checks passed; existing Starlette/httpx deprecation and Vite large-chunk warnings remain
- 274 source/test/config/lockfile hashes unchanged before/after; paired manifests and release-source-stability.json record exact evidence
- [Implementation QA](../2026-10-13-text-trial-preflight/verification.md): 46 focused / 138 combined adapter-policy checks
- [Independent audit](../2026-10-13-text-preflight-audit/verification.md): 190 combined, including 52 independent cases; no blocking finding

The standalone CLI uses fixed synthetic context, current production payload serialization and a terminal in-memory transport. It does not read real configuration, secrets, runtime data, dispatch tools, persist drafts, contact a provider or establish any token/fee usage. Its 45-second supervisor is a local process deadline, not a billing cap. Provider/model/endpoint preview choices remain explicit and do not select a final model.

Live-account eligibility and the separately proposed single synthetic text call's US$0.10 budget remain unanswered. Real voice, model semantics, mounted UI, general cross-application control and hardware remain distinct gates. This batch does not implement the separately reviewed watch lifecycle design.

Shared product/README/decision/handoff/work-log and continuous plan are updated. Model research proposal and independently reviewed retention design are included as designs only. Same ongoing186-document intake retained with focused rereads. Parent owns immutable publication/ref/CI verification; no merge/deploy or real data removal.
