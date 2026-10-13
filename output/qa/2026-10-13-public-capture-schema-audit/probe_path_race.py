import importlib.util, json, os, sqlite3, sys, tempfile
from pathlib import Path
ROOT=Path('/workspace/shared/fyp-agent-20261012/desk-companion')
sys.path.insert(0,str(ROOT/'backend'))
from desk.store import Store

def v2(root):
 s=Store(root,password='synthetic-only')
 with s.connection(write=True) as c:
  c.execute('DROP TABLE public_capture_operations'); c.execute('DROP TABLE public_captures'); c.execute('PRAGMA user_version=2')
 return s
spec=importlib.util.spec_from_file_location('cli', ROOT/'scripts/migrate_public_capture.py'); cli=importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
with tempfile.TemporaryDirectory(prefix='capture-audit-') as t:
 root=Path(t)/'approved'; other=Path(t)/'unapproved'; v2(root); v2(other)
 original=cli._existing_private_database
 def changed(path):
  result=original(path)
  (root/'desk.sqlite3').rename(root/'approved-original.sqlite3')
  (root/'desk.sqlite3').symlink_to(other/'desk.sqlite3')
  return result
 cli._existing_private_database=changed
 result=cli.main(['--runtime',str(root),'--allow-public-capture-migration'])
 with sqlite3.connect(other/'desk.sqlite3') as c: version=c.execute('PRAGMA user_version').fetchone()[0]
 print(json.dumps({'cli_result':result,'unapproved_target_version':version,'path_is_symlink':(root/'desk.sqlite3').is_symlink()}))
