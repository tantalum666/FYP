# Offline text-trial preflight

31 October 2026 integration: read [current compatibility and migration rules](pr5-integration.md) first. Dated October 12–13 acceptance statements below remain historical; this integration preserves Alice/current Omni and the current task/job/permission core.
Updated 2026-10-13. This is an **offline-only engineering preview**, not a live-provider runner, model recommendation, provider authorization or successful model acceptance. It implements no application route and changes no runtime settings. The owner has not fixed a provider/model or approved a paid trial.

## Run without credentials

From `desk-companion/`, using the existing installed environment:

```sh
.venv/bin/python -I scripts/check_text_trial.py \
  --provider gemini --model fixture-model --endpoint ''

.venv/bin/python -I scripts/check_text_trial.py \
  --provider qwen --model fixture-model \
  --endpoint https://synthetic.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions
```

`fixture-model` and the synthetic workspace are intentionally fictional examples. No model or account is contacted. Provider, model and endpoint are required explicit preview inputs; Gemini's empty base endpoint uses the existing pinned production default. Syntax acceptance does not establish model availability, account eligibility, region support, authorization or pricing. There is no live flag, API-key input, runtime/database path, custom prompt or tool-execution option. Do not supply actual credentials in command arguments or the environment.

The supervisor launches the worker with an empty environment, Python isolated mode, no stdin and discarded stderr. It does not inspect, copy or log inherited credential values. The worker constructs `TextConfig` with a fixed non-secret fixture marker, never calls `TextConfig.environment`, and uses a terminal in-memory HTTPX transport with no network delegate. No `Runtime`, actual application `Store`, application service, owner account, credential file or filesystem database is constructed. The only database is fresh SQLite `:memory:` adapter-usage accounting, closed after each preview. This is code-path isolation, not an OS/network sandbox against arbitrary modified Python or dependencies.

## Production adapter contract

The fixture calls the existing `TextAssistant.generate_guarded` → `generate` path, so its captured JSON uses the production Qwen/Gemini serializer and bounded response reader. A narrowed subclass of the production `TextPlan` advertises only `task_create_draft`; it is a validation schema, not a second planner. The one tool descriptor reuses `TaskInput`'s schema.

Input is fixed synthetic text: “请只建立一个待审阅的本地任务草稿，标题为“FYP synthetic test A”，不要保存任务或安排提醒。” The payload includes fixed application instructions, a fictional 2026-01-01 UTC timestamp/timezone, schema and that one tool definition. It does not call business/personal-context projection or load memories, conversation history, calendar, task, source, artifact, school or device data. Existing [privacy consent](personal-context.md) and [provider policy](provider-policy.md) remain unchanged. Configuring a preview grants none of those sharing permissions.

The mock response is fixed and labeled synthetic. Local validation requires precisely `task_create_draft`, title `FYP synthetic test A`, timezone `UTC`, and `follow_up_enabled: false`; additional keys, other tools, changed title, reminders or approval fields fail. The false field is explicit because production `TaskInput` otherwise defaults follow-up on. Even valid output is only a returned in-memory plan: no tool dispatch, proposal persistence, task save, reminder, approval or external effect occurs. It does not claim to validate a live draft's persistence or the truthfulness of natural-language model output.

## Bounds and truthful reporting

- Exactly one admitted mock POST, no redirect following, fallback or retry; a second transport attempt fails before producing another fixture response
- Actual serialized request body ≤16 KiB; the report records its byte count and SHA-256, parsed payload, exact URL and method, omitting credential headers
- Actual outgoing payload must include Qwen `max_tokens: 1600`, non-streaming and thinking disabled, or Gemini `generationConfig.maxOutputTokens: 1600` with JSON MIME; missing/changed limits fail rather than being asserted from configuration
- Production 128 KiB raw response limit, 30-second between-chunk checks and five-second HTTPX inactivity configuration remain reused; malformed/oversized/protocol/error responses stop after one attempt
- The normal CLI supervises the whole worker with a 45-second subprocess timeout and kills/reaps it on expiry. Process creation, OS scheduling and kill/reap latency are not real-time guarantees. Direct imported worker calls and the internal worker entry are unsupervised; they must not be described as independently enforcing this wall-clock bound
- The timeout bounds local test-process behavior only. It is not evidence of server cancellation, remote deletion, a financial hard cap or a guarantee that already generated provider output would not be billed

Success is named `offline_preflight_passed`; every report says `live_acceptance: not_run`, zero network requests, one mock request, no dispatch and no saved draft. Usage rows count adapter attempts only; no real token usage or price is invented. A mock success tests serialization and fences, not semantics, natural voice, audio, account access or real task execution.

## Before any live test

This implementation deliberately has no code path to enable live access. A later separately reviewed integration must obtain the user's provider/model/destination, exact synthetic-data and one-call spending approval; establish permitted account/region access and a secure credential route; recheck current official model-specific limits and actual account cost controls; keep one request/no repair retry; and inspect a real response plus an independently read-back unapproved synthetic draft in an isolated fixture. Credentials, new accounts/terms and billing require their applicable authorization. A preview must never be treated as satisfying those gates.

The 16 KiB request size is not an exact input-token count. Provider-side output-token fields are documented generation limits, not proof of total billing. Unknown/missing usage and delayed console accounting must remain unknown. Voice is a separate later scope with independently reviewed output/cost constraints; this work does not enable or test audio.

## Files and verification

- `backend/desk/text_trial_preflight.py`: fixed fixture and guarded production-adapter preview
- `scripts/check_text_trial.py`: isolated offline supervisor
- `tests/test_text_trial_preflight.py`: positive, hostile, drift, no-network, scope and real worker-timeout tests
- [Focused QA and example reports](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/output/qa/2026-10-13-text-trial-preflight/verification.md)

No existing production source file was modified. Existing capacity, app integration, UI, assets, actual runtime, accounts, Git operations and deployment are outside this slice.
