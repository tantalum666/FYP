import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const req=createRequire(process.cwd()+'/desk-companion/frontend/package.json'),ts=req('typescript');
const base='desk-companion/frontend/src/workspace/agent/';
function extract(file,name){
 const raw=fs.readFileSync(base+file,'utf8'),ast=ts.createSourceFile(file,raw,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);let found;
 function visit(n){if(ts.isFunctionDeclaration(n)&&n.name?.text===name)found=n;ts.forEachChild(n,visit)} visit(ast);assert.ok(found,name);
 return ts.transpileModule(found.getText(ast),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;
}
function inject(code,name,scope){return new Function(...Object.keys(scope),code+'\nreturn '+name)(...Object.values(scope))}
const settle=()=>new Promise(r=>setImmediate(r));
let resolves=[],locks=[],allowed=true,token={current:0};
const noop=()=>{};
const commit=inject(extract('RunPanel.tsx','commit'),'commit',{
 fresh:true,setNavigate:noop,setDetailGeneration:noop,onReviewProposal:noop,onReviewBrowserJob:noop,onReviewConnectorIntent:noop,
 detailRefreshToken:token,showSearch:true,selected:'run-a',setDetailRefreshing:v=>locks.push(v),reload:()=>new Promise(r=>resolves.push(r)),fence:{accepts:()=>allowed},epoch:1,setShowSearch:noop,setComposeGoal:noop,setSelected:noop,setCompose:noop,
});
commit({id:'run-a',compose:false});commit({id:'run-a',compose:false});
assert.deepEqual(locks,[true,true]);resolves.shift()();await settle();assert.deepEqual(locks,[true,true]);resolves.shift()();await settle();assert.deepEqual(locks,[true,true,false]);
commit({id:'run-a',compose:false});allowed=false;resolves.shift()();await settle();assert.equal(locks.at(-1),true);
let searchEpoch=1,handoffs=[],resolve;
const search={fence:{capture:()=>searchEpoch,accepts:v=>v===searchEpoch},open:()=>new Promise(r=>resolve=r)};
const open=inject(extract('WorkSearchPanel.tsx','open'),'open',{search,fence:{accepts:()=>true},epoch:1,onOpenRun:id=>handoffs.push(id)});
let pending=open({kind:'run',id:'one'});resolve({kind:'run',value:{run:{id:'one'}}});searchEpoch++;await pending;assert.deepEqual(handoffs,[]);
pending=open({kind:'run',id:'two'});resolve({kind:'run',value:{run:{id:'two'}}});await pending;assert.deepEqual(handoffs,['two']);
console.log(JSON.stringify({status:'passed',actual_source_functions:['RunWorkspace.commit','WorkSearchPanel.open'],scenarios:['superseded refresh cannot unlock','parent privacy cannot unlock','search invalidation cannot hand off','current exact run may hand off']},null,2));
