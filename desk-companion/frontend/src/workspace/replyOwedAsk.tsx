import type { Translate } from "../types";

/** The English string is the question the local parser answers. */
export const REPLY_OWED_ASK = ["Who do I need to reply to?", "我该回复谁？"] as const;

export function ReplyOwedAsk({
  t,
  onAsk,
}: {
  t: Translate;
  onAsk: (phrase: string) => void;
}) {
  const [en, zh] = REPLY_OWED_ASK;
  const phrase = t(en, zh);
  return (
    <button
      type="button"
      className="text-button assistant-reply-owed-ask"
      onClick={() => onAsk(phrase)}
    >
      {phrase}
    </button>
  );
}
