import assert from "node:assert/strict";
import test from "node:test";
import { handoverTicket } from "../src/workspace/voice-ticket.ts";

test("waits for local slot handover without creating duplicate provider sessions", async () => {
  let calls = 0,
    now = 0;
  const result = await handoverTicket(
    async () => {
      if (++calls < 4) throw { code: "VOICE_BUSY" };
      return "one-ticket";
    },
    () => true,
    {
      now: () => now,
      sleep: async (ms) => {
        now += ms;
      },
    },
  );
  assert.equal(result, "one-ticket");
  assert.equal(calls, 4);
  assert.equal(now, 750);
});

test("does not retry connection or permission failures", async () => {
  for (const code of [
    "CONNECTION_LOST",
    "VOICE_NOT_CONFIGURED",
    "AUTH_REQUIRED",
  ]) {
    let calls = 0;
    await assert.rejects(
      handoverTicket(
        async () => {
          calls++;
          throw { code };
        },
        () => true,
      ),
    );
    assert.equal(calls, 1);
  }
});

test("stopping during handover prevents another ticket request", async () => {
  let active = true,
    calls = 0;
  await assert.rejects(
    handoverTicket(
      async () => {
        calls++;
        throw { code: "VOICE_BUSY" };
      },
      () => active,
      {
        sleep: async () => {
          active = false;
        },
      },
    ),
  );
  assert.equal(calls, 1);
});

test("another active conversation cannot cause unbounded polling", async () => {
  let now = 0,
    calls = 0;
  await assert.rejects(
    handoverTicket(
      async () => {
        calls++;
        throw { code: "VOICE_BUSY" };
      },
      () => true,
      {
        now: () => now,
        sleep: async (ms) => {
          now += ms;
        },
      },
    ),
  );
  assert.equal(calls, 20);
  assert.ok(now <= 5000);
});
