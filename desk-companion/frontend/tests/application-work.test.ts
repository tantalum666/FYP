import test from 'node:test';
import assert from 'node:assert/strict';
import { newRunDraft, prepareRun, exactTaskHandoffReady } from '../src/workspace/agent/types.ts';
import type { RunScope } from '../src/workspace/agent/types.ts';
const scope: RunScope = {
  scope_revision: 'a'.repeat(64), modes: ['deterministic', 'model'], sources: [], events: [],
  tasks: [{ id: 'task-1', title: 'Test work', version: 1 }], limits: {}, business_context_allowed: true,
  destinations: [{ id: 'provider', kind: 'text', provider: 'fixture', endpoint: 'https://example.test' }],
  applications: { enabled: true, configured: true, scope: 'applications:test', permission_mode: 'ask',
    sources: [{ source_id: 'quote.html', sha256: 'b'.repeat(64), bytes: 123, kind: 'browser' }] },
};
const draft = () => ({ ...newRunDraft('Compare and prepare files'), task_ids: ['task-1'], mode: 'model' as const,
  destination: 'provider', share: true, retain: true, allow_application_jobs: true, application_source_ids: ['quote.html'] });
test('application work requires explicit opt-in, a selected task and admitted input files', () => {
  assert.equal(prepareRun(draft(), scope)?.allow_application_jobs, true);
  assert.equal(prepareRun({ ...draft(), allow_application_jobs: false }, scope), null);
  assert.equal(prepareRun({ ...draft(), task_ids: [] }, scope), null);
  assert.equal(prepareRun({ ...draft(), application_source_ids: ['private.txt'] }, scope), null);
  assert.equal(prepareRun({ ...draft(), application_source_ids: ['quote.html', 'quote.html'] }, scope), null);
  assert.equal(prepareRun({ ...draft(), share: false }, scope), null);
});
test('disconnected executor, fixed mode, over-budget and stale selections do not start application work', () => {
  assert.equal(prepareRun(draft(), { ...scope, applications: undefined }), null);
  assert.equal(prepareRun({ ...draft(), mode: 'deterministic' }, scope), null);
  assert.equal(prepareRun({ ...draft(), application_job_budget: 9 }, scope), null);
  assert.equal(prepareRun({ ...draft(), application_job_budget: NaN }, scope), null);
  assert.equal(prepareRun(draft(), { ...scope, applications: { ...scope.applications!, sources: [] } }), null);
  assert.equal(prepareRun(draft(), { ...scope, business_context_allowed: false }), null);
});
test('ordinary work remains opt-in and exact-task handoffs cannot inherit application execution', () => {
  const local = { ...newRunDraft('Compile selected task'), task_ids: ['task-1'], retain: true };
  assert.equal(prepareRun(local, scope)?.allow_application_jobs, undefined);
  assert.equal(exactTaskHandoffReady(['task-1'], local, scope), true);
  assert.equal(exactTaskHandoffReady(['task-1'], { ...local, allow_application_jobs: true }, scope), false);
});
