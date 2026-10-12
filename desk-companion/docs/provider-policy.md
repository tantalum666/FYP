# Provider connection policy

Updated 12 October 2026. Model providers remain disabled until the operator configures one. A valid configuration is not proof of account access, model availability, latency, naturalness or cost.

## Accepted destinations

The same `provider_policy.py` rules protect text and realtime voice. Endpoints are operator configuration, never model-supplied tool arguments.

- Gemini text uses `https://generativelanguage.googleapis.com/v1beta`; an empty endpoint selects this default
- Gemini voice uses `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`; an empty endpoint selects this default
- Qwen text uses the exact `/compatible-mode/v1/chat/completions` path on the existing shared domains `dashscope.aliyuncs.com`, `dashscope-intl.aliyuncs.com`, `dashscope-us.aliyuncs.com`, or a single workspace/trial label followed by a published region and `.maas.aliyuncs.com`
- Allowed Qwen text workspace regions are `cn-beijing`, `ap-southeast-1`, `ap-northeast-1`, `eu-central-1`, `us-east-1`, and `cn-hongkong`
- Qwen voice uses `/api-ws/v1/realtime` on the Beijing/Singapore workspace domains or the `dashscope.aliyuncs.com` / `dashscope-intl.aliyuncs.com` shared gateways. Gateway acceptance does not establish that a particular realtime model or account is available there

Configure the base WebSocket endpoint without a query. The Qwen adapter adds its configured model parameter itself. Gemini credentials remain in the server-side header rather than a URL. Unsupported destinations require an explicit code/policy change; do not enter a proxy or arbitrary relay endpoint as a provider URL.

The validator rejects userinfo, explicit ports (including `:443`), queries, fragments, whitespace/control characters, backslashes, misleading host suffixes, unexpected subdomains, wrong paths and malformed URLs. Model identifiers and credential header values are also checked. Invalid configuration reports unconfigured rather than raising a URL-parser exception.

## Transport behavior

Credential-bearing HTTP and WebSocket calls do not follow redirects. A redirect fails the connection and requires the operator to review the configured official endpoint. Environment proxy discovery is disabled for these calls (`httpx trust_env=False`, WebSocket `proxy=None`), so `HTTP_PROXY`, `HTTPS_PROXY` or `ALL_PROXY` cannot silently route a provider call. Deployments that require a proxy or private trust store need a separately reviewed explicit transport configuration; this version has no such setting.

TLS verification remains enabled. There is no fallback to HTTP, insecure certificates, another provider, a new endpoint or an automatic paid reconnect. Voice configuration is checked again immediately before opening the credential-bearing connection. This is destination validation for the existing single-host prototype, not an OS/network sandbox or a guarantee against an operator-controlled DNS/TLS environment.

Personal-context sharing is a separate permission. Selecting a provider does not by itself authorize uploading screenshots, arbitrary files, personal memories, saved chat history or business records. Calendar/task data retains its projection rules and additionally requires explicit business-context consent bound to the configured destination.

## Source and verification scope

Rules were checked against these primary sources on 12 October 2026:

- [Alibaba Model Studio base URLs](https://help.aliyun.com/en/model-studio/base-url): shared and regional workspace endpoints
- [Alibaba WebSocket connection overview](https://help.aliyun.com/en/model-studio/realtime-websocket-overview): realtime path, model query and regional gateways
- [Gemini Live WebSocket reference](https://ai.google.dev/api/live): pinned bidirectional endpoint
- [Gemini API reference](https://ai.google.dev/api): server-side API-key header and text API shape

`tests/test_provider_policy.py` exercises accepted and rejected targets, malformed ports, provider/channel binding, header/model values, redirect denial, proxy settings and configuration changes between voice ticket and connect. Existing fake voice transports use a syntactically approved synthetic workspace domain and never make a real provider request. No account was configured and no paid call or real audio capture was used to validate this change.

## Personal context in voice sessions

Voice sends an initial bounded memory projection only for a signed-in owner who explicitly enables memory use and approves that exact voice destination. Paired displays and voice agents never receive personal memory or saved conversation history. No voice transcript is added to retained text conversations. Memory-write tools are neither advertised nor authorized for voice; changes stay in the owner’s text/review flow.

Saved task, calendar and computer-job tools additionally require the owner’s explicit business-context sharing setting and exact destination approval. Without that consent, these tools are not advertised and invented calls fail before reading saved data. Local manual operations and the immediate physical-output stop remain available.

A session pins the context/privacy revision. A change to memory, context settings, destination or global privacy settings ends the session before further provider sends/receives or at the one-second watchdog. The user sees `VOICE_CONTEXT_CHANGED` and must start a new session after reviewing settings; there is no automatic paid reconnect. This stops subsequent use but cannot recall bytes already sent or guarantee remote deletion. Audio already in flight may also have reached the provider before a setting change was observed.


## Bounded text response reading (durable-run integration)

The shared Qwen/Gemini text transport now streams admitted identity-encoded JSON instead of buffering an arbitrary response before validation. Raw response storage is capped at 128 KiB; declared oversize/invalid lengths, compression, malformed JSON and elapsed-budget violations fail without retry. Numeric usage records remain unchanged and failed calls still consume the run's reserved attempt.

A 30-second monotonic deadline is checked after response headers and on every raw body chunk. HTTPX uses five-second per-phase inactivity timeouts. Nominal body read time can overrun the deadline by an already-blocked read timeout; response-header parsing and blocked OS operations are not forcibly killed. These checks bound application body storage and ordinary streaming progress, not an OS-level hard deadline. Generation fences separately prevent late results from publishing after cancellation/shutdown. Synthetic MockTransport tests include trickle chunks, unknown-length oversize bodies, rejected compressed responses, malformed JSON, both provider response schemas and no automatic retries. No live paid-provider or voice-protocol claim follows from these tests.
