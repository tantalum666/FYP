# Group 2 · Continue here

17 November2026. Continue in `/Users/tantalum/.codex/worktrees/official-agent-mainline-20261117/FYP`, branch `codex/official-agent-mainline-20261117`, PR127 (draft/open, stacked on126→124). Read [AGENTS](AGENTS.md), [product](product.md), [handoff](handoff.md), latest [decisions](decision-log.md), [Pi wake contract](desk-companion/docs/pi-power-recovery.md) and [current QA](output/qa/2026-11-17-pi-mainline-wake/verification.md).

Application8c67ddbe is now deployed/read back across Mac, native Simulator and Pi. Paired early RTC renewal is installed and actual boot ordering verified; delayed self-start was later reported/observed, but repeated undervoltage means stable recovery is not accepted. Preserve2.4GHz/original app performance, A3/data/grants. No firmware change, active observer, new paid call or CI. The earlier paid-budget question is unanswered. Follow the single next step in handoff, and do not reinstall old embedded RTC units.

Latest replacement-adapter check:485s/98samples before SSH timeout,18current undervoltage/throttling samples, unchanged2.4GHz limit and successful local API probes until loss. The new power path fails stability acceptance. Read [supply QA](output/qa/2026-11-17-pi-supply-check/verification.md); no test observer remains active. Source/app/wake configuration unchanged by this observation.
