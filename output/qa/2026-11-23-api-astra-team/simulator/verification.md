# Group 2 iPhone Simulator acceptance

On 23 November 2026, a request in Alice’s ordinary Home composer turned a verified synthetic booking into one private event in the desk calendar. The preview left the calendar empty until **Save to calendar** was tapped. Replaying that exact confirmation returned the same event. The app’s Calendar screen then showed one entry on 30 November. [Preview before Save](flight-calendar-preview.jpg) · [Saved event in Calendar](flight-calendar-day.jpg) · [Machine-readable results](receipts.json).

## What the owner saw

1. In an isolated iPhone 17 Pro Simulator running iOS 26.5 (23F77), the ordinary composer created the reference FR4315 fixture booking from HKG to HND. Its original quote was HK$34.00. Separate decisions approved the initial quote and the revised HK$35.43. The original fixture then returned a completed receipt with a matching HK$35.43 capture.
2. From Home, the signed-in test owner entered “Add this booked flight to my desk calendar” in the same conversation. A simulator touch activated **Send message**. The Home action **Review flight calendar times** opened the preview. It showed 30 November, 19:00–21:10 in Asia/Hong_Kong, with both **Save to calendar** and **Skip** available. SQLite still contained zero events. The original airport times were 19:00 in Hong Kong and 22:10 in Tokyo.
3. A simulator touch activated **Save to calendar**. Alice replied “I found this test flight on your desk calendar.” The authenticated event endpoint returned the same title and times as the preview. The desk’s calendar collection expanded exactly one occurrence from 11:00 to 13:10 UTC. The normal Calendar screen displayed **19:00 – 21:10** and **Test itinerary: FR4315 HKG → HND** on 30 November.
4. The native bridge replayed the original confirmation body and operation ID in the original signed-in session. The message endpoint and both event reads returned HTTP 200. The event ID and version 1 matched across the replay. A separate SQLite read still found exactly one private, busy event with an empty reminder list. The event held the public flight designator and airports. Its booking locator was absent.

| Checkpoint | Calendar events | Bookings | Supplier searches | Supplier bookings submitted | Supplier price answers | Original-record reads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Completed fixture before calendar request | 0 | 1 | 1 | 1 | 1 | 3 |
| Preview displayed | 0 | 1 | 1 | 1 | 1 | 4 |
| Owner confirmed | 1 | 1 | 1 | 1 | 1 | 5 |
| Exact confirmation replayed | 1 | 1 | 1 | 1 | 1 | 5 |

The calendar handoff made two read-only requests to the original supplier fixture. The original booking, capture and price-answer counts held steady. The text-model transport and Google received zero calls from the handoff. The isolated backend refused non-loopback network access and recorded zero such attempts. The reservation reference visible in the preview screenshot belongs to the repository’s synthetic fixture.

## Native Google refresh timeout

A separate fixture intercepted the native **POST /api/google/refresh** on loopback. From the same WKWebView, the real **DeskNative.request** bridge received HTTP 200 and the expected `desk-loopback-14s` marker after 14.228 seconds. The fixture measured its delay at 14.001 seconds. A subsequent native **GET /api/health** returned HTTP 200 and `ok` in 0.006 seconds. This check used a fresh local server with no Google account or external Google request.

## Tested source and restoration

The direct composer entry, calendar UI and native bridge were tested at `bc2796cc`, based on the model projection at `e06c5149`. The release owner matched the staged SHA-256 prefixes for the calendar handoff, commerce dispatcher, assistant panel, flight card and native app delegate against those Git blobs. The receipt records full hashes and a manifest digest for 501 staged backend and frontend source files. The distinct official Function for colloquial wording arrived at `f57e317c` and has separate backend protocol coverage. [Parent acceptance](../verification.md).

The app was built from a private snapshot using TypeScript, Vite and XcodeBuildMCP. Only QA packaging identifiers, app group, Keychain service and launch origin were isolated. A fresh loopback FastAPI server, SQLite database, mock Session and original repository flight fixture supplied the data. The simulator was newly created for this check. An initial automated keyboard input introduced extra spaces and was discarded before submission. The successful run checked the ordinary WKWebView editor’s exact text and used simulator touches for Send, opening the review and Save.

The temporary simulator was stopped and deleted, the QA backend port was closed, the private build and fixture database were removed, and XcodeBuildMCP’s previously empty session defaults were restored. The regular iPhone 17 Pro remained booted with the same app container, native executable-library fingerprint and frontend entry-bundle fingerprint. The run never opened the regular simulator’s data directory or the deployment’s database. No live payments, hardware deployment or real-account integration took place.

Read the repository agent instructions and current handoff, the current product requirements and ordinary flight sections, the recent calendar-aware decision, the travel journey in the personal-agent research index, the prior fare/calendar acceptance, the ordinary flight booking contract, the native bridge and the existing flight and Session fixtures. The simulator acceptance wrote only its two screenshots, this note and its receipts.
