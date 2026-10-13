"""Read-only product inspection; mutations are confined to isolated synthetic SQLite."""
import json, sqlite3, tempfile
from pathlib import Path
from desk.store import Store
out = {}
with tempfile.TemporaryDirectory(prefix='watch-retention-audit-') as tmp:
    store = Store(tmp, password='synthetic-only')
    with store.connection(write=True) as c:
        c.execute('PRAGMA user_version=2')
        c.execute('CREATE TABLE audit_lifecycle_marker(id INTEGER PRIMARY KEY)')
        c.execute('INSERT INTO audit_lifecycle_marker VALUES(1)')
    Store(tmp, password='synthetic-only')
    with store.connection() as c:
        out['legacy_bootstrap'] = {'version_after_reopen': c.execute('PRAGMA user_version').fetchone()[0], 'marker_rows': c.execute('SELECT COUNT(*) FROM audit_lifecycle_marker').fetchone()[0]}
    try:
        with store.connection(write=True) as c:
            c.executescript('CREATE TABLE audit_partial_migration(id INTEGER); INSERT INTO audit_partial_migration VALUES(1);')
            raise RuntimeError('injected-after-script')
    except RuntimeError:
        pass
    with store.connection() as c:
        out['executescript_after_context_rollback'] = c.execute('SELECT COUNT(*) FROM audit_partial_migration').fetchone()[0]
# Enumerate simplified valid state transitions under TOTAL receipt admission.
seen=set(); todo=[('active',1)]
while todo:
    s,n=todo.pop()
    if (s,n) in seen: continue
    seen.add((s,n))
    nxt=[]
    if s=='active':
        nxt += [('paused',n+1),('terminal',n+1),('terminal',n)]
        if n<256: nxt += [('active',n+1)]
    elif s=='paused':
        nxt += [('terminal',n+1),('terminal',n)]
        if n<256: nxt += [('active',n+1)]
    elif s=='terminal':
        nxt += [('purged',n+1)]
        if n<=254: nxt += [('trashed',n+1)]
    elif s=='trashed':
        assert n<=255
        nxt += [('terminal',n+1),('purged',n+1)]
    todo += nxt
out['abstract_receipt_model']={'states':len(seen),'max_receipts':max(n for _,n in seen),'every_admitted_trash_restorable':True,'lifetime_256_max_receipts':259*256}
assert out['legacy_bootstrap']['version_after_reopen']==1
assert out['executescript_after_context_rollback']==1
assert out['abstract_receipt_model']['max_receipts']==259
print(json.dumps(out,indent=2))
