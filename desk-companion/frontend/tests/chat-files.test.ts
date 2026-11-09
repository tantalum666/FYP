import assert from "node:assert/strict";
import test from "node:test";
import {
  CHAT_FILE_BYTES,
  encodeChatFile,
  fileBytesLabel,
  validateChatFile,
} from "../src/workspace/chatFiles.ts";

test("selected content retains Unicode filename and exact bytes for sending", async () => {
  const file = new File(["本地附件\nfixture"], "课堂笔记.md", {
    type: "text/markdown",
  });
  const result = await encodeChatFile(file);
  assert.equal(result.name, "课堂笔记.md");
  assert.equal(
    Buffer.from(result.data, "base64").toString("utf8"),
    "本地附件\nfixture",
  );
});
test("file limits reject empty, oversized, executable and path-like choices", () => {
  for (const file of [
    { name: "empty.txt", size: 0 },
    { name: "large.pdf", size: CHAT_FILE_BYTES + 1 },
    { name: "run.exe", size: 12 },
    { name: "../notes.txt", size: 20 },
  ])
    assert.throws(() => validateChatFile(file));
  for (const name of [
    "report.PDF",
    "work.docx",
    "sheet.xlsx",
    "slides.pptx",
    "photo.webp",
  ])
    assert.doesNotThrow(() => validateChatFile({ name, size: 128 }));
  assert.equal(fileBytesLabel(1024), "1 KB");
  assert.equal(fileBytesLabel(1024 * 1024), "1.0 MB");
});
