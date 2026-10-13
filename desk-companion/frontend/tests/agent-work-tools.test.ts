import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import {
  budgetLimit,
  newRunDraft,
  prepareRun,
  runActions,
  validWorkGoal,
} from "../src/workspace/agent/types.ts";
import type { RunDraft, RunScope } from "../src/workspace/agent/types.ts";
import {
  browserExportVerified,
  browserVerified,
} from "../src/workspace/browser/types.ts";
import type { BrowserJob } from "../src/workspace/browser/types.ts";

const scope: RunScope = {
  scope_revision: "a".repeat(64),
  modes: ["deterministic", "model"],
  sources: [],
  tasks: [],
  events: [],
  business_context_allowed: false,
  limits: { model_call_budget_max: 24, tool_call_budget_max: 16 },
  destinations: [
    {
      id: "text-approved",
      kind: "text",
      provider: "Fixture only",
      endpoint: "https://provider.example/v1",
    },
  ],
  browser: {
    configured: true,
    ready: true,
    reason: null,
    experimental: true,
    scope: "public_synthetic_only",
    network_boundary: "request_filter_not_hard_network_sandbox",
    live_acceptance: "not_verified_here",
    destination: {
      id: "stackedit_markdown_v1",
      url: "https://stackedit.io/app",
    },
    sources: [
      {
        id: "python_asyncio",
        label: "Asyncio",
        url: "https://docs.python.org/3/library/asyncio.html",
      },
      {
        id: "python_pathlib",
        label: "Pathlib",
        url: "https://docs.python.org/3/library/pathlib.html",
      },
    ],
    limits: {},
  },
};
const draft = (extra: Partial<RunDraft> = {}): RunDraft => ({
  ...newRunDraft("Compare the selected official sources"),
  mode: "model",
  retain: true,
  destination: "text-approved",
  share: true,
  browser_source_ids: ["python_asyncio"],
  browser_public_only: true,
  ...extra,
});

test("chat goal prefill preserves exact user text but inherits no retention, data-sharing or tool permission", () => {
  const text = "  Compare these notes\n保留此草稿";
  const value = newRunDraft(text);
  assert.equal(value.goal, text);
  assert.equal(value.retain, false);
  assert.equal(value.share, false);
  assert.equal(value.destination, "");
  assert.equal(value.browser_public_only, false);
  assert.deepEqual(value.browser_source_ids, []);
  assert.equal(value.allow_mutation_proposals, false);
  assert.equal(prepareRun(value, scope), null);
  assert.equal(validWorkGoal({ id: "click-one", text }), true);
  assert.equal(validWorkGoal({ id: "", text }), false);
  assert.equal(validWorkGoal({ id: "click-one", text: "   " }), false);
  assert.equal(
    validWorkGoal({ id: "click-one", text: "x".repeat(4001) }),
    false,
  );
});

test("public-browser-only model work needs explicit source grant and independent provider consent", () => {
  const value = prepareRun(draft(), scope);
  assert.deepEqual(value?.browser_source_ids, ["python_asyncio"]);
  assert.equal(value?.browser_public_only, true);
  assert.equal(prepareRun(draft({ browser_public_only: false }), scope), null);
  assert.equal(prepareRun(draft({ share: false }), scope), null);
  assert.equal(prepareRun(draft({ destination: "unapproved" }), scope), null);
  assert.equal(prepareRun(draft({ mode: "deterministic" }), scope), null);
  assert.equal(prepareRun(draft({ browser_source_ids: [] }), scope), null);
});

test("browser selection cannot invent sources, duplicate grants or bypass unavailable admission", () => {
  assert.equal(
    prepareRun(
      draft({ browser_source_ids: ["https://private.invalid"] }),
      scope,
    ),
    null,
  );
  assert.equal(
    prepareRun(
      draft({ browser_source_ids: ["python_asyncio", "python_asyncio"] }),
      scope,
    ),
    null,
  );
  assert.equal(prepareRun(draft(), { ...scope, browser: undefined }), null);
  for (const extra of [
    { configured: false },
    { ready: false },
    {
      destination: { id: "stackedit_markdown_v1", url: "https://evil.invalid" },
    },
  ]) {
    assert.equal(
      prepareRun(draft(), {
        ...scope,
        browser: { ...scope.browser!, ...extra },
      }),
      null,
    );
  }
});

test("browser selection counts toward model evidence total and snapshots grants at exact review", () => {
  const local = {
    ...scope,
    sources: Array.from({ length: 10 }, (_, n) => ({
      id: `source-${n}`,
      name: "Fixture",
      format: "text" as const,
      sha256: "f".repeat(64),
      byte_count: 1,
      revision: 1,
      status: "verified" as const,
    })),
  };
  const form = draft({
    source_ids: local.sources.slice(0, 9).map((source) => source.id),
  });
  const review = prepareRun(form, local)!;
  assert.ok(review);
  assert.equal(
    prepareRun(
      { ...form, source_ids: local.sources.map((source) => source.id) },
      local,
    ),
    null,
  );
  form.browser_source_ids.push("python_pathlib");
  assert.deepEqual(review.browser_source_ids, ["python_asyncio"]);
  assert.equal(review.browser_public_only, true);
});

test("model and tool attempt budgets enforce exact integral bounds and lower operator ceilings", () => {
  assert.equal(prepareRun(draft(), scope)?.model_call_budget, 8);
  assert.equal(
    prepareRun(draft({ model_call_budget: 24, tool_call_budget: 16 }), scope)
      ?.tool_call_budget,
    16,
  );
  for (const n of [0, -1, 1.5, NaN, Infinity, 25])
    assert.equal(prepareRun(draft({ model_call_budget: n }), scope), null);
  for (const n of [0, -1, 1.5, NaN, Infinity, 17])
    assert.equal(prepareRun(draft({ tool_call_budget: n }), scope), null);
  const lower = {
    ...scope,
    limits: { model_call_budget_max: 4, tool_call_budget_max: 3 },
  };
  assert.equal(prepareRun(draft(), lower), null);
  assert.ok(
    prepareRun(draft({ model_call_budget: 4, tool_call_budget: 3 }), lower),
  );
  assert.equal(
    budgetLimit({ ...scope, limits: { model_call_budget_max: 100 } }, "model"),
    24,
  );
});

test("verified export bytes are distinct from browser completion with unresolved cleanup", () => {
  const job = {
    state: "unknown",
    cleanup_confirmed: false,
    result: {
      verified: true,
      export_method: "stackedit_ui_markdown_download",
      byte_count: 321,
      sha256: "f".repeat(64),
      browser_close_confirmed: true,
      process_cleanup_confirmed: false,
    },
  } as BrowserJob;
  assert.equal(browserExportVerified(job), true);
  assert.equal(browserVerified(job), false);
  assert.equal(
    browserVerified({
      ...job,
      state: "succeeded",
      cleanup_confirmed: true,
      result: { ...job.result!, process_cleanup_confirmed: true },
    }),
    true,
  );
});

test("goal handoffs preserve active drafts and linked browser review delegates without approving inside run detail", () => {
  const file = (name: string) =>
    readFileSync(
      new URL(`../src/workspace/agent/${name}`, import.meta.url),
      "utf8",
    );
  const panel = file("RunPanel.tsx"),
    composer = file("RunComposer.tsx"),
    jobs = file("RunBrowserJobs.tsx");
  assert.match(panel, /initialGoal!.id === lastGoal.current/);
  assert.match(panel, /if \(guard.busy \|\| guard.dirty\) setPendingGoal/);
  assert.match(panel, /initialGoal=\{composeGoal\?\.text\}/);
  assert.match(panel, /voiceOrigin=\{composeGoal\?\.voiceOrigin\}/);
  assert.match(composer, /newRunDraft\(initialGoal\)/);
  assert.match(jobs, /onReview\?\.\(job.id\)/);
  assert.doesNotMatch(jobs, /\/approve|usePrivateMutation|request\(/);
  assert.match(
    file("RunBrowserSelection.tsx"),
    /browser_public_only: false,\s+share: false,\s+retain: false/,
  );
});

const expanded: RunScope = {
  ...scope,
  sources: [
    {
      id: "file-1",
      name: "Private notes",
      format: "text",
      sha256: "f".repeat(64),
      byte_count: 4,
      revision: 1,
      status: "verified",
    },
  ],
  tasks: [{ id: "task-1", title: "Private task", version: 1 }],
  events: [{ id: "event-1", title: "Private event", version: 1 }],
  connectors: {
    scope_revision: "c".repeat(64),
    tools: Array.from({ length: 9 }, (_, i) => ({
      tool_id: `mcp.fixture.read_${i}`,
      connector_id: "fixture",
      tool_name: `read_${i}`,
      effect: "read" as const,
      input_schema: { type: "object" },
      descriptor_sha256: "d".repeat(64),
      grant_sha256: "e".repeat(64),
      endpoint: "https://fixture.example/mcp",
      destination_scope: "Fictional workspace only",
      data_policy: "public_or_synthetic" as const,
      review_required: true as const,
      live_acceptance: "not_verified_here" as const,
    })),
  },
  personal_context: {
    revision: "b".repeat(64),
    memory_allowed: true,
    history_allowed: true,
    limits: { memories: 8, messages: 12 },
    memories: Array.from({ length: 9 }, (_, i) => ({
      id: `memory-${i}`,
      version: 1,
      category: "preference",
      summary: `Fact preview ${i}`,
    })),
    conversations: [
      {
        id: "thread-1",
        version: 1,
        title: "Chosen thread",
        eligible_message_count: 5,
      },
      {
        id: "empty-thread",
        version: 2,
        title: "No eligible history",
        eligible_message_count: 0,
      },
    ],
  },
};

test("selected personal context requires explicit derived-retention acknowledgment and current category permission", () => {
  const selected = draft({
    personal_context: {
      memory_ids: ["memory-0"],
      conversation_id: "thread-1",
      retain_derived_context: true,
    },
  });
  assert.deepEqual(
    prepareRun(selected, expanded)?.personal_context,
    selected.personal_context,
  );
  assert.equal(
    prepareRun(
      {
        ...selected,
        personal_context: {
          ...selected.personal_context,
          retain_derived_context: false,
        },
      },
      expanded,
    ),
    null,
  );
  assert.equal(
    prepareRun(selected, {
      ...expanded,
      personal_context: {
        ...expanded.personal_context!,
        memory_allowed: false,
      },
    }),
    null,
  );
  assert.equal(
    prepareRun(selected, {
      ...expanded,
      personal_context: {
        ...expanded.personal_context!,
        history_allowed: false,
      },
    }),
    null,
  );
  assert.equal(
    prepareRun(selected, { ...expanded, personal_context: undefined }),
    null,
  );
});

test("personal selection rejects unlisted/duplicate facts and conversations with no eligible messages", () => {
  for (const memory_ids of [
    ["missing"],
    ["memory-0", "memory-0"],
    expanded.personal_context!.memories.map((memory) => memory.id),
  ]) {
    assert.equal(
      prepareRun(
        draft({
          personal_context: {
            memory_ids,
            conversation_id: null,
            retain_derived_context: true,
          },
        }),
        expanded,
      ),
      null,
    );
  }
  for (const conversation_id of ["missing", "empty-thread"])
    assert.equal(
      prepareRun(
        draft({
          personal_context: {
            memory_ids: [],
            conversation_id,
            retain_derived_context: true,
          },
        }),
        expanded,
      ),
      null,
    );
});

test("personal context is never counted as evidence or silently added to local work", () => {
  const personal_context = {
    memory_ids: ["memory-0"],
    conversation_id: null,
    retain_derived_context: true,
  };
  assert.equal(
    prepareRun(draft({ browser_source_ids: [], personal_context }), expanded),
    null,
  );
  assert.equal(
    prepareRun(
      draft({
        mode: "deterministic",
        source_ids: ["file-1"],
        browser_source_ids: [],
        personal_context,
      }),
      expanded,
    ),
    null,
  );
  assert.equal(prepareRun(draft(), expanded)?.personal_context, null);
  const form = draft({ personal_context });
  const review = prepareRun(form, expanded)!;
  personal_context.memory_ids.push("memory-1");
  assert.deepEqual(review.personal_context?.memory_ids, ["memory-0"]);
});

test("connector-only work requires two separate exact-provider sharing choices and no automatic call approval", () => {
  const connector = draft({
    browser_source_ids: [],
    browser_public_only: false,
    connector_tool_ids: ["mcp.fixture.read_0"],
    share_connector_results_with_provider: true,
  });
  const input = prepareRun(connector, expanded)!;
  assert.ok(input);
  assert.equal(input.share_connector_results_with_provider, true);
  assert.deepEqual(input.mutation_requests, []);
  assert.equal(
    prepareRun(
      { ...connector, share_connector_results_with_provider: false },
      expanded,
    ),
    null,
  );
  assert.equal(prepareRun({ ...connector, share: false }, expanded), null);
  assert.equal(
    prepareRun({ ...connector, destination: "other-provider" }, expanded),
    null,
  );
  assert.equal(
    prepareRun({ ...connector, mode: "deterministic" }, expanded),
    null,
  );
});

test("public-only connector grants cannot combine private evidence or saved context but can include public browser sources", () => {
  const connector = draft({
    connector_tool_ids: ["mcp.fixture.read_0"],
    share_connector_results_with_provider: true,
  });
  assert.ok(prepareRun(connector, expanded));
  for (const extra of [
    { source_ids: ["file-1"] },
    { task_ids: ["task-1"] },
    { event_ids: ["event-1"] },
    {
      personal_context: {
        memory_ids: ["memory-0"],
        conversation_id: null,
        retain_derived_context: true,
      },
    },
    {
      personal_context: {
        memory_ids: [],
        conversation_id: "thread-1",
        retain_derived_context: true,
      },
    },
  ]) {
    assert.equal(
      prepareRun(
        { ...connector, ...extra },
        { ...expanded, business_context_allowed: true },
      ),
      null,
    );
  }
});

test("connector selection fails closed for unknown, duplicate, excessive and unreviewed tool grants", () => {
  const connector = draft({ share_connector_results_with_provider: true });
  for (const connector_tool_ids of [
    ["mcp.unknown.tool"],
    ["mcp.fixture.read_0", "mcp.fixture.read_0"],
    expanded.connectors!.tools.map((tool) => tool.tool_id),
  ]) {
    assert.equal(
      prepareRun({ ...connector, connector_tool_ids }, expanded),
      null,
    );
  }
  assert.equal(
    prepareRun(
      { ...connector, connector_tool_ids: ["mcp.fixture.read_0"] },
      { ...expanded, connectors: undefined },
    ),
    null,
  );
  assert.equal(
    prepareRun(
      { ...connector, connector_tool_ids: ["mcp.fixture.read_0"] },
      {
        ...expanded,
        connectors: {
          ...expanded.connectors!,
          tools: expanded.connectors!.tools.map((tool) => ({
            ...tool,
            review_required: false as unknown as true,
          })),
        },
      },
    ),
    null,
  );
  const form = { ...connector, connector_tool_ids: ["mcp.fixture.read_0"] };
  const input = prepareRun(form, expanded)!;
  form.connector_tool_ids.push("mcp.fixture.read_1");
  assert.deepEqual(input.connector_tool_ids, ["mcp.fixture.read_0"]);
});

test("invalidated personal-context bindings cannot be refreshed by resume, steering or provider retry", () => {
  for (const reason of [
    "RUN_PERSONAL_CONTEXT_CHANGED",
    "RUN_PERSONAL_CONTEXT_BINDING_CHANGED",
    "RUN_PERSONAL_CONTEXT_BINDING_INVALID",
    "RUN_PERSONAL_CONTEXT_UNAVAILABLE",
    "RUN_PERSONAL_CONTEXT_NOT_APPROVED",
    "RUN_PERSONAL_CONTEXT_LIMIT",
    "RUN_CONNECTOR_SCOPE_CHANGED",
  ]) {
    assert.deepEqual(runActions("blocked", reason), ["cancel"]);
    assert.deepEqual(runActions("failed", reason), []);
    assert.deepEqual(runActions("cancelled", reason), []);
  }
});
