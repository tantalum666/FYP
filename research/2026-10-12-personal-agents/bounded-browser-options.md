# Bounded browser and desktop adapter options

Research date: 2026-10-12 UTC. Primary sources retrieved on that date. Research only: no package installation, browser launch, website interaction, credentials, or FYP source edits were performed by this worker.

## Recommendation

Implement a **FYP-owned, typed Playwright Python adapter** behind the existing durable-job executor registry. Begin with one reviewed public-read → existing document-editor → exported-artifact workflow. Keep approval, cancellation, evidence, and independent verification in the FYP service. Do not expose general browser code execution, arbitrary shell, or unrestricted click/type/navigation primitives to the planner.

Write and unit-test the adapter cloud-first, but **do not claim cloud browser execution**. The parent reports that both ordinary and permitted escalated cloud launch failed with a sandbox socket `Operation not permitted` error. No further launch retry, disabling sandbox flags, or alternative bypass is proposed. The existing Mac6.1SolMax QA task can validate the same FYP-owned runtime using an isolated browser after implementation, subject to its actual prerequisites and approved scope. Developer tool/browser access is not runtime capability in the FYP application.

The first result should be described as a **bounded, deterministic cross-web-application workflow**. Two tabs alone prove nothing. The proof is that the FYP worker reads state from one independently maintained application/site, manipulates another existing application's real UI, and verifies that application's exported result. This does not establish broad agent adaptability, control of arbitrary desktop apps, or authenticated third-party writes.

## Options compared

### Playwright Python library: recommended first adapter

Playwright supplies browser navigation, semantic locators, input actions, independent contexts, and event handling without requiring an LLM or a hosted model. Its Python asynchronous API fits a Python worker. Keep the browser off the FastAPI request lifecycle; a job should own its browser process and cleanup.

Use reviewed app-specific operations, such as `read_public_page` and `create_source_brief_in_stackedit`, rather than a caller-provided script. Actionability checks and automatic waiting help locate ready controls; they are not proof that a business write succeeded. Never interpret a timeout after clicking as permission to submit again. [Playwright actions](https://playwright.dev/python/docs/input), [auto-waiting](https://playwright.dev/python/docs/actionability)

### Playwright MCP: transport convenience, extra surface

The official server exposes browser operations through MCP and structured accessibility snapshots. The server itself need not call a paid model; its client determines that. However, the current tool list includes `browser_run_code_unsafe`, explicitly described as arbitrary server-process JavaScript and RCE-equivalent, plus page JavaScript evaluation. Origin flags are expressly not a security boundary and do not cover redirects. A default persistent profile is inappropriate for this test; isolated mode is available.

A filtered gateway and separately secured runtime could make MCP useful later, but it adds little to the first Python-only integration. Never expose the stock server directly to the planner or assume a descriptive permission field enforces the FYP's approval policy. [Official MCP repository and security guidance](https://github.com/microsoft/playwright-mcp)

### Selenium: credible alternative, no advantage here

Selenium WebDriver drives real browsers locally or remotely without an LLM. It is sensible if the project already depends on WebDriver/Grid. Here, it adds a browser-driver compatibility layer without solving authorization or process isolation. Selenium Manager can discover, download, and cache missing drivers; pre-provision and pin those instead of allowing new downloads during an approved job. [WebDriver](https://www.selenium.dev/documentation/webdriver/), [Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/)

### Browser Use: distinguish Actor from Agent

The deterministic Actor/BrowserSession API operates through CDP, not Playwright, and supports direct CSS element interactions without model calls. Prompt-based element finding and content extraction are separate LLM-powered paths. The high-level Agent consumes an LLM; official supported-model documentation includes Ollama, so a paid service is not intrinsically mandatory, but a local model still needs provisioning, resources, and evaluation. [Actor basics](https://docs.browser-use.com/open-source/legacy/actor/basics), [Actor examples](https://docs.browser-use.com/open-source/legacy/actor/examples), [models](https://docs.browser-use.com/open-source/supported-models)

For this already-structured FYP architecture, adding Browser Use's agent loop duplicates orchestration and expands dependencies. Its documented browser defaults include extensions, download acceptance, PDF downloads, clipboard and notification permissions. Each would need explicit overriding. Domain navigation restrictions must not be represented as verified whole-process network confinement. [Browser parameters](https://docs.browser-use.com/open-source/customize/browser/all-parameters)

### Direct desktop alternatives

- **PyAutoGUI:** genuine mouse/keyboard control of applications on Windows, macOS, and Linux. It has a corner-triggered fail-safe; leave it enabled. Coordinate actions require a live display and strong target-window validation, and do not provide origin confinement. It is a later option for a specifically approved application pair, not a replacement for browser boundaries. [Official documentation](https://pyautogui.readthedocs.io/en/latest/)
- **pywinauto:** Win32/UI Automation targeting can provide better semantic control on Windows. Its Application scope is process-bound; Desktop can cross process boundaries. It does not establish a Linux-cloud or macOS solution. [Getting started](https://pywinauto.readthedocs.io/en/latest/getting_started.html)
- **macOS Accessibility/Apple events:** require their actual granted permissions. Existing developer-tool access does not establish permissions for the FYP's own executable. If new Accessibility permission is needed, stop under the current no-security-change scope. [Apple permission guidance](https://support.apple.com/guide/mac-help/allow-accessibility-apps-to-access-your-mac-mh43185/mac)
- **LibreOffice UNO:** an official application API callable from Python is a practical later bridge into Writer/Calc. This is real application automation, but must be labelled an API integration rather than visual desktop operation. Its Python support can be optional in Linux packages. A `soffice` command existing does not prove UNO is available. [LibreOffice Python API help](https://help.libreoffice.org/latest/en-US/text/sbasic/python/main0000.html)

## Authentic acceptance workflow

### Preferred document variant: public documentation → StackEdit

Candidate workflow, not executed or UI-validated in this research:

1. The user authorizes one exact public documentation URL for reading and identifies the intended StackEdit destination and application-owned `.md` export slot. Use only public/synthetic content. For example: source title, source URL, observed heading, retrieval time, and a user-provided note.
2. FYP creates the durable run and starts its registered browser adapter. The browser reads the real source page, captures the title/heading with selectors, records the final URL and evidence, and rejects unexpected navigation. FYP then prepares the exact document preview/digest for owner approval before editor effects; this preserves current exact-content approval rather than silently introducing a bounded-transformation grant.
3. A distinct clean destination context opens the real StackEdit app. Through its UI, create a fresh named document, enter only the approved content, and use the editor's Markdown export action. Do not construct the final file directly, inject editor state with JavaScript, fake its network responses, or call a self-authored CRUD demo.
4. Independent verification checks the exported bytes, document name, exact required fields, source URL, size, and digest. A separate verification context may re-import that exact artifact through the editor's own local import UI if that round-trip has been approved and confirmed to work without an upload to a service. Compare the rendered document with the approved fields.
5. Close owned contexts and processes, then mark verified success only after artifact and lifecycle checks. Preserve an uncertain result if a commit/export may have happened but cannot be verified. Only the retained export is durable; the nonpersistent editor workspace disappears with its context. A job-owned context does not isolate the Mac itself: record actual sandbox and egress readiness, and do not call routing-only checks strict network confinement.

StackEdit is an existing Markdown editor with offline editing and local-file export functionality; cloud synchronization/publishing are separate capabilities and outside this workflow. Its exact current selectors, no-login behavior, dependency origins, and service-worker-blocked compatibility still require Mac acceptance testing. If they fail, stop and report; do not silently grant permissions, enable sync, or select a new external destination. [Official StackEdit site](https://stackedit.io/), [upstream welcome/export guide](https://github.com/benweet/stackedit/blob/master/src/data/welcomeFile.md)

### Alternative visual-artifact variant: public documentation → Excalidraw

The FYP reads the source, then uses Excalidraw's actual drawing/text UI to create a source card and exports one `.excalidraw` JSON file. A separate parser checks the text and scene fields; a fresh context reopens the artifact using an approved local import. Excalidraw documents local-first browser saving and an open JSON format. This demonstrates an independent diagram application, not a document/spreadsheet editor or native OS application. [Upstream Excalidraw](https://github.com/excalidraw/excalidraw/blob/master/README.md)

An unmodified, pinned, locally hosted version of an upstream application can support repeatable offline acceptance, but obtaining/building/running it is a separate prerequisite. A mock page or application written solely to make the adapter pass cannot replace the authentic-app acceptance gate.

## Required adapter contract and restrictions

The following are proposed engineering requirements, not claims that Playwright provides a complete security boundary.

- **Authority:** bind job ID, owner, approved intent digest, operation/schema version, exact source URL, destination application ID, content digest, expiry, and output path into the execution claim. Recheck authority immediately before every mutating step. No argument accepts Python, JavaScript, shell commands, arbitrary executable paths, or arbitrary browser flags.
- **Contexts:** create fresh nonpersistent contexts; no user profile, extensions, CDP connection to a personal browser, imported cookie/storage file, or credential discovery. Separate source and destination contexts prevents storage sharing. Do not persist whole storage state just to preserve one document. Context isolation is not an OS sandbox. [Context behavior](https://playwright.dev/python/docs/api/class-browsercontext)
- **Origins:** exact normalized scheme/host/port and allowed paths, with separate known asset origins. No wildcard domain suffixes or caller-chosen localhost. Validate navigation, frames, popups, new tabs, redirects, and final URL. Reject URL credentials, unexpected schemes, file URLs, and access to metadata/private-network services; an explicitly named loopback test app is the only local exception.
- **Network:** install default-deny request and WebSocket handlers before pages; block service workers. Permit only reviewed request methods/endpoints and no sync, sharing, analytics, external images, or model endpoints. Browser handlers are defense in depth. Playwright warns that page routing handles only the first URL of a redirect; URL checks after arrival cannot undo a transmission. For a strict network guarantee, use an already-provisioned approved egress boundary that also covers browser-process traffic, DNS/private-address destinations, and redirects. If absent, label confinement unverified and limit acceptance to trusted synthetic data; do not change OS/network security settings to manufacture a pass. [Routing redirect caveat](https://playwright.dev/python/docs/api/class-page#page-route), [network/service-worker caveat](https://playwright.dev/python/docs/network)
- **Permissions:** no camera, microphone, location, clipboard, notifications, payment handlers, new OS grants, saved credentials, TLS-error bypass, CSP bypass, or disabling browser security. Require `chromium_sandbox=True`; fail closed if unavailable. Playwright's documented launch default is false, so omission is not sufficient. [Launch options](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch)
- **Files:** default `accept_downloads=False`; the export workflow may use a dedicated destination context with a single approved export budget and cancel other download events. Do not call this a guarantee against every temporary browser disk write. Save only the expected format under the preallocated job directory, bound size/count/time, avoid executable extensions, reject traversal/symlinks/overwrites, and hash the artifact. No file chooser, upload, drag/drop, or arbitrary local file reads. A round-trip import is separately restricted to the one approved artifact. [Download lifecycle](https://playwright.dev/python/docs/downloads)
- **Lifecycle:** fixed job deadline and step budgets; cancellation token checked before effects; one job owns one browser process group. Close contexts, then browser, with bounded grace and a supervisor kill of owned descendants if needed. Never kill the user's browser. Test stale leases, process crashes, browser disconnects, and orphan detection. Killing stops future work; it cannot roll back a completed remote write. [Browser close behavior](https://playwright.dev/python/docs/api/class-browser)
- **Evidence:** record adapter version, browser version, approved origin manifest, operation sequence, intent hash, source observations, relevant screenshots, export digest, and terminal cleanup status. Redact cookies and auth headers; do not retain unrestricted HAR/HTML just because capture is available. Verifier independently reads the artifact or destination state; an executor's success string is insufficient.
- **Uncertain writes:** if a click or export times out after possible dispatch, reconcile actual destination/artifact state. Never replay merely because no success response arrived. Approval changes and cancellation invalidate outstanding action claims; stale approvals cannot authorize a new target or content.

## Acceptance gates beyond the happy path

Test rejected unapproved origin, redirect, popup, embedded frame, service worker, WebSocket, extra download, arbitrary import, stale approval, intent mutation, cancellation before and during a write, browser crash, output collision, and verifier mismatch. Include a hostile instruction in source text to establish that page content cannot change authority. Record these as policy-boundary tests, not a general prompt-injection security certification.

After the deterministic path passes, vary legitimate source content, document titles, minor layout changes, and non-destructive error conditions. That can begin measuring robustness. A hardcoded selector workflow succeeding once is not evidence that an agent can plan novel cross-application tasks.

## Read-only cloud inventory and limitations

Observed in this worker's execution environment on 2026-10-12:

- Non-root Linux x86_64; Python and Node/npm available
- Python distribution `playwright` version 1.62.0 installed
- `/usr/bin/chromium` wrapper and `/usr/lib/chromium/chromium` binary present
- No Playwright default browser cache found at the two inspected standard paths
- No Selenium, browser-use, PyAutoGUI, or pywinauto distribution reported by the active Python's package metadata query
- No `DISPLAY` or `WAYLAND_DISPLAY` value; no Xvfb, xdotool, wmctrl, Docker, or Podman found on the inspected PATH
- `mousepad` and a `soffice` wrapper found; neither was launched or validated
- No browser dependency mention in the two checked desk-companion dependency manifests; this is not a full source audit

The managed network allowlist does not list the proposed public source/editor origins. No runtime reachability is claimed. Most importantly, the parent's already-verified sandbox launch failure supersedes installed-binary presence: **cloud browser execution is blocked**. Do not retry or route around it. All real browser/application acceptance results must come from the authorized Mac QA environment or a later explicitly approved working environment.

No change to repository planning/source, no autonomous desktop access, and no new persistent access were made by this research worker.
