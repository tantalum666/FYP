import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { cardPatch, minorUnits } from "../src/workspace/purchaseCardFields.ts";

test("money parsing keeps two decimals and rejects extra precision", () => {
  assert.equal(minorUnits("45"), 4500);
  assert.equal(minorUnits("45.00"), 4500);
  assert.equal(minorUnits("45.5"), 4550);
  assert.equal(minorUnits("0", true), 0);
  assert.equal(minorUnits("0"), null);
  assert.equal(minorUnits("45.001"), null);
  assert.equal(minorUnits(""), null);
});

test("a card update sends only the fields the owner provided", () => {
  const body = cardPatch({ budget_minor: 8000 });
  assert.deepEqual(body, { budget_minor: 8000 });
  assert.equal("sku" in body, false);
  assert.equal("quantity" in body, false);
  assert.equal("merchants" in body, false);
});

test("the tasks page shows the purchase card and does not call a purchase success", () => {
  const panel = fs.readFileSync(
    new URL("../src/workspace/PurchaseCardPanel.tsx", import.meta.url),
    "utf8",
  );
  const tasks = fs.readFileSync(
    new URL("../src/workspace/TaskPanel.tsx", import.meta.url),
    "utf8",
  );
  assert.match(panel, /Nothing has been bought/);
  assert.match(panel, /This is not a live purchase/);
  assert.match(panel, /Nothing was approved/);
  assert.match(tasks, /PurchaseCardPanel/);
  assert.match(tasks, /!displayMode && <PurchaseCardPanel/);
});
