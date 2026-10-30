import { useEffect, useRef, useState } from "react";
import { Plug } from "lucide-react";
import { Modal } from "../../components/Dialogs";
import { useDraftGuard } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import { useWorkspace } from "../WorkspaceContext";
import { ResponseFence } from "../personal/responseFence";
import { usePrivateMutation } from "../personal/usePrivateMutation";
import type { PrivateMutation } from "../personal/usePrivateMutation";
import { ConnectorIntentDetail } from "./ConnectorIntentDetail";
import { connectorError, connectorState } from "./labels";
import {
  connectorAccess,
  connectorCancellable,
  connectorId,
  connectorReviewable,
  connectorReviewKey,
  connectorSelection,
} from "./types";
import { useConnectorData } from "./useConnectorData";
import "./connectors.css";

function MutationFeedback({
  mutation,
  t,
  approval,
  canRetry,
  onRetry,
}: {
  mutation: PrivateMutation;
  t: Translate;
  approval: boolean;
  canRetry: boolean;
  onRetry: () => void;
}) {
  return (
    <>
      {!!mutation.error && (
        <p className="error-message" role="alert">
          {connectorError(mutation.error, t)}
        </p>
      )}
      {mutation.busy && (
        <p role="status">
          {approval
            ? t(
                "Waiting for the approval receipt; this is not evidence of a completed call.",
                "正在等待批准回执；这不代表调用已完成。",
              )
            : t("Waiting for the cancellation receipt.", "正在等待取消回执。")}
        </p>
      )}
      {mutation.pending && !mutation.busy && (
        <div className="connector-warning" role="status">
          <p>
            {t(
              "The response is unknown. Refresh saved status first. Any retry keeps the same operation ID and exact request; it does not create a replacement intent. Closing discards only local retry data, and does not stop server work.",
              "响应未知，请先刷新已保存状态。重试会保持同一操作 ID 及完整请求，不会新建替代调用意图。关闭仅清除本地重试资料，不会停止服务端工作。",
            )}
          </p>
          <button
            type="button"
            className="secondary"
            disabled={!canRetry || mutation.busy}
            onClick={onRetry}
          >
            {approval
              ? t("Retry the same exact approval", "重试同一逐项批准")
              : t("Retry the same cancellation", "重试同一取消请求")}
          </button>
        </div>
      )}
    </>
  );
}

function ConnectorWorkspace({
  t,
  fence,
  epoch,
  privateVisible,
  initialIntentId,
}: {
  t: Translate;
  fence: ResponseFence;
  epoch: number;
  privateVisible: boolean;
  initialIntentId: string | null;
}) {
  const [selected, setSelected] = useState<string | null>(initialIntentId);
  const [switchTo, setSwitchTo] = useState<{ id: string | null } | null>(null);
  const [requestedReview, setRequestedReview] = useState<string | null>(null);
  const lastRequested = useRef(initialIntentId);
  const [acknowledgedKey, setAcknowledgedKey] = useState<string | null>(null);
  const [cancelVersion, setCancelVersion] = useState<number | null>(null);
  const [approvalKey, setApprovalKey] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const approval = usePrivateMutation();
  const cancellation = usePrivateMutation();
  const data = useConnectorData(fence, epoch, privateVisible, selected);
  const snapshot = data.snapshot;
  const detail = snapshot?.detail ?? null;
  const metadata =
    snapshot?.rows.find((row) => row.id === selected) ??
    snapshot?.selectedMetadata ??
    null;
  const intent = privateVisible && detail ? detail : metadata;
  const exactKey = detail ? connectorReviewKey(detail) : null;
  const acknowledged = !!exactKey && exactKey === acknowledgedKey;
  const approvalLocked = approval.busy || approval.pending;
  const cancellationLocked = cancellation.busy || cancellation.pending;
  const dirty =
    acknowledged ||
    cancelVersion !== null ||
    approval.pending ||
    cancellation.pending;
  const busy = approval.busy || cancellation.busy;
  const reviewable =
    !!detail &&
    privateVisible &&
    connectorReviewable(
      detail,
      snapshot?.capabilities ?? null,
      data.fresh,
      data.now,
    );
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  useDraftGuard(dirty, busy);
  useEffect(() => {
    if (initialIntentId !== lastRequested.current) {
      lastRequested.current = initialIntentId;
      if (initialIntentId) setRequestedReview(initialIntentId);
    }
  }, [initialIntentId]);
  useEffect(() => {
    // A new version/content can never inherit consent to the preceding preview.
    setAcknowledgedKey(null);
  }, [exactKey]);
  useEffect(() => {
    if (!snapshot) return;
    window.dispatchEvent(new Event("desk:agent-runs"));
  }, [
    snapshot?.rows.map((row) => `${row.id}:${row.version}`).join("|"),
    snapshot?.detail?.version,
  ]);
  function changed(message: string) {
    setNotice(message);
    window.dispatchEvent(new Event("desk:connector-intents"));
    window.dispatchEvent(new Event("desk:agent-runs"));
    void data.reload(true);
  }
  function switchSelection(next: string | null) {
    setSelected(next);
    setAcknowledgedKey(null);
    setApprovalKey(null);
    setCancelVersion(null);
    setNotice("");
    setSwitchTo(null);
    approval.clear();
    cancellation.clear();
  }
  function choose(next: string | null) {
    const action = connectorSelection(selected, next, dirty, busy);
    if (action === "confirm") setSwitchTo({ id: next });
    if (action === "switch") switchSelection(next);
  }
  async function approve() {
    const captured = fence.capture();
    if (
      !alive.current ||
      !fence.accepts(captured) ||
      !detail ||
      !privateVisible ||
      !acknowledged ||
      approvalLocked ||
      cancellationLocked ||
      !connectorReviewable(
        detail,
        snapshot?.capabilities ?? null,
        data.fresh,
        Date.now(),
      )
    )
      return;
    setApprovalKey(connectorReviewKey(detail));
    await approval.run(
      `/connectors/intents/${detail.id}/approve`,
      {
        expected_version: detail.version,
        intent_hash: detail.intent_hash,
        public_only: true,
      },
      () => {
        if (!alive.current || !fence.accepts(captured)) return;
        setAcknowledgedKey(null);
        changed(
          t(
            "Approval recorded. Follow the saved status; a completed call still needs independent outcome verification.",
            "批准已记录。请查看已保存状态；调用完成后仍需独立核验实际结果。",
          ),
        );
      },
    );
  }
  async function cancel() {
    const captured = fence.capture();
    if (
      !alive.current ||
      !fence.accepts(captured) ||
      !intent ||
      !data.fresh ||
      cancellationLocked ||
      cancelVersion !== intent.version ||
      !connectorCancellable(intent)
    )
      return;
    await cancellation.run(
      `/connectors/intents/${intent.id}/cancel?metadata_only=true`,
      {
        expected_version: cancelVersion,
      },
      () => {
        if (!alive.current || !fence.accepts(captured)) return;
        setCancelVersion(null);
        changed(
          t(
            "Cancellation requested. This does not undo an action already sent.",
            "已请求取消；这不会撤销已经发出的动作。",
          ),
        );
      },
    );
  }
  const canRetryApproval =
    !!detail &&
    data.fresh &&
    privateVisible &&
    !cancellationLocked &&
    !detail.cancel_requested &&
    detail.state === "review" &&
    reviewable &&
    exactKey === approvalKey;
  const canRetryCancel =
    !!intent &&
    data.fresh &&
    connectorCancellable(intent) &&
    cancelVersion === intent.version;
  function retry(approveRequest: boolean) {
    if (
      !alive.current ||
      !fence.accepts(epoch) ||
      !(approveRequest ? canRetryApproval : canRetryCancel)
    )
      return;
    void (approveRequest ? approval.retry() : cancellation.retry());
  }
  return (
    <div className="connector-workspace">
      {!privateVisible && (
        <p className="connector-warning" role="status">
          {t(
            "Private content is hidden. Only content-free status and cancellation are loaded. Show private content to inspect destinations, arguments and results or approve a call.",
            "私人内容已隐藏。只读取不含正文的状态及取消操作。显示私人内容后才能查看目标、参数与结果或批准调用。",
          )}
        </p>
      )}
      <p className="workspace-hint">
        {t(
          "Each exact call is reviewed separately, including reads. Closing this panel does not cancel an approved call.",
          "每次完整调用都需分别审阅，包括读取。关闭此面板不会取消已批准调用。",
        )}
      </p>
      <button
        type="button"
        className="secondary"
        disabled={data.loading}
        onClick={() => void data.reload(true)}
      >
        {t("Refresh saved status", "刷新已保存状态")}
      </button>
      {!!data.error && (
        <p role="alert" className="error-message">
          {connectorError(data.error, t)}
        </p>
      )}
      {!data.fresh && (
        <p role="status">
          {data.loading
            ? t("Loading current connector status…", "正在读取连接器当前状态…")
            : t(
                "Current status is unavailable. Actions stay disabled until a fresh response arrives.",
                "当前状态不可用。收到最新响应前操作保持停用。",
              )}
        </p>
      )}
      {privateVisible && snapshot?.capabilities?.tools.length === 0 && (
        <p className="connector-warning">
          {t(
            "No connector tools are configured. Connectors are off by default; an operator must grant an exact endpoint and tool before work can use it.",
            "尚未配置连接器工具。连接器默认关闭；操作人员必须先授予完整端点及工具，工作才能使用。",
          )}
        </p>
      )}
      {snapshot && (
        <label className="field">
          {t("Saved calls (latest 50)", "已保存调用（最近 50 项）")}
          <select
            value={selected ?? ""}
            disabled={busy}
            onChange={(event) => choose(event.target.value || null)}
          >
            <option value="">
              {t("Choose a call to inspect", "选择调用以查看")}
            </option>
            {selected && !snapshot.rows.some((row) => row.id === selected) && (
              <option value={selected}>
                {t("Linked call", "关联调用")}: {selected}
              </option>
            )}
            {snapshot.rows.map((row) => (
              <option key={row.id} value={row.id}>
                {row.id} · {connectorState(row.state, t)}
              </option>
            ))}
          </select>
        </label>
      )}
      {snapshot?.rows.length === 0 && !selected && (
        <p>{t("No saved connector calls.", "尚无已保存连接器调用。")}</p>
      )}
      {selected && snapshot && !intent && (
        <p>
          {t(
            "The selected call is unavailable in the current response. Refresh its saved status.",
            "当前响应中无法获取所选调用，请刷新已保存状态。",
          )}
        </p>
      )}
      {requestedReview && requestedReview !== selected && (
        <div className="connector-warning">
          <p>
            {t(
              "A linked call is ready to open. Current approval choices stay here until you switch.",
              "有一项关联调用可打开。切换前，当前批准选择仍保留在此。",
            )}
          </p>
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={() => {
              choose(requestedReview);
              setRequestedReview(null);
            }}
          >
            {t("Open linked call", "打开关联调用")}
          </button>
        </div>
      )}
      {switchTo && (
        <div className="connector-warning" role="alert">
          <p>
            {t(
              "Discard this local review choice and retry data before switching? Saved calls remain and are not cancelled.",
              "切换前放弃本地审阅选择与重试资料？已保存调用会保留，不会被取消。",
            )}
          </p>
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={() => setSwitchTo(null)}
          >
            {t("Keep reviewing", "继续审阅")}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={() => switchSelection(switchTo.id)}
          >
            {t("Discard and switch", "放弃并切换")}
          </button>
        </div>
      )}
      {intent && (
        <ConnectorIntentDetail
          intent={intent}
          t={t}
          privateVisible={privateVisible}
          fresh={data.fresh}
          reviewable={reviewable}
          acknowledged={acknowledged}
          approvalLocked={approvalLocked}
          cancellationLocked={cancellationLocked}
          onAcknowledge={(checked) =>
            setAcknowledgedKey(checked ? exactKey : null)
          }
          onApprove={() => void approve()}
          onCancel={() => setCancelVersion(intent.version)}
        />
      )}
      {cancelVersion !== null && (
        <div className="connector-warning" role="alert">
          <p>
            {t(
              "Cancel this exact call? Cancellation can stop work that has not been sent, but cannot undo a call already dispatched.",
              "取消此次完整调用？取消可停止尚未发出的工作，但无法撤销已经发出的调用。",
            )}
          </p>
          {intent && cancelVersion !== intent.version && (
            <p>
              {t(
                "The saved version changed. Choose Cancel this call again to review the current version.",
                "已保存版本变化，请再次选择取消此次调用以核对当前版本。",
              )}
            </p>
          )}
          <button
            type="button"
            className="secondary"
            disabled={cancellationLocked}
            onClick={() => setCancelVersion(null)}
          >
            {t("Keep this call", "保留此次调用")}
          </button>
          <button
            type="button"
            className="secondary connector-stop"
            disabled={
              !intent ||
              !data.fresh ||
              cancellationLocked ||
              cancelVersion !== intent.version ||
              !connectorCancellable(intent)
            }
            onClick={() => void cancel()}
          >
            {t("Confirm cancellation", "确认取消")}
          </button>
        </div>
      )}
      <MutationFeedback
        mutation={approval}
        t={t}
        approval
        canRetry={canRetryApproval}
        onRetry={() => retry(true)}
      />
      <MutationFeedback
        mutation={cancellation}
        t={t}
        approval={false}
        canRetry={canRetryCancel}
        onRetry={() => retry(false)}
      />
      {notice && <p role="status">{notice}</p>}
    </div>
  );
}

export interface ConnectorReviewPanelProps {
  t: Translate;
  visibleOverride?: boolean;
  reviewIntentId?: string | null;
  onReviewClosed?: () => void;
}
export function ConnectorReviewPanel({
  t,
  visibleOverride = true,
  reviewIntentId,
  onReviewClosed,
}: ConnectorReviewPanelProps) {
  const { data, offline, stale } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [sessionEpoch, setSessionEpoch] = useState(0);
  const fence = useRef(new ResponseFence());
  const owner = data?.principal.kind === "owner";
  const access = connectorAccess(
    owner,
    !offline && !stale,
    visibleOverride,
    data?.personal_context_visible === true,
  );
  const identity = `${data?.principal.kind ?? "none"}:${data?.principal.id ?? "none"}:${sessionEpoch}:${access.privateVisible}`;
  fence.current.update(identity, access.available && open);
  const epoch = fence.current.version;
  useEffect(() => {
    const invalidate = () => {
      // Fence synchronously before React processes the session-change remount.
      fence.current.update("session-changing", false);
      setSessionEpoch((value) => value + 1);
    };
    window.addEventListener("desk:session", invalidate);
    return () => {
      fence.current.update("unmounted", false);
      window.removeEventListener("desk:session", invalidate);
    };
  }, []);
  useEffect(() => {
    if (connectorId(reviewIntentId)) setOpen(true);
  }, [reviewIntentId]);
  return (
    <div className="connector-entry">
      <button type="button" className="secondary" onClick={() => setOpen(true)}>
        <Plug size={17} /> {t("Connector review", "连接器审阅")}
      </button>
      <small>
        {t("Exact public calls · owner approval", "完整公开调用 · 本人批准")}
      </small>
      {open && (
        <Modal
          title={t("Connector review", "连接器审阅")}
          closeLabel={t("Close connector review", "关闭连接器审阅")}
          wide
          onClose={() => {
            fence.current.update("closed", false);
            setOpen(false);
            onReviewClosed?.();
          }}
        >
          {!owner ? (
            <p>
              {t(
                "Sign in as the owner to review connector calls. Paired screens cannot inspect or approve them.",
                "请以拥有者身份登录以审阅连接器调用。配对终端不能查看或批准。",
              )}
            </p>
          ) : !access.available ? (
            <p role="status">
              {t(
                "Connect to the current owner workspace to inspect or cancel calls. Cached private content and local approval choices have been cleared.",
                "请连接当前拥有者工作空间以查看或取消调用。已清除缓存私人内容及本地批准选择。",
              )}
            </p>
          ) : (
            <ConnectorWorkspace
              key={`${identity}:${epoch}`}
              t={t}
              fence={fence.current}
              epoch={epoch}
              privateVisible={access.privateVisible}
              initialIntentId={
                connectorId(reviewIntentId) ? reviewIntentId : null
              }
            />
          )}
        </Modal>
      )}
    </div>
  );
}
