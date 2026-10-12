# First personal-agent implementation checkpoint

Recorded 2026-10-12 12:48 UTC. Branch: `codex/personal-agent-kernel-20261012`; draft PR #5 stacked on PR #4. Source checkpoint is being prepared, not merged or deployed.

## Verified

- Integrated `bash scripts/check_software.sh --skip-assets`: Ruff clean, **361 backend tests**, **50 frontend tests**, TypeScript and Vite production build passed. Log: [checkpoint-software-checks.log](checkpoint-software-checks.log). The explicit partial-checkout flag was used while A1 transfer was pending.
- Subsequently ran the exact omitted `scripts/check_assets.py` stage after unchanged A1 restoration: **both VRM and A1 provenance hashes pass**, [checkpoint-assets.log](checkpoint-assets.log). A1 SHA256 `a7b428a2437da70880fea628dca23c0ded7a24294595b13437b4ae99fe5a09f9`. No source replacement or generated placeholder.
- Independent standalone test application process, actual loopback HTTP write/read and independent SQLite inspection: [application-http-integration.json](application-http-integration.json), separately rerun [application-independent-http.json](application-independent-http.json).
- Privacy/concurrency review: [independent-privacy-review.md](independent-privacy-review.md); scoped review counts overlap the aggregate and are not added to it.
- [Personal UI evidence](personal-ui/verification.md), [routines evidence](routines-verification.json), [provider/voice review](voice-provider-integration-review.md), [CI reproducibility](ci-reproducibility.md).

## Scope and outstanding evidence

Implemented owner-reviewed facts, optional retained text threads, separate saved-context/provider consent, privacy-fenced responses, standalone fictional-data application adapter, deterministic persistent routines, bilingual interfaces and software CI configuration. No general computer control, model-quality parity or commercial product internals claimed.

Actual new-feature DOM interaction and screenshots await the pinned source on an isolated Mac task using the user-requested model; the original preview remains untouched. GitHub Actions success requires a remote run after publication. Cloud Chromium did not reach a page and is not reported as browser acceptance.

Live paid providers, microphone/camera collection, real user credentials, general PC/LCU, Pi/iPhone hardware performance, mechanical output and school submission were not exercised. Remaining warnings: pre-existing backend dependency deprecation and production bundle-size warnings. Content-free receipt/tombstone metadata remains indefinite; local SQLite content is not advertised as application-encrypted or forensically erased.

## Documentation

Updated product/handoff/work log/decision log, implementation plan, README, architecture and dated inventory supersession. Feature contracts describe real defaults, boundaries, recovery semantics and limits. All changes preserve previous school, artwork/prompt and licensed-model assets by overlaying the full remote tree; omitted local files are never treated as deletions.
