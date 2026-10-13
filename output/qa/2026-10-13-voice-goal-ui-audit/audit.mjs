// Independent production-code execution with deterministic hooks and fake transports.
// Not browser, microphone, provider or DOM evidence.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const root=process.cwd(), qa=root+'/output/qa/2026-10-13-voice-goal-ui-audit';
const req=createRequire(root+'/desk-companion/frontend/package.json'), ts=req('typescript');
const base=root+'/desk-companion/frontend/src/';
const jsx=(type,props)=>({type,props});
function load(path,deps={},extra=''){
 const source=fs.readFileSync(base+path,'utf8')+extra;
 const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 const out={};new Function('exports','require',js)(out,n=>n==='react/jsx-runtime'?{jsx,jsxs:jsx,Fragment:'Fragment'}:deps[n]??{});return out;
}
const vt=load('workspace/voiceWork/types.ts'), at=load('workspace/agent/types.ts');
const {ResponseFence}=load('workspace/personal/responseFence.ts');
const {PrivateWriteQueue}=load('workspace/personal/privateWrite.ts');
const nodes=x=>!x||typeof x!=='object'?[]:Array.isArray(x)?x.flatMap(nodes):[x,...nodes(x.props?.children)];
const text=x=>typeof x==='string'?x:!x||typeof x!=='object'?'':Array.isArray(x)?x.map(text).join(''):text(x.props?.children);
const button=(tree,label)=>nodes(tree).find(x=>x.type==='button'&&text(x)===label);
class Hooks{
 slots=[];i=0;effects=[];
 react={useState:(v)=>{const n=this.i++;this.slots[n]??={value:typeof v==='function'?v():v};return[this.slots[n].value,v=>this.slots[n].value=typeof v==='function'?v(this.slots[n].value):v]},useRef:v=>{const n=this.i++;return this.slots[n]??={current:v}},useEffect:(fn,deps)=>{const n=this.i++,old=this.slots[n];if(old&&old.deps?.length===deps?.length&&deps?.every((v,i)=>Object.is(v,old.deps[i])))return;this.slots[n]={deps};this.effects.push(()=>{old?.cleanup?.();this.slots[n].cleanup=fn()})}};
 render(fn,effects=true){this.i=0;const out=fn();if(effects)this.flush();return out}
 flush(){this.effects.splice(0).forEach(f=>f())}
 close(){this.slots.forEach(x=>x?.cleanup?.())}
}
const tick=()=>new Promise(r=>setImmediate(r));
class ApiError extends Error{constructor(code,status=0){super(code);this.code=code;this.status=status}}
const input=(patch={})=>({type:'voice_input',role:'user',operation:'replace',voice_session_ref:'session-one',input_segment_id:'input-one',sequence:1,revision:1,text:'Synthetic speech marker',eligible:true,reason:null,provider:'gemini',model:'protocol-fake',destination_id:'synthetic-destination',boundary:'unfinalized',observed_at:new Date().toISOString(),...patch});
const receipt=i=>({voice_origin_ref:'opaque-ref',text:i.text,revision:i.revision,boundary:i.boundary,provider:i.provider,model:i.model,destination_id:i.destination_id,observed_at:i.observed_at,owner_reviewed_at:new Date().toISOString(),expires_at:new Date(Date.now()+300000).toISOString(),snapshot_kind:'owner_snapshot'});
function voiceWorld(){
 const h=new Hooks(),pending=[],handoffs=[],fence=new ResponseFence();fence.update('owner:A',true);
 const module=load('workspace/voiceWork/VoiceWorkPanel.tsx',{react:h.react,'../../api':{ApiError,request:(path,opts)=>new Promise((resolve,reject)=>pending.push({path,opts,resolve,reject}))},'../../components/Dialogs':{Modal:'Modal'},'../agent/labels':{agentError:e=>e.code??String(e)},'./types':vt});
 let i=input(),props={state:vt.reduceVoiceInputs(vt.emptyVoiceInputs(),i),owner:true,fence,t:en=>en,onHandoff:g=>{handoffs.push(g);return true}};
 const render=(effects=true)=>h.render(()=>module.VoiceWorkPanel(props),effects);
 const select=()=>nodes(render()).find(x=>x.type?.name==='VoiceInputList').props.onSelect(i);
 return {h,render,select,pending,handoffs,fence,get input(){return i},patch(p){props={...props,...p}},setInput(next){i=next;props={...props,state:vt.reduceVoiceInputs(props.state,next)}},module};
}
const results=[];
async function check(name,fn){try{await fn();results.push({name,status:'pass'})}catch(e){results.push({name,status:'FAIL',error:e.stack})}}
await check('server-normalized reducer cannot derive authority from display/tool/finality events',()=>{
 let state=vt.emptyVoiceInputs();for(const i of [{type:'transcript',role:'assistant',text:'start work'},{type:'turn_complete'},{...input(),role:'assistant'},{...input(),operation:'append'}])assert.equal(vt.reduceVoiceInputs(state,i),state);
 state=vt.reduceVoiceInputs(state,input());const immutable=state.inputs[0];const next=vt.reduceVoiceInputs(state,input({revision:2,sequence:2,text:'new fragment'}));assert.equal(immutable.text,'Synthetic speech marker');assert.equal(next.inputs[0].boundary,'unfinalized');
});
await check('codepoint-valid voice input is also a valid work handoff',()=>{const i=input({text:'😀'.repeat(2001)});assert.equal(vt.validVoiceGoal(i.text),true);assert.equal(at.validWorkGoal({id:'draft',text:i.text,voiceOrigin:vt.voiceGoalOrigin(receipt(i))}),true)});
await check('expired voice goal is rejected before queued Work navigation',()=>{const r=receipt(input());r.expires_at=new Date(Date.now()-1).toISOString();assert.equal(at.validWorkGoal({id:'draft',text:r.text,voiceOrigin:vt.voiceGoalOrigin(r)}),false)});
await check('owner selection is explicit, deduped, immutable, and handoff carries no transcript duplicate',async()=>{
 const w=voiceWorld();try{w.render();assert.equal(w.pending.length,0);w.select();w.select();assert.equal(w.pending.length,1);assert.equal(w.handoffs.length,0);const req=w.pending.shift();assert.deepEqual(JSON.parse(req.opts.body),{voice_session_ref:'session-one',input_segment_id:'input-one',expected_revision:1});req.resolve(receipt(w.input));await tick();let tree=w.render();nodes(tree).find(n=>n.type==='textarea').props.onChange({target:{value:'Edited selected goal'}});w.setInput(input({revision:2,sequence:2,text:'Later user speech'}));tree=w.render();assert.equal(nodes(tree).find(n=>n.type==='textarea').props.value,'Edited selected goal');const end=button(tree,'End voice and review work');end.props.onClick();end.props.onClick();assert.equal(w.handoffs.length,1);assert.equal(w.handoffs[0].text,'Edited selected goal');assert.equal('text' in w.handoffs[0].voiceOrigin,false)}finally{w.h.close()}
});
await check('freeze failure keeps speech alive and retries exact selected revision',async()=>{
 const w=voiceWorld();try{w.select();const first=w.pending.shift();first.reject(new ApiError('CONNECTION_LOST'));await tick();let tree=w.render();assert.equal(w.handoffs.length,0);button(tree,'Retry the same snapshot').props.onClick();assert.deepEqual(w.pending[0].opts,first.opts);w.pending.shift().resolve(receipt(w.input));await tick();tree=w.render();button(tree,'Dismiss and keep talking').props.onClick();assert.equal(w.handoffs.length,0)}finally{w.h.close()}
});
for(const change of ['owner','hidden','session','provider','offline'])await check('late freeze fenced before effects: '+change,async()=>{
 const w=voiceWorld();try{w.select();const old=w.pending.shift();w.fence.update(change==='hidden'||change==='offline'?'owner:A':'owner:'+change,!['hidden','offline'].includes(change));if(change==='owner')w.patch({owner:false});w.render(false);old.resolve(receipt(w.input));await tick();const tree=w.render(false);assert.equal(nodes(tree).filter(x=>x.type==='textarea').length,0);assert.equal(w.handoffs.length,0)}finally{w.h.close()}
});
await check('non-owner selection callback never sends a freeze',()=>{const w=voiceWorld();try{w.patch({owner:false});w.select();assert.equal(w.pending.length,0)}finally{w.h.close()}});
await check('unknown run create retains exact serialized goal, origin and operation ID after expiry',async()=>{
 let n=0,calls=[];const q=new PrivateWriteQueue(async o=>{calls.push({...o});if(n++===0)throw new ApiError('CONNECTION_LOST');return {run:{id:'same-run'}}},()=> 'operation-one');const body={goal:'Reviewed goal',voice_origin_ref:'ephemeral-ref',retain:true};await assert.rejects(q.send('/agent-runs',body));body.goal='new unreviewed text';assert.equal(q.pending,true);const r=await q.retry();assert.equal(r.run.id,'same-run');assert.deepEqual(calls[0],calls[1]);assert.equal(q.pending,false);
});

function workspaceWorld(){
 const h=new Hooks(),fence=new ResponseFence();fence.update('owner',true);
 let guard={dirty:false,busy:false},handled=0,refreshes=0,props={t:en=>en,fence,epoch:fence.version,initialGoal:null,onGoalHandled:()=>{handled++}},state={fresh:true,loading:false,error:null,value:{runs:[],scope:{scope_revision:'s',modes:['deterministic'],sources:[],tasks:[],events:[],destinations:[],limits:{}}},reload:async()=>{refreshes++}};
 const module=load('workspace/agent/RunPanel.tsx',{react:h.react,'../../components/Dialogs':{Modal:'Modal'},'../../components/DraftGuard':{useDraftState:()=>guard},'./types':at,'./useAgentRuns':{useAgentRuns:()=>state},'./labels':{agentError:e=>String(e),modeLabel:x=>x,stateLabel:x=>x},'./RunComposer':{RunComposer:'RunComposer'},'./RunDetail':{RunDetail:'RunDetail'},'./WorkSearchPanel':{WorkSearchPanel:'WorkSearchPanel'}},'\nexport { RunWorkspace };');
 return{h,fence,render:(effects=true)=>h.render(()=>module.RunWorkspace(props),effects),guard:v=>guard=v,props:v=>props={...props,...v},state:v=>state={...state,...v},handled:()=>handled,refreshes:()=>refreshes};
}
await check('dirty Work draft survives queued voice handoff until explicit discard and carries exact origin',()=>{
 const w=workspaceWorld();try{w.render();button(w.render(),'Start persistent work').props.onClick();let tree=w.render();assert.ok(nodes(tree).some(n=>n.type==='RunComposer'));w.guard({dirty:true,busy:false});const r=receipt(input()),goal={id:r.voice_origin_ref,text:'Edited voice goal',voiceOrigin:vt.voiceGoalOrigin(r)};w.props({initialGoal:goal});w.render();tree=w.render();assert.equal(nodes(tree).find(n=>n.type==='RunComposer').props.initialGoal,undefined);button(tree,'Use the goal from chat').props.onClick();tree=w.render();assert.ok(button(tree,'Keep editing'));assert.equal(nodes(tree).find(n=>n.type==='RunComposer').props.initialGoal,undefined);button(tree,'Discard and continue').props.onClick();tree=w.render();const composer=nodes(tree).find(n=>n.type==='RunComposer');assert.equal(composer.props.initialGoal,goal.text);assert.deepEqual(composer.props.voiceOrigin,goal.voiceOrigin);assert.equal(w.handled(),1)}finally{w.h.close()}
});
await check('expired queued goal cannot discard unrelated Work draft via an old navigation confirmation',()=>{
 const w=workspaceWorld();const oldNow=Date.now;try{w.render();button(w.render(),'Start persistent work').props.onClick();w.render();w.guard({dirty:true,busy:false});const r=receipt(input()),goal={id:r.voice_origin_ref,text:'Voice draft',voiceOrigin:vt.voiceGoalOrigin(r)};w.props({initialGoal:goal});w.render();let tree=w.render();button(tree,'Use the goal from chat').props.onClick();tree=w.render();Date.now=()=>Date.parse(r.expires_at)+1;button(tree,'Discard and continue').props.onClick();tree=w.render();assert.equal(nodes(tree).find(n=>n.type==='RunComposer').props.initialGoal,undefined);assert.match(text(tree),/expired/i)}finally{Date.now=oldNow;w.h.close()}
});
await check('transient refresh failure keeps composer goal and origin mounted but disables handoff',()=>{
 const w=workspaceWorld();try{const r=receipt(input()),goal={id:r.voice_origin_ref,text:r.text,voiceOrigin:vt.voiceGoalOrigin(r)};w.props({initialGoal:goal});w.render();let tree=w.render();assert.equal(nodes(tree).find(n=>n.type==='RunComposer').props.initialGoal,goal.text);w.state({fresh:false,error:{code:'CONNECTION_LOST'}});tree=w.render();const composer=nodes(tree).find(n=>n.type==='RunComposer');assert.equal(composer.props.initialGoal,goal.text);assert.equal(composer.props.fresh,false);assert.equal(button(tree,'Start persistent work').props.disabled,true);w.state({fresh:true,error:null});tree=w.render();assert.equal(nodes(tree).find(n=>n.type==='RunComposer').props.fresh,true)}finally{w.h.close()}
});
await check('search navigation retains dirty guard without prematurely replacing composer',()=>{
 const w=workspaceWorld();try{w.render();button(w.render(),'Start persistent work').props.onClick();w.render();w.guard({dirty:true,busy:false});button(w.render(),'Find saved work').props.onClick();let tree=w.render();assert.ok(button(tree,'Keep editing'));assert.ok(nodes(tree).some(n=>n.type==='RunComposer'));assert.equal(nodes(tree).some(n=>n.type==='WorkSearchPanel'),false);button(tree,'Keep editing').props.onClick();tree=w.render();assert.ok(nodes(tree).some(n=>n.type==='RunComposer'))}finally{w.h.close()}
});
function composerWorld(voice=true){
 const h=new Hooks(),fence=new ResponseFence();fence.update('owner',true);let calls=[];
 const mutation={busy:false,pending:false,error:null,run:async(...args)=>{calls.push(args)},retry:async()=>true};
 const module=load('workspace/agent/RunComposer.tsx',{react:h.react,'../../components/Dialogs':{Modal:'Modal'},'../../components/DraftGuard':{useDraftGuard:()=>{}},'../personal/usePrivateMutation':{usePrivateMutation:()=>mutation},'./types':at,'./labels':{modeLabel:x=>x},'../voiceWork/VoiceWorkPanel':{VoiceOriginLabel:'VoiceOriginLabel'}});
 const r=receipt(input());let props={t:en=>en,scope:{scope_revision:'s'.repeat(64),modes:['deterministic','model'],sources:[{id:'source',name:'Synthetic.csv',format:'csv',sha256:'a'.repeat(64),byte_count:12,revision:1,status:'verified'}],tasks:[],events:[],destinations:[],limits:{},business_context_allowed:false},fence,fresh:true,initialGoal:'Reviewed goal',...(voice?{voiceOrigin:vt.voiceGoalOrigin(r)}:{}),onClose:()=>{},onRefresh:()=>{},onCreated:()=>{}};
 return {h,r,fence,mutation,calls,render:(effects=true)=>h.render(()=>module.RunComposer(props),effects),props:p=>props={...props,...p}};
}
await check('voice composer deterministic with every consent/evidence clear; typed handoff retains model default',()=>{
 for(const voice of [true,false]){const w=composerWorld(voice);try{const tree=w.render();const selects=nodes(tree).filter(n=>n.type==='select');assert.equal(selects[0].props.value,voice?'deterministic':'model');for(const n of nodes(tree).filter(n=>n.type==='input'&&n.props.type==='checkbox'))assert.equal(n.props.checked,false);assert.equal(w.calls.length,0)}finally{w.h.close()}}
});
await check('composer cannot create after origin expiry and does not silently drop provenance',async()=>{
 const w=composerWorld(),oldNow=Date.now;try{w.render();let tree=w.render();let checks=nodes(tree).filter(n=>n.type==='input'&&n.props.type==='checkbox');checks[0].props.onChange({target:{checked:true}});tree=w.render();checks=nodes(tree).filter(n=>n.type==='input'&&n.props.type==='checkbox');checks.at(-1).props.onChange({target:{checked:true}});tree=w.render();const form=nodes(tree).find(n=>n.type==='form');form.props.onSubmit({preventDefault(){}});tree=w.render();const start=button(tree,'Start this persistent work');assert.ok(start);Date.now=()=>Date.parse(w.r.expires_at)+1;await start.props.onClick();assert.equal(w.calls.length,0)}finally{Date.now=oldNow;w.h.close()}
});


await check('saved composer Start callback cannot dispatch reviewed private goal after owner epoch changes',async()=>{
 const w=composerWorld();try{w.render();let tree=w.render();let checks=nodes(tree).filter(n=>n.type==='input'&&n.props.type==='checkbox');checks[0].props.onChange({target:{checked:true}});tree=w.render();checks=nodes(tree).filter(n=>n.type==='input'&&n.props.type==='checkbox');checks.at(-1).props.onChange({target:{checked:true}});tree=w.render();nodes(tree).find(n=>n.type==='form').props.onSubmit({preventDefault(){}});tree=w.render();const start=button(tree,'Start this persistent work');w.fence.update('owner:B',true);await start.props.onClick();assert.equal(w.calls.length,0)}finally{w.h.close()}
});


await check('saved input selection callback cannot dispatch freeze after owner epoch changes',()=>{
 const w=voiceWorld();try{const tree=w.render(),select=nodes(tree).find(n=>n.type?.name==='VoiceInputList').props.onSelect;w.fence.update('owner:B',true);select(w.input);assert.equal(w.pending.length,0)}finally{w.h.close()}
});


function assistantWorld(){
 const h=new Hooks();h.react.useCallback=(fn,deps)=>{const n=h.i++,old=h.slots[n];if(old&&old.deps.length===deps.length&&deps.every((v,i)=>v===old.deps[i]))return old.fn;h.slots[n]={deps,fn};return fn};
 const old={};let timer=0;const listeners=new Map();for(const[k,v]of Object.entries({window:{addEventListener:(n,f)=>listeners.set(n,f),removeEventListener:n=>listeners.delete(n),dispatchEvent:()=>{}},setInterval:()=>++timer,clearInterval:()=>{},setTimeout:()=>++timer,clearTimeout:()=>{}})){old[k]=Object.getOwnPropertyDescriptor(globalThis,k);Object.defineProperty(globalThis,k,{value:v,configurable:true})}
 let workspace={data:{principal:{kind:'owner',id:'owner-one'},personal_context_visible:true,voice:{configured:true,provider:'fake',model:'protocol-fake',config_revision:'provider-one'},text_ai:{configured:false}},offline:false,stale:false,refresh:async()=>{}},requests=[],engines=[];
 class Engine{stopped=false;closes=0;constructor(cb,current){this.cb=cb;this.current=current;engines.push(this)}async start(){this.started=true}close(){this.closes++;this.stopped=true}interrupt(){this.cb({type:'speech_muted'})}hearAgain(){this.cb({type:'speech_resumed'})}}
 const imports={react:h.react,'../api':{ApiError,errorText:e=>e.code,request:async(path,opts)=>{requests.push({path,opts});return{proposals:[]}}},'./WorkspaceContext':{useWorkspace:()=>workspace},'./audio':{VoiceAudio:Engine},'./voiceWork/VoiceWorkPanel':{VoiceWorkPanel:'VoiceWorkPanel'},'./voiceWork/types':vt,'../components/DraftGuard':{useDraftGuard:()=>{}},'../native':{apiOrigin:()=> 'https://synthetic.invalid'},'./personal/responseFence':{ResponseFence},'./personal/usePrivateMutation':{usePrivateMutation:()=>({busy:false,pending:false,clear(){}})},'./personal/usePersonalContext':{usePersonalContext:()=>({settings:null,memories:[],reload:async()=>{}})},'./personal/types':load('workspace/personal/types.ts'),'./agent/RunPanel':{RunPanel:'RunPanel'},'./personal/PersonalContextPanel':{PersonalContextPanel:'PersonalContextPanel',ModeLabel:'ModeLabel'}};
 const module=load('workspace/AssistantPanel.tsx',imports);const render=(effects=true)=>h.render(()=>module.AssistantPanel({t:en=>en}),effects);
 return{render,requests,engines,listeners,patch:p=>workspace={...workspace,...p},data:p=>workspace.data={...workspace.data,...p},close(){h.close();for(const[k,d]of Object.entries(old)){if(d)Object.defineProperty(globalThis,k,d);else delete globalThis[k]}}};
}
await check('Assistant raw/partial/assistant events never auto-freeze or handoff, explicit reviewed handoff ends only voice',async()=>{
 const w=assistantWorld();try{w.render();let tree=w.render();button(tree,'Start conversation').props.onClick();await tick();tree=w.render();const e=w.engines[0];assert.ok(e.started);for(const event of [{type:'ready'},{type:'transcript',role:'assistant',text:'Start work yes approved',final:true},{type:'turn_complete'},input()])e.cb(event);tree=w.render();assert.equal(w.requests.filter(x=>x.path!=='/assistant/proposals').length,0);assert.equal(nodes(tree).find(x=>x.type==='RunPanel').props.initialGoal,undefined);const panel=nodes(tree).find(x=>x.type==='VoiceWorkPanel');assert.equal(panel.props.owner,true);assert.equal(panel.props.state.inputs.length,1);const r=receipt(input());panel.props.onHandoff({id:r.voice_origin_ref,text:'Explicit edited goal',voiceOrigin:vt.voiceGoalOrigin(r)});tree=w.render();assert.equal(e.stopped,true);assert.equal(nodes(tree).find(x=>x.type==='RunPanel').props.initialGoal.text,'Explicit edited goal');assert.equal(w.requests.filter(x=>x.path!=='/assistant/proposals').length,0);e.cb(input({text:'Late old audio input',sequence:2,revision:2}));tree=w.render();assert.equal(nodes(tree).find(x=>x.type==='VoiceWorkPanel').props.state.inputs.length,0)}finally{w.close()}
});
for(const change of ['owner','hidden','offline','provider'])await check('Assistant '+change+' render fences engine and queued goal before effect cleanup',async()=>{
 const w=assistantWorld();try{w.render();let tree=w.render();const oldStart=button(tree,'Start conversation');oldStart.props.onClick();await tick();const e=w.engines[0];e.cb({type:'ready'});e.cb(input());tree=w.render();const onHandoff=nodes(tree).find(x=>x.type==='VoiceWorkPanel').props.onHandoff;if(change==='owner')w.data({principal:{kind:'owner',id:'owner-two'}});if(change==='hidden')w.data({personal_context_visible:false});if(change==='offline')w.patch({offline:true});if(change==='provider')w.data({voice:{configured:true,config_revision:'provider-two'}});tree=w.render(false);assert.equal(e.current(),false);e.cb(input({text:'Late text',revision:2,sequence:2}));onHandoff({id:'late',text:'Late old goal'});tree=w.render(false);assert.equal(nodes(tree).find(x=>x.type==='RunPanel').props.initialGoal,undefined);oldStart.props.onClick();assert.equal(w.engines.length,1)}finally{w.close()}
});
await check('Assistant same-turn double Start cannot open two microphone engines',async()=>{const w=assistantWorld();try{w.render();const start=button(w.render(),'Start conversation');start.props.onClick();start.props.onClick();await tick();assert.equal(w.engines.length,1)}finally{w.close()}});


for(const code of ['RUN_SESSION_EXPIRED','PRIVATE_CONTEXT_HIDDEN','VOICE_CONTEXT_CHANGED','OWNER_SIGN_IN_REQUIRED','AUTH_REQUIRED'])await check('freeze '+code+' invalidates immediately instead of preserving a private retry',async()=>{
 const w=voiceWorld();let invalidations=0;try{w.patch({onInvalidated:()=>{invalidations++;w.fence.update('invalid',false)}});w.select();w.pending.shift().reject(new ApiError(code,403));await tick();const tree=w.render();assert.equal(invalidations,1);assert.equal(button(tree,'Retry the same snapshot'),undefined);assert.equal(w.handoffs.length,0)}finally{w.h.close()}
});


await check('Assistant ready and audio remain active until an actual ended event',async()=>{
 const w=assistantWorld();try{w.render();button(w.render(),'Start conversation').props.onClick();await tick();const e=w.engines[0];for(const event of [{type:'ready'},{type:'audio',audio:'AAAAAA=='},{type:'transcript',role:'assistant',text:'Synthetic reply'},{type:'interrupted'},{type:'turn_complete'}]){e.cb(event);const tree=w.render();assert.ok(button(tree,'End conversation'),event.type);assert.equal(button(tree,'Start conversation'),undefined,event.type)}e.cb({type:'ended'});const tree=w.render();assert.ok(button(tree,'Start conversation'));assert.equal(button(tree,'End conversation'),undefined)}finally{w.close()}
});

fs.writeFileSync(qa+'/independent-results.json',JSON.stringify({category:'production reducer/component callback/hook and queue protocol-fake; not DOM/browser',results},null,2));
console.log(JSON.stringify(results,null,2));
if(results.some(r=>r.status==='FAIL'))process.exitCode=1;
