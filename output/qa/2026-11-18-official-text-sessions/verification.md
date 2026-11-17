# Group 2 · Official text Sessions and batched proactive delivery

18 November 2026, Hong Kong. The ordinary OpenAI path behind both application message routes has moved from the local model loop to official Sessions and Functions in [PR 132](https://github.com/tantalum666/FYP/pull/132), based on the PR 131 deployment handoff. The other change applies Anthropic’s outbox guidance to Alice’s existing notification delivery. [Design and reading record](design.md) · [article and implementation decisions](../../../research/2026-11-18-always-on-personal-agent.md) · [acceptance receipt](acceptance.json).

## Ordinary conversations

- Exercised a first message, a function call and a follow-up in the same scoped session. Checked duplicate operation replay, independent owner logins, fresh local context after a provider-side 404, source/privacy changes, private-mode inputs, revoked login and stale function requests.
- Checked a function-result acknowledgment lost before acceptance, an input acknowledgment lost after acceptance, duplicate SSE events, commentary and output belonging to another turn. Only a pending matching function executes. Only the current completed root turn and its final-answer message establish a model reply. A review card comes from its local business receipt.
- Lost draft acknowledgments leave one pending task draft, and the task remains uncommitted. A concurrent Full-to-Ask change leaves a prepared draft for review. Browser admission and mail drafting retained their own confirmations. No fixture sent email or placed an order.
- Checked eventual metadata lookup after an unknown session creation, cleanup after logout/forgetting, 409 deletion retries and server-side expiration. Known expired resources are replaced before submitting the next message. Scripted terminal failure and cancellation, historical function items and wrong-turn final messages could not produce a verified answer or execute an action.
- The recorded creation body contained 34 owner-visible functions. An isolated copy of the official Python SDK 3.53.0 validated the actual serialized create, follow-up and tool-result shapes. The app uses its existing HTTP transport and pinned provider/loopback settings. The prior live browser acceptance was for a different feature. This turn did not send a live inference request. [API reference](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/methods/create) · [Function results](https://developers.openai.com/api/docs/guides/agents-api/tools/functions).

## Personal-agent behavior

Multiple current findings accumulated during quiet hours. Reopening the store produced one content-free notification with individually reviewable findings. Acknowledging one retained the shared notification for the others. Tests covered priority ordering, the minimum interval across midnight, atomic notification receipts, dismissal, and migration of a legacy record whose notification was already delivered. Releasing a finding used no new inference.

The current source groups up to three findings. Existing daily limits remain six interruptions in Normal and two in Less often. Per-interruption spacing is 30 minutes and two hours respectively. The source-backed finding, the notification and the original task remain distinct records. [Proactive contract](../../../desk-companion/docs/proactive-research.md).

## Actual browser checks

The real Web composer submitted two related messages through the normal SSE endpoint to an isolated FastAPI instance with a scripted OpenAI transport. The browser showed the clock-function result and the answer to the follow-up. There was one session creation, one function receipt, one follow-up input and zero page errors. No production database was opened by the fixture.

In the Chinese phone layout, two fictional studio findings accumulated in quiet hours, survived reinitializing the service, and produced one notification. Both were visible in Conversation. Each acknowledgment succeeded independently and the notice closed after the second. The two images were visually checked and their hashes are recorded in the receipt. An initial browser fixture used an unlisted local origin, and a phone assertion used a helper rejected by CSP. The final checks used the existing supported QA port and normal DOM locators. Application origin and CSP policies were preserved.

## Checks, scope and next acceptance

Across 25 affected test files, **328 distinct cases passed** in targeted local runs, including 20 dedicated Sessions cases. Counts were deduplicated from collected node IDs, selectors, failure reports and successful focused reruns. This was not a new full-repository run. Earlier test failures exposed fixtures still stubbing the former planner. Provider-specific tests now exercise the Sessions wire path, and compatibility fixtures explicitly select their scripted provider. The local Ruff check and staged whitespace, link and publication-scope checks passed. The existing TestClient dependency deprecation warning remained.

Reviewed the repository entry rules, current product and handoff, relevant November decisions, the personal-agent index, deployment receipts, prior official capability reviews, the actual text/attachment/permission/notification paths and the school repository’s collaboration convention. Updated current entry points, product and capability status, the delivery and text contracts, research index, decision log, work log and handoff. Raw local logs, synthetic stores and screenshots remain private.

The normal Mac Web, iPhone Simulator and Pi release last verified is `c607759e`. No deployment, GitHub CI, new credential, remote automation or background model activation was part of this change. The next acceptance is one real read-only function and one same-session follow-up, under a separately authorized allowance, with remote result and deletion readback. [Running release](../2026-11-18-three-end-rollout/verification.md).
