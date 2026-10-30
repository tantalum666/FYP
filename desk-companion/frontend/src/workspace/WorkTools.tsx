import { useEffect, useState } from "react";
import type { Translate } from "../types";
import { errorText, request } from "../api";
import { Modal } from "../components/Dialogs";
import { useDraftGuard } from "../components/DraftGuard";
import { useWorkspace } from "./WorkspaceContext";
import { RunPanel } from "./agent/RunPanel";
import type { WorkGoalRequest } from "./agent/types";
import { ResponsibilitiesPanel } from "./responsibilities/ResponsibilitiesPanel";
import { RoutinesPanel } from "./RoutinesPanel";
import { BrowserWorkflowPanel } from "./browser/BrowserWorkflowPanel";
import { ConnectorReviewPanel } from "./connectors/ConnectorReviewPanel";
import { ProposalActionCard } from "./ProposalActionCard";
import type { Proposal } from "./assistantTypes";
import { usePrivateMutation } from "./personal/usePrivateMutation";
import { MutationFeedback } from "./personal/MutationFeedback";
import { RetainedChatPanel } from "./personal/RetainedChatPanel";

function ProposalReview({
  id,
  t,
  close,
}: {
  id: string;
  t: Translate;
  close: () => void;
}) {
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [error, setError] = useState<unknown>(null);
  const mutation = usePrivateMutation();
  const { refresh } = useWorkspace();
  useDraftGuard(mutation.pending, mutation.busy);
  useEffect(() => {
    let current = true;
    void request<{ proposals: Proposal[] }>("/assistant/proposals").then(
      (result) => {
        if (current)
          setProposal(result.proposals.find((p) => p.id === id) ?? null);
      },
      (failure) => {
        if (current) setError(failure);
      },
    );
    return () => {
      current = false;
    };
  }, [id]);
  return (
    <Modal
      title={t("Review requested change", "核对请求的修改")}
      closeLabel={t("Close review", "关闭核对")}
      onClose={close}
      busy={mutation.busy}
      dirty={mutation.pending}
    >
      {!!error && <p role="alert">{errorText(error, t)}</p>}
      {proposal ? (
        <ProposalActionCard
          proposal={proposal}
          t={t}
          busy={mutation.busy || mutation.pending}
          onDecision={(action) => {
            void mutation.run(
              `/assistant/proposals/${id}/decisions`,
              { action },
              async () => {
                await refresh();
                close();
              },
            );
          }}
        />
      ) : (
        <p>
          {t(
            "No pending change is available. Refresh the work to see its current result.",
            "当前没有可审批的修改，请刷新工作查看结果。",
          )}
        </p>
      )}
      <MutationFeedback mutation={mutation} t={t} />
    </Modal>
  );
}

export default function WorkTools({
  t,
  initialGoal,
  onInitialGoalHandled,
}: {
  t: Translate;
  initialGoal?: WorkGoalRequest;
  onInitialGoalHandled?: () => void;
}) {
  const { data, offline, stale } = useWorkspace();
  const [goal, setGoal] = useState<WorkGoalRequest | null>(null);
  const [proposal, setProposal] = useState<string | null>(null);
  const [browserJob, setBrowserJob] = useState<string | null>(null);
  const [connectorIntent, setConnectorIntent] = useState<string | null>(null);
  const privateVisible = !!data?.personal_context_visible && !offline && !stale;
  const [epoch, setEpoch] = useState(0);
  useEffect(() => {
    const clear = () => {
      setGoal(null);
      setProposal(null);
      setBrowserJob(null);
      setConnectorIntent(null);
      setEpoch((n) => n + 1);
    };
    window.addEventListener("desk:session", clear);
    window.addEventListener("desk:personal-context", clear);
    return () => {
      window.removeEventListener("desk:session", clear);
      window.removeEventListener("desk:personal-context", clear);
    };
  }, []);
  return (
    <section
      className="work-tools"
      aria-label={t("Research and follow-up", "资料工作与持续跟进")}
    >
      <div className="workspace-inline-actions">
        <RunPanel
          t={t}
          initialGoal={goal ?? initialGoal}
          onGoalHandled={() => {
            setGoal(null);
            onInitialGoalHandled?.();
          }}
          onReviewProposal={setProposal}
          onReviewBrowserJob={setBrowserJob}
          onReviewConnectorIntent={setConnectorIntent}
        />
        <ResponsibilitiesPanel t={t} onCompile={setGoal} />
      </div>
      <details>
        <summary>{t("Scheduled check-ins", "定期检查")}</summary>
        <RoutinesPanel t={t} />
      </details>
      <details>
        <summary>
          {t("Saved conversations and context", "保存的会话与上下文")}
        </summary>
        {privateVisible && (
          <RetainedChatPanel key={`${epoch}:${data?.principal.id}`} t={t} />
        )}
      </details>
      <details open={!!browserJob || !!connectorIntent}>
        <summary>
          {t("Public browser and connectors", "公开网页与连接器")}
        </summary>
        <BrowserWorkflowPanel
          t={t}
          reviewEffectId={browserJob}
          onReviewClosed={() => setBrowserJob(null)}
        />
        <ConnectorReviewPanel
          t={t}
          reviewIntentId={connectorIntent}
          onReviewClosed={() => setConnectorIntent(null)}
        />
      </details>
      {privateVisible && proposal && (
        <ProposalReview
          key={`${epoch}:${proposal}`}
          id={proposal}
          t={t}
          close={() => setProposal(null)}
        />
      )}
    </section>
  );
}
