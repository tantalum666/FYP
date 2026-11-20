import assert from "node:assert/strict";
import test from "node:test";
import {
  diagnosticsLines,
  type DiagnosticsReport,
} from "../src/diagnosticsData.ts";

const report: DiagnosticsReport = {
  versions: { service: "0.1.0", python: "3.12.0" },
  provider: {
    configured: true,
    name: "qwen",
    background: false,
    cap_used: 2,
    cap_limit: 20,
  },
  backup: {
    last_at: "2026-10-02T00:00:00.000000Z",
    file_name: "desk-20261002T000000Z.sqlite3",
    bytes: 4096,
    retained: 1,
  },
  database: { bytes: 8192 },
  scheduler: { ticks: { rules: "ready" }, backup: "ready" },
};

test("diagnostics lines show cap and backup and drop unknown secret fields", () => {
  const leaked = {
    ...report,
    api_key: "super-secret-key",
    password: "fixture-secret",
  };
  const text = diagnosticsLines(leaked, "en")
    .map((line) => `${line.label}=${line.value}`)
    .join("\n");
  assert.match(text, /Follow-up requests today=2 \/ 20/);
  assert.match(text, /desk-20261002T000000Z\.sqlite3/);
  assert.equal(text.includes("super-secret-key"), false);
  assert.equal(text.includes("fixture-secret"), false);
  assert.equal(
    diagnosticsLines(report, "zh").some((line) => line.label === "最近备份"),
    true,
  );
});

test("a missing backup is named without inventing a file", () => {
  const empty = {
    ...report,
    backup: { last_at: null, file_name: null, bytes: null, retained: 0 },
    scheduler: { ticks: {}, backup: "idle" },
  };
  const values = diagnosticsLines(empty, "en").map((line) => line.value);
  assert.ok(values.includes("None yet"));
  assert.ok(values.includes("No ticks yet"));
});

test("platform costs and local holds have independent scopes", () => {
  const rows = diagnosticsLines(
    {
      ...report,
      openai_spending: {
        day: "2026-11-19",
        allocated_usd: 9,
        available_usd: 0.3,
        local_budget_used_usd: 8.7,
        reserved_or_unpriced_usd: 8.5,
        observed_usage_estimate_usd: 0.2,
        last_platform_statement: {
          amount_usd: "0.432109876",
          utc_day: "2026-11-19",
          scope: "All projects",
          imported_at: "2026-11-19T01:25Z",
        },
      },
    },
    "en",
  );
  assert.ok(
    rows.some(
      (row) =>
        row.label.includes("platform") &&
        row.value === "US$0.43 · 2026-11-19 UTC · All projects",
    ),
  );
  assert.ok(
    rows.some(
      (row) => row.label.includes("reservations") && row.value === "US$8.50",
    ),
  );
});
