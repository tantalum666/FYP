# Provider connection policy

Integrated 31 October 2026; original endpoint-source research was dated 12 October. Model providers remain disabled until the operator configures one. A valid configuration is not proof of account access, model availability, latency, naturalness or cost.

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

Personal-context sharing is a separate permission. Selecting a provider does not by itself authorize uploading screenshots, arbitrary files, personal memories, saved chat history or business records. Normal Alice/Omni retains the current projection/authority contract. Retained conversations and Work additionally use their explicitly scoped destination/context selection; see [saved-work privacy](personal-context.md).

## Source and verification scope

Rules were checked against these primary sources on 12 October 2026:

- [Alibaba Model Studio base URLs](https://help.aliyun.com/en/model-studio/base-url): shared and regional workspace endpoints
- [Alibaba WebSocket connection overview](https://help.aliyun.com/en/model-studio/realtime-websocket-overview): realtime path, model query and regional gateways
- [Gemini Live WebSocket reference](https://ai.google.dev/api/live): pinned bidirectional endpoint
- [Gemini API reference](https://ai.google.dev/api): server-side API-key header and text API shape

`tests/test_provider_policy.py` exercises accepted and rejected targets, malformed ports, provider/channel binding, header/model values, redirect denial, proxy settings and configuration changes between voice ticket and connect. Existing fake voice transports use a syntactically approved synthetic workspace domain and never make a real provider request. No account was configured and no paid call or real audio capture was used to validate this change.

## Current voice and retained-context integration

Current Qwen Omni, Qwen Audio and Gemini protocol adapters remain in the existing voice service. The Qwen Omni production endpoint `wss://maas.qianwenaiapi.com/api-ws/v1/realtime` and configured model remain supported. The old PR5 rule that prohibited all voice memory tools is superseded by the accepted current owner proposal/permission path. Paired and live replay boundaries retain their current tests. Retained text-history consent is not substituted for ordinary voice settings.

Voice Work only records bounded server-observed input candidates for an actual visible owner. Selection/freeze and explicit Work admission are separate. It neither grants action authority nor automatically persists a transcript. Current memory revisions invalidate normal replay and the retained Work projection; provider and privacy changes fence retained handoffs. No live voice call was made in this integration.

## Bounded text response reading (durable-run integration)

The shared Qwen/Gemini text transport now streams admitted identity-encoded JSON instead of buffering an arbitrary response before validation. Raw response storage is capped at 128 KiB and explicit structural depth at 64; declared oversize/invalid lengths, compression, malformed JSON and elapsed-budget violations fail without retry. Numeric usage records remain unchanged and failed calls still consume the run's reserved attempt.

A 30-second monotonic deadline is checked after response headers and on every raw body chunk. HTTPX uses five-second per-phase inactivity timeouts. Nominal body read time can overrun the deadline by an already-blocked read timeout; response-header parsing and blocked OS operations are not forcibly killed. These checks bound application body storage and ordinary streaming progress, not an OS-level hard deadline. Generation fences separately prevent late results from publishing after cancellation/shutdown. Synthetic MockTransport tests include trickle chunks, unknown-length oversize bodies, rejected compressed responses, malformed JSON, both provider response schemas and no automatic retries. No live paid-provider or voice-protocol claim follows from these tests.
