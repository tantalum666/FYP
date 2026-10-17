# Focused assistant UI reference

Group 2 ·17 October 2026. The owner requested a simpler AI interface with one input or voice button. [Native ImageGen reference](reference.png) was generated before implementation, selected by the assistant as an engineering reference; it is not an owner-approved final mockup. The original1254×1254 PNG bytes are preserved from the native generation result. The design intention below is a reconstruction from the run context, not a claimed verbatim copy of the tool prompt.

The reference uses a white panel, open chat area, centered “What can I help you with?”, and one tinted bottom composer. Empty text shows a44px violet mic; entered text replaces it with Send. Plus/More disclose additional actions. Inter, dark#242936, secondary#747D91, border#E8EAF0 and violet#6266D9 align with the existing app.

Implementation preserves those hierarchy, font, palette, composer/button and whitespace choices. Deliberate functional differences: the existing close/dirty guard remains; More has a separate short toolbar row; a compact Local mode caption prevents the disabled text model from masquerading as open-ended AI. File approvals and drafts appear only when needed. Voice has a focused listening view with stop/end and optional visual sharing; destination/retention text appears with sharing controls.

Conversation text stays in component memory, bounded to40 entries and lost on close; it is not a new persistent memory product or model-history protocol. Secondary file forms remain mounted after first opening so returning to chat does not erase unsaved text; the parent close guard still protects them. Confirmation/cancellation, unknown-write recovery and owner boundaries remain in their existing services.

[Actual screenshots and fidelity/interaction checks](../../../output/qa/2026-10-17-assistant-simplify-avatar/verification.md) distinguish this reference from the runnable UI. No new Qwen paid calls or real media capture were used for the redesign.
