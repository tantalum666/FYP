import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "../../../desk-companion/frontend/node_modules/react/index.js";
import { renderToStaticMarkup } from "../../../desk-companion/frontend/node_modules/react-dom/server.node.js";
register(new URL("../../../desk-companion/frontend/tests/fixtures/render-tsx-loader.mjs", import.meta.url));
const { RetentionConfirmation, WatchUsage } =
  await import("../../../desk-companion/frontend/src/workspace/responsibilities/WatchRetention.tsx");
const { watchError } =
  await import("../../../desk-companion/frontend/src/workspace/responsibilities/labels.ts");
const usage = {
  version: 1,
  retained_count: 20,
  trashed_count: 4,
  lifetime_count: 256,
  lifetime_limit: 256,
  lifetime_remaining: 0,
  state: "known",
};
const preview = {
  kind: "watch_retention_preview",
  preview_id: "preview-one",
  action: "purge",
  responsibility: {
    id: "opaque-watch-one",
    title: "<script>Synthetic history</script>",
    status: "cancelled",
    version: 3,
    retention_version: 2,
    retention_state: "trashed",
  },
  counts: {
    definitions: 1,
    source_baselines: 2,
    retained_reviews: 9,
    operation_receipts: 8,
  },
  retained_operation_receipts_after: 9,
  logical_slots_released: 1,
  receipts_retained: true,
  independent_tasks_retained: true,
  independent_work_retained: true,
  expires_at: "2026-10-13T12:05:00Z",
  maintenance_usage: usage,
  revision: 9,
};
function nodes(v:any):any[]{if(!v||typeof v!=='object')return [];if(Array.isArray(v))return v.flatMap(nodes);return [v,...nodes(v.props?.children)];}
test('AUDIT actual confirmation callbacks strict true only for purge; no action during render',()=>{for(const action of ['trash','restore','purge']){const got:any[]=[];let cancels=0;const tree=RetentionConfirmation({preview:{...preview,action},t:(s:string)=>s,disabled:false,onConfirm:(value:any)=>got.push(value),onCancel:()=>cancels++});assert.equal(got.length,0);const buttons=nodes(tree).filter(n=>n.type==='button');assert.equal(buttons.length,2);buttons[1].props.onClick();assert.equal(cancels,1);assert.equal(got.length,0);buttons[0].props.onClick();assert.deepEqual(got,[action==='purge']);}});
test('AUDIT bilingual unknown invalid aggregates never become apparent free capacity',()=>{for(const zh of [false,true])for(const bad of [NaN,Infinity,-1,21,'0',null]){const html=renderToStaticMarkup(createElement(WatchUsage,{usage:{...usage,retained_count:bad},limit:20,t:(a:string,b:string)=>zh?b:a}));assert.match(html,zh?/用量未知/:/Unknown usage/);assert.doesNotMatch(html,/20 slots remaining|20 剩余位置|0\/20/);}});
test('AUDIT bilingual long untrusted title and ID remain escaped as text and content includes narrow-safe wrappers',()=>{for(const zh of [false,true]){const target='<img src=x onerror=alert(1)>'+('中a'.repeat(65));const html=renderToStaticMarkup(createElement(RetentionConfirmation,{preview:{...preview,responsibility:{...preview.responsibility,title:target,id:target}},t:(a:string,b:string)=>zh?b:a,disabled:false,onConfirm(){throw Error('auto');},onCancel(){}}));assert.doesNotMatch(html,/<img /);assert.match(html,/&lt;img /);assert.match(html,/watch-retention-confirm irreversible/);assert.match(html,zh?/预览到期/:/Preview expires/);}});
