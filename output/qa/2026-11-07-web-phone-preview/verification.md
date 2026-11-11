# Group 2 - Web and phone preview opening

7 November 2026, Asia/Hong_Kong. Owner asked to open the mobile and web versions for inspection.

Read current AGENTS, START, handoff, product requirements (current UI/provider/permission section), latest relevant decision and frontend package/Vite configuration; reused the existing private Mac launcher and owner runtime. Markdown inventory found only the root AGENTS. No code or business configuration was changed.

Started source855e60ee on loopback API8831 and Vite5190, retaining the existing normal Mac runtime. Private process/log record: ~/.config/desk-companion/web-phone-preview-20261107. Opened the desktop conversation in Chrome and phone surface in the in-app browser. Both visibly show Desk connected, Alice, composer and OpenAI Realtime with microphone off. No paid model request or media capture was started by the opening check.

Direct CDP metric overrides did not produce a correctly composed preview image; those overrides were cleared. The supported in-app viewport control now holds393x852 for the requested phone view, while desktop Chrome uses its normal window. Both final tabs are marked deliverable. The phone is a browser preview, not a newly built native iOS application. Only loading/display was checked, not a full interaction regression.

Updated handoff runtime note and work-log. No new decision, source changes, CI, Pi operation or GitHub publication was needed for this local preview request.
