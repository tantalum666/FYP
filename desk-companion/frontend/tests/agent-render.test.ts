import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import { newRunDraft } from "../src/workspace/agent/types.ts";
import type { RunScope } from "../src/workspace/agent/types.ts";

// Render production TSX with the installed compiler and React server renderer.
// This exercises markup and translations; it is explicitly not a browser/click test.
register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { MetadataControls } =
  await import("../src/workspace/agent/RunMetadataPanel.tsx");
const { RunBrowserJobs } =
  await import("../src/workspace/agent/RunBrowserJobs.tsx");
const { RunContextSelection } =
  await import("../src/workspace/agent/RunContextSelection.tsx");
const { RunConnectorSelection } =
  await import("../src/workspace/agent/RunConnectorSelection.tsx");
const { RunConnectorResults } =
  await import("../src/workspace/agent/RunConnectorResults.tsx");
const { Modal } = await import("../src/components/Dialogs.tsx");
const { GuardContextProvider, useDraftState } =
  await import("../src/components/DraftGuard.tsx");
const fence = new ResponseFence();
fence.update("owner:fixture:metadata", true);
const row = {
  id: "run-fixture",
  state: "running",
  version: 2,
  created_at: "2026-10-13T05:00:00.000Z",
  updated_at: "2026-10-13T05:01:00.000Z",
  goal: "PRIVATE_GOAL",
  state_reason: "PRIVATE_REASON",
  source_ids: ["PRIVATE_SOURCE"],
  artifact_ids: ["PRIVATE_FILE"],
  proposal_ids: ["PRIVATE_REVIEW"],
};

test("actual metadata card markup has stop controls and no private fields in English or Chinese", () => {
  for (const zh of [false, true]) {
    const markup = renderToStaticMarkup(
      createElement(MetadataControls, {
        run: row,
        t: (en: string, cn: string) => (zh ? cn : en),
        fence,
        fresh: true,
        onChanged: () => {},
      }),
    );
    assert.doesNotMatch(
      markup,
      /PRIVATE_GOAL|PRIVATE_REASON|PRIVATE_SOURCE|PRIVATE_FILE|PRIVATE_REVIEW/,
    );
    assert.match(markup, /run-fixture/);
    assert.match(markup, zh ? /取消工作/ : /Cancel work/);
    assert.match(markup, zh ? /暂停/ : /Pause/);
    assert.doesNotMatch(markup, /disabled=""/);
  }
});

test("metadata markup disables stale controls and removes all actions for terminal or unknown status", () => {
  const props = { t: (en: string) => en, fence, onChanged: () => {} };
  const stale = renderToStaticMarkup(
    createElement(MetadataControls, { ...props, run: row, fresh: false }),
  );
  assert.equal((stale.match(/disabled=""/g) ?? []).length, 2);
  for (const state of ["succeeded", "cancelled", "unknown"]) {
    const terminal = renderToStaticMarkup(
      createElement(MetadataControls, {
        ...props,
        run: { ...row, state },
        fresh: true,
      }),
    );
    assert.doesNotMatch(terminal, /<button/);
  }
});

test("browser result markup separates verified bytes from uncertain cleanup and has no inline approval", () => {
  const job = {
    id: "browser-fixture",
    state: "unknown",
    version: 3,
    cleanup_confirmed: false,
    expires_at: "2026-10-13T06:00:00Z",
    created_at: row.created_at,
    cancel_requested: false,
    error: "BROWSER_CLEANUP_UNCONFIRMED",
    result: {
      verified: true,
      export_method: "stackedit_ui_markdown_download",
      byte_count: 123,
      sha256: "f".repeat(64),
      browser_close_confirmed: true,
      process_cleanup_confirmed: false,
    },
  };
  const markup = renderToStaticMarkup(
    createElement(RunBrowserJobs, {
      jobs: [job],
      t: (en: string) => en,
      locked: false,
      onReview: () => {},
    }),
  );
  assert.match(markup, /Export bytes independently read back/);
  assert.match(markup, /execution or cleanup remains uncertain/);
  assert.match(markup, /Open browser review and result/);
  assert.doesNotMatch(markup, /Approve this exact/);
});

const catalog: RunScope = {
  modes: ["deterministic", "model"],
  scope_revision: "f".repeat(64),
  sources: [],
  tasks: [],
  events: [],
  limits: {},
  business_context_allowed: false,
  destinations: [],
  personal_context: {
    revision: "f".repeat(64),
    memory_allowed: true,
    history_allowed: true,
    limits: { memories: 8, messages: 12 },
    memories: [
      {
        id: "memory-one",
        version: 1,
        category: "fact",
        summary: "A selected fact preview",
      },
    ],
    conversations: [
      {
        id: "thread-one",
        version: 1,
        title: "Saved thread",
        eligible_message_count: 5,
      },
    ],
  },
  connectors: {
    scope_revision: "c".repeat(64),
    tools: [
      {
        tool_id: "mcp.fixture.read",
        connector_id: "fixture",
        tool_name: "read",
        effect: "read",
        input_schema: {},
        descriptor_sha256: "d".repeat(64),
        grant_sha256: "e".repeat(64),
        endpoint: "https://fixture.example/mcp",
        destination_scope: "Synthetic only",
        data_policy: "public_or_synthetic",
        review_required: true,
        live_acceptance: "not_verified_here",
      },
    ],
  },
};

test("actual personal-context and connector selections do not precheck permissions in either language", () => {
  for (const zh of [false, true]) {
    const props = {
      draft: newRunDraft("An explicit chat goal"),
      scope: catalog,
      t: (en: string, cn: string) => (zh ? cn : en),
      onChange: () => {},
    };
    const context = renderToStaticMarkup(
      createElement(RunContextSelection, props),
    );
    const connectors = renderToStaticMarkup(
      createElement(RunConnectorSelection, props),
    );
    assert.doesNotMatch(context + connectors, /checked=""/);
    assert.match(
      context,
      zh ? /不会自动选择任何内容/ : /Nothing is selected automatically/,
    );
    assert.match(
      connectors,
      zh ? /每次调用（包括读取）/ : /Every call, including a read/,
    );
    assert.match(connectors, /https:\/\/fixture.example\/mcp/);
  }
});

test("actual markup blocks mixing private context and public-only connectors", () => {
  const props = { scope: catalog, t: (en: string) => en, onChange: () => {} };
  const context = renderToStaticMarkup(
    createElement(RunContextSelection, {
      ...props,
      draft: { ...newRunDraft(), connector_tool_ids: ["mcp.fixture.read"] },
    }),
  );
  assert.match(context, /Personal context cannot be combined/);
  assert.equal((context.match(/disabled=""/g) ?? []).length, 2);
  const connectors = renderToStaticMarkup(
    createElement(RunConnectorSelection, {
      ...props,
      draft: { ...newRunDraft(), source_ids: ["private-file"] },
    }),
  );
  assert.match(connectors, /Connector work cannot include local files/);
  assert.match(connectors, /disabled=""/);
});

test("connector result markup cannot imply independent verification or follow a remote review URL", () => {
  const result = {
    tool: "mcp.fixture.read",
    arguments: {},
    operation_key: "fixture-op",
    reference_id: "b".repeat(32),
    state: "observed" as const,
    result: {
      connector_intent_id: "b".repeat(32),
      review_url: "https://untrusted.invalid/approve",
      observation: { text: ["untrusted body"] },
    },
  };
  const props = { t: (en: string) => en, locked: false, onReview: () => {} };
  const markup = renderToStaticMarkup(
    createElement(RunConnectorResults, { ...props, results: [result] }),
  );
  assert.match(markup, /Remote response observed · not independently verified/);
  assert.match(markup, /Open exact connector review and result/);
  assert.doesNotMatch(
    markup,
    /untrusted.invalid|untrusted body|<a |Approve this/,
  );
  const invalid = renderToStaticMarkup(
    createElement(RunConnectorResults, {
      ...props,
      results: [
        {
          ...result,
          result: { ...result.result, connector_intent_id: "../other" },
        },
      ],
    }),
  );
  assert.equal(invalid, "");
});

test("Work modal owns a separate draft guard from the retained parent chat input", () => {
  function Probe() {
    const guard = useDraftState();
    return createElement(
      "span",
      null,
      `${guard.dirty ? "dirty" : "clean"}:${guard.busy ? "busy" : "idle"}`,
    );
  }
  const previous = Object.getOwnPropertyDescriptor(globalThis, "document");
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: { documentElement: { lang: "en" } },
  });
  try {
    const markup = renderToStaticMarkup(
      createElement(
        GuardContextProvider,
        { value: { dirty: true, busy: true, register: () => {} } },
        createElement(Modal, {
          title: "Work tasks",
          closeLabel: "Close",
          onClose: () => {},
          children: createElement(Probe),
        }),
      ),
    );
    assert.match(markup, /clean:idle/);
    assert.doesNotMatch(markup, /dirty:busy/);
  } finally {
    if (previous) Object.defineProperty(globalThis, "document", previous);
    else Reflect.deleteProperty(globalThis, "document");
  }
});
