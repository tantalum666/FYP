import { useEffect, useRef, useState } from "react";
import { Modal } from "../../components/Dialogs";
import { useDraftState } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import { useWorkspace } from "../WorkspaceContext";
import { ResponseFence } from "../personal/responseFence";
import { personalContextVisible } from "../personal/types";
import { agentError, modeLabel, stateLabel } from "./labels";
import { RunComposer } from "./RunComposer";
import { RunDetail } from "./RunDetail";
import { useAgentRuns } from "./useAgentRuns";
import "./agent.css";
type Props = {
  t: Translate;
  visibleOverride?: boolean;
  onReviewProposal?: (proposalId: string) => void;
};
export function RunPanel({
  t,
  visibleOverride = true,
  onReviewProposal,
}: Props) {
  const { data, offline, stale } = useWorkspace();
  const visible =
    visibleOverride &&
    personalContextVisible(
      data?.principal.kind === "owner",
      data?.personal_context_visible,
      offline,
      stale,
    );
  const [open, setOpen] = useState(false),
    [sessionEpoch, setSessionEpoch] = useState(0);
  const fence = useRef(new ResponseFence());
  const identity = `${data?.principal.kind ?? "none"}:${data?.principal.id ?? "none"}:${sessionEpoch}`;
  fence.current.update(identity, visible);
  const epoch = fence.current.version;
  useEffect(() => {
    const changed = () => {
      fence.current.update(`invalidated:${crypto.randomUUID()}`, false);
      setOpen(false);
      setSessionEpoch((x) => x + 1);
    };
    window.addEventListener("desk:session", changed);
    return () => window.removeEventListener("desk:session", changed);
  }, []);
  useEffect(() => {
    setOpen(false);
  }, [epoch]);
  return (
    <div className="agent-entry">
      <button
        type="button"
        className="secondary"
        disabled={!visible}
        onClick={() => setOpen(true)}
      >
        {t("Work tasks", "工作任务")}
      </button>
      <small>
        {visible
          ? t(
              "Start scoped work, inspect progress and collect files",
              "开始限定范围的工作、查看进展并获取文件",
            )
          : t(
              "Owner sign-in and visible, connected private context required",
              "需要本人登录且私人上下文可见、连接有效",
            )}
      </small>
      {open && visible && (
        <Modal
          title={t("Work tasks", "工作任务")}
          closeLabel={t("Close", "关闭")}
          onClose={() => setOpen(false)}
          wide
        >
          <RunWorkspace
            key={epoch}
            t={t}
            fence={fence.current}
            epoch={epoch}
            onReviewProposal={
              onReviewProposal
                ? (id) => {
                    setOpen(false);
                    onReviewProposal(id);
                  }
                : undefined
            }
          />
        </Modal>
      )}
    </div>
  );
}
function RunWorkspace({
  t,
  fence,
  epoch,
  onReviewProposal,
}: {
  t: Translate;
  fence: ResponseFence;
  epoch: number;
  onReviewProposal?: (id: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null),
    [compose, setCompose] = useState(false);
  const [detailGeneration, setDetailGeneration] = useState(0);
  const [navigate, setNavigate] = useState<{
    id: string | null;
    compose: boolean;
    proposal?: string;
  } | null>(null);
  const guard = useDraftState();
  const { value, error, loading, reload } = useAgentRuns(
    fence,
    selected,
    epoch,
  );
  function go(next: {
    id: string | null;
    compose: boolean;
    proposal?: string;
  }) {
    if (guard.busy) return;
    if (guard.dirty) setNavigate(next);
    else commit(next);
  }
  function commit(next: {
    id: string | null;
    compose: boolean;
    proposal?: string;
  }) {
    setNavigate(null);
    setDetailGeneration((x) => x + 1);
    if (next.proposal) {
      onReviewProposal?.(next.proposal);
      return;
    }
    setSelected(next.id);
    setCompose(next.compose);
  }
  return (
    <div className="agent-workspace">
      <p className="workspace-hint">
        {t(
          "Work continues while this panel is closed if the server and your authorization remain available. Ordinary chat is separate. Results stay here; this feature sends no outside notifications.",
          "只要服务端和授权仍有效，关闭此面板后工作仍可继续。普通聊天独立进行，结果保留于此，不发送外部通知。",
        )}
      </p>
      <div className="workspace-inline-actions">
        <button
          className="primary"
          disabled={!value?.scope || guard.busy}
          onClick={() => go({ id: selected, compose: true })}
        >
          {t("Start persistent work", "开始持续工作")}
        </button>
        <button
          className="secondary"
          disabled={loading}
          onClick={() => void reload(true)}
        >
          {t("Refresh", "刷新")}
        </button>
      </div>
      {!!error && (
        <p className="error-message" role="alert">
          {agentError(error, t)}
        </p>
      )}
      {loading && !value && (
        <p role="status">{t("Loading current work…", "正在读取当前工作…")}</p>
      )}
      {navigate && (
        <div className="agent-notice" role="alert">
          <p>
            {t(
              "Discard the current unsent control draft or in-memory retry data? A request already sent is not cancelled. Inspect its saved result before repeating it.",
              "放弃当前未发送操作草稿或内存中的重试资料？已发送请求不会被取消，重复操作前请先核对保存结果。",
            )}
          </p>
          <div className="workspace-inline-actions">
            <button className="primary" onClick={() => setNavigate(null)}>
              {t("Keep editing", "继续编辑")}
            </button>
            <button className="secondary" onClick={() => commit(navigate)}>
              {t("Discard and continue", "放弃并继续")}
            </button>
          </div>
        </div>
      )}
      {value && (
        <div className="agent-layout">
          <nav
            aria-label={t("Saved work tasks", "保存的工作任务")}
            className="agent-run-list"
          >
            {!value.runs.length && (
              <p>
                {t(
                  "No work tasks yet. A chat message does not create one automatically.",
                  "尚无工作任务，聊天消息不会自动创建任务。",
                )}
              </p>
            )}
            {value.runs.map((run) => (
              <button
                key={run.id}
                type="button"
                aria-current={selected === run.id ? "true" : undefined}
                className="agent-run-choice"
                disabled={guard.busy}
                onClick={() => {
                  if (run.id !== selected) go({ id: run.id, compose: false });
                }}
              >
                <strong>{run.goal || t("Untitled work", "未命名工作")}</strong>
                <span>{stateLabel(run.state, t)}</span>
                <small>
                  {modeLabel(run.mode, t)} · {run.updated_at}
                </small>
              </button>
            ))}
          </nav>
          <div>
            {value.detail && selected === value.detail.run.id ? (
              <RunDetail
                key={`${value.detail.run.id}:${detailGeneration}`}
                detail={value.detail}
                t={t}
                fence={fence}
                onChanged={() => void reload(true)}
                onReviewProposal={
                  onReviewProposal
                    ? (proposal) =>
                        go({ id: selected, compose: false, proposal })
                    : undefined
                }
              />
            ) : (
              <p>
                {t(
                  "Choose a work task to inspect its plan, reviews and files.",
                  "选择工作任务以检查计划、审阅与文件。",
                )}
              </p>
            )}
          </div>
        </div>
      )}
      {compose && value?.scope && (
        <RunComposer
          t={t}
          scope={value.scope}
          fence={fence}
          onRefresh={() => void reload(true)}
          onClose={() => setCompose(false)}
          onCreated={(run) => {
            setCompose(false);
            setSelected(run.id);
            void reload(true);
          }}
        />
      )}
    </div>
  );
}
