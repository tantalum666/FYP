# Group 2 · Resuming flight options after a desk restart

The repaired API candidate `14e1ce9114fde47e924dc3c35c83f2f23d050185` restored the owner’s original flight choices after a backend restart and respected a lower budget stated in the same conversation. Its complete Git tree `f175e57428fcd268c73743e539ba14cf2dd94d85` matched the detached checkout used for the HTTP tests. The restart, account isolation, fare, calendar-conflict and booking-to-calendar checks below gave the same results before and after the budget repair. [Machine-readable results](receipts.json)

| Action in the ordinary Alice conversation | Observation |
| --- | --- |
| Create two HK$50 shortlists for HKG to HND, then restart the server with the same database and login cookie | The replacement process began with an empty chat buffer. “Pick the second option” asked the owner to distinguish 4 and 6 December. Reopening list 1 returned its three original options without a supplier or model call. |
| Pick the original second option from list 1 after the inventory changed | FQ355 moved from HK$36 to HK$43.25. The newly second-ranked flight was FQ345. Alice returned FQ355 for the original date, and repeating the same request reused its approval without another search. Confirming at the old HK$36 returned HTTP 409. |
| Open the same chat and select or confirm the same quote from a second login | The other login’s review collection was empty. Reading the list, selecting its second option and submitting its bound quote each returned HTTP 404. |
| Change FQ355 to HK$55, then make it available at HK$44 and add a busy appointment | The HK$55 fare exceeded the original HK$50 limit and invalidated the earlier approval. The later HK$44 quote was unapproved. A calendar event created before confirmation blocked the booking. The supplier recorded zero orders and the desk recorded zero approved amounts. |
| Choose a clear departure from the same restored list and expressly approve HK$30 | Only this approval created a fixture booking. Its original supplier record matched FQ365 and HK$30. The separate calendar preview added zero flight events. Saving created one private 18:00–21:00 Hong Kong event on 4 December. The calendar path read the original receipt twice and added zero purchases. |

## Lower budget stated during selection

On the initial candidate `c6542aac904d3d451cb89868436c74ffeda8da1a`, the English request reduced the ceiling from HK$50 to HK$32 and asked for the second option only if it fit. Alice offered an actionable HK$43.25 quote. SQLite still held the HK$50 ceiling. The preceding release `01a15501250383ed5218eda2bce9cd83e665a789` could list alternatives before restart, then returned HTTP 404 for the same login’s request to select an original option after restart.

On the repair, the identical English request and a later tap on the original option both rejected HK$43.25. When the selected fare fell to HK$31.50, Alice offered it for fresh approval. The model fixture supplied HK$90 and the stored quote still capped the fare at the owner’s HK$32. A Chinese request for the original second option with a stated maximum of 32 港元 produced an unapproved HK$30.25 quote with the same stored ceiling. A longer Chinese formulation prompted Alice to ask the owner to specify the option and limit, both when the fare was available and when it exceeded the cap. These five budget samples produced zero supplier bookings. [Exact requests and results](receipts.json)

## Evidence and scope

Independent checks used detached checkouts, fresh FastAPI/Uvicorn processes on loopback, throwaway SQLite databases and the production composer’s streaming HTTP endpoint. The unstreamed message and authenticated calendar/commerce endpoints supplied the control reads. The model protocol and inventory were local fixtures. The scripted supplier maintained an original booking record independently of the desk. The run used no provider account, external network connection or paid call.

Read the project instructions, handoff, current flight product requirements, recent commerce decisions, travel section of the personal-agent research index, ordinary-flight contract, scoped review storage and handlers, and the previous calendar acceptance. The historical Simulator and provider journeys retain their own evidence. This review adds the restart, changed-inventory, ownership, budget and calendar observations above. [Flight contract](../../../../desk-companion/docs/conversation-flight-booking.md) · [Previous calendar acceptance](../simulator/verification.md)
