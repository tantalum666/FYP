# Original Pi application release and public weather

On **23 November 2026 at 23:40 Hong Kong time**, the original Raspberry Pi 5 independently served `a17ac3497eaa1a564768037554280336f4c24245`, the same application accepted on the normal Mac Web and installed iPhone Simulator. The Pi switched once from `08200201`. Intermediate builds `689d1d8e` and `ca01d23c` were staged and rehearsed while the original service kept running. The final API and kiosk were both active with zero automatic restarts. [Machine-readable device and weather receipts](receipts.json) · [Previous Pi release](../pi-stable-release/verification.md)

## What the owner can ask

Three fresh Chinese messages went through the ordinary assistant endpoint on the running Pi. Each operation recorded one successful read-only `weather_query`. The responses resolved the requested destination, local date and rainfall outlook. Japan was already on 24 November while Hong Kong was still on 23 November.

| Destination | Current reading | Precipitation in the reply |
| --- | --- | --- |
| Tokyo | Open-Meteo model estimate, 24 Nov 00:30 JST, **7.0 °C** | Heavy rain forecast for the day, **100%** maximum hourly precipitation probability and **16.5 mm**. The reply included 16:00–19:00 local time. |
| Narita International Airport | Open-Meteo model estimate, 24 Nov 00:30 JST, **7.9 °C** | Heavy rain forecast for the day, **100%** maximum hourly probability and **14.5 mm**. The reply included 17:00–20:00 local time. |
| Hong Kong | Hong Kong Observatory station observation, 23 Nov 23:00 HKT, **23 °C** | The HKO bulletin for 24 November forecast a few showers, more frequent at first. The separate Open-Meteo daily data for 23 November gave **37%** maximum hourly probability. |

The normal data store gained three ordinary reply receipts and three read-tool audit rows. Conversation-history counts, model usage, the normal spending ledger and the flight/shop order tables stayed unchanged. No payment or supplier order was submitted. The exact public responses are bound to hashes in the receipt. [Hong Kong Observatory local forecast](https://www.hko.gov.hk/en/wxinfo/currwx/flw.htm) · [Open-Meteo forecast data](https://open-meteo.com/en/docs)

## Kiosk, retained data and rollback

- The real **1280 × 720** kiosk displayed Alice, the connected status and the composer. Its original Chromium profile contained the new production JavaScript entry. The normal and device HTML hashes matched the release. Eight bootstrap resources and the avatar, licence and font files were also verified over HTTP.
- During the normal switch, the Pi’s own Chromium opened an isolated synthetic desk at `/?surface=device`. Starting a conversation displayed a **48 CSS-pixel** Listening row with three **44 × 44** controls. Switching back to text succeeded. The fixture used a synthetic microphone and a loopback-only voice protocol, and ran without a second simultaneous normal renderer. The owner’s actual kiosk subsequently reopened under its original profile. This checked the rendered controls without a paid voice session.
- All **585** original release files and **631** target files passed the manifest check. The direct archive delivered 75 changed files and reused 556. It created a separate ARM Python 3.13 environment that kept the 39 existing packages and added only the two lock-verified OpenCC 1.4.2 packages.
- A network-disabled rehearsal on a private copy preserved the contents of all 130 original tables. After four additive provider/checkout tables were created, the old binary reopened the 134-table copy with its contents intact. The switch retained verified database, data-file and ledger backups plus the previous release and launchers. In the live store, 28 protected table fingerprints matched, and preexisting business and session rows were independently checked across 56 tables after the weather requests.
- The pre-switch owner cookie worked after restart. A3 v9 settings and its cached audio matched. Text, hosted browser and voice delegation retained GPT-6.2 Sol, with GPT-Live-1.1 for speech. The existing Gmail and Google Calendar identities, versions and scopes matched. The new LetsFG connection was disconnected.
- A separate original-device read confirmed the installed RTC helper SHA-256 `84c7c9aa1438f7acdb992f4530b2d2804eba50991c4da350c129fd49aae4770e`, both retained rollback files and the active timer. The PMIC, Linux and owner record agreed on an enabled deadline 178 seconds ahead. The 2.4 GHz CPU ceiling, boot configuration and firmware settings matched the preflight. The Pi stayed on the same boot throughout this application switch. [RTC deployment and recovery evidence](../pi-recovery/verification.md)

The release used the checked desktop manifest, pinned original-Pi SSH/SFTP route and existing staging, locked-environment, backup and rollback operators. An early staging-only weather observer incorrectly rejected HTTPX’s keyword-form call before reaching the network. That observer was corrected and real first-party reads were repeated. The final normal Pi results above used its unmodified running service. Screenshots from the synthetic fixture, complete operator output, owner-store snapshots and credentials stayed outside these public receipts.

## 24 November ticket-only follow-up

At 00:18:35 HKT the original device independently served `92acac8e`. The signed-in normal Pi returned the exact Chinese and English fresh-quote prompts when its login had no eligible fare. The actual kiosk profile contained the matching compiled entry. Both services were active, the previous RTC helper, A3 v9 and original grants matched, and 57 pre-existing business and session tables were checked. The two local replies created zero seller requests, bookings, model usage or changes to the normal budget. This delta reused the preceding real weather and listening evidence. [Supplemental device and prompt receipt](ticket-92acac8e.json).
