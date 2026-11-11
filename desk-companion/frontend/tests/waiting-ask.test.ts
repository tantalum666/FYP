import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { WaitingAskButton, WAITING_ASK } = await import(
  "../src/workspace/waitingAsk.tsx"
);

const en = (english: string) => english;
const zh = (_english: string, chinese: string) => chinese;

test("the waiting question is its own button and does not submit the composer", () => {
  let asked = "";
  const markup = renderToStaticMarkup(
    createElement(WaitingAskButton, {
      t: en,
      onAsk: (phrase: string) => {
        asked = phrase;
      },
    }),
  );
  assert.match(markup, /What am I waiting on\?/);
  assert.match(markup, /type="button"/);
  assert.equal(markup.includes("type=\"submit\""), false);
  assert.deepEqual(WAITING_ASK, ["What am I waiting on?", "我在等什么"]);
  assert.equal(asked, "");
});

test("the Chinese label is the same question", () => {
  const markup = renderToStaticMarkup(
    createElement(WaitingAskButton, { t: zh, onAsk: () => undefined }),
  );
  assert.match(markup, /我在等什么/);
  assert.equal(markup.includes("What am I waiting on?"), false);
});
