import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "../../../desk-companion/frontend/node_modules/typescript/lib/typescript.js";
import { ResponseFence } from "../../../desk-companion/frontend/src/workspace/personal/responseFence.ts";
import * as retention from "../../../desk-companion/frontend/src/workspace/responsibilities/retention.ts";
class HookHarness {
  slots: any[] = [];
  index = 0;
  effects: (() => void)[] = [];
  react = {
    useState: (initial: any) => {
      const n = this.index++;
      this.slots[n] ??= {
        value: typeof initial === "function" ? initial() : initial,
      };
      return [
        this.slots[n].value,
        (next: any) => {
          this.slots[n].value =
            typeof next === "function" ? next(this.slots[n].value) : next;
        },
      ];
    },
    useRef: (value: any) => {
      const n = this.index++;
      this.slots[n] ??= { current: value };
      return this.slots[n];
    },
    useCallback: (callback: any, deps: any[]) => {
      const n = this.index++;
      if (!this.equal(this.slots[n]?.deps, deps))
        this.slots[n] = { deps, callback };
      return this.slots[n].callback;
    },
    useEffect: (effect: () => void | (() => void), deps: any[]) => {
      const n = this.index++;
      if (this.equal(this.slots[n]?.deps, deps)) return;
      const old = this.slots[n];
      this.slots[n] = { deps };
      this.effects.push(() => {
        old?.cleanup?.();
        this.slots[n].cleanup = effect();
      });
    },
  };
  equal(a: any[] | undefined, b: any[]) {
    return (
      !!a && a.length === b.length && a.every((v, i) => Object.is(v, b[i]))
    );
  }
  render<T>(body: () => T): T {
    this.index = 0;
    const result = body();
    this.effects.splice(0).forEach((effect) => effect());
    return result;
  }
  close() {
    this.slots.forEach((slot) => slot.cleanup?.());
  }
}

const usage = {version:1,retained_count:20,trashed_count:1,lifetime_count:30,lifetime_limit:256,lifetime_remaining:226,state:"known"};
const row = {id:"watch-one",title:"Synthetic history",version:3,retention_version:1,retention_state:"retained",status:"cancelled",hidden:false,task_ids:["task-one"],fields:["status"],review_budget:10,reviews_used:2};
function preview(action="purge", source:any=row) { return {kind:"watch_retention_preview",preview_id:"preview-one",action,responsibility:source,counts:{definitions:1,source_baselines:1,retained_reviews:2,operation_receipts:3},retained_operation_receipts_after:4,logical_slots_released:action === "purge" ? 1 : 0,receipts_retained:true,independent_tasks_retained:true,independent_work_retained:true,expires_at:new Date(Date.now()+300000).toISOString(),maintenance_usage:usage,revision:5}; }
const disposition = (key="operation-one") => ({kind:"retention_disposition",responsibility_id:"watch-one",retention_state:"purged",retention_version:2,original_operation_kind:"purge",review_id:null,operation_id:key,revision:6,recorded_success:true});
const listing = () => ({responsibilities:[{...row,retention_state:"trashed"}],maintenance_usage:usage,revision:5,server_time:new Date().toISOString()});
const detail = () => ({responsibility:{...row},reviews:[1,2].map(n=>({id:`review-${n}`,responsibility_id:row.id,version:1,changed_fields:["status"],changed_ids:["task-one"],delivery_state:"dismissed"})),selected_tasks:[{id:"task-one",title:"Synthetic task",available:true,version:1}],revision:5});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function setup() {
  const hooks=new HookHarness(), events=new EventTarget(), pending:any[]=[], calls:any[]=[], changed:any[]=[], denials:any[]=[];
  const previous=Object.getOwnPropertyDescriptor(globalThis,"window");
  Object.defineProperty(globalThis,"window",{configurable:true,value:Object.assign(events,{setTimeout,clearTimeout})});
  const exports:any={};
  const code=ts.transpileModule(readFileSync(new URL("../../../desk-companion/frontend/src/workspace/responsibilities/useWatchRetention.ts",import.meta.url),"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  new Function("require","exports",code)((name:string)=>{
    if(name==="react")return hooks.react;
    if(name==="../../api")return {request:(path:string,options:any={})=>{calls.push({path,options});return new Promise((resolve,reject)=>pending.push({path,options,resolve,reject}));}};
    if(name.endsWith("responseFence"))return {ResponseFence};
    if(name==="./retention")return retention;
    throw Error(name);
  },exports);
  const fence=new ResponseFence(); fence.update("owner",true); const epoch=fence.version;
  let fresh=true,snapshot=5;
  const render=()=>hooks.render(()=>exports.useWatchRetention(fence,epoch,fresh,snapshot,(v:any)=>changed.push(v),(e:any)=>denials.push(e)));
  const settle=async(value:any)=>{pending.shift().resolve(value);await tick();return render();};
  const ready=async()=>{render();return settle(listing());};
  const prepared=async(action="purge")=>{let state=await ready();state.inspect(row.id);state=await settle(detail());state.prepare(state.detail.responsibility,action);state=await settle(preview(action));return state;};
  return {render,ready,prepared,settle,pending,calls,changed,denials,fence,events,setFresh:(v:boolean)=>{fresh=v;},revision:()=>{snapshot++;},close:()=>{hooks.close();if(previous)Object.defineProperty(globalThis,"window",previous);else Reflect.deleteProperty(globalThis,"window");}};
}
test('AUDIT not-mounted: cancel before preview resolves suppresses its late success and final captured callback',async()=>{const h=setup();try{let s=await h.ready();s.inspect(row.id);s=await h.settle(detail());s.prepare(s.detail.responsibility,'purge');const finalize=s.confirm;s.cancel();s=await h.settle(preview());assert.equal(s.preview,null);finalize(preview(),true);assert.equal(h.calls.filter(c=>c.path.endsWith('/retention')).length,0);}finally{h.close();}});
test('AUDIT not-mounted: old preparation success cannot replace a newer action preview',async()=>{const h=setup();try{let s=await h.ready();s.inspect(row.id);s=await h.settle(detail());s.prepare(s.detail.responsibility,'trash');const old=h.pending.shift();s.prepare(s.detail.responsibility,'purge');s=await h.settle(preview());assert.equal(s.preview.action,'purge');old.resolve(preview('trash'));await tick();s=h.render();assert.equal(s.preview.action,'purge');}finally{h.close();}});
test('AUDIT not-mounted: exact action and terminal states fail closed without mutation',async()=>{for(const status of ['active','paused','blocked']){const h=setup();try{let s=await h.ready();s.inspect(row.id);s=await h.settle({...detail(),responsibility:{...row,status}});assert.equal(s.detail,null);assert.equal(h.calls.filter(c=>c.path.endsWith('/retention')).length,0);}finally{h.close();}}});
test('AUDIT not-mounted: captured retry and delayed successful result are fenced synchronously by personal change',async()=>{const h=setup();try{let s=await h.prepared();s.confirm(s.preview,true);const op=h.pending.shift();op.reject({status:503});await tick();s=h.render();assert.equal(s.pending,true);const retry=s.retry;s.retry();const inflight=h.pending.shift();h.events.dispatchEvent(new Event('desk:personal-context'));retry();inflight.resolve(disposition(inflight.options.headers['X-Operation-Id']));await tick();s=h.render();assert.equal(s.list,null);assert.equal(s.result,null);assert.equal(s.pending,false);assert.equal(h.changed.length,0);assert.equal(h.calls.filter(c=>c.path.endsWith('/retention')).length,2);}finally{h.close();}});
test('AUDIT not-mounted: queue cannot mint fresh key after malformed success, and no auto retry',async()=>{const h=setup();try{let s=await h.prepared();s.confirm(s.preview,true);const orig=h.pending.shift();orig.resolve({...disposition(orig.options.headers['X-Operation-Id']),responsibility_id:'wrong'});await tick();s=h.render();assert.equal(s.pending,true);const count=h.calls.length;s.confirm(preview(),true);s.prepare(row,'purge');await tick();assert.equal(h.calls.length,count);s.retry();const next=h.pending.shift();assert.deepEqual(next.options,orig.options);next.resolve(disposition(next.options.headers['X-Operation-Id']));await tick();assert.equal(h.changed.length,1);}finally{h.close();}});
test('AUDIT not-mounted: past expiry and non-boolean consent cannot call retention',async()=>{const h=setup();try{let s=await h.prepared();for(const flag of [1,'true',{},null])s.confirm(s.preview,flag);assert.equal(h.pending.length,0);s.preview.expires_at='2000-01-01T00:00:00Z';s.confirm(s.preview,true);assert.equal(h.pending.length,0);}finally{h.close();}});
test('AUDIT not-mounted: successful old read after denial does not restore access',async()=>{const h=setup();try{let s=await h.ready();s.refresh();const denied=h.pending.shift();s.refresh();const success=h.pending.shift();denied.reject({status:401});await tick();success.resolve(listing());await tick();s=h.render();assert.equal(s.available,false);assert.equal(s.list,null);s.refresh();assert.equal(h.pending.length,0);}finally{h.close();}});
test('AUDIT not-mounted: monotonic deadline blocks purge despite wall clock rollback',async()=>{const h=setup();const clock=Date.now,desc=Object.getOwnPropertyDescriptor(globalThis,'performance');try{let s=await h.prepared();const wall=Date.now(),mono=performance.now();Date.now=()=>wall-600000;Object.defineProperty(globalThis,'performance',{configurable:true,value:{now:()=>mono+300001}});s.confirm(s.preview,true);assert.equal(h.pending.length,0);}finally{Date.now=clock;if(desc)Object.defineProperty(globalThis,'performance',desc);h.close();}});
