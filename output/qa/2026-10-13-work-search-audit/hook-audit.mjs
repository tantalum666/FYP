// Independent deterministic hook execution, not a mounted-browser acceptance claim.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const root=process.cwd();
const req=createRequire(root+'/desk-companion/frontend/package.json');
const ts=req('typescript');
const base=root+'/desk-companion/frontend/src/';
function load(path, deps={}) {
 const js=ts.transpileModule(fs.readFileSync(base+path,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;
 const out={}; new Function('exports','require',js)(out,n=>{if(n in deps)return deps[n]; throw Error(n)});return out;
}
const {ResponseFence}=load('workspace/personal/responseFence.ts');
const types=load('workspace/agent/workSearch.ts');
class ApiError extends Error {constructor(code,status=0){super(code);this.code=code;this.status=status}}
function world(){
 let slots=[],index=0,pendingEffects=[],fresh=true;
 let parent=new ResponseFence();parent.update('owner:A',true);
 let listeners=new Map(),calls=[];
 globalThis.window={addEventListener(n,f){listeners.set(n,f)},removeEventListener(n){listeners.delete(n)}};
 const hooks={useRef(v){const i=index++;return slots[i]??=( {current:v})},useState(v){const i=index++;if(!(i in slots))slots[i]=v;return [slots[i],v=>{slots[i]=typeof v==='function'?v(slots[i]):v}]},useEffect(fn,deps){const i=index++;const old=slots[i];if(!old||deps.some((v,j)=>v!==old.deps[j])){slots[i]={deps};pendingEffects.push(()=>{old?.cleanup?.();slots[i].cleanup=fn()})}}};
 const {useWorkSearch}=load('workspace/agent/useWorkSearch.ts',{'react':hooks,'../../api':{ApiError,request:(path,opts)=>new Promise((resolve,reject)=>calls.push({path,opts,resolve,reject}))},'../personal/responseFence':{ResponseFence},'./workSearch':types});
 function render(effects=true){index=0;let state=useWorkSearch(parent,parent.version,fresh);if(effects) pendingEffects.splice(0).forEach(f=>f());return state}
 return {render,calls,parent, listeners,setFresh:v=>fresh=v,tick:async()=>{await new Promise(r=>setImmediate(r));return render()}};
}
const id=n=>n.toString(16).padStart(32,'0');
const hit=n=>({id:id(n),kind:'source',title:'duplicate.txt',timestamp:null,matched_fields:['title'],match_reason:'phrase',format:'text',byte_count:8,recorded_status:'verified',revision:1});
const page=(items=[hit(1)])=>({items,total:items.length,snapshot:'a'.repeat(64),next_offset:null,search_scope:'local_metadata',ranking:'lexical_v1',file_status_basis:'last_recorded'});
const detail=n=>({id:id(n),name:'duplicate.txt',format:'text',byte_count:8,sha256:'b'.repeat(64),status:'verified',revision:1});
let count=0;
for(const transition of ['owner','hidden','stale','session','offline']){
 const w=world();let s=w.render();s.setQuery('private');s=w.render();s.submit();w.calls.shift().resolve(page([hit(1),hit(2)]));s=await w.tick();
 assert.equal(s.detail,null);assert.equal(w.calls.length,0);
 const opening=s.open(hit(2));const request=w.calls.shift();assert.equal(request.path,'/sources/'+id(2));
 if(transition==='owner')w.parent.update('owner:B',true);
 if(transition==='hidden')w.parent.update('owner:A',false);
 if(transition==='stale')w.setFresh(false);
 if(['session','offline'].includes(transition))w.listeners.get(transition==='session'?'desk:session':'offline')();
 s=w.render(false);assert.equal(s.value,null,transition);assert.equal(s.query,'',transition);assert.equal(s.detail,null,transition);
 request.resolve(detail(2));assert.equal(await opening,null,transition);count++;
}
{
 const w=world();let s=w.render();s.submit();const old=w.calls.shift();s.setQuery('second');s=w.render();s.submit();const recent=w.calls.shift();recent.resolve(page([hit(2)]));s=await w.tick();old.resolve(page([hit(1)]));s=await w.tick();assert.equal(s.value.page.items[0].id,id(2));
 const opening=s.open(hit(2));const pending=w.calls.shift();s.clear();pending.resolve(detail(2));assert.equal(await opening,null);assert.equal((await w.tick()).detail,null);count++;
}
console.log(JSON.stringify({status:'passed',independent_hook_scenarios:count,browser_evidence:false},null,2));
