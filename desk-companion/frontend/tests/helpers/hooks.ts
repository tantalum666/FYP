// Deterministic lifecycle harness for actual React hooks.
export class Hooks {
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
