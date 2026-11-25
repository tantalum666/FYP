# Group 2 · Current handoff

25 November 2026, Hong Kong. Public `main` remains `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (PR #157). [Product](product.md) · [decisions](decision-log.md) · [work history](work-log.md).

## This slice (managed-browser FastClient deadline)

Branch `cursor/managed-browser-deadline-fixture-e853` from `main` only (does not stack #158–#161). Offline `FastClient.active_seconds` 0.25→2.0 so pre-auth origin work cannot burn the active budget before `owner_input`; regression covers 300ms pre-auth delay + stale-form fence. Production 90s budgets unchanged. [Verification](output/qa/2026-11-25-managed-deadline/verification.md).

## Related open PRs (unchanged product tips)

| PR | Tip | Note |
|---|---|---|
| #158 | `0e9ea44a` | chrome-only kill |
| #159 | `1f760a41` | task-recovery ports |
| #160 | `d8aad9fb` | EOF + trailing-whitespace hygiene |
| #161 | product `be5cfaf3` / notes `1fd85555` | initiative follow-up |

Prior four-way `0234fc1ebb` (3082/1skip) preserved; not re-run this cycle.

## Running software (unchanged)

Mac Web / Simulator `b759950c`. Defaults GPT-6.2 Sol / GPT-Live-1.1 / A3 v9.

## Not done

No GitHub merge, CI, deploy, Pi, live mailbox, paid model. Pristine-main `test_unadmitted_origin_and_auth_are_never_auto_approved` → `unknown` remains out of scope.

**Next step** — Parent rechecks weekly included usage, then Codex review of this PR and open #158–#161. Pi update stays a separate device step.
