# Group 2 · Reopen UI preview

2 November2026, Asia/Hong_Kong. Owner requested opening the webpage. Read AGENTS, handoff and current entry in full; product current-priority/current-requirements sections; latest UI/cross-application decisions; ui-copy contract; relevant startup/configure sections of app.py, application_work_acceptance.py and Vite config. Located relevant Markdown with rg; no whole-history reread.

Port5191 and8861 were stopped. Restarted the existing synthetic work-ui-01 data with ordinary create_app, scheduler=False, no connectors/public capture, and text/voice/Omni/computer providers disabled. This is a UI preview, not the earlier offline scripted execution runner. API on127.0.0.1:8861 (PID40997); Vite on127.0.0.1:5191 proxies it. No real user store, .env, model budget, application VM or Pi changed.

Opened visible in-app-browser tab at http://127.0.0.1:5191/?page=tasks and observed Desk connected, Tasks, Work & tools, current synthetic task and Alice controls. Marked the tab as a deliverable. No product source changes, full test rerun or new publication required for reopening the preview. Updated runtime handoff and work log. Next implementation step remains ordinary Alice/Omni long-task admission/recovery, offline first.
