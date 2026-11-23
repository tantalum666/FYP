# Group 2 · Google Calendar import review

On 23 November 2026, an independent reviewer verified the first `google-backup` checkpoint, `401e0fb227257b7aa24be690863c5eef4553db6f`. The source was extracted by commit hash. The tests ran on macOS with Python 3.14.5, Node 22.23.4, temporary SQLite desks and a synthetic Google transport.

| Case | Observed outcome |
| --- | --- |
| Two grants import the same occurrence ID | The original sample produced two local IDs, then returned HTTP 409 on restore and left the destination empty. The identical sample on the corrected commit exported two distinct backup identifiers, confirmed with HTTP 200 and read both original local IDs and titles from the fresh calendar. [Original HTTP sample](backup_roundtrip.py) |
| Upgrade an actual pre-feature database | Historical commit `e06c5149` created two v2 entries through HTTP. Google supplied one replacement and the owner edited the other. The first implementation, `f7ba18c9`, classified both as conflicts. The corrected commit advanced the Google copy to v3 on its original ID and preserved the owner's v2 title and notes. An attempt to override that manual edit returned HTTP 422 with no changes. [Upgrade fixture](verify_upgrade.py) |
| Inaccessible and cancelled events in one review | The preview changed zero events. Confirmation updated one, removed one explicit cancellation and kept two, including the Google 404. A repeated confirmation returned the original receipt. When the provider could return the unavailable event again, a new review and confirmation updated its original local ID. An unrelated listed event received zero detail requests. |
| Delayed response across owner-session renewal | A focused Node test exercised the actual DataPanel component against a simulated session transition with the same grant and visible status. The former request's delayed success and recovery both left its private title absent. Recovery for a request from the current session displayed the current title. The check used component output. |

## Reproduction

Set `BEFORE` and `CANDIDATE` to the respective extracted `desk-companion` directories, `QA` to this directory and `PYTHON` to the installed project interpreter. The candidate frontend uses the project's installed Node packages. The Python fixtures share the candidate's in-memory provider through the [fixture import](google_desk_fixture.py).

```sh
scratch=$(mktemp -d)
PYTHONPATH="$BEFORE/backend:$CANDIDATE/tests" "$PYTHON" "$QA/verify_upgrade.py" seed "$scratch/desk"
PYTHONPATH="$CANDIDATE/backend:$CANDIDATE/tests" "$PYTHON" "$QA/verify_upgrade.py" verify "$scratch/desk"
PYTHONPATH="$CANDIDATE/backend:$CANDIDATE/tests" "$PYTHON" -m pytest -q -s "$QA/backup_roundtrip.py"
(cd "$CANDIDATE/frontend" && node --experimental-strip-types --test --test-name-pattern='after desk:session$' tests/google-import-review.test.ts)
```
