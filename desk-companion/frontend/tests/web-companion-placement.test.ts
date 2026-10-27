import assert from "node:assert/strict";
import test from "node:test";
import {
  anchoredGeometry,
  defaultPreference,
  geometry,
} from "../src/companion/placement.ts";

test("the default companion stays inside its sidebar space at normal and short heights", () => {
  for (const anchor of [
    { x: 16, y: 680, width: 208, height: 240 },
    { x: 16, y: 410, width: 178, height: 130 },
  ]) {
    for (const mode of ["full", "half", "head"] as const) {
      const box = anchoredGeometry(
        mode,
        anchor,
        { width: 1440, height: 1000 },
        0.6,
      )!;
      assert.ok(box.x >= anchor.x);
      assert.ok(box.x + box.width <= anchor.x + anchor.width);
      assert.ok(box.y >= anchor.y);
      assert.ok(box.y + box.visibleHeight <= anchor.y + anchor.height - 40);
    }
  }
});

test("hiding the sidebar companion keeps its recall control clear of the chat button", () => {
  const anchor = { x: 16, y: 680, width: 208, height: 240 };
  const box = anchoredGeometry(
    "hidden",
    anchor,
    { width: 1440, height: 1000 },
    0.6,
  )!;
  assert.equal(box.visibleHeight, 0);
  assert.ok(box.handleX >= anchor.x);
  assert.ok(box.handleX + 40 <= anchor.x + anchor.width);
  assert.ok(box.handleY + 36 < anchor.y + anchor.height - 40);
});

test("an unavailable sidebar uses the existing floating preference without changing it", () => {
  assert.equal(
    anchoredGeometry("full", null, { width: 390, height: 844 }, 0.6),
    null,
  );
  assert.equal(
    anchoredGeometry(
      "full",
      { x: 0, y: 0, width: 0, height: 0 },
      { width: 390, height: 844 },
      0.6,
    ),
    null,
  );
  assert.equal(
    anchoredGeometry(
      "full",
      { x: 0, y: 0, width: 200, height: 240 },
      { width: 1440, height: 1000 },
      NaN,
    ),
    null,
  );
  const preference = { ...defaultPreference(), x: 0.35, y: 0.8, scale: 1.25 };
  const saved = structuredClone(preference);
  const before = geometry(
    preference,
    { width: 1440, height: 1000 },
    "web",
    0.6,
  );
  anchoredGeometry(
    "full",
    { x: 16, y: 680, width: 208, height: 240 },
    { width: 1440, height: 1000 },
    0.6,
  );
  assert.deepEqual(preference, saved);
  assert.deepEqual(
    geometry(preference, { width: 1440, height: 1000 }, "web", 0.6),
    before,
  );
});
