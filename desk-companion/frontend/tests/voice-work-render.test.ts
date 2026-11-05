import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  emptyVoiceInputs,
  reduceVoiceInputs,
} from "../src/workspace/voiceWork/types.ts";
register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { VoiceInputList, VoiceOriginLabel } =
  await import("../src/workspace/voiceWork/VoiceWorkPanel.tsx");
const input = {
  type: "voice_input",
  role: "user",
  operation: "replace",
  voice_session_ref: "session",
  input_segment_id: "input",
  sequence: 1,
  revision: 1,
  text: "<script>synthetic goal</script>",
  eligible: true,
  reason: null,
  provider: "gemini",
  model: "protocol-fake",
  destination_id: "destination",
  boundary: "unfinalized",
  observed_at: "2026-10-13T06:00:00Z",
};
test("actual voice markup is bilingual, escaped, unselected and honest about incomplete transcription", () => {
  for (const zh of [false, true]) {
    const t = (en: string, cn: string) => (zh ? cn : en);
    const state = reduceVoiceInputs(emptyVoiceInputs(), input);
    const markup = renderToStaticMarkup(
      createElement(VoiceInputList, {
        state,
        owner: true,
        disabled: false,
        onSelect() {},
        t,
      }),
    );
    assert.match(markup, zh ? /转写尚未完成/ : /Incomplete transcription/);
    assert.match(markup, zh ? /作为工作目标/ : /Use this as a work goal/);
    assert.match(markup, /&lt;script&gt;/);
    assert.doesNotMatch(markup, /<script>|checked=|Start work/);
    const paired = renderToStaticMarkup(
      createElement(VoiceInputList, {
        state: emptyVoiceInputs(),
        owner: false,
        disabled: false,
        onSelect() {},
        t,
      }),
    );
    assert.doesNotMatch(paired, /<button|synthetic goal/);
    assert.match(paired, zh ? /重新连接后打开工作/ : /Reconnect to open Work/);
    const provenance = renderToStaticMarkup(
      createElement(VoiceOriginLabel, { origin: state.inputs[0], t }),
    );
    assert.match(provenance, zh ? /不证明说话者身份/ : /not who spoke/);
  }
});
