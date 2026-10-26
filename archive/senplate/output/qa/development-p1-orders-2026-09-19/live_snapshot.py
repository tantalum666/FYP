from pathlib import Path
import json, sys, httpx
root=Path(__file__).resolve().parents[3]
creds=json.loads((root/'.runtime/credentials.json').read_text())
account=next(x for x in creds['accounts'] if x['role']=='manager')
with httpx.Client(base_url='http://127.0.0.1:8799',trust_env=False) as client:
    token=client.post('/v1/auth/sessions',json={'username':account['username'],'password':account['password']}).json()['access_token']
    client.headers.update({'Authorization':'Bearer '+token,'X-Context-ID':creds['workspace_id']})
    base='/v1/workspaces/'+creds['workspace_id']
    station=client.get(base+'/overview').json()['station']
    orders=client.get(base+'/orders').json()['items']
    menu=client.get(base+'/menu').json()
    result={'checkpoint':sys.argv[1], 'station':{k:station[k] for k in ['session_id','net_g','reserved_g','available_to_promise_g','incoming_g','service_type']},'orders':[{k:o[k] for k in ['id','number','state','version','reserved_g','expected_g','actual_g','total_minor','history']} for o in orders], 'menu':[{k:i[k] for k in ['slug','manual_stock','reserved_portions','available_portions','price_minor','version','quote_version']} for i in menu['items']]}
    target=Path(__file__).with_name('cross-client-checkpoints.json')
    prior=json.loads(target.read_text()) if target.exists() else []
    prior.append(result);target.write_text(json.dumps(prior,indent=2))
    print(json.dumps(result,indent=2))
