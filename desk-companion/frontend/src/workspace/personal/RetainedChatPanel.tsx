import { useState } from "react";
import type { Translate } from "../../types";
import type { Proposal } from "../assistantTypes";
import { useDraftGuard } from "../../components/DraftGuard";
import { PersonalContextPanel } from "./PersonalContextPanel";
import { usePersonalContext } from "./usePersonalContext";
import { usePrivateMutation } from "./usePrivateMutation";
import { MutationFeedback } from "./MutationFeedback";
import { ProposalActionCard } from "../ProposalActionCard";

export function RetainedChatPanel({ t }: { t: Translate }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [reply, setReply] = useState<{
    message: string;
    proposal?: Proposal;
  } | null>(null);
  const context = usePersonalContext(true, selected);
  const mutation = usePrivateMutation();
  const locked = mutation.busy || mutation.pending;
  useDraftGuard(!!text.trim() || mutation.pending, mutation.busy);
  return (
    <section>
      <PersonalContextPanel
        context={context}
        selected={selected}
        mutation={mutation}
        draftDirty={!!text.trim()}
        voiceActive={false}
        t={t}
        onSelect={(id, mutationComplete = false) => {
          if (!text.trim() && (!locked || mutationComplete)) {
            setSelected(id);
            setReply(null);
          }
        }}
      />
      {reply && !selected && (
        <p className="personal-text" role="status">
          {reply.message}
        </p>
      )}
      {reply?.proposal && (
        <ProposalActionCard
          proposal={reply.proposal}
          t={t}
          busy={locked}
          onDecision={(action) =>
            void mutation.run(
              `/assistant/proposals/${reply.proposal!.id}/decisions`,
              { action },
              async () => {
                setReply(null);
                await context.reload(true);
              },
            )
          }
        />
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!text.trim() || locked) return;
          void mutation.run<{ message: string; proposal?: Proposal }>(
            "/assistant/retained-messages",
            {
              message: text,
              language: t("en", "zh"),
              conversation_id: selected,
            },
            async (result) => {
              setText("");
              setReply(result);
              await context.reload(true);
            },
          );
        }}
      >
        <label className="field">
          {t("Message", "消息")}
          <textarea
            value={text}
            maxLength={3000}
            disabled={locked}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <button
          className="primary"
          disabled={locked || !text.trim() || !context.settings}
        >
          {t("Send", "发送")}
        </button>
      </form>
      <MutationFeedback mutation={mutation} t={t} />
    </section>
  );
}
