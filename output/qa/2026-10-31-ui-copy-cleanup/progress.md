# Group 2 · UI copy and information hierarchy cleanup

Owner feedback: the interface is too wordy across pages. Current task is to reduce default reading load and foreground the actual action/result, not add another explanatory page. Pi remains paused; no paid model round or CI.

Branch codex/ui-copy-cleanup-20261031, based on PR74 head89f215e. Same active software worktree and existing isolated QA API8861/Vite5191; no real user database or provider configuration changes. User instructions retain Alice and distinct phone navigation.

Focused reads: current AGENTS/product requirements/handoff/decision, web and permission UX contracts, software-maintenance frontend responsibilities and lifecycle invariants. Product Design audit/router/critical overrides/user-context/communication/audit framework read; preflight found no saved design context. Frontend testing skill read; React guidance from this same task chain retained. CUA in-app browser only; its getTab wrapper failed, supported agent.browsers Tab API worked. Unrelated browser inventory was not retained or used.

Current-run before evidence: tasks, Work detail, new Work, Settings, Memory, Style, Import/share and task detail captured and visually inspected at1280x800. Screenshots under ignored desk-companion/.runtime/ui-copy-audit. Metric scope uses the actual main region or named active dialog, excluding background text. Work detail2710 characters; default new Work1368; Settings1177; memory353; style231; import/share1184; task detail711. Earlier unscoped counts were corrected before comparison.

Findings: Work IDs/call counters/capacity and repeated caveats bury file results; composer exposes optional report/provider/experimental configuration; Settings repeats heading explanations and scope notes; task view repeatedly explains Edit/verification instead of showing progress; persona repeats a permission claim that is inaccurate in Full mode. Existing simple calendar/home layouts and Alice should remain.

Implementation direction: remove redundant narration, use concise user-facing status, put technical detail/history/capacity behind explicit disclosure, simplify common Work input and review while retaining explicit retention/provider/action choices. Keep exact approval content, failure recovery, dirty-form guards and all backend gates. Do not use blanket CSS hiding or delete user-authored content.

Status: implementation/local acceptance complete and source752ab66 published to draftPR75; exact remote source head verified. Follow-up records publication and updates original-checkout routing only.

Compaction recovery read AGENTS/product/handoff and the latest decision-log sections; reused this round’s completed audit and interactions. Final source review covered RunPanel/RunDetail/RunComposer, application selection/results, shared action cards, permission/data panels and CSS. Rechecked only changed copy/format assertions before final303-test suite and build. Current screenshots/QA are dated across31October–1November; the established QA directory remains unchanged.
