# Group 2 · First-request weather recovery

23 November 2026. The deployed application at `689d1d8e` returned “暂时没有读到东京所问日期的天气资料。” for the owner's first “帮我查一下东京的天气”. An authenticated, independent weather read on the same process at 14:44:58 UTC also returned unavailable. That release recorded no failure stage or upstream exception. A separate operator probe at 14:45:51 UTC completed both geocoding requests and the global forecast, and a new ordinary operation later returned 7.4°C at 23:45 in Tokyo. The original operation kept its original receipt.

A fresh instrumented application using the same weather implementation independently observed a cold TLS connection to the geocoder hit the production three-second limit at 14:54:11 UTC. The next attempt completed in 1.461 seconds. The returned forecast was valid. These measurements establish a recoverable transport failure mode. The earlier production outage could also have occurred at a different upstream stage.

## First normal HTTP request under controlled TLS latency

The same Mandarin input entered a fresh signed-in desk over the ordinary HTTP message route. A real loopback TLS listener held each geocoding handshake for 4.2 seconds and served the same forecast fixture to both versions. The application used its normal HTTPX network stack. Only the public destination addresses were redirected to the listener.

| Weather implementation | First ordinary result | Time |
|---|---|---|
| Deployed `689d1d8e` | Four consecutive three-second connection deadlines expired across two Chinese name variants. The owner received the same unavailable wording. | 12.24 s |
| Revised source | Both variants started together. Their three-second first attempts timed out. Both six-second attempts finished the handshake in 4.21 seconds. The first ordinary reply identified Tokyo and included the dated fixture range and 73% peak hourly precipitation probability. | 7.47 s |

An independent reviewer also held TLS for 3.4 seconds separately on the forecast and geocoding endpoints. The deployed code exhausted two three-second attempts on each endpoint. The candidate's second connection recovered both, in 6.412 and 6.433 seconds total respectively. [Before](replay-before.json) · [After](replay-after.json) · [TLS replay](replay_tls.py).

## Fresh public data

Two isolated ordinary SSE questions crossed Tokyo midnight. The public Tokyo result at **00:00 JST on 24 November** was 7.2°C, with a daily forecast of 6.8–18.3°C, 100% peak hourly precipitation probability, and 16.5 mm of precipitation. The hourly model indicated 16:00–19:00 local time. Reykjavík at **15:00 GMT on 23 November** was 7.6°C, with a 100% peak hourly probability and 11.7 mm forecast for its own local date. Both are Open-Meteo estimates. GeoNames and Open-Meteo returned real data. These reads made zero OpenAI requests. [Tokyo](live-tokyo.json) · [Reykjavík](live-reykjavik.json).

## Operation and regression evidence

Each fixed public read still makes at most two GET attempts. The second global TLS connection permits six seconds. Reads can also recover once from a transient disconnect, read timeout or selected temporary server error. A server's explicit `Retry-After` suppresses that immediate retry and sets the local backoff, capped at one day. A persistent transient transport failure is coalesced for five seconds. The existing successful caches, midnight expiry, city ranking, units and source calculations still apply.

An unavailable structured weather response identifies whether geocoding or the forecast failed, with a bounded category and HTTP status where available. The ordinary operation also keeps this location-free diagnostic in `weather_source_failure`, so a later successful read cannot overwrite the diagnostic for the first request. This field contains no URL, user message or coordinates.

Fourteen targeted tests passed, including transient errors inside the first ordinary HTTP request, partial Chinese-script lookups, negative-cache recovery, rate-limit backoff, preserved old operation receipts and cache concurrency. Ruff and the scoped diff check passed. Complete suites were not repeated. The comparison used the deployed source's weather path, which matched the weather code on `8e1469ea` before this patch. No running desk was modified. The release owner handles deployment and the combined handoff.

To run the TLS control on a checked-out version with the frozen dependencies installed, use `PYTHONPATH=backend:tests .venv/bin/python ../output/qa/2026-11-23-global-weather-cold-start/replay_tls.py` from `desk-companion`. The probe generates a throwaway loopback certificate and database. It makes no external requests.


## Station reading during a forecast outage

A general today or rain question keeps the available station temperature and adds one brief sentence when today's precipitation outlook is missing. Chinese reads “暂时查不到今天的降雨预报。” and English reads “Today's rain forecast is unavailable.” The current-only case retains its short observation. Nine targeted cases exercised the ordinary Chinese and English message endpoint, zero probability and amount, qualitative conditions, HKO’s category, the recorded 20:45 HKO bulletin and a temperature-range-only forecast. An available bulletin answers the question without an added outage sentence.
