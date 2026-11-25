# Group 2 · Current handoff

25 November 2026, Hong Kong. Public `main` remains `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (PR #157). [Product](product.md) · [decisions](decision-log.md) · [work history](work-log.md).

## This slice

Independent branch `cursor/suggestion-followup-status-e853` from that main tip (not #158/#159/#160, not throwaway `65eb854e`). Conversation findings already had Sources and Got it; they lacked an explicit owner follow-up bound to a private task with revisitable status. That journey is implemented and locally verified: Follow up on this → private task by id → live status on the finding card → Tasks listing; draft/send never claimed. [Verification](output/qa/2026-11-25-initiative-followup/verification.md).

Open PRs #158 / #159 / #160 stay untouched. #160 EOF blank-line hygiene is on tip `a4882b89` (whitespace only; suites remain on `87a38f48` / `65eb854e`).

## Running software (unchanged this slice)

Normal Mac Web and Simulator still run application `b759950c` from the workspace redesign release. Defaults stay GPT-6.2 Sol / GPT-Live-1.1 / A3 v9. [Workspace release](output/qa/2026-11-25-workspace-redesign/verification.md) · [continuity](output/qa/2026-11-24-continuity/verification.md).

## Not done

No GitHub merge, CI, deploy, Pi/hardware, live mailbox, paid model, provider/A3 change, or import of #158–#160 features. Local fixture browser evidence is not live external acceptance.

**Next step** — Parent rechecks remaining weekly included usage, then Codex review of this new PR (and optionally #158/#159/#160). The Pi update from `92acac8e` to `b759950c` stays a separate device step.
