import { useEffect, useRef, useState } from "react";
import { Globe2 } from "lucide-react";
import { Modal } from "../../components/Dialogs";
import { useDraftGuard } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import { useWorkspace } from "../WorkspaceContext";
import { personalContextVisible } from "../personal/types";
import { ResponseFence } from "../personal/responseFence";
import { usePrivateMutation } from "../personal/usePrivateMutation";
import type { PrivateMutation } from "../personal/usePrivateMutation";
import { BrowserJobDetail } from "./BrowserJobDetail";
import {
  browserError,
  browserState,
  browserLimit,
  browserSourceLabel,
} from "./labels";
import {
  browserReady,
  browserReviewable,
  browserSelection,
  catalogUrl,
} from "./types";
import type { BrowserJob, BrowserObservation } from "./types";
import { useBrowserData } from "./useBrowserData";
import "./browser.css";

function Recovery({
  mutation,
  t,
  visible,
}: {
  mutation: PrivateMutation;
  t: Translate;
  visible: boolean;
}) {
  if (!visible) return null;
  return (
    <>
      {!!mutation.error && (
        <p className="error-message" role="alert">
          {browserError(mutation.error, t)}
        </p>
      )}
      {mutation.pending && (
        <div className="browser-warning" role="status">
          <p>
            {t(
              "The response is unknown. Check the saved job first. Recovery sends the same request ID, never a newly approved action. Closing this panel removes its local retry data; saved jobs remain on the server.",
              "响应未知，请先检查已保存作业。恢复只发送相同请求 ID，不会新批准另一次动作。关闭面板会清除本地重试资料，服务端作业仍保留。",
            )}
          </p>
          <button
            className="secondary"
            type="button"
            disabled={mutation.busy}
            onClick={() => void mutation.retry()}
          >
            {t("Recover the same request", "恢复同一请求")}
          </button>
        </div>
      )}
    </>
  );
}

function BrowserWorkspace({
  t,
  identity,
  available,
  privateVisible,
  concealed,
  initialJobId,
  onEffectChanged,
}: {
  t: Translate;
  identity: string;
  available: boolean;
  privateVisible: boolean;
  concealed: boolean;
  initialJobId: string | null;
  onEffectChanged?: (jobId: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(initialJobId);
  const lastRequested = useRef(initialJobId);
  const [requestedReview, setRequestedReview] = useState<string | null>(null);
  const [switchTo, setSwitchTo] = useState<{ id: string | null } | null>(null);
  const [sourceId, setSourceId] = useState("");
  const [pages, setPages] = useState<(string | null)[]>([null]);
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [publicOnly, setPublicOnly] = useState(false);
  const [observation, setObservation] = useState<{
    value: BrowserObservation;
    identity: string;
  } | null>(null);
  const [notice, setNotice] = useState("");
  const [downloadError, setDownloadError] = useState<unknown>(null);
  const mutation = usePrivateMutation();
  const cancelMutation = usePrivateMutation();
  const verificationMutation = usePrivateMutation();
  const [downloading, setDownloading] = useState(false);
  const downloadActive = useRef(false);
  const alive = useRef(true);
  const fence = useRef(new ResponseFence());
  fence.current.update(
    `${identity}:${selected ?? "new"}`,
    privateVisible && available,
  );
  const epoch = fence.current.version;
  const metadataFence = useRef(new ResponseFence());
  metadataFence.current.update(`${identity}:${selected ?? "new"}`, available);
  const data = useBrowserData(
    true,
    identity,
    available,
    privateVisible,
    selected,
    pages[pages.length - 1],
  );
  const snapshot = data.snapshot;
  const visible = privateVisible && available && data.fresh;
  const ready = browserReady(snapshot?.capabilities ?? null, visible);
  const locked = mutation.busy || mutation.pending || downloading;
  const checking =
    verificationMutation.busy || verificationMutation.pending || downloading;
  const dirty = !!title.trim() || !!note.trim() || !!observation || publicOnly;
  const formDirty = !!title.trim() || !!note.trim() || publicOnly;
  const currentObservation =
    observation && observation.identity === `${identity}:${selected ?? "new"}`
      ? observation.value
      : null;
  const job = snapshot?.detail ?? null;
  useEffect(() => {
    alive.current = true;
    const invalidate = () => {
      fence.current.update("session-changing", false);
      metadataFence.current.update("session-changing", false);
    };
    window.addEventListener("desk:session", invalidate);
    return () => {
      alive.current = false;
      invalidate();
      window.removeEventListener("desk:session", invalidate);
    };
  }, []);
  useDraftGuard(
    dirty ||
      mutation.pending ||
      cancelMutation.pending ||
      verificationMutation.pending,
    mutation.busy ||
      cancelMutation.busy ||
      verificationMutation.busy ||
      downloading,
  );
  useEffect(() => {
    setObservation(null);
    setTitle("");
    setNote("");
    setPublicOnly(false);
    setSwitchTo(null);
  }, [identity, selected, concealed]);
  useEffect(() => {
    setNotice("");
    setDownloadError(null);
    mutation.clear();
    verificationMutation.clear();
    // A privacy/session transition discards retry payloads and their callbacks.
    // Offline masks the same unsent draft; explicit hide/session changes clear it.
    // It never cancels a dispatched server-side operation or claims rollback.
  }, [epoch]);
  useEffect(() => {
    cancelMutation.clear();
  }, [identity, available]);
  useEffect(() => {
    if (initialJobId !== lastRequested.current) {
      lastRequested.current = initialJobId;
      if (initialJobId) setRequestedReview(initialJobId);
    }
  }, [initialJobId]);
  useEffect(() => {
    const first = snapshot?.capabilities.sources[0]?.id;
    if (
      first &&
      !snapshot?.capabilities.sources.some((source) => source.id === sourceId)
    )
      setSourceId(first);
  }, [snapshot?.capabilities, sourceId]);
  function changed(id: string) {
    onEffectChanged?.(id);
    window.dispatchEvent(new Event("desk:browser-jobs"));
    window.dispatchEvent(new Event("desk:agent-runs"));
    void data.reload();
  }
  function choose(next: string | null) {
    const action = browserSelection(
      selected,
      next,
      dirty,
      locked || checking || cancelMutation.busy || cancelMutation.pending,
    );
    if (action === "confirm") setSwitchTo({ id: next });
    if (action === "switch") setSelected(next);
  }
  async function observe() {
    if (
      !ready ||
      locked ||
      !snapshot?.capabilities.sources.some((source) => source.id === sourceId)
    )
      return;
    const token = fence.current.capture();
    setNotice("");
    await mutation.run<{ observation: BrowserObservation }>(
      "/browser/observations",
      { source_id: sourceId, public_only: true },
      (result) => {
        if (!fence.current.accepts(token)) return;
        setObservation({
          value: result.observation,
          identity: `${identity}:${selected ?? "new"}`,
        });
        setTitle("");
        setNote("");
        setPublicOnly(false);
      },
    );
  }
  async function prepare(event: React.FormEvent) {
    event.preventDefault();
    if (!ready || locked || !currentObservation || !publicOnly || !title.trim())
      return;
    const token = fence.current.capture();
    await mutation.run<{ job: BrowserJob }>(
      "/browser/jobs",
      {
        observation_id: currentObservation.id,
        title,
        note,
        public_only: true,
      },
      (result) => {
        if (!fence.current.accepts(token)) return;
        setSelected(result.job.id);
        changed(result.job.id);
      },
    );
  }
  async function approve() {
    if (!job || locked || !browserReviewable(job, ready, Date.now())) return;
    const token = fence.current.capture();
    const id = job.id;
    await mutation.run(
      `/browser/jobs/${encodeURIComponent(id)}/approve`,
      {
        expected_version: job.version,
        intent_hash: job.intent_hash,
        public_only: true,
      },
      () => {
        if (!fence.current.accepts(token)) return;
        setNotice(
          t(
            "Approval recorded. Follow the job status; approval is not evidence of a completed export.",
            "批准已记录，请查看作业状态；批准不代表导出已完成。",
          ),
        );
        changed(id);
      },
    );
  }
  async function cancel() {
    if (
      !job ||
      !available ||
      !data.fresh ||
      cancelMutation.busy ||
      cancelMutation.pending
    )
      return;
    const token = metadataFence.current.capture();
    const id = job.id;
    await cancelMutation.run(
      `/browser/jobs/${encodeURIComponent(id)}/cancel`,
      {},
      () => {
        if (!metadataFence.current.accepts(token)) return;
        setNotice(
          t(
            "Cancellation requested. Check the final outcome; existing exports are not deleted.",
            "已请求取消，请检查最终结果；已有导出不会删除。",
          ),
        );
        changed(id);
      },
    );
  }
  async function verify() {
    if (!job || !visible || checking) return;
    const token = fence.current.capture();
    const id = job.id;
    await verificationMutation.run(
      `/browser/jobs/${encodeURIComponent(id)}/reconcile`,
      {},
      () => {
        if (!fence.current.accepts(token)) return;
        setNotice(
          t(
            "Read-only verification returned. Inspect the recorded evidence below.",
            "只读核验已返回，请检查下方记录证据。",
          ),
        );
        changed(id);
      },
    );
  }
  async function download() {
    if (!job || !visible || checking || downloadActive.current) return;
    const token = fence.current.capture();
    downloadActive.current = true;
    setDownloading(true);
    setDownloadError(null);
    try {
      const { downloadBrowserExport } = await import("./download");
      await downloadBrowserExport(
        job,
        () => alive.current && fence.current.accepts(token),
      );
    } catch (error) {
      if (alive.current && fence.current.accepts(token))
        setDownloadError(error);
    } finally {
      downloadActive.current = false;
      if (alive.current) setDownloading(false);
    }
  }
  return (
    <div className="browser-workflow">
      <p>
        {t(
          "Read one catalogued public source, review an exact brief, then approve a single StackEdit edit and Markdown export. This is an experimental, bounded browser workflow.",
          "读取一项目录内公开来源，核对完整简报，再批准一次 StackEdit 编辑与 Markdown 导出。这是实验性受限浏览器流程。",
        )}
      </p>
      <div className="browser-status" role="status">
        <strong>
          {ready
            ? t(
                "Runtime reports ready · experimental",
                "运行环境报告就绪 · 实验性",
              )
            : t("New browser work is not available", "暂不能启动浏览器工作")}
        </strong>
        {snapshot?.capabilities.reason && (
          <p>
            {browserError({ code: snapshot.capabilities.reason }, t)}{" "}
            <code>{snapshot.capabilities.reason}</code>
          </p>
        )}
        <p>
          {t(
            "Readiness is not a completed live-app acceptance test. Source reads and exported bytes must be observed for each job. No general desktop control is provided.",
            "就绪状态不是实际应用验收已通过。每项作业都需实际观察来源并核验导出字节；不提供通用桌面控制。",
          )}
        </p>
        {snapshot && (
          <small>
            {t("Network boundary: ", "网络边界：")}
            {snapshot.capabilities.network_boundary}
            {t(
              ". Browser routing is not a full OS/network sandbox. Public or synthetic text only; no login, private data, sync or publishing.",
              "。浏览器路由限制不是完整系统／网络沙箱。仅使用公开或虚构文字，不登录、不处理私人数据、不同步或发布。",
            )}
          </small>
        )}
      </div>
      {(!available || !privateVisible) && (
        <p role="status">
          {t(
            "Private details are hidden while this view is offline, stale, signed out or privacy-hidden. Only current owner-visible stop controls can remain available.",
            "离线、状态过时、退出登录或隐私隐藏时，私人详情不显示。仅当前拥有者可用的停止控制会保留。",
          )}
        </p>
      )}
      {!!data.error && (
        <p className="error-message" role="alert">
          {browserError(data.error, t)}
        </p>
      )}
      {requestedReview && visible && (
        <div className="browser-warning" role="status">
          <p>
            {t(
              "Another work task requested a browser review. Your current draft stays here until you choose to switch.",
              "另一项工作请求核对浏览器操作。切换前会保留当前草稿。",
            )}
          </p>
          <button
            type="button"
            className="secondary"
            disabled={
              locked ||
              checking ||
              cancelMutation.busy ||
              cancelMutation.pending
            }
            onClick={() => {
              choose(requestedReview);
              setRequestedReview(null);
            }}
          >
            {t("Open requested review", "打开请求的核对")}
          </button>
        </div>
      )}
      {selected && !snapshot && available && (
        <button
          type="button"
          className="secondary"
          disabled={
            locked || checking || cancelMutation.busy || cancelMutation.pending
          }
          onClick={() => choose(null)}
        >
          {t("Return to source catalog", "返回来源目录")}
        </button>
      )}
      <button
        type="button"
        className="text-button"
        disabled={!available || data.loading}
        onClick={() => void data.reload()}
      >
        {data.loading
          ? t("Refreshing…", "正在刷新…")
          : t("Refresh capability and status", "刷新能力与状态")}
      </button>
      {snapshot && (
        <label className="field">
          {t("Workflow", "流程")}
          <select
            value={selected ?? ""}
            disabled={
              locked ||
              checking ||
              cancelMutation.busy ||
              cancelMutation.pending
            }
            onChange={(event) => choose(event.target.value || null)}
          >
            <option value="">{t("New source brief", "新来源简报")}</option>
            {selected &&
              !snapshot.jobs.some((item) => item.id === selected) && (
                <option value={selected}>
                  {t("Selected job", "所选作业")}
                </option>
              )}
            {snapshot.jobs.map((item) => (
              <option key={item.id} value={item.id}>
                {visible
                  ? (item.request?.title ?? item.id)
                  : t("Private job", "私人作业")}{" "}
                · {browserState(item.state, t)}
              </option>
            ))}
          </select>
        </label>
      )}
      {snapshot && (pages.length > 1 || snapshot.nextCursor) && (
        <div className="workspace-inline-actions">
          <small>
            {t("Saved jobs page ", "已保存作业页 ")}
            {pages.length} · {snapshot.jobs.length} {t("shown", "项")}
          </small>
          <button
            className="text-button"
            type="button"
            disabled={
              pages.length <= 1 ||
              locked ||
              checking ||
              cancelMutation.busy ||
              cancelMutation.pending
            }
            onClick={() => setPages((old) => old.slice(0, -1))}
          >
            {t("Previous page", "上一页")}
          </button>
          <button
            className="text-button"
            type="button"
            disabled={
              !snapshot.nextCursor ||
              locked ||
              checking ||
              cancelMutation.busy ||
              cancelMutation.pending
            }
            onClick={() => {
              if (snapshot.nextCursor)
                setPages((old) => [...old, snapshot.nextCursor]);
            }}
          >
            {t("Next page", "下一页")}
          </button>
        </div>
      )}
      {switchTo && visible && (
        <div className="browser-warning" role="alert">
          <p>
            {t(
              "Discard this unsaved source brief before switching?",
              "切换前放弃尚未保存的来源简报？",
            )}
          </p>
          <div className="workspace-inline-actions">
            <button className="secondary" onClick={() => setSwitchTo(null)}>
              {t("Keep editing", "继续编辑")}
            </button>
            <button
              className="secondary"
              onClick={() => {
                setSelected(switchTo.id);
                setSwitchTo(null);
              }}
            >
              {t("Discard and switch", "放弃并切换")}
            </button>
          </div>
        </div>
      )}
      {!selected && visible && snapshot && (
        <>
          <label className="field">
            {t("Fixed public source catalog", "固定公开来源目录")}
            <select
              value={sourceId}
              disabled={locked || !ready || formDirty}
              onChange={(event) => {
                setSourceId(event.target.value);
                setObservation(null);
                setPublicOnly(false);
              }}
            >
              {snapshot.capabilities.sources.map((source) => (
                <option key={source.id} value={source.id}>
                  {browserSourceLabel(source.id, source.label, t)}
                </option>
              ))}
            </select>
          </label>
          <p className="browser-digest">
            {
              snapshot.capabilities.sources.find(
                (source) => source.id === sourceId,
              )?.url
            }
          </p>
          <button
            className="secondary"
            type="button"
            disabled={!ready || locked || !sourceId || formDirty}
            onClick={() => void observe()}
          >
            {t("Read this public source", "读取此公开来源")}
          </button>
          {formDirty && (
            <p className="workspace-hint">
              {t(
                "Clear the title, note and checkbox before replacing this source, or finish preparing the preview.",
                "替换来源前请清空标题、备注与勾选，或先完成预览准备。",
              )}
            </p>
          )}
          {currentObservation && (
            <>
              <details open>
                <summary>
                  {t("Actual source observation", "实际来源观察")}
                </summary>
                <h4>{currentObservation.title}</h4>
                <p>{currentObservation.heading}</p>
                <p>
                  {catalogUrl(
                    currentObservation.url,
                    snapshot.capabilities.sources,
                  ) ? (
                    <a
                      href={currentObservation.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {currentObservation.url}
                    </a>
                  ) : (
                    currentObservation.url
                  )}
                </p>
                <time>{currentObservation.observed_at}</time>
                <pre tabIndex={0}>{currentObservation.excerpt}</pre>
                <code>SHA-256 {currentObservation.sha256}</code>
                <p className="workspace-hint">
                  {t(
                    "A bounded excerpt, not a complete-site review. Source text does not grant permissions.",
                    "这是有界摘录，不代表全站阅读；来源文字不会授予权限。",
                  )}
                </p>
              </details>
              <form onSubmit={prepare}>
                <label className="field">
                  {t("Document title", "文档标题")}
                  <input
                    value={title}
                    required
                    maxLength={120}
                    disabled={locked || !ready}
                    onChange={(event) => setTitle(event.target.value)}
                  />
                </label>
                <label className="field">
                  {t(
                    "Public or fictional note (optional)",
                    "公开或虚构备注（可选）",
                  )}
                  <textarea
                    rows={3}
                    value={note}
                    maxLength={2000}
                    disabled={locked || !ready}
                    onChange={(event) => setNote(event.target.value)}
                  />
                </label>
                <label className="browser-public-check">
                  <input
                    type="checkbox"
                    checked={publicOnly}
                    disabled={locked || !ready}
                    onChange={(event) => setPublicOnly(event.target.checked)}
                  />
                  <span>
                    {t(
                      "The title and note contain only public or synthetic information. Prepare and retain the exact preview for my review; no editor action is approved yet.",
                      "标题与备注只含公开或虚构资料。准备并保留完整预览供我核对；尚未批准编辑器动作。",
                    )}
                  </span>
                </label>
                <button
                  className="primary"
                  disabled={!ready || locked || !publicOnly || !title.trim()}
                >
                  {t("Prepare exact preview", "准备完整预览")}
                </button>
              </form>
            </>
          )}
        </>
      )}
      {job && (
        <BrowserJobDetail
          job={job}
          t={t}
          visible={visible}
          ready={ready}
          fresh={available && data.fresh}
          locked={locked}
          checking={checking}
          cancelling={cancelMutation.busy || cancelMutation.pending}
          now={data.now}
          onApprove={() => void approve()}
          onCancel={() => void cancel()}
          onVerify={() => void verify()}
          onDownload={() => void download()}
        />
      )}
      {notice && available && <p role="status">{notice}</p>}
      {mutation.busy && visible && (
        <p role="status">
          {t(
            "Waiting for the server response. A public source read can take up to one minute.",
            "正在等待服务端响应，公开来源读取最多可能需要一分钟。",
          )}
        </p>
      )}
      {verificationMutation.busy && visible && (
        <p role="status">
          {t(
            "Reading existing export evidence; no editor action is being repeated.",
            "正在读取已有导出证据，不会重复编辑器动作。",
          )}
        </p>
      )}
      <Recovery mutation={mutation} t={t} visible={visible} />
      <Recovery mutation={cancelMutation} t={t} visible={available} />
      <Recovery mutation={verificationMutation} t={t} visible={visible} />
      {!!downloadError && visible && (
        <p role="alert" className="error-message">
          {browserError(downloadError, t)}
        </p>
      )}
      {snapshot && (
        <details>
          <summary>{t("Workflow limits", "流程限制")}</summary>
          <dl className="browser-facts">
            {Object.entries(snapshot.capabilities.limits).map(
              ([name, value]) => (
                <span style={{ display: "contents" }} key={name}>
                  <dt>{browserLimit(name, t)}</dt>
                  <dd>{String(value)}</dd>
                </span>
              ),
            )}
          </dl>
          <p>
            {t(
              "No arbitrary URLs, account sign-in, personal browser profile, model call or repeated uncertain write. Closing this panel does not stop an approved server job. Use Cancel to request a stop.",
              "不接受任意网址，不登录账号，不使用个人浏览器资料，不调用模型，也不重复结果未知的写入。关闭面板不会停止服务端已批准作业，请使用取消请求停止。",
            )}
          </p>
        </details>
      )}
    </div>
  );
}

export interface BrowserWorkflowPanelProps {
  t: Translate;
  visibleOverride?: boolean;
  reviewEffectId?: string | null;
  onReviewClosed?: () => void;
  onEffectChanged?: (jobId: string) => void;
}
export function BrowserWorkflowPanel({
  t,
  visibleOverride = true,
  reviewEffectId,
  onReviewClosed,
  onEffectChanged,
}: BrowserWorkflowPanelProps) {
  const { data, offline, stale } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [sessionEpoch, setSessionEpoch] = useState(0);
  const owner = data?.principal.kind === "owner";
  const available = owner && !offline && !stale && visibleOverride;
  const privateVisible = personalContextVisible(
    owner,
    data?.personal_context_visible,
    offline || !visibleOverride,
    stale,
  );
  const identity = `${data?.principal.kind ?? "none"}:${data?.principal.id ?? "none"}:${sessionEpoch}`;
  useEffect(() => {
    const changed = () => setSessionEpoch((epoch) => epoch + 1);
    window.addEventListener("desk:session", changed);
    return () => window.removeEventListener("desk:session", changed);
  }, []);
  useEffect(() => {
    if (reviewEffectId) setOpen(true);
  }, [reviewEffectId]);
  return (
    <div className="browser-workflow-entry">
      <button className="secondary" type="button" onClick={() => setOpen(true)}>
        <Globe2 size={17} /> {t("Browser workflow", "浏览器流程")}
      </button>
      <small>
        {t(
          "Public sources → reviewed Markdown export",
          "公开来源 → 核对后导出 Markdown",
        )}
      </small>
      {open && (
        <Modal
          title={t("Browser workflow", "浏览器流程")}
          closeLabel={t("Close browser workflow", "关闭浏览器流程")}
          wide
          onClose={() => {
            setOpen(false);
            onReviewClosed?.();
          }}
        >
          {!owner ? (
            <p>
              {t(
                "Sign in as the owner to inspect browser work. A paired screen cannot approve this workflow.",
                "请以拥有者身份登录后查看浏览器工作；配对终端不能批准此流程。",
              )}
            </p>
          ) : (
            <BrowserWorkspace
              key={identity}
              t={t}
              identity={identity}
              available={available}
              privateVisible={privateVisible}
              concealed={
                data?.personal_context_visible !== true || !visibleOverride
              }
              initialJobId={reviewEffectId ?? null}
              onEffectChanged={onEffectChanged}
            />
          )}
        </Modal>
      )}
    </div>
  );
}
