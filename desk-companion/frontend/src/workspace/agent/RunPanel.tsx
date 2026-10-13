import { useEffect, useRef, useState } from "react";
import { apiOrigin } from "../../native";
import { Modal } from "../../components/Dialogs";
import { useDraftState } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import { useWorkspace } from "../WorkspaceContext";
import { ResponseFence } from "../personal/responseFence";
import { agentError, modeLabel, stateLabel } from "./labels";
import { RunComposer } from "./RunComposer";
import { RunDetail } from "./RunDetail";
import { RunMetadataPanel } from "./RunMetadataPanel";
import { runAccess } from "./runMetadata";
import { validWorkGoal } from "./types";
import type { WorkGoalRequest } from "./types";
import { useAgentRuns } from "./useAgentRuns";
import { WorkSearchPanel } from "./WorkSearchPanel";
import "./agent.css";
type Props = {
  t: Translate;
  visibleOverride?: boolean;
  onReviewProposal?: (proposalId: string) => void;
  initialGoal?: WorkGoalRequest | null;
  onGoalHandled?: () => void;
  onReviewBrowserJob?: (jobId: string) => void;
  onReviewConnectorIntent?: (intentId: string) => void;
};
export function RunPanel({
  t,
  visibleOverride = true,
  onReviewProposal,
  initialGoal,
  onGoalHandled,
  onReviewBrowserJob,
  onReviewConnectorIntent,
}: Props) {
  const { data, offline, stale } = useWorkspace();
  const access = runAccess(
    data?.principal.kind === "owner",
    !offline && !stale,
    visibleOverride,
    data?.personal_context_visible === true,
  );
  const visible = access.privateVisible;
  const [open, setOpen] = useState(false),
    [sessionEpoch, setSessionEpoch] = useState(0);
  const [goalNotice, setGoalNotice] = useState(false);
  const [handledGoalId, setHandledGoalId] = useState<string | null>(null);
  const goalRequest = initialGoal?.id === handledGoalId ? null : initialGoal;
  function acknowledgeGoal() {
    if (goalRequest) setHandledGoalId(goalRequest.id);
    onGoalHandled?.();
  }
  const fence = useRef(new ResponseFence());
  const identity = `${data?.principal.kind ?? "none"}:${data?.principal.id ?? "none"}:${sessionEpoch}`;
  fence.current.update(
    `${identity}:${apiOrigin()}:${data?.voice.config_revision ?? ""}:${visible ? "private" : "metadata"}`,
    access.available,
  );
  const epoch = fence.current.version;
  useEffect(() => {
    const changed = () => {
      fence.current.update(`invalidated:${crypto.randomUUID()}`, false);
      setOpen(false);
      setSessionEpoch((x) => x + 1);
    };
    window.addEventListener("desk:session", changed);
    window.addEventListener("desk:personal-context", changed);
    return () => {
      window.removeEventListener("desk:session", changed);
      window.removeEventListener("desk:personal-context", changed);
    };
  }, []);
  useEffect(() => {
    setOpen(false);
  }, [epoch]);
  useEffect(() => {
    if (!goalRequest) return;
    if (visible && validWorkGoal(goalRequest)) {
      setGoalNotice(false);
      setOpen(true);
    } else {
      if (visible) setGoalNotice(true);
      acknowledgeGoal();
    }
  }, [goalRequest, visible, onGoalHandled]);
  return (
    <div className="agent-entry">
      {visible && goalNotice && (
        <p role="status">
          {t(
            "The handoff goal expired or is no longer available. Select and review a new voice snapshot; no work was started.",
            "移交目标已到期或不可用，请选择并审阅新的语音快照；未开始工作。",
          )}
        </p>
      )}
      <button
        type="button"
        className="secondary"
        disabled={!access.available}
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
          : access.available
            ? t(
                "Private details hidden · status and stop controls available",
                "私人详情已隐藏 · 可查看状态并停止工作",
              )
            : t(
                "Owner sign-in and a current connection required",
                "需要本人登录且连接有效",
              )}
      </small>
      {open && access.available && (
        <Modal
          title={t("Work tasks", "工作任务")}
          closeLabel={t("Close", "关闭")}
          onClose={() => setOpen(false)}
          wide
        >
          {visible ? (
            <RunWorkspace
              key={epoch}
              t={t}
              fence={fence.current}
              epoch={epoch}
              initialGoal={goalRequest}
              onGoalHandled={acknowledgeGoal}
              onReviewBrowserJob={
                onReviewBrowserJob
                  ? (id) => {
                      setOpen(false);
                      onReviewBrowserJob(id);
                    }
                  : undefined
              }
              onReviewConnectorIntent={
                onReviewConnectorIntent
                  ? (id) => {
                      setOpen(false);
                      onReviewConnectorIntent(id);
                    }
                  : undefined
              }
              onReviewProposal={
                onReviewProposal
                  ? (id) => {
                      setOpen(false);
                      onReviewProposal(id);
                    }
                  : undefined
              }
            />
          ) : (
            <RunMetadataPanel
              key={epoch}
              t={t}
              fence={fence.current}
              epoch={epoch}
            />
          )}
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
  initialGoal,
  onGoalHandled,
  onReviewBrowserJob,
  onReviewConnectorIntent,
}: {
  t: Translate;
  fence: ResponseFence;
  epoch: number;
  onReviewProposal?: (id: string) => void;
  initialGoal?: WorkGoalRequest | null;
  onGoalHandled?: () => void;
  onReviewBrowserJob?: (id: string) => void;
  onReviewConnectorIntent?: (id: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null),
    [compose, setCompose] = useState(false);
  const [detailGeneration, setDetailGeneration] = useState(0);
  const [showSearch, setShowSearch] = useState(false);
  const [detailRefreshing, setDetailRefreshing] = useState(false);
  const detailRefreshToken = useRef(0);
  const [composeGoal, setComposeGoal] = useState<WorkGoalRequest | null>(null);
  const [expiredGoal, setExpiredGoal] = useState(false);
  const [pendingGoal, setPendingGoal] = useState<WorkGoalRequest | null>(null);
  const lastGoal = useRef<string | null>(null);
  const [navigate, setNavigate] = useState<{
    id: string | null;
    compose: boolean;
    search?: boolean;
    proposal?: string;
    browserJob?: string;
    connectorIntent?: string;
    goal?: WorkGoalRequest;
  } | null>(null);
  const guard = useDraftState();
  const { value, fresh, error, loading, reload } = useAgentRuns(
    fence,
    selected,
    epoch,
  );
  useEffect(() => {
    if (!fresh) return;
    if (!validWorkGoal(initialGoal)) {
      if (initialGoal) {
        setExpiredGoal(true);
        onGoalHandled?.();
      }
      return;
    }
    if (initialGoal!.id === lastGoal.current) return;
    lastGoal.current = initialGoal!.id;
    if (guard.busy || guard.dirty) setPendingGoal(initialGoal!);
    else commit({ id: selected, compose: true, goal: initialGoal! });
    onGoalHandled?.();
  }, [initialGoal, onGoalHandled, guard.busy, guard.dirty, selected, fresh]);
  useEffect(() => {
    if (!pendingGoal?.voiceOrigin) return;
    const timer = setTimeout(
      () => {
        setPendingGoal(null);
        setExpiredGoal(true);
      },
      Math.max(0, Date.parse(pendingGoal.voiceOrigin.expires_at) - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [pendingGoal]);
  function go(next: {
    id: string | null;
    compose: boolean;
    search?: boolean;
    proposal?: string;
    browserJob?: string;
    connectorIntent?: string;
    goal?: WorkGoalRequest;
  }) {
    if (
      !fresh &&
      (next.proposal ||
        next.browserJob ||
        next.connectorIntent ||
        next.compose ||
        next.search)
    )
      return;
    if (guard.busy) return;
    if (guard.dirty) setNavigate(next);
    else commit(next);
  }
  function commit(next: {
    id: string | null;
    compose: boolean;
    search?: boolean;
    proposal?: string;
    browserJob?: string;
    connectorIntent?: string;
    goal?: WorkGoalRequest;
  }) {
    if (
      !fresh &&
      (next.proposal ||
        next.browserJob ||
        next.connectorIntent ||
        next.compose ||
        next.search)
    )
      return;
    if (next.goal && !validWorkGoal(next.goal)) {
      setNavigate(null);
      setExpiredGoal(true);
      return;
    }
    setExpiredGoal(false);
    setNavigate(null);
    setDetailGeneration((x) => x + 1);
    if (next.proposal) {
      onReviewProposal?.(next.proposal);
      return;
    }
    if (next.browserJob) {
      onReviewBrowserJob?.(next.browserJob);
      return;
    }
    if (next.connectorIntent) {
      onReviewConnectorIntent?.(next.connectorIntent);
      return;
    }
    // Reopening an already selected search hit must refresh its version before
    // controls become usable, even though the selected ID itself did not change.
    const refreshToken = ++detailRefreshToken.current;
    if (showSearch && !next.search && next.id && next.id === selected) {
      setDetailRefreshing(true);
      void reload(true).finally(() => {
        if (refreshToken === detailRefreshToken.current && fence.accepts(epoch))
          setDetailRefreshing(false);
      });
    } else setDetailRefreshing(false);
    setShowSearch(next.search === true);
    setComposeGoal(next.goal ?? null);
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
          type="button"
          className="secondary"
          disabled={!fresh || guard.busy}
          aria-pressed={showSearch}
          onClick={() =>
            go({ id: selected, compose: false, search: !showSearch })
          }
        >
          {showSearch
            ? t("Back to work", "返回工作")
            : t("Find saved work", "查找已保存工作")}
        </button>
        <button
          className="primary"
          disabled={!fresh || !value?.scope || guard.busy}
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
      {value && !fresh && (
        <p className="agent-notice" role="status">
          {t(
            "Current work could not be refreshed. Your draft and exact retry data are preserved, but actions and linked reviews stay disabled until a fresh response arrives.",
            "未能刷新当前工作。草稿与同一请求的重试资料已保留，但收到最新响应前，操作及关联审阅保持停用。",
          )}
        </p>
      )}
      {expiredGoal && (
        <p role="status">
          {t(
            "The voice goal expired while waiting. Your existing draft is unchanged. Select and review a new snapshot.",
            "等待期间语音目标已到期，现有草稿保持不变。请重新选择并审阅快照。",
          )}
        </p>
      )}
      {pendingGoal && (
        <div className="agent-notice" role="status">
          <p>
            {t(
              "A goal from chat is ready. Your current draft stays here until you choose to use it.",
              "聊天中的目标已准备好。在您选择使用前，会保留当前草稿。",
            )}
          </p>
          <button
            className="secondary"
            disabled={!fresh || guard.busy}
            onClick={() => {
              go({ id: selected, compose: true, goal: pendingGoal });
              setPendingGoal(null);
            }}
          >
            {t("Use the goal from chat", "使用聊天中的目标")}
          </button>
          <button className="secondary" onClick={() => setPendingGoal(null)}>
            {t("Dismiss", "关闭")}
          </button>
        </div>
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
            <button
              className="secondary"
              disabled={!fresh || guard.busy}
              onClick={() => commit(navigate)}
            >
              {t("Discard and continue", "放弃并继续")}
            </button>
          </div>
        </div>
      )}
      {showSearch && (
        <WorkSearchPanel
          t={t}
          fence={fence}
          epoch={epoch}
          fresh={fresh}
          onOpenRun={(id) => go({ id, compose: false })}
        />
      )}
      {value && !showSearch && (
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
                fresh={fresh && !detailRefreshing}
                onChanged={() => void reload(true)}
                onReviewProposal={
                  onReviewProposal
                    ? (proposal) =>
                        go({ id: selected, compose: false, proposal })
                    : undefined
                }
                onReviewBrowserJob={
                  onReviewBrowserJob
                    ? (browserJob) =>
                        go({ id: selected, compose: false, browserJob })
                    : undefined
                }
                onReviewConnectorIntent={
                  onReviewConnectorIntent
                    ? (connectorIntent) =>
                        go({ id: selected, compose: false, connectorIntent })
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
      {compose && !showSearch && value?.scope && (
        <RunComposer
          key={detailGeneration}
          t={t}
          scope={value.scope}
          fence={fence}
          fresh={fresh}
          initialGoal={composeGoal?.text}
          voiceOrigin={composeGoal?.voiceOrigin}
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
