import type { Translate } from "../types";

/** The English string is the question the local parser answers. */
export const WAITING_ASK = ["What am I waiting on?", "我在等什么"] as const;

export function WaitingAskButton({
  t,
  onAsk,
}: {
  t: Translate;
  onAsk: (phrase: string) => void;
}) {
  const [en, zh] = WAITING_ASK;
  const phrase = t(en, zh);
  return (
    <button
      type="button"
      className="text-button assistant-waiting-ask"
      onClick={() => onAsk(phrase)}
    >
      {phrase}
    </button>
  );
}
