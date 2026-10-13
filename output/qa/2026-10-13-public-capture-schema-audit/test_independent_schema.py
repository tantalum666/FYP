"""Independent offline probes. Synthetic temporary stores only."""
from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
import sys
import pytest
ROOT=Path('/workspace/shared/fyp-agent-20261012/desk-companion')
sys.path.insert(0,str(ROOT/'backend'))
from desk.store import Store, DomainError
from desk.public_capture_schema import CAPTURE_DDL, CAPTURE_INDEX_DDL, validate_public_capture_schema

def create(root, version=3):
    s=Store(root,password='synthetic-only')
    if version < 3:
        with s.connection(write=True) as c:
            c.execute('DROP TABLE public_capture_operations')
            c.execute('DROP TABLE public_captures')
            c.execute(f'PRAGMA user_version={version}')
    return s

def row(c, **changes):
    data=dict(id='a'*32,state='review',version=1,intent_json='{}',intent_hash='b'*64,
        policy_version=1,session_hash='c'*64,privacy_revision='1:1',generation=0,
        created_at='2026-10-13T00:00:00Z',updated_at='2026-10-13T00:00:00Z',
        expires_at='2026-10-13T00:05:00Z',source_operation_key='audit-source',stage='review')
    data.update(changes)
    c.execute(f"INSERT INTO public_captures({','.join(data)}) VALUES({','.join('?' for _ in data)})",list(data.values()))

def cli(name='public_capture'):
    spec=importlib.util.spec_from_file_location('audit_cli_'+name,ROOT/f'scripts/migrate_{name}.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def invoke(module,root,name='public_capture'):
    return module.main(['--runtime',str(root),'--allow-'+name.replace('_','-')+'-migration'])

@pytest.mark.parametrize('change',[
    ('DEFAULT 0','DEFAULT 1'),('generation BETWEEN 0','generation BETWEEN -1'),
    ("'unknown'","'Unknown'"),('8192','8193'),("typeof(version)='integer'","typeof(version) IN('integer','real')"),
    ('version BETWEEN 1','version BETWEEN 0'),('source_operation_key TEXT NOT NULL UNIQUE','source_operation_key TEXT NOT NULL'),
    ('intent_hash TEXT NOT NULL','intent_hash BLOB NOT NULL'),('PRIMARY KEY NOT NULL','PRIMARY KEY'),
])
def test_exact_constraints_rejected(tmp_path,change):
    s=create(tmp_path)
    with s.connection(write=True) as c:
        c.execute('DROP TABLE public_capture_operations'); c.execute('DROP TABLE public_captures')
        assert change[0] in CAPTURE_DDL[0]
        c.execute(CAPTURE_DDL[0].replace(*change)); c.execute(CAPTURE_DDL[1])
        for sql in CAPTURE_INDEX_DDL:c.execute(sql)
    before=s.path.read_bytes()
    with pytest.raises(DomainError,match='SCHEMA_STRUCTURE_UNSUPPORTED'): Store(tmp_path)
    assert s.path.read_bytes()==before

@pytest.mark.parametrize('value',[0,1,None,'yes',[],{},1.0])
@pytest.mark.parametrize('flag',['allow_watch_retention_migration','allow_public_capture_migration'])
def test_bool_identity_not_truthiness(tmp_path,flag,value):
    with pytest.raises(DomainError,match='SCHEMA_MIGRATION_OPT_IN_REQUIRED'):
        Store(tmp_path/'missing',**{flag:value})
    assert not (tmp_path/'missing').exists()

@pytest.mark.parametrize('field,value',[
    ('source_id',b'bad'),('source_operation_key','a\x00b'),('intent_hash','b'*64+'\x00'),
    ('policy_version',2),('dispatch_possible',2),('cancel_requested',-1),('version',1.5),
])
def test_corrupt_scalar_refused(tmp_path,field,value):
    s=create(tmp_path)
    with s.connection(write=True) as c:
        c.execute('PRAGMA ignore_check_constraints=ON'); row(c,**{field:value})
    with pytest.raises(DomainError,match='SCHEMA_STRUCTURE_UNSUPPORTED'):Store(tmp_path)


def test_private_json_megabyte_never_projected_or_repaired(tmp_path):
    s=create(tmp_path)
    bad='invalid-private-json'*65536
    with s.connection(write=True) as c:
        c.execute('PRAGMA ignore_check_constraints=ON'); row(c,intent_json=bad,acquisition_json=bad)
    with closing(sqlite3.connect(s.path)) as c:
        observed=[]
        def rf(cursor, values):
            observed.extend(values); return values
        c.row_factory=rf
        validate_public_capture_schema(c)
        assert all(not isinstance(x,str) or len(x)<10000 for x in observed)
    assert Store(tmp_path).schema_version==3
    with s.connection() as c:
        assert c.execute('SELECT intent_json,acquisition_json FROM public_captures').fetchone()[:]==(bad,bad)


def test_capture_limit_201_fails_without_truncation(tmp_path):
    s=create(tmp_path)
    with s.connection(write=True) as c:
        for i in range(201):row(c,id=f'{i:032x}',source_operation_key=f'audit-{i}')
    with pytest.raises(DomainError,match='SCHEMA_STRUCTURE_UNSUPPORTED'):Store(tmp_path)


def test_open_reader_keeps_coherent_v2_snapshot(tmp_path):
    s=create(tmp_path,2)
    with closing(sqlite3.connect(s.path.as_uri()+'?mode=ro',uri=True,isolation_level=None)) as reader:
        reader.execute('BEGIN')
        assert reader.execute('PRAGMA user_version').fetchone()[0]==2
        assert not reader.execute("SELECT 1 FROM sqlite_master WHERE name='public_captures'").fetchall()
        Store(tmp_path,allow_public_capture_migration=True)
        assert reader.execute('PRAGMA user_version').fetchone()[0]==2
        assert not reader.execute("SELECT 1 FROM sqlite_master WHERE name='public_captures'").fetchall()
        reader.execute('COMMIT');reader.execute('BEGIN')
        assert reader.execute('PRAGMA user_version').fetchone()[0]==3
        validate_public_capture_schema(reader)

@pytest.mark.parametrize('version',[-1,0,4,999,2147483647])
def test_unsupported_versions_unchanged(tmp_path,version):
    s=create(tmp_path)
    with s.connection(write=True) as c:c.execute(f'PRAGMA user_version={version}')
    before=s.path.read_bytes()
    with pytest.raises(DomainError,match='SCHEMA_VERSION_UNSUPPORTED'):Store(tmp_path,allow_public_capture_migration=True)
    assert s.path.read_bytes()==before

@pytest.mark.parametrize('mode',[0o640,0o604,0o666])
@pytest.mark.parametrize('target',['database','directory'])
def test_cli_permission_boundaries(tmp_path,target,mode):
    root=tmp_path/'runtime'; s=create(root,2)
    (s.path if target=='database' else root).chmod(mode if target=='database' else mode|0o100)
    assert invoke(cli(),root)==1
    with sqlite3.connect(s.path) as c:assert c.execute('PRAGMA user_version').fetchone()[0]==2
    assert not (root/'credentials.json').exists()


def test_historical_v2_store_rejects_v3(tmp_path):
    s=create(tmp_path);before=s.path.read_bytes()
    spec=importlib.util.spec_from_file_location('desk.audit_schema2_store', '/workspace/shared/fyp-schema2-store-cc1751a.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    with pytest.raises(old.DomainError,match='SCHEMA_VERSION_UNSUPPORTED'):old.Store(tmp_path)
    assert s.path.read_bytes()==before

def legacy(root):
    s=create(root,2)
    with s.connection(write=True) as c:
        for name in ('responsibility_operations','responsibility_reviews','responsibility_sources','responsibilities'):
            c.execute('DROP TABLE '+name)
        c.execute('PRAGMA user_version=1')
    return s


def test_staged_clis_v1_to_v2_to_v3(tmp_path):
    s=legacy(tmp_path)
    assert invoke(cli(),tmp_path)==1
    assert invoke(cli('watch_retention'),tmp_path,'watch_retention')==0
    with s.connection() as c:
        assert c.execute('PRAGMA user_version').fetchone()[0]==2
        assert not c.execute("SELECT 1 FROM sqlite_master WHERE name='public_captures'").fetchone()
    assert invoke(cli('watch_retention'),tmp_path,'watch_retention')==0
    assert invoke(cli(),tmp_path)==0
    assert invoke(cli('watch_retention'),tmp_path,'watch_retention')==1
    assert not (tmp_path/'credentials.json').exists()


def test_runtime_cannot_adopt_watch_only_handle(tmp_path):
    from desk.runtime import Runtime
    legacy(tmp_path)
    s=Store(tmp_path,allow_watch_retention_migration=True)
    assert s.schema_version==2
    with pytest.raises(DomainError,match='SCHEMA_MIGRATION_REQUIRED'):Runtime(s)
    with s.connection() as c:
        assert not c.execute("SELECT 1 FROM sqlite_master WHERE name='private_files'").fetchone()

@pytest.mark.parametrize('marker',['CREATE TABLE public_captures','CREATE TABLE public_capture_operations','CREATE INDEX public_captures_created','CREATE INDEX public_capture_operations_capture','PRAGMA user_version=3'])
def test_abrupt_process_exit_rolls_back(tmp_path,marker):
    import subprocess
    s=create(tmp_path,2)
    with s.connection() as c:before='\n'.join(c.iterdump())
    program='''
import os, sys
from contextlib import contextmanager
from desk.store import Store
original=Store.connection
class Crash:
    def __init__(self,c):self.c=c
    def execute(self,sql,*a):
        result=self.c.execute(sql,*a)
        if sql.startswith(sys.argv[2]):os._exit(71)
        return result
    def __getattr__(self,name):return getattr(self.c,name)
@contextmanager
def connection(self,write=False):
    with original(self,write=write) as c:yield Crash(c) if write else c
Store.connection=connection
Store(sys.argv[1],allow_public_capture_migration=True)
'''
    result=subprocess.run([sys.executable,'-c',f"import sys;sys.path.insert(0,{str(ROOT/'backend')!r});\n"+program,str(tmp_path),marker],capture_output=True,timeout=15)
    assert result.returncode==71,result.stderr
    with s.connection() as c:
        assert c.execute('PRAGMA user_version').fetchone()[0]==2
        assert '\n'.join(c.iterdump())==before
    assert Store(tmp_path,allow_public_capture_migration=True).schema_version==3

@pytest.mark.parametrize('name',['public_capture','watch_retention'])
@pytest.mark.parametrize('change',['symlink','hardlink','replacement','directory_replacement','database_mode','directory_mode'])
def test_post_preflight_path_swap_refused_before_mutation(tmp_path,monkeypatch,name,change):
    root=tmp_path/'approved';other=tmp_path/'other'
    init=create if name=='public_capture' else legacy
    s=init(root,2) if name=='public_capture' else init(root)
    outsider=init(other,2) if name=='public_capture' else init(other)
    start_version=2 if name=='public_capture' else 1
    module=cli(name);original=module._existing_private_database
    def mutate(path):
        result=original(path)
        if change in ('symlink','hardlink','replacement'):
            s.path.rename(root/'original.sqlite3')
            if change=='symlink':s.path.symlink_to(outsider.path)
            elif change=='hardlink':s.path.hardlink_to(outsider.path)
            else:outsider.path.rename(s.path)
        elif change=='directory_replacement':
            root.rename(tmp_path/'original-directory');other.rename(root)
        elif change=='database_mode':s.path.chmod(0o644)
        else:root.chmod(0o755)
        return result
    monkeypatch.setattr(module,'_existing_private_database',mutate)
    assert invoke(module,root,name)==1
    for db in tmp_path.rglob('*.sqlite3'):
        if db.is_symlink():continue
        with closing(sqlite3.connect(db)) as c:
            assert c.execute('PRAGMA user_version').fetchone()[0]==start_version
    assert not list(tmp_path.rglob('credentials.json'))

@pytest.mark.parametrize('name,version',[('public_capture',3),('watch_retention',2)])
def test_readonly_current_schema_revalidates_same_inode_damage(tmp_path,monkeypatch,name,version):
    s=create(tmp_path,version);module=cli(name);original=module._existing_private_database
    def mutate(path):
        result=original(path)
        with s.connection(write=True) as c:c.execute('DELETE FROM owner')
        return result
    monkeypatch.setattr(module,'_existing_private_database',mutate)
    assert invoke(module,tmp_path,name)==1
    with s.connection() as c:assert c.execute('SELECT count(*) FROM owner').fetchone()[0]==0
    assert not (tmp_path/'credentials.json').exists()

@pytest.mark.parametrize('name',['public_capture','watch_retention'])
def test_accepted_private_mode_not_changed_after_commit(tmp_path,name):
    s=create(tmp_path,2) if name=='public_capture' else legacy(tmp_path)
    s.path.chmod(0o700)
    assert invoke(cli(name),tmp_path,name)==0
    assert s.path.stat().st_mode&0o777==0o700
    with s.connection() as c:
        assert c.execute('PRAGMA user_version').fetchone()[0]==(3 if name=='public_capture' else 2)
