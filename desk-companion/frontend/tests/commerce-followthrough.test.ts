import assert from "node:assert/strict";
import test from "node:test";
import {
  appendOrderUpdates,
  type ConversationTurn,
} from "../src/workspace/conversationTranscript.ts";
import {
  legTime,
  orderUpdates,
  watchedMarks,
  orderStatus,
  type CommerceReview,
} from "../src/workspace/commercePresentation.ts";
const t = (en: string, zh: string) => zh;
function flight(id: string, state: string, version: number): CommerceReview {
  return {
    id,
    state,
    version,
    kind: "flight",
    segments: [
      {
        flight: "AF2979",
        origin: "HKG",
        destination: "HND",
        departs: "2026-11-27T11:30",
        arrives: "2026-11-27T17:39",
      },
    ],
    currency: "HKD",
    quoted_minor: 5200,
    review_minor: 5200,
    approved_minor: 5200,
    previous_minor: null,
    review_deadline_ms: null,
    charged_minor: null,
    pnr: null,
    released: state === "stopped",
    adults: 1,
  };
}
test("show only new verified changes to orders already underway in this conversation", () => {
  const waiting = flight("a", "stopping", 3),
    stopped = flight("a", "stopped", 4),
    old = flight("b", "completed", 9);
  assert.deepEqual(orderUpdates(watchedMarks([waiting]), [old, stopped]), [
    stopped,
  ]);
  assert.deepEqual(
    orderUpdates(watchedMarks([old, stopped]), [old, stopped]),
    [],
  );
  assert.deepEqual(
    orderUpdates(watchedMarks([waiting]), [flight("a", "stopping", 4)]),
    [],
  );
  assert.deepEqual(
    orderUpdates(watchedMarks([flight("a", "quoted", 1)]), [
      flight("a", "expired", 2),
    ]),
    [],
  );
  assert.deepEqual(
    orderUpdates(watchedMarks([flight("a", "reprice", 3)]), [
      flight("a", "reprice", 4),
    ]).map((r) => r.version),
    [4],
  );
  assert.ok(!JSON.stringify(watchedMarks([waiting])).includes("AF2979"));
});
test("a short status distinguishes a released hold from an unconfirmed charge, with overnight dates intact", () => {
  assert.match(
    orderStatus(flight("a", "stopped", 4), t),
    /预授权已释放，未扣款/,
  );
  assert.doesNotMatch(
    orderStatus(flight("a", "unverified", 4), t),
    /未扣款|已释放/,
  );
  assert.equal(
    legTime({
      flight: "F1",
      origin: "HKG",
      destination: "NRT",
      departs: "2026-12-31T23:20",
      arrives: "2027-01-01T04:30",
    }),
    "2026-12-31 · 23:20–2027-01-01 04:30",
  );
});

test("a settled order replaces the pending answer and appears only once after another user turn", () => {
  const old = flight("a", "stopping", 2),
    done = flight("a", "stopped", 3);
  const pending: ConversationTurn = {
    id: 1,
    role: "assistant",
    body: "checking",
    orderKey: "flight/a",
    commerceChat: "my-chat",
  };
  const immediate = appendOrderUpdates([pending], [done], "my-chat", t);
  assert.equal(immediate.length, 1);
  assert.equal(immediate[0].body, orderStatus(done, t));
  const later = appendOrderUpdates(
    [pending, { id: 2, role: "user", body: "hello" }],
    [done],
    "my-chat",
    t,
  );
  assert.equal(later.length, 3);
  assert.deepEqual(appendOrderUpdates(later, [done], "my-chat", t), later);
  assert.ok(watchedMarks([old]).length);
});
