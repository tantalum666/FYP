import test from "node:test";
import assert from "node:assert/strict";
import {
  defaultPreference,
  edgeIntent,
  geometry,
  movedPreference,
  readPreference,
  scaleLimit,
} from "../src/companion/placement.ts";

test("edge depth distinguishes free, half, head and hidden on left, right and bottom", () => {
  const v = { width: 1280, height: 800 };
  assert.deepEqual(edgeIntent(600, 400, v, "web"), {
    dock: "free",
    mode: "full",
  });
  for (const [distance, mode] of [
    [60, "half"],
    [25, "head"],
    [5, "hidden"],
  ] as const) {
    assert.deepEqual(edgeIntent(distance, 300, v, "web"), {
      dock: "left",
      mode,
    });
    assert.deepEqual(edgeIntent(1280 - distance, 300, v, "web"), {
      dock: "right",
      mode,
    });
    assert.deepEqual(edgeIntent(600, 778 - distance, v, "web"), {
      dock: "bottom",
      mode,
    });
  }
});
test("invalid or blocked storage data cannot strand the companion", () => {
  assert.deepEqual(readPreference("garbage"), defaultPreference());
  assert.deepEqual(
    readPreference('{"version":2,"mode":"hidden"}'),
    defaultPreference(),
  );
  const p = readPreference(
    '{"version":1,"mode":"nope","dock":"top","x":-9,"y":12,"size":"giant"}',
  );
  assert.equal(p.mode, "full");
  assert.equal(p.dock, "free");
  assert.equal(p.x, 0);
  assert.equal(p.y, 1);
  assert.equal(p.size, "medium");
});
test("resizing keeps free figures and every hidden recall button inside usable screen bounds", () => {
  for (const v of [
    { width: 1280, height: 800 },
    { width: 390, height: 844 },
    { width: 280, height: 320 },
  ]) {
    for (const surface of ["web", "device"] as const) {
      const g = geometry(
        { ...defaultPreference(), scale: 2 },
        v,
        surface,
        0.31,
      );
      assert.ok(g.x >= 0 && g.x + g.width <= v.width);
      assert.ok(g.y >= 0 && g.y + g.visibleHeight <= v.height - g.bottomInset);
      for (const dock of ["free", "left", "right", "bottom"] as const) {
        const hidden = geometry(
          { ...defaultPreference(), mode: "hidden", dock },
          v,
          surface,
          0.31,
        );
        assert.ok(hidden.handleX >= 0 && hidden.handleX + 40 <= v.width);
        assert.ok(hidden.handleY >= 0 && hidden.handleY + 36 <= v.height);
        assert.equal(hidden.visibleHeight, 0);
      }
    }
  }
});
test("saved continuous scale survives reload and legacy sizes migrate without losing placement", () => {
  const raw = {
    ...defaultPreference(),
    scale: 1.37,
    dock: "right",
    mode: "head",
    y: 0.42,
  };
  const restored = readPreference(JSON.stringify(raw));
  assert.equal(restored.scale, 1.37);
  assert.equal(restored.dock, "right");
  assert.equal(restored.mode, "head");
  assert.equal(restored.y, 0.42);
  for (const [size, expected] of [
    ["small", 0.8],
    ["medium", 1],
    ["large", 1.2],
  ] as const) {
    const { scale: _old, ...legacy } = { ...defaultPreference(), size };
    assert.equal(readPreference(JSON.stringify(legacy)).scale, expected);
  }
  assert.equal(readPreference(JSON.stringify({ ...raw, scale: 80 })).scale, 2);
  assert.equal(
    readPreference(JSON.stringify({ ...raw, scale: -1 })).scale,
    0.5,
  );
});
test("arbitrary scaling keeps a docked head cropped and the complete character fits after recall", () => {
  const view = { width: 1024, height: 600 };
  const aspect = 460 / 1492;
  const max = scaleLimit(view, "device", aspect);
  assert.ok(max > 1 && max < 2);
  const p = {
    ...defaultPreference(),
    scale: Math.min(1.37, max),
    mode: "head" as const,
    dock: "right" as const,
  };
  const head = geometry(p, view, "device", aspect);
  assert.ok(Math.abs(head.visibleHeight / head.height - 0.21) < 0.001);
  assert.ok(head.x < view.width && head.x + head.width > view.width);
  const full = geometry(
    { ...p, mode: "full", dock: "free" },
    view,
    "device",
    aspect,
  );
  assert.ok(
    full.y >= 0 && full.y + full.height <= view.height - full.bottomInset,
  );
  assert.ok(full.x >= 0 && full.x + full.width <= view.width);
});
test("a docked head can be dragged back to a complete in-bounds figure", () => {
  const v = { width: 1024, height: 600 };
  const start = {
    ...defaultPreference(),
    mode: "head" as const,
    dock: "left" as const,
  };
  const next = movedPreference(
    start,
    400,
    150,
    { dock: "free", mode: "full" },
    v,
    "device",
    0.31,
  );
  const g = geometry(next, v, "device", 0.31);
  assert.equal(next.mode, "full");
  assert.equal(next.dock, "free");
  assert.ok(g.x >= 0 && g.x + g.width <= v.width);
  assert.ok(g.y + g.height <= v.height - g.bottomInset);
});
