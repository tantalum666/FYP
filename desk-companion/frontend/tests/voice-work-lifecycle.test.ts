import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import * as voiceTypes from "../src/workspace/voiceWork/types.ts";
import * as agentTypes from "../src/workspace/agent/types.ts";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";

// Production component callbacks and hook state in a deterministic protocol-fake
// harness. This is not a DOM, browser layout, microphone or paid-provider test.
class Hooks {
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
    useEffect: (effect: any, deps: any[]) => {
      const n = this.index++;
      const old = this.slots[n];
      if (
        old &&
        old.deps.length === deps.length &&
        old.deps.every((v: any, i: number) => Object.is(v, deps[i]))
      )
        return;
      this.slots[n] = { deps };
      this.effects.push(() => {
        old?.cleanup?.();
        this.slots[n].cleanup = effect();
      });
    },
  };
  render(fn: () => any) {
    this.index = 0;
    const result = fn();
    this.effects.splice(0).forEach((effect) => effect());
    return result;
  }
  close() {
    this.slots.forEach((slot) => slot.cleanup?.());
  }
}
const jsx = (type: any, props: any) => ({ type, props });
const nodes = (tree: any): any[] =>
  !tree || typeof tree !== "object"
    ? []
    : Array.isArray(tree)
      ? tree.flatMap(nodes)
      : [tree, ...nodes(tree.props?.children)];
const text = (tree: any): string =>
  typeof tree === "string"
    ? tree
    : !tree || typeof tree !== "object"
      ? ""
      : Array.isArray(tree)
        ? tree.map(text).join("")
        : text(tree.props?.children);
function load(file: string, imports: Record<string, any>) {
  const source = readFileSync(
    new URL(`../src/workspace/${file}`, import.meta.url),
    "utf8",
  );
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  const exports: any = {};
  new Function("require", "exports", compiled)((name: string) => {
    if (name === "react/jsx-runtime")
      return { jsx, jsxs: jsx, Fragment: "Fragment" };
    return imports[name] ?? {};
  }, exports);
  return exports;
}
function setup() {
  const hooks = new Hooks(),
    pending: any[] = [],
    handoffs: any[] = [];
  const fence = new ResponseFence();
  fence.update("owner", true);
  class ApiError extends Error {
    code: string;
    constructor(code: string) {
      super(code);
      this.code = code;
    }
  }
  const module = load("voiceWork/VoiceWorkPanel.tsx", {
    react: hooks.react,
    "../../api": {
      ApiError,
      request: (path: string, options: any) =>
        new Promise((resolve, reject) =>
          pending.push({ path, options, resolve, reject }),
        ),
    },
    "../../components/Dialogs": { Modal: "Modal" },
    "../agent/labels": {
      agentError: (error: any) => error.code ?? error.message,
    },
    "./types": voiceTypes,
  });
  const input = {
    type: "voice_input",
    role: "user",
    operation: "replace",
    voice_session_ref: "session",
    input_segment_id: "input",
    sequence: 1,
    revision: 1,
    text: "Original synthetic speech",
    eligible: true,
    reason: null,
    provider: "gemini",
    model: "protocol-fake",
    destination_id: "destination",
    boundary: "unfinalized",
    observed_at: new Date().toISOString(),
  };
  let props: any = {
    state: voiceTypes.reduceVoiceInputs(voiceTypes.emptyVoiceInputs(), input),
    owner: true,
    fence,
    t: (en: string) => en,
    onHandoff: (goal: any) => handoffs.push(goal),
  };
  const render = () => hooks.render(() => module.VoiceWorkPanel(props));
  const select = () =>
    nodes(render())
      .find((node) => node.type?.name === "VoiceInputList")
      .props.onSelect(input);
  const receipt = () => ({
    ...input,
    voice_origin_ref: "draft-ref",
    owner_reviewed_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 300000).toISOString(),
    snapshot_kind: "owner_snapshot",
  });
  const flush = () => new Promise((resolve) => setImmediate(resolve));
  return {
    hooks,
    render,
    select,
    receipt,
    pending,
    handoffs,
    fence,
    input,
    flush,
    patch: (next: any) => {
      props = { ...props, ...next };
    },
    close: () => hooks.close(),
  };
}
test("freeze is explicit and deduped; editable snapshot survives live revisions and ends voice only at handoff", async () => {
  const h = setup();
  try {
    h.render();
    assert.equal(h.pending.length, 0);
    h.select();
    h.select();
    assert.equal(h.pending.length, 1);
    assert.equal(h.pending[0].path, "/voice/work-drafts");
    assert.deepEqual(JSON.parse(h.pending[0].options.body), {
      voice_session_ref: "session",
      input_segment_id: "input",
      expected_revision: 1,
    });
    assert.equal(h.handoffs.length, 0);
    h.pending[0].resolve(h.receipt());
    await h.flush();
    let tree = h.render();
    const editor = nodes(tree).find((node) => node.type === "textarea");
    editor.props.onChange({ target: { value: "Owner edited goal" } });
    h.patch({
      state: voiceTypes.reduceVoiceInputs(voiceTypes.emptyVoiceInputs(), {
        ...h.input,
        text: "Later unrelated fragment",
        revision: 2,
        sequence: 2,
      }),
    });
    tree = h.render();
    assert.equal(
      nodes(tree).find((node) => node.type === "textarea").props.value,
      "Owner edited goal",
    );
    const end = nodes(tree).find(
      (node) =>
        node.type === "button" && text(node) === "End voice and review work",
    );
    end.props.onClick();
    end.props.onClick();
    assert.equal(h.handoffs.length, 1);
    assert.equal(h.handoffs[0].text, "Owner edited goal");
    assert.equal(h.handoffs[0].voiceOrigin.voice_origin_ref, "draft-ref");
    assert.equal("text" in h.handoffs[0].voiceOrigin, false);
  } finally {
    h.close();
  }
});
test("failed freeze keeps conversation and retries identical segment/revision; dismissal never starts Work", async () => {
  const h = setup();
  try {
    h.select();
    h.pending[0].reject({ code: "CONNECTION_LOST" });
    await h.flush();
    let tree = h.render();
    assert.match(text(tree), /Voice has not been ended/);
    assert.equal(h.handoffs.length, 0);
    nodes(tree)
      .find(
        (node) =>
          node.type === "button" && text(node) === "Retry the same snapshot",
      )
      .props.onClick();
    assert.deepEqual(h.pending[1].options, h.pending[0].options);
    h.pending[1].resolve(h.receipt());
    await h.flush();
    tree = h.render();
    nodes(tree)
      .find((node) => node.type === "Modal")
      .props.onClose();
    assert.equal(
      nodes(h.render()).some((node) => node.type === "textarea"),
      false,
    );
    assert.equal(h.handoffs.length, 0);
  } finally {
    h.close();
  }
});
test("paired owner loss, epoch invalidation and unmount reject late freeze responses", async () => {
  for (const kind of ["paired", "epoch", "unmount"]) {
    const h = setup();
    try {
      h.select();
      if (kind === "paired") {
        h.patch({ owner: false });
        h.render();
      } else if (kind === "epoch") h.fence.update("owner-new", true);
      else h.close();
      h.pending[0].resolve(h.receipt());
      await h.flush();
      assert.equal(h.handoffs.length, 0);
      if (kind !== "unmount")
        assert.equal(
          nodes(h.render()).some((node) => node.type === "textarea"),
          false,
        );
    } finally {
      h.close();
    }
  }
  const paired = setup();
  try {
    paired.patch({ owner: false });
    paired.select();
    assert.equal(paired.pending.length, 0);
  } finally {
    paired.close();
  }
});
test("actual composer initialization defaults only voice to deterministic and retains no scopes", () => {
  for (const voice of [false, true]) {
    const hooks = new Hooks();
    const module = load("agent/RunComposer.tsx", {
      react: hooks.react,
      "./types": agentTypes,
      "../personal/usePrivateMutation": {
        usePrivateMutation: () => ({ busy: false, pending: false }),
      },
      "../../components/DraftGuard": { useDraftGuard() {} },
    });
    const fence = new ResponseFence();
    fence.update("owner", true);
    const voiceOrigin = voice
      ? {
          voice_origin_ref: "draft-ref",
          expires_at: new Date(Date.now() + 300000).toISOString(),
        }
      : undefined;
    hooks.render(() =>
      module.RunComposer({
        t: (en: string) => en,
        scope: {
          modes: ["deterministic", "model"],
          scope_revision: "s".repeat(64),
          sources: [],
          tasks: [],
          events: [],
          destinations: [],
          limits: {},
          business_context_allowed: false,
        },
        fence,
        fresh: true,
        initialGoal: "Reviewed goal",
        voiceOrigin,
        onClose() {},
        onCreated() {},
        onRefresh() {},
      }),
    );
    const draft = hooks.slots.find(
      (slot) => slot.value?.goal === "Reviewed goal",
    ).value;
    assert.equal(draft.mode, voice ? "deterministic" : "model");
    assert.equal(draft.retain, false);
    assert.equal(draft.share, false);
    assert.deepEqual(draft.source_ids, []);
    assert.deepEqual(draft.personal_context.memory_ids, []);
    assert.equal(draft.personal_context.conversation_id, null);
    assert.equal(draft.voice_origin_ref, voice ? "draft-ref" : undefined);
    hooks.close();
  }
});

test("stale selection callback cannot freeze an old input in a new owner epoch", () => {
  const h = setup();
  try {
    const select = nodes(h.render()).find(
      (node) => node.type?.name === "VoiceInputList",
    ).props.onSelect;
    h.fence.update("new-owner", true);
    select(h.input);
    assert.equal(h.pending.length, 0);
  } finally {
    h.close();
  }
});
test("reviewed Start callback cannot dispatch an old goal across an owner epoch change", async () => {
  const hooks = new Hooks(),
    calls: any[] = [],
    fence = new ResponseFence();
  fence.update("owner", true);
  const module = load("agent/RunComposer.tsx", {
    react: hooks.react,
    "./types": agentTypes,
    "./labels": { modeLabel: (mode: string) => mode },
    "../personal/usePrivateMutation": {
      usePrivateMutation: () => ({
        busy: false,
        pending: false,
        run: async (...args: any[]) => calls.push(args),
      }),
    },
    "../../components/DraftGuard": { useDraftGuard() {} },
  });
  const props = {
    t: (en: string) => en,
    scope: {
      modes: ["deterministic"],
      scope_revision: "s".repeat(64),
      sources: [
        {
          id: "source",
          name: "Synthetic.csv",
          status: "verified",
          sha256: "s".repeat(64),
          byte_count: 10,
        },
      ],
      tasks: [],
      events: [],
      destinations: [],
      limits: {},
      business_context_allowed: false,
    },
    fence,
    fresh: true,
    initialGoal: "Reviewed goal",
    onClose() {},
    onCreated() {},
    onRefresh() {},
  };
  const render = () => hooks.render(() => module.RunComposer(props));
  try {
    let tree = render();
    nodes(tree)
      .find((node) => node.type === "input" && node.props.type === "checkbox")
      .props.onChange({ target: { checked: true } });
    tree = render();
    nodes(tree)
      .filter((node) => node.type === "input" && node.props.type === "checkbox")
      .at(-1)
      .props.onChange({ target: { checked: true } });
    tree = render();
    nodes(tree)
      .find((node) => node.type === "form")
      .props.onSubmit({ preventDefault() {} });
    tree = render();
    const start = nodes(tree).find(
      (node) => node.type === "button" && text(node) === "Start work",
    );
    assert.ok(start);
    fence.update("new-owner", true);
    await start.props.onClick();
    assert.equal(calls.length, 0);
  } finally {
    hooks.close();
  }
});

test("a consumed voice handoff keeps the Work composer mounted until privacy is invalidated", () => {
  const hooks = new Hooks();
  const previousWindow = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: new EventTarget(),
  });
  let workspace = {
    data: {
      principal: { kind: "owner", id: "owner" },
      personal_context_visible: true,
      voice: { config_revision: "fixture" },
    },
    offline: false,
    stale: false,
  };
  let ended = 0;
  try {
    const module = load("voiceWork/useVoiceWorkHandoff.tsx", {
      react: { ...hooks.react, lazy: () => "LazyPanel", Suspense: "Suspense" },
      "../WorkspaceContext": { useWorkspace: () => workspace },
      "../personal/responseFence": { ResponseFence },
      "./types": voiceTypes,
    });
    const render = () =>
      hooks.render(() =>
        module.useVoiceWorkHandoff(
          (en: string) => en,
          undefined,
          false,
          () => ended++,
        ),
      );
    render();
    let result = render();
    result.observe({
      type: "voice_input",
      role: "user",
      operation: "replace",
      voice_session_ref: "session",
      input_segment_id: "input",
      sequence: 1,
      revision: 1,
      text: "Compile the selected notes",
      eligible: true,
      reason: null,
      provider: "gemini",
      model: "fixture",
      destination_id: "destination",
      boundary: "unfinalized",
      observed_at: new Date().toISOString(),
    });
    result = render();
    nodes(result.panel)
      .find((node) => node.props?.onHandoff)
      .props.onHandoff({ id: "goal", goal: "Compile the selected notes" });
    assert.equal(ended, 1);
    result = render();
    nodes(result.panel)
      .find((node) => node.props?.onInitialGoalHandled)
      .props.onInitialGoalHandled();
    result = render();
    assert.ok(
      nodes(result.panel).some((node) => node.props?.onInitialGoalHandled),
      "Consuming the prefill must not close the Work composer",
    );
    workspace = {
      ...workspace,
      data: { ...workspace.data, personal_context_visible: false },
    };
    assert.equal(render().panel, null);
  } finally {
    hooks.close();
    if (previousWindow)
      Object.defineProperty(globalThis, "window", previousWindow);
    else Reflect.deleteProperty(globalThis, "window");
  }
});
