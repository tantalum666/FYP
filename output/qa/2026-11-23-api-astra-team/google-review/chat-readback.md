# Group 2 · Last confirmed calendar refresh in chat

Independent HTTP review passed on commit `4e772ee2c40a38ea888215f5e8b9b24e9c5011be`, tree `2259321946c0b4bb263dc1c7c2934fc5552257e3`. The test used the ordinary owner message and streaming endpoints, a temporary SQLite desk, a controlled clock and synthetic transports. [Runnable sample](chat_readback_case.py)

| Time in UTC | Owner action and observable result |
| --- | --- |
| 03:07 | Opened a four-event refresh preview. A chat question found no confirmed result. |
| 03:16 | Confirmed one update and one cancellation. Two copies stayed local, including one unavailable from Google. |
| 03:25 | Opened a new preview proposing two removals and one update. Left it pending. |
| 03:31 | The English JSON reply and Chinese streaming reply both reported the 03:16 confirmation. The stream returned one final answer. Neither response contained an appointment title. |

Hiding private context prevented the original request key from replaying the counts. A different owner login, a replacement grant and a disconnected account each received the unavailable answer. Disconnecting cleared the stored summary. Reinstating the original synthetic grant still gave the unavailable answer.

The observed tool was `connected_app_query` with `service=google_calendar` and `view=last_refresh`. The chat requests made zero Google HTTP calls and zero model calls. One focused pytest case passed on Python 3.14.5.

Run from the extracted candidate's `desk-companion` directory with `QA` set to this review directory.

```sh
PYTHONPATH=backend:tests .venv/bin/python -m pytest -q "$QA/chat_readback_case.py"
```
