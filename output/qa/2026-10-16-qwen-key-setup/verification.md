# Group 2: local Qwen credential setup QA

Date:16 October2026. Continuing the existing model-selection work: owner reported a domestic Key, selected Qwen3.8 Omni Flash Realtime, then supplied Qianwen platform Chat docs and base URL. No Key was requested in chat.

## Reading and source boundaries

[Inventory](reading-inventory.json) continues the same session's observed-text chain through the15 October Pi record.136 current pre-edit Markdown versions matched the recorded observed content; this is exact-text inheritance, not a second independent full read. RootAGENTS/product/handoff, operator guide and relevant current architecture/README/config sections were reread. New/modified text is authored/reviewed here. Prior chat or unfinished independent recovery is not promoted to live-provider evidence.

Read actual Qianwen Chat and Realtime pages and their API-Key/config links. Alibaba official navigation links the Qianwen homepage, which links the platform docs. The user's Chat URL initially failed direct fetch, then loaded through the docs' own navigation. The Chat base uses`https://maas.qianwenaiapi.com/compatible-mode/v1`; Omni uses a separate`wss://maas.qianwenaiapi.com/api-ws/v1/realtime` with model query. No secret was transmitted to either endpoint. Legacy Alibaba workspace routes are not silently mixed with this platform.

## Actual implementation and local result

Added the standard-library[setup helper](../../../desk-companion/scripts/configure_qwen.py) and[7 dedicated tests](../../../desk-companion/tests/test_qwen_key_setup.py). Native macOS hidden input or real-terminal getpass; no secret arguments or echo. Directory components open without following links; a0600 temporary file is published atomically without replacing an existing file.0700 destination directory, ownership checks, cancellation and injection rejection. Provider flags staynone and backgroundoff.

Actual local metadata: credential_present=true, provider_enabled=false, mode0600; selected_model=qwen3.8-omni-flash-realtime. Destination is the owner's private`~/.config/desk-companion/qwen.env`, outside the checkout. No secret body, prefix or hash is recorded. This staged file is not automatically loaded by the application and does not prove valid authentication.

First launch with systemPython3.9 stopped before input because of evaluated union annotations. Postponed annotations fixed compatibility; dedicated tests reran. One native attempt did not save, and metadata confirmed no config existed. A subsequent native entry completed and read-only status passed. No screenshots or clipboard reads were used.

## Checks and remaining work

Executed: project Python pytest on test_qwen_key_setup.py,7passed; Ruff on both new files,passed. SystemPython3.9 executed the native entry and read-only status successfully. App backend protocols were not modified, so unrelated application/frontend tests were not repeated. Documentary targets/identity/group names, whitespace, staged secrets and publication are checked separately.

Updated product, handoff, decision/work logs, software README/operator/architecture, companion architecture, service example and dated comparisons. Added[qwen-local-setup](../../../desk-companion/docs/qwen-local-setup.md). Old unchosen-model state is superseded by the owner's explicit choice; actual permissions, spend cap, Omni protocol and Pi/GUI acceptance remain open. No model request, account creation, service restart, media capture, originalA1 runtime change, Pi connection, hardware or school action occurred.

The local-target check found3 old absolute Downloads references no longer present on this host. Reread both historical notes to EOF, then changed only those links to the existing repository-owned school/teammate copies underinputs. No binary or school document body changed. The earlier1318/1319 result is dated evidence; this run records the current target state separately.

Current checks passed:137 project Markdown versions covered by inherited observed text/relevant rereads/authored changes;138 documents and1,334 local targets checked,1,333 resolve and one expected install-generated credentials target is absent. No unexpected broken links or wrong group numbers; identity source, existing backend/protected-path scope and whitespace passed. Real Key remains outside Git; staged scan and remote metadata are verified separately.

Staged secret scanning identified one generic-key finding in the synthetic test literal at test_qwen_key_setup.py:15. Metadata-only inspection established the fixture location; no real Key was staged or displayed. Replaced the literal with an explicitly constructed low-entropy fixture, retaining all security assertions and no scanner suppression. Re-ran the7 tests and final staged scan before publication.
