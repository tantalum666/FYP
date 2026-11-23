# Group 2 · Global weather

23 November 2026. The weather code at `0b597cd8` follows `0a0f7996` on the dedicated source branch based on `412721b2`. All runtime checks used an isolated desk. The earlier distributed release remains recorded in the integration handoff.

## Public weather through the regular composer

The owner's Chinese Tokyo and Hong Kong questions went through a real local TCP login, the ordinary SSE composer and the shared weather tool. Each reply matched the authenticated structured weather read. The test also exercised three cities outside Asia, Hong Kong tomorrow, a three-date ordinary Sessions function and the Live voice WebSocket. Open-Meteo, GeoNames and HKO returned public network data. The model endpoints used scripted protocols. The run incurred zero OpenAI charges and made no external account writes. [Run receipt](receipts.json) · [Reproducible probe](check_public.py).

Final readback finished at 2026-11-23T13:20:13+00:00. The timestamp below is the destination’s observation or model time. HKO supplied the physical station reading. Other current values are Open-Meteo’s model estimates. The displayed daily ranges in these five cases came from Open-Meteo.

| Destination | Local time and UTC offset | Current | Daily range | Forecast |
|---|---|---|---|---|
| Tokyo | 22:15 +0900 | 8.8°C | 4.2–12.8°C | 0% peak hourly precipitation probability. 0 mm forecast for the day. |
| Hong Kong | 21:00 +0800 | 23°C | 21.2–24°C | HKO’s 20:45 forecast expected several showers tonight and more frequent rain early tomorrow. Open-Meteo supplied a 10% peak hourly probability. |
| Cape Town | 15:15 +0200 | 22.2°C | 15.4–23.3°C | 49% peak hourly precipitation probability. 0 mm forecast for the day. |
| Reykjavík | 13:15 +0000 | 8.1°C | 6.9–8.6°C | 100% peak hourly precipitation probability. 11.7 mm forecast for the day. Expected precipitation includes 15:00–20:00. |
| Buenos Aires | 10:15 -0300 | 26.5°C | 18.4–29.7°C | 4% peak hourly precipitation probability. 0 mm forecast for the day. |

HKO’s separately dated 24 November forecast returned 18–23°C, rain more frequent early and a medium category for significant rain. The category stayed qualitative. The Tokyo three-day Sessions result used 24, 25 and 26 November in the destination timezone.

## Failure and correction

* The previous schema enumerated only `hong_kong`. The spoken guidance also explicitly restricted weather to Hong Kong. Its current route returned only a station temperature. The shared tool now requires a named place in newly advertised model calls and sends its summary and dated fields through both protocols.
* A real geocoding search for simplified 东京 initially returned two Chinese villages. Traditional 東京 returned Japan’s capital. The OpenCC dictionaries normalize both written forms. The lookup ranks populated places across results, applies geographic filters and asks for the city or region on ambiguity. A missing place or a failed search cannot silently borrow Hong Kong.
* The local day and time come from the destination’s IANA timezone and epoch timestamps. An hourly precipitation amount belongs to the preceding hour. Daily percentages are the maximum hourly precipitation probability. HKO’s past rainfall measurements never supply forecast probabilities. Missing hourly values or precipitation probabilities remain missing.
* During network verification, the first five-city pass stopped on a Buenos Aires lookup before a usable result was observed. A fresh diagnostic read recovered the intended city and real weather. Another run retained the Hong Kong forecast while its station connection timed out. Direct probes reproduced TLS handshakes exceeding five seconds and obtained an official station response at 6.8 seconds. The HKO connection budget now allows seven seconds. The final TCP acceptance requires both its fresh station measurement and its official local outlook. Complete feed failures return a dated stale indication when a source timestamp is available.
* Exact location is never requested by the conversational lookup. Explicit coordinates are rounded to a tenth of a degree. City resolution and weather caches are bounded in process memory. Multiple concurrent reads of the same public resource share one request. Forecast snapshots expire at destination midnight. A city lookup with Home weather disabled leaves the preference off. A failed traditional or simplified lookup cannot promote an unrelated, unverified village.

## Other runtime checks

124 focused local tests exercised weather, the ordinary Sessions transport, streaming, context limits, Live voice setup and calls, and existing voice lifecycles. The tests include the local date boundary where Hong Kong and Tokyo are on different dates, a cache crossing Tokyo midnight, incomplete provider data, geographic ambiguity, missing destinations, coarse coordinates, multi-day output and a partial Chinese geocoder outage. Ruff, frozen dependency validation and the scoped diff check passed. The Starlette TestClient emitted its existing deprecation warning.

Standalone city requests bypass paid text generation. Complex requests use the advertised permitted Functions under the existing conversation policy. The Live probe used a normal authenticated `/api/voice/tickets` and `/api/voice/ws` connection, a split synthetic input transcript, a deliberately empty remote function argument and a function result bound to that call. The real public result identified Japan and the returned caption matched the tool summary. This checks the voice transport and application dispatch. Physical speech recognition, speech synthesis quality and model tool selection require a separate live acceptance.

The existing Mac CPython 3.14.5 ran an isolated `uv sync --frozen` and the real API calls. The two `py3-none-any` wheels total 569,165 bytes. The converter also ran on local Python 3.12.13 and 3.13.13. Binary-only resolver checks accepted Linux aarch64 Python 3.13.5 and Windows x86-64 Python 3.12. The original Pi and a running Windows installation were outside this branch check.

From a development checkout with the frozen dependencies installed, run the TCP probe in `desk-companion` with `PYTHONPATH=backend:tests .venv/bin/python ../output/qa/2026-11-23-global-weather/check_public.py`. It uses a temporary database and a loopback port.

## Sources and review scope

The existing Agents Sessions, application Functions and Live response-item lifecycle remain the execution interfaces. I checked their public contracts, the project's actual session construction, function registry, tool visibility, context clipping, voice schema flattening, call dispatch, workspace preferences, Home read path and renderers. [Sessions](https://developers.openai.com/api/docs/guides/agents-api/sessions) · [Functions](https://developers.openai.com/api/docs/guides/agents-api/tools/functions) · [Live conversations](https://developers.openai.com/api/docs/guides/live-conversations).

The public forecast supplies WMO conditions, ranges, interval precipitation amount and probabilities. The geocoding API supplies multilingual aliases, qualifiers, place types and zones. HKO specifies separate station, short-range local and nine-day products, including the significant-rain category. [Forecast API](https://open-meteo.com/en/docs) · [Geocoding and GeoNames](https://open-meteo.com/en/docs/geocoding-api) · [HKO specification](https://www.hko.gov.hk/en/weatherAPI/doc/files/HKO_Open_Data_API_Documentation.pdf) · [OpenCC](https://github.com/BYVoid/OpenCC).

Read the full project AGENTS and handoff, product sections on daily speech, Home weather, current voice and official ordinary chat, and corresponding November decisions. Checked the scoped November 16 speaker requirements, the location and weather section of the Home contract, the ordinary Sessions contract, the prior voice evaluation, and the risk/verification sections of the user's review manual. Updated product, decision log, handoff, work log, daily presence, Home and public data attributions. The integration owner handles installed-device acceptance.
