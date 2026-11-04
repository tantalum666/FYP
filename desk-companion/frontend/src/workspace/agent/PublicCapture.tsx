import { useEffect, useRef, useState } from "react";
import { useDraftGuard } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import type { ResponseFence } from "../personal/responseFence";
import { captureError, captureStateLabel, captureUrl } from "./capturePolicy";
import { usePublicCaptures } from "./usePublicCaptures";
import { CapacityLine } from "./RetainedCapacity";
import { SourcePreview } from "./SourcePreview";
import { CaptureProvenance } from "./CaptureProvenance";
import type { SourceRecord } from "./types";
export function PublicCapture({
  t,
  fence,
  epoch,
  fresh,
  hidden = false,
  historyOnly = false,
  onDraftChange,
  onChanged,
}: {
  t: Translate;
  fence: ResponseFence;
  epoch: number;
  fresh: boolean;
  hidden?: boolean;
  historyOnly?: boolean;
  onDraftChange?: (dirty: boolean) => void;
  onChanged?: () => void;
}) {
  const api = usePublicCaptures(fence, epoch, fresh, hidden);
  const [url, setUrl] = useState(""),
    [label, setLabel] = useState(""),
    [retainRecord, setRetainRecord] = useState(false);
  const [publicOnly, setPublicOnly] = useState(false),
    [retainSnapshot, setRetainSnapshot] = useState(false);
  const [preview, setPreview] = useState<SourceRecord | null>(null),
    [discard, setDiscard] = useState<string | null>(null);
  const mounted = useRef(true),
    freshNow = useRef(fresh);
  freshNow.current = fresh;
  const dirty = !!url || !!label || api.pending.length > 0;
  useDraftGuard(dirty, api.busy);
  useEffect(() => {
    onDraftChange?.(dirty);
  }, [dirty, onDraftChange]);
  useEffect(() => {
    setPublicOnly(false);
    setRetainSnapshot(false);
    setPreview(null);
  }, [api.selected?.id, api.selected?.version, api.review]);
  useEffect(() => {
    mounted.current = true;
    const clear = () => {
      setUrl("");
      setLabel("");
      setRetainRecord(false);
      setPublicOnly(false);
      setRetainSnapshot(false);
      setPreview(null);
      setDiscard(null);
    };
    const events = ["desk:session", "desk:personal-context", "offline"];
    events.forEach((event) => window.addEventListener(event, clear));
    return () => {
      mounted.current = false;
      events.forEach((event) => window.removeEventListener(event, clear));
    };
  }, []);
  const safe = () =>
    mounted.current &&
    freshNow.current &&
    fence.accepts(epoch) &&
    api.available;
  async function prepare() {
    if (!safe()) return;
    if (await api.prepare(url, label, retainRecord)) {
      if (!safe()) return;
      setUrl("");
      setLabel("");
      setRetainRecord(false);
      onChanged?.();
    }
  }
  function reopen(id: string) {
    if (!safe() || api.busy) return;
    if (dirty) {
      setDiscard(id);
      return;
    }
    void api.read(id);
  }
  const selected = api.selected,
    review = api.review;
  const locked = !safe() || api.busy;
  return (
    <details className="agent-upload agent-capture">
      <summary>
        {hidden
          ? t("Public capture status and stop", "公开采集状态与停止")
          : historyOnly
            ? t("Saved public-page captures", "已保存的公开页面采集")
            : t("Add web page", "添加网页")}
      </summary>
      <p className="workspace-hint">
        {t(
          "200 lifetime capture records, including cancelled or failed reviews. Sources share 100 slots / 64 MiB, including unknown reservations. This version has no capture/source deletion or capacity reclamation.",
          "终身最多200条采集记录，包括取消或失败的审阅。来源共用100个位置／64 MiB，包括未知保留位置。本版不支持采集／来源删除或容量回收。",
        )}
      </p>
      {!api.enabled && !hidden && (
        <p>
          {t(
            "New public captures are disabled or unavailable. Existing history can still be inspected and stopped.",
            "新公开采集已禁用或不可用，仍可检查和停止已有记录。",
          )}
        </p>
      )}
      {!hidden && !historyOnly && api.enabled && (
        <div>
          <p>
            {t(
              "Enter one public HTTPS URL with a path, no query, fragment, login or private token. URL and label stay in memory until you save the review. Preparing saves a permanent local record but makes no website or DNS request.",
              "输入带路径的公开HTTPS网址，不含查询、片段、登录或私人令牌。保存审阅前，网址与标签仅在内存中。准备步骤会保存永久本地记录，但不请求网站或DNS。",
            )}
          </p>
          <label>
            {t("Exact public URL", "确切公开网址")}
            <input
              type="text"
              autoComplete="off"
              spellCheck={false}
              maxLength={1024}
              value={url}
              disabled={locked || api.pending.length > 0}
              onChange={(e) => {
                if (safe()) {
                  setUrl(e.target.value);
                  setRetainRecord(false);
                }
              }}
            />
          </label>
          <label>
            {t("Local label (optional)", "本地标签（可选）")}
            <input
              type="text"
              autoComplete="off"
              maxLength={120}
              value={label}
              disabled={locked || api.pending.length > 0}
              onChange={(e) => {
                if (safe()) {
                  setLabel(e.target.value);
                  setRetainRecord(false);
                }
              }}
            />
          </label>
          <label className="agent-check">
            <input
              type="checkbox"
              checked={retainRecord}
              disabled={locked || api.pending.length > 0}
              onChange={(e) => {
                if (safe()) setRetainRecord(e.target.checked);
              }}
            />
            {t(
              "Retain this URL, label and review record locally, even if I cancel",
              "即使取消，也在本地保留此网址、标签及审阅记录",
            )}
          </label>
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="secondary"
              disabled={
                locked ||
                !retainRecord ||
                !captureUrl(url) ||
                api.pending.length > 0
              }
              onClick={() => void prepare()}
            >
              {t("Save local review · no GET", "保存本地审阅 · 不发GET")}
            </button>
            <button
              type="button"
              className="secondary"
              disabled={locked || api.pending.length > 0}
              onClick={() => {
                if (safe()) {
                  setUrl("");
                  setLabel("");
                  setRetainRecord(false);
                }
              }}
            >
              {t("Clear unsent draft", "清除未发送草稿")}
            </button>
          </div>
        </div>
      )}
      <button
        type="button"
        className="secondary"
        disabled={locked}
        onClick={() => {
          if (safe()) void api.read();
        }}
      >
        {t("List retained captures", "列出保留的采集")}
      </button>
      <p className="workspace-hint">
        {t(
          "Reopening reads saved status only. It does not contact the website or verify source bytes. Another new capture is another request and may reserve another source.",
          "重新打开只读取保存状态，不联系网站或核验来源字节。另建采集代表另一个请求，可能再占一个来源位置。",
        )}
      </p>
      <ul className="agent-capture-list">
        {api.records.map((item) => (
          <li key={item.id}>
            <span>
              {hidden ? item.id : item.label || item.display_name} ·{" "}
              {captureStateLabel(item.state, t)}
            </span>
            <button
              type="button"
              className="secondary"
              disabled={locked}
              onClick={() => reopen(item.id)}
            >
              {t("Reopen", "重新打开")}
            </button>
          </li>
        ))}
      </ul>
      {api.cursor && (
        <button
          type="button"
          className="secondary"
          disabled={locked}
          onClick={() => {
            if (safe()) void api.read(null, api.cursor);
          }}
        >
          {t("Next history page", "下一页历史")}
        </button>
      )}
      {discard && (
        <div role="alert" className="agent-notice">
          <p>
            {t(
              "Your unsent draft or original retry data is still here. Clear the unsent draft first; resolve an unknown operation before switching records. Closing never cancels an already sent request.",
              "未发送草稿或原操作重试资料仍保留。请先清除未发送草稿；结果未知的操作需先恢复，再切换记录。关闭不会取消已发送请求。",
            )}
          </p>
          <button
            type="button"
            className="secondary"
            onClick={() => setDiscard(null)}
          >
            {t("Keep this draft", "保留此草稿")}
          </button>
        </div>
      )}
      {selected && (
        <section className="agent-notice">
          <strong>{captureStateLabel(selected.state, t)}</strong>
          <small>
            {selected.id} · v{selected.version} · {selected.updated_at}
          </small>
          {!hidden && (
            <>
              <p className="agent-text">{selected.url}</p>
              <p>
                {selected.label} · {selected.display_name}
              </p>
              <p>
                {t("Source status", "来源状态")}:{" "}
                {selected.source_status === "verified"
                  ? t("Verified retained bytes", "保留字节已核验")
                  : selected.source_status === "unknown" ||
                      selected.source_status === undefined
                    ? t("Unknown retained reservation", "保留位置状态未知")
                    : t(
                        "No recorded source reservation",
                        "无记录的来源保留位置",
                      )}
              </p>
            </>
          )}
          <p>
            {selected.dispatch_possible
              ? t(
                  "The website request may already have been sent. Stop cannot recall traffic or delete retained bytes.",
                  "网站请求可能已发出，停止无法撤回流量或删除已保留字节。",
                )
              : t(
                  "No HTTP dispatch is recorded. DNS or connection traffic may still have occurred after approval.",
                  "未记录HTTP发送；批准后仍可能已产生DNS或连接流量。",
                )}
          </p>
          {selected.error_code && (
            <p role="status">
              {captureError({ code: selected.error_code }, t)}{" "}
              <small>{selected.error_code}</small>
            </p>
          )}
          {review && !hidden && (
            <div className="agent-review">
              {!api.reviewReady && (
                <p role="status">
                  {t(
                    "This review has expired or its clock changed. Reopen saved status; old approval cannot continue.",
                    "此审阅已到期或时钟发生变化。请重新打开保存状态；旧批准不能继续。",
                  )}
                </p>
              )}
              <h4>
                {t(
                  "Approve this exact destination and retention",
                  "批准确切目的地与保留范围",
                )}
              </h4>
              <p className="agent-text">{review.url}</p>
              <small>
                {t("Review expires", "审阅到期")}: {review.expires_at}
              </small>
              <p>
                {t(
                  "One bounded GET only: no redirects, credentials, cookies, scripts, images or linked pages. Host/path and connection metadata go to this website and DNS infrastructure; your label and Work context do not. This is not permission for another destination.",
                  "仅一次有界GET：不跟随跳转，不用凭据、Cookie、脚本、图片或关联页面。主机／路径及连接元数据会提供给该网站与DNS基础设施；不发送标签或工作上下文。这不授权其他目的地。",
                )}
              </p>
              <p>
                {t(
                  "Limits: 20 seconds network, 60 seconds execution, 16 KiB conservative headers, 128 KiB response, 24 KiB extracted UTF-8 text. Only HTTP 200 with complete supported framing is accepted; no retries or browser fallback.",
                  "上限：网络20秒、执行60秒、保守报头16 KiB、响应128 KiB、提取UTF-8文本24 KiB。仅接受完整且受支持报文的HTTP 200，不重试，也不回退至浏览器。",
                )}
              </p>
              <p>
                {t(
                  "Keep the immutable extracted text and acquisition receipt locally indefinitely. Raw bytes are not retained. Static text may differ from the rendered page; content is untrusted. Capture does not start Work, select a source or grant model sharing.",
                  "无限期在本地保留不可变提取文本与采集回执，不保留原始字节。静态文本可能与渲染页面不同，内容不受信任。采集不会开始工作、选择来源或授权模型共享。",
                )}
              </p>
              <ul>
                <CapacityLine
                  t={t}
                  label={t("Source slots", "来源位置")}
                  value={review.source_capacity.count}
                />
                <CapacityLine
                  t={t}
                  label={t("Source reserved bytes", "来源保留字节")}
                  value={review.source_capacity.bytes}
                  bytes
                />
              </ul>
              <p>
                {review.history_used}/200{" "}
                {t(
                  "lifetime records; capacity is advisory and checked again on approval/save",
                  "终身记录；容量仅供参考，批准／保存时再次检查",
                )}
              </p>
              <label className="agent-check">
                <input
                  type="checkbox"
                  checked={publicOnly}
                  disabled={locked || api.pending.length > 0}
                  onChange={(e) => {
                    if (safe()) setPublicOnly(e.target.checked);
                  }}
                />
                {t(
                  "This exact URL is public and contains no private or secret token",
                  "此确切网址公开，且不含私人或秘密令牌",
                )}
              </label>
              <label className="agent-check">
                <input
                  type="checkbox"
                  checked={retainSnapshot}
                  disabled={locked || api.pending.length > 0}
                  onChange={(e) => {
                    if (safe()) setRetainSnapshot(e.target.checked);
                  }}
                />
                {t(
                  "Retain this extracted snapshot and receipt indefinitely with no delete control",
                  "无限期保留提取快照与回执，本版无删除入口",
                )}
              </label>
              <button
                type="button"
                className="primary"
                disabled={
                  locked ||
                  !api.enabled ||
                  !publicOnly ||
                  !retainSnapshot ||
                  api.pending.length > 0 ||
                  !api.reviewReady
                }
                onClick={() => {
                  if (safe())
                    void api.approve(review, publicOnly, retainSnapshot);
                }}
              >
                {t("Approve one public GET", "批准一次公开GET")}
              </button>
            </div>
          )}
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="secondary"
              disabled={locked}
              onClick={() => {
                if (safe()) void api.read(selected.id);
              }}
            >
              {t("Refresh saved status", "刷新保存状态")}
            </button>
            {selected.cancel_available && (
              <button
                type="button"
                className="secondary agent-stop"
                disabled={locked}
                onClick={() => {
                  if (safe()) void api.stop(selected);
                }}
              >
                {t("Stop this capture", "停止此采集")}
              </button>
            )}
            {!hidden && (
              <button
                type="button"
                className="secondary"
                disabled={locked}
                onClick={() => {
                  if (safe()) void api.reconcile(selected);
                }}
              >
                {t(
                  "Reconcile original source locally · no GET",
                  "本地核验原来源 · 不发GET",
                )}
              </button>
            )}
          </div>
          {!hidden && selected.acquisition && (
            <CaptureProvenance value={selected.acquisition} t={t} />
          )}
          {!hidden &&
            selected.source_status === "verified" &&
            selected.source_id &&
            selected.acquisition && (
              <>
                <button
                  type="button"
                  className="secondary"
                  disabled={locked}
                  onClick={() => {
                    if (safe() && selected.acquisition && selected.source_id)
                      setPreview({
                        id: selected.source_id,
                        name: selected.display_name!,
                        format: "text",
                        sha256: selected.acquisition.extracted_sha256,
                        byte_count: selected.acquisition.extracted_byte_count,
                        revision: 1,
                        status: "verified",
                        provenance_kind: "public_web_snapshot",
                        acquisition: selected.acquisition,
                      });
                  }}
                >
                  {t("Inspect retained text", "检查保留文本")}
                </button>
                <p>
                  {t(
                    "To use this source, refresh the source list and explicitly select it in Work. Nothing has been selected or started for you.",
                    "要使用此来源，请刷新来源列表并在工作中明确选择。尚未替您选择来源或开始任务。",
                  )}
                </p>
              </>
            )}
        </section>
      )}
      {api.pending.map((operation) => (
        <div key={operation.key} role="status" className="agent-notice">
          <p>
            {t(
              "Original operation result is unconfirmed. Retry uses the identical request and key within this privacy session; it never creates a replacement capture.",
              "原操作结果未确认。重试仅在此隐私会话内使用完全相同的请求与键，不会创建替代采集。",
            )}
          </p>
          <small>
            {operation.kind} · {operation.key}
          </small>
          <button
            type="button"
            className="secondary"
            disabled={locked}
            onClick={() => {
              if (safe()) void api.retry(operation);
            }}
          >
            {t("Recover original operation", "恢复原操作")}
          </button>
        </div>
      ))}
      {!!api.error && (
        <p role="alert" className="error-message">
          {captureError(api.error, t)}
        </p>
      )}
      {preview && safe() && !hidden && (
        <SourcePreview
          source={preview}
          t={t}
          fence={fence}
          onClose={() => setPreview(null)}
        />
      )}
    </details>
  );
}
