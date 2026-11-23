import phrases from "../../../backend/desk/data/quiet-chat-phrases.json" with { type: "json" };

export function quietChatIntent(message: string) {
  const text = message.normalize("NFKC").toLowerCase().trim()
    .replace(/\s+/gu, " ").replace(/[.!?。]+$/u, "").trim();
  if (phrases.read.includes(text)) return "read";
  if (phrases.ack.includes(text)) return "ack";
}
