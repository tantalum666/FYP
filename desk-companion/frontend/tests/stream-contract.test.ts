import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { consumeChunk, emptyStream, readBody } from "../src/replyStream.ts";

const fixture = new URL("../../contracts/assistant-stream.sse", import.meta.url);

function reduce(body: string) {
  let state = emptyStream();
  let pending = "";
  for (let index = 0; index < body.length; index += 5) {
    const next = consumeChunk(state, pending, body.slice(index, index + 5));
    state = next.state;
    pending = next.buffer;
  }
  assert.equal(pending, "");
  return state;
}

test("a buffered phone body and small chunks reach the same reply", async () => {
  const bytes = readFileSync(fixture);
  const text = bytes.toString("utf8");
  let buffered = "";
  await readBody(new Response(bytes), (chunk) => {
    buffered += chunk;
  });
  const chunks: string[] = [];
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (let index = 0; index < bytes.length; index += 7) {
        controller.enqueue(bytes.subarray(index, index + 7));
      }
      controller.close();
    },
  });
  await readBody(new Response(stream), (chunk) => chunks.push(chunk));
  const fromPhone = reduce(buffered);
  const fromWeb = reduce(chunks.join(""));
  assert.deepEqual(fromPhone, fromWeb);
  assert.equal(fromPhone.message, "It is Tuesday. Morning.");
  assert.equal(fromPhone.tools.length, 1);
  assert.equal(fromPhone.tools[0].tool, "owner_clock");
  assert.equal(fromPhone.tools[0].phase, "finished");
  assert.equal(fromPhone.tools[0].saved, false);
  assert.equal("arguments" in fromPhone.tools[0], false);
  assert.equal(fromPhone.reply?.message, "It is Tuesday. Morning.");
  assert.equal(fromPhone.error, "TEXT_AI_UNAVAILABLE");
  assert.equal(fromPhone.status, 503);
  assert.equal(fromPhone.done, true);
  assert.equal(text.includes("\"arguments\""), false);
});
