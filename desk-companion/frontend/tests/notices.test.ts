import assert from "node:assert/strict";
import test from "node:test";
import {
  browserPayload,
  openNotices,
  showBrowserNotice,
  type DeskNotice,
} from "../src/workspace/notices.ts";

const notice = (state: DeskNotice["state"]): DeskNotice => ({
  id: "morning_brief-2026-10-02",
  state,
  title_en: "Morning briefing",
  title_zh: "早晨简报",
  body_en: "1 open task.",
  body_zh: "1 件事务。",
  reason_en: "Quiet hours are not in effect.",
  reason_zh: "当前不在安静时段。",
  push: { title: "Morning briefing", body: "1 open task.", tag: "morning_brief-2026-10-02" },
});

test("an open page can show one browser notification and skip duplicates", () => {
  const payload = browserPayload(notice("open"), "zh");
  assert.equal(payload.title, "早晨简报");
  assert.equal(payload.options.tag, "morning_brief-2026-10-02");
  const shown: string[] = [];
  const notifier = {
    permission: "granted",
    show(title: string, options: { tag: string }) {
      shown.push(title + ":" + options.tag);
    },
  };
  assert.equal(showBrowserNotice(notice("open"), "en", notifier), true);
  assert.deepEqual(shown, ["Morning briefing:morning_brief-2026-10-02"]);
  assert.equal(
    showBrowserNotice(notice("open"), "en", { permission: "default", show: notifier.show }),
    false,
  );
  assert.equal(showBrowserNotice(notice("dismissed"), "en", notifier), false);
  assert.equal(openNotices([notice("open"), notice("open"), notice("dismissed")]).length, 1);
});
