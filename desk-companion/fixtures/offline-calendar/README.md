# Offline calendar fixtures

`desk-calendar-fixture-v1` files for the local schedule journey. Nothing here is a live calendar account.

One sync reads one batch. `sequence` orders revisions inside that batch. The same id and sequence with the same content is a duplicate. A lower sequence that arrives after a higher one is stale and does not rewrite the task. `interrupt` commits revisions already read and is not success. `revoke` and `disconnect` stop before any later revision is read.
