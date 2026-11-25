import assert from "node:assert/strict";
import test from "node:test";
import { canActOnFinding, cueTarget, findingMatchesNotice, findingSource, noticeTarget } from "../src/workspace/findingNavigation.ts";

test("an Inbox receipt opens its bound item; reading it has no dismissal or write action", () => {
  for (const [kind,page] of Object.entries({morning_brief:"today",evening_check:"tasks",memory_morning:"memory",memory_followup:"memory",mail_followup:"tasks",
      calendar_deadline:"calendar",calendar_conflict:"calendar",calendar_decision:"calendar",calendar_cancelled:"calendar"})) {
    const result=noticeTarget({id:"receipt",kind}); assert.equal(result?.page,page); assert.equal(result?.itemId,undefined);
  }
  assert.equal(noticeTarget({id:"notice",kind:"initiative"})?.itemId,"notice");
  assert.equal(noticeTarget({id:"receipt",kind:"followup",task_id:"original"})?.itemId,"original");
  assert.equal(noticeTarget({id:"receipt",kind:"followup"})?.page,"tasks");
  assert.equal(noticeTarget({id:"receipt",kind:"other"}),undefined);
});

test("a Home cue opens the intended destination without applying a task or notice action", () => {
  assert.equal(cueTarget({id:"n",kind:"initiative"})?.page,"assistant");
  assert.equal(cueTarget({id:"n",kind:"morning_brief"})?.page,"today");
  assert.equal(cueTarget({id:"n",kind:"evening_check"})?.page,"tasks");
  assert.equal(cueTarget({id:"n",kind:"task",task_id:"selected-task"})?.itemId,"selected-task");
  assert.equal(cueTarget({id:"n",kind:"task"}),undefined);
  assert.equal(cueTarget({id:"n",kind:"posture"}),undefined);
});

test("source navigation preserves the cited task, memory or local occurrence", () => {
  assert.deepEqual(findingSource({kind:"task",ref:"task:bound"}),{page:"tasks",itemId:"bound"});
  assert.deepEqual(findingSource({kind:"memory",ref:"memory:one"}),{page:"memory",itemId:"one"});
  assert.deepEqual(findingSource({kind:"calendar",ref:"calendar:one:2026-11-25T18:00"}),{page:"calendar",itemId:"calendar:one:2026-11-25T18:00"});
  for(const [kind, ref] of [["calendar","calendar:google:external"],["calendar","calendar:incomplete"],["task","memory:t"],["memory","memory:"],["mail","mail:gmail:m"]])
    assert.equal(findingSource({kind,ref}),undefined);
});

test("only the matching receipt expands a finding and historical or withdrawn rows cannot act", () => {
  assert.ok(findingMatchesNotice({id:"old"},"insight-old"));
  assert.ok(findingMatchesNotice({id:"one",notice_id:"batch"},"batch"));
  assert.equal(findingMatchesNotice({id:"one",notice_id:"batch"},"insight-one"),false);
  assert.equal(findingMatchesNotice({id:"two"},"batch"),false);
  assert.equal(canActOnFinding({historical:true}),false);
  assert.equal(canActOnFinding({withdrawn:true}),false);
  assert.ok(canActOnFinding({}));
});
