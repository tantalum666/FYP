import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

// Actual hook under deterministic hooks/transport; no device or paid model.
class Hooks {
  slots: any[] = [];
  index = 0;
  effects: (() => void)[] = [];
  same(a: any[], b: any[]) {
    return a.length === b.length && a.every((v, i) => Object.is(v, b[i]));
  }
  react = {
    useState: (initial: any) => {
      const n = this.index++;
      this.slots[n] ??= {
        value: typeof initial === "function" ? initial() : initial,
      };
      return [
        this.slots[n].value,
        (value: any) => {
          this.slots[n].value =
            typeof value === "function" ? value(this.slots[n].value) : value;
        },
      ];
    },
    useRef: (value: any) => {
      const n = this.index++;
      this.slots[n] ??= { current: value };
      return this.slots[n];
    },
    useCallback: (fn: any, deps: any[]) => {
      const n = this.index++;
      const old = this.slots[n];
      if (old && this.same(old.deps, deps)) return old.fn;
      this.slots[n] = { fn, deps };
      return fn;
    },
    useEffect: (fn: any, deps: any[]) => {
      const n = this.index++;
      const old = this.slots[n];
      if (old && this.same(old.deps, deps)) return;
      this.slots[n] = { deps };
      this.effects.push(() => {
        old?.cleanup?.();
        this.slots[n].cleanup = fn();
      });
    },
  };
  render(fn: () => any) {
    this.index = 0;
    const out = fn();
    this.effects.splice(0).forEach((f) => f());
    return out;
  }
  close() {
    this.slots.forEach((s) => s.cleanup?.());
  }
}
function harness() {
  const hooks = new Hooks();
  const engines: any[] = [];
  let calls = 0;
  class Engine {
    stopped = false;
    emit: any;
    constructor(emit: any) {
      this.emit = emit;
      engines.push(this);
    }
    start() {
      return Promise.resolve();
    }
    stop() {
      this.stopped = true;
    }
  }
  const code = ts.transpileModule(
    readFileSync(
      new URL("../src/workspace/wake/useAliceWake.ts", import.meta.url),
      "utf8",
    ),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } },
  ).outputText;
  const exported: any = {};
  new Function("require", "exports", code)(
    (name: string) =>
      name === "react"
        ? hooks.react
        : name.endsWith("WakeAudio")
          ? { WakeAudio: Engine }
          : name.endsWith("native")
            ? { apiOrigin: () => "http://127.0.0.1:5191" }
            : name.endsWith("voice-ticket")
              ? { handoverTicket: () => Promise.resolve("fixture") }
              : { request: () => Promise.resolve({ ticket: "fixture" }) },
    exported,
  );
  const props = {
    available: true,
    paused: false,
    engaged: false,
    onWake: async () => {
      calls++;
    },
  };
  const render = () => hooks.render(() => exported.useAliceWake(props));
  return { hooks, engines, props, render, calls: () => calls };
}
test("idle returns to local wait and never reconnects a cloud call without another keyword", () => {
  const h = harness();
  let state = h.render();
  assert.equal(h.engines.length, 0);
  state.enable();
  state = h.render();
  assert.equal(h.engines.length, 1);
  h.engines[0].emit({ type: "ready" });
  state = h.render();
  assert.equal(state.state, "waiting");
  assert.equal(h.calls(), 0);
  h.engines[0].emit({ type: "wake" });
  assert.equal(h.calls(), 1);
  h.props.engaged = true;
  state = h.render();
  assert.ok(h.engines[0].stopped);
  h.props.engaged = false;
  state = h.render();
  assert.equal(h.engines.length, 2);
  assert.equal(h.calls(), 1);
  h.engines[0].emit({ type: "wake" });
  assert.equal(h.calls(), 1);
  h.engines[1].emit({ type: "ready" });
  state = h.render();
  assert.equal(state.state, "waiting");
  h.hooks.close();
  h.engines[1].emit({ type: "wake" });
  assert.equal(h.calls(), 1);
});
test("error disarms instead of paid retries; suspension releases local listening", () => {
  const h = harness();
  h.render().enable();
  h.render();
  h.engines[0].emit({ type: "error" });
  let state = h.render();
  assert.equal(state.enabled, false);
  assert.equal(state.state, "error");
  assert.equal(h.calls(), 0);
  h.render();
  assert.equal(h.engines.length, 1);
  state.enable();
  h.render();
  assert.equal(h.engines.length, 2);
  h.props.paused = true;
  h.render();
  assert.ok(h.engines[1].stopped);
  h.props.paused = false;
  h.render();
  assert.equal(h.engines.length, 3);
  assert.equal(h.calls(), 0);
  h.hooks.close();
  assert.ok(h.engines[2].stopped);
});
