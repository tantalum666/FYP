import { useDraftGuard } from "../components/DraftGuard";
import { ExportLink } from "./ExportLink";
import { useCallback, useEffect, useRef, useState } from "react";
import { DateTime } from "luxon";
import { Download, Upload, Link2, FileClock } from "lucide-react";
import { ApiError, errorText, pendingWrite, request, write, type PendingWrite } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { OwnerAccess } from "./OwnerAccess";
import { apiOrigin } from "../native";
import { ResponseFence } from "./personal/responseFence";
import {
  ChangedDetails, importStatus, refreshAction, refreshCounts, refreshPlan, resolutionLabel,
  verifiedChangeIds, type GoogleStatus, type ImportRow,
} from "./GoogleImportReview";

interface Preview {
  preview_id: string;
  kind: string;
  rows: ImportRow[];
  warnings: string[];
  metadata: Record<string, unknown>;
  expires_at: string;
}
interface Share {
  id: string;
  start: string;
  end: string;
  mode: string;
  expires_at: string;
}

interface ImportResult {
  created: number;
  updated: number;
  removed: number;
  kept: number;
  tasks_created: number;
  tasks_kept: number;
  memories_created: number;
  memories_kept: number;
}

export function DataPanel({ t }: { t: Translate }) {
  const { data, offline, stale, refresh } = useWorkspace();
  const [start, setStart] = useState(DateTime.now().toISODate()!),
    [end, setEnd] = useState(DateTime.now().plus({ days: 30 }).toISODate()!);
  const [draft, setPreview] = useState<(Preview & { epoch?: number }) | null>(null),
    [replace, setReplace] = useState(false),
    [selection, setSelection] = useState<{ review: string; ids: string[] } | null>(null),
    [activity, setBusy] = useState<boolean | number>(false),
    [error, setError] = useState<unknown>(null),
    [notice, setNotice] = useState<string | { session: string; epoch?: number; text: string }>("");
  const [shares, setShares] = useState<Share[]>([]),
    [mode, setMode] = useState("busy"),
    [link, setLink] = useState("");
  const [loaded, setGoogle] = useState<(GoogleStatus & { scope: string }) | null>(null);
  const [sessionEpoch, setSessionEpoch] = useState(0);
  const owner = data?.principal.kind === "owner";
  const online = !offline && !stale;
  const visible = owner && !!data?.personal_context_visible && online;
  const session = JSON.stringify([
    data?.principal.kind, data?.principal.id, sessionEpoch, online, visible,
  ]);
  const scope = JSON.stringify([session, data?.google.connected, data?.google.connected_at]);
  const google = loaded?.scope === scope ? loaded : null;
  const canReview = !!(
    visible && google?.review_version && data?.google.connected &&
    google.connected_at === data.google.connected_at
  );
  const fence = useRef(new ResponseFence()).current;
  fence.update(JSON.stringify([scope, google?.version, google?.review_version]), canReview);
  const epoch = fence.capture();
  const busy = activity === true || activity === epoch;
  const lastWrite = useRef<{ key: string; epoch: number } | null>(null);
  const isGoogle = draft?.kind === "google" || draft?.kind === "google_refresh";
  const preview =
    isGoogle && (draft.epoch !== epoch || !canReview || draft.metadata.review_version !== google?.review_version)
      ? null : draft;
  const reviewingRefresh = preview?.kind === "google_refresh";
  const verified = reviewingRefresh ? verifiedChangeIds(preview.rows) : [];
  const reviewKey = `${epoch}/${preview?.preview_id}`;
  const selectedIds = selection?.review === reviewKey ? selection.ids : verified;
  const lastRefresh = canReview ? google?.last_refresh : null;
  const message = typeof notice === "string"
    ? notice
    : notice.session === session && (notice.epoch === undefined || fence.accepts(notice.epoch)) && notice.text;
  useDraftGuard(!!preview, busy);
  const loadGeneration = useRef(0);
  const load = useCallback(async () => {
    const generation = ++loadGeneration.current;
    const token = fence.capture();
    const current = () => generation === loadGeneration.current && token === fence.capture();
    if (owner)
      try {
        const [s, g] = await Promise.all([
          request<{ shares: Share[] }>("/shares"),
          request<GoogleStatus>("/google/status"),
        ]);
        if (current()) {
          setShares(s.shares);
          setGoogle({ ...g, scope });
        }
      } catch (e) {
        if (current()) {
          setGoogle(null);
          setError(e);
        }
      }
  }, [owner, scope, fence]);
  useEffect(() => {
    void load();
    return () => { loadGeneration.current += 1; };
  }, [load]);
  useEffect(() => {
    if (isGoogle && !preview) setPreview(null);
  }, [isGoogle, preview]);
  useEffect(() => {
    const sessionChanged = () => {
      fence.update("session-changing", false);
      setSessionEpoch((value) => value + 1);
      setGoogle(null);
      setPreview((old) => old?.kind.startsWith("google") ? null : old);
      setNotice("");
      setError(null);
    };
    window.addEventListener("desk:session", sessionChanged);
    window.addEventListener("desk:personal-context", sessionChanged);
    return () => {
      fence.update("unmounted", false);
      window.removeEventListener("desk:session", sessionChanged);
      window.removeEventListener("desk:personal-context", sessionChanged);
    };
  }, [fence]);
  useEffect(() => {
    // retryPending emits the same operation object at start and completion.
    // Reopening this panel cannot adopt a retry begun by the previous session.
    let retry: PendingWrite | null = null;
    const retrying = (event: Event) => {
      const operation = (event as CustomEvent<PendingWrite>).detail;
      const last = lastWrite.current;
      if (fence.accepts(epoch) && (last?.key !== operation.key || last.epoch === epoch))
        retry = operation;
    };
    const recovered = (event: Event) => {
      const { operation, result } = (event as CustomEvent<{ operation: PendingWrite; result: Preview }>).detail;
      if (!fence.accepts(epoch) || operation !== retry) return;
      retry = null;
      if (["/google/preview", "/google/refresh"].includes(operation.path) &&
          result.metadata.review_version === google?.review_version) {
        setError(null);
        setPreview({ ...result, epoch });
        setReplace(false);
      } else if (preview && isGoogle && (
        operation.path === `/exchange/${preview.preview_id}/apply` ||
        operation.path === `/google/${preview.preview_id}/discard`
      )) {
        setError(null);
        setPreview((old) => old?.preview_id === preview.preview_id ? null : old);
        void load();
        void refresh();
      }
    };
    window.addEventListener("desk:write-retrying", retrying);
    window.addEventListener("desk:write-recovered", recovered);
    return () => {
      window.removeEventListener("desk:write-retrying", retrying);
      window.removeEventListener("desk:write-recovered", recovered);
    };
  }, [epoch, fence, google?.review_version, isGoogle, load, preview, refresh]);
  function writeReview<T>(path: string, body: unknown) {
    if (!fence.accepts(epoch)) throw new ApiError("IMPORT_EXPIRED", 410);
    const pending = pendingWrite();
    const last = lastWrite.current;
    if (pending && last?.key === pending.key && last.epoch !== epoch)
      throw new ApiError("PENDING_WRITE");
    const result = write<T>(path, body);
    const op = pendingWrite();
    if (op?.path === path && JSON.stringify(op.body) === JSON.stringify(body))
      lastWrite.current = { key: op.key, epoch };
    return result;
  }
  async function act(action: () => Promise<unknown>, googleAction = false) {
    const current = () => !googleAction || epoch === fence.capture();
    if (!current()) return;
    setBusy(googleAction ? epoch : true);
    setError(null);
    setNotice("");
    try {
      return await action();
    } catch (e) {
      if (!current()) return;
      if (googleAction && e instanceof ApiError && (
        [401, 403, 410].includes(e.status) ||
        ["APP_CONNECTION_CHANGED", "GOOGLE_NOT_CONNECTED", "VERSION_CONFLICT"].includes(e.code)
      )) {
        if (isGoogle) setPreview((old) => old === draft ? null : old);
        void load();
      }
      setError(e);
    } finally {
      if (current()) setBusy(false);
    }
  }
  async function importFile(file: File | undefined, kind: "ics" | "backup") {
    if (!file) return;
    if (file.size > (kind === "ics" ? 1_000_000 : 100_000_000)) {
      setNotice(t("This file is too large.", "文件太大。"));
      return;
    }
    await act(async () => {
      const content = await file.text();
      const result = await write<Preview>(
        `/exchange/${kind}/preview`,
        kind === "ics"
          ? { content, start, end, source_name: file.name.slice(0, 80) }
          : { content },
      );
      setPreview(result);
      setReplace(false);
    });
  }
  function previewGoogle(path: "/google/preview" | "/google/refresh") {
    void act(async () => {
      if (!fence.accepts(epoch) || !google) return;
      const result = await writeReview<Preview>(path, { start, end, expected_version: google.version });
      if (!fence.accepts(epoch)) return;
      if (result.metadata.review_version !== google.review_version) {
        throw new ApiError("IMPORT_EXPIRED", 410);
      }
      setPreview({ ...result, epoch });
      setReplace(false);
    }, true);
  }
  async function confirmPreview() {
    if (!preview) return;
    const submit = isGoogle ? writeReview : write;
    const resolutions = selectedIds.filter((id) => !verified.includes(id));
    const result = await submit<ImportResult>(`/exchange/${preview.preview_id}/apply`, {
      replace_matching: replace,
      ...(verified.length ? { selected_event_ids: verified.filter((id) => selectedIds.includes(id)) } : {}),
      ...(reviewingRefresh && resolutions.length ? { resolve_event_ids: resolutions } : {}),
    });
    if (isGoogle && !fence.accepts(epoch)) return;
    if (reviewingRefresh) {
      setNotice({ session, epoch, text: refreshCounts(result, t) });
    } else if (isGoogle) {
      setNotice({
        session, epoch,
        text: t(
          `${result.created} added · ${result.updated} updated · ${result.kept} kept`,
          `新增 ${result.created} 项 · 更新 ${result.updated} 项 · 保留 ${result.kept} 项`,
        ),
      });
    } else {
      setNotice(t(
        `Imported: ${result.created} added, ${result.updated} updated; ${result.kept} kept. Tasks: ${result.tasks_created} added, ${result.tasks_kept} kept. Facts: ${result.memories_created ?? 0} added, ${result.memories_kept ?? 0} kept.`,
        `导入完成：新增${result.created}项，更新${result.updated}项，保留${result.kept}项。事务：新增${result.tasks_created}项，保留${result.tasks_kept}项。事实：新增${result.memories_created ?? 0}条，保留${result.memories_kept ?? 0}条。`,
      ));
    }
    setPreview(null);
    if (isGoogle) await load();
    if (!isGoogle || fence.accepts(epoch)) await refresh();
  }

  async function discardPreview() {
    if (!preview) return;
    if (isGoogle) {
      await writeReview(`/google/${preview.preview_id}/discard`, {});
      if (!fence.accepts(epoch)) return;
    }
    setPreview(null);
  }
  function chooseCopy(id: string, checked: boolean) {
    setSelection((previous) => {
      const ids = previous?.review === reviewKey ? previous.ids : verified;
      return { review: reviewKey, ids: checked ? [...ids, id] : ids.filter((other) => other !== id) };
    });
  }
  const review = preview && (
    <section className="workspace-section">
      <h3>{reviewingRefresh ? t("Review refresh", "检查刷新") : t("Review import", "检查导入")}</h3>
      {preview.kind !== "backup" && !reviewingRefresh && (
        <p>
          {t(
            "New events are private, with reminders off.",
            "新增事项默认私人，提醒关闭。",
          )}
        </p>
      )}
      {reviewingRefresh ? <p>
        {String(preview.metadata.start)} → {String(preview.metadata.end)}
        {" · "}{refreshPlan(preview.rows, t, selectedIds)}
      </p> : <p>
        {preview.rows.length} {t("entries", "项")} ·{" "}
        {preview.rows.filter((r) => r.status === "new").length}{" "}
        {t("new", "新增")} ·{" "}
        {preview.rows.filter((r) => r.status === "changed").length}{" "}
        {t("changed", "已有变化")}
      </p>}
      {preview.kind === "backup" && (
        <p>
          {t(
            "Recovery merges missing events, tasks and saved facts. Existing data and preferences are kept. Restored tasks have follow-ups paused.",
            "恢复合并缺少的日程、事务和已保存的事实，保留已有数据及当前偏好。恢复的事务暂不自动跟进。",
          )}
        </p>
      )}
      {preview.kind === "backup" && (
        <p>
          {Number(preview.metadata.tasks_count ?? 0)}{" "}
          {t("tasks in this backup", "项事务在此备份中")}
          {" · "}
          {Number(preview.metadata.memories_count ?? 0)}{" "}
          {t("saved facts in this backup", "条已保存的事实在此备份中")}
        </p>
      )}
      <div className="import-preview-list">
        {preview.rows.map((r, i) => {
          const action = reviewingRefresh && refreshAction(r);
          return (
            <div key={r.existing_id ?? i}>
              <strong>{r.event.title}</strong>
              <small>
                {r.event.start_local.replace("T", " ")} · {r.event.timezone} ·{" "}
                {importStatus(r.status, t)}
              </small>
              {r.previous && <ChangedDetails previous={r.previous} event={r.event} t={t} />}
              {action && r.existing_id && (
                <label className="check-field">
                  <input type="checkbox" disabled={busy} value={r.existing_id}
                    aria-label={`${resolutionLabel(action, t)} · ${r.event.title}`}
                    checked={selectedIds.includes(r.existing_id)}
                    onChange={({ currentTarget }) => chooseCopy(currentTarget.value, currentTarget.checked)}
                  />
                  {resolutionLabel(action, t)}
                </label>
              )}
            </div>
          );
        })}
      </div>
      {preview.warnings.map((message, i) => (
        <p className="error-message" key={i}>
          {message}
        </p>
      ))}
      {preview.kind !== "backup" && !reviewingRefresh &&
        preview.rows.some((r) => r.status === "changed") && (
          <label className="check-field">
            <input
              type="checkbox"
              checked={replace}
              onChange={(e) => setReplace(e.target.checked)}
            />
            {t(
              "Replace matching changed entries after checking them",
              "检查后替换对应的已变化事项",
            )}
          </label>
        )}
      <div className="workspace-inline-actions">
        <button
          className="primary"
          disabled={
            busy ||
            (!reviewingRefresh && !preview.rows.length &&
              !Number(preview.metadata.tasks_count) &&
              !Number(preview.metadata.memories_count))
          }
          onClick={() => void act(confirmPreview, isGoogle)}
        >
          {reviewingRefresh ? t("Confirm local refresh", "确认刷新本地副本") : t("Apply import", "确认导入")}
        </button>
        <button
          className="secondary"
          onClick={() => void act(discardPreview, isGoogle)}
          disabled={busy}
        >
          {t("Discard preview", "放弃预览")}
        </button>
      </div>
    </section>
  );
  return (
    <div className="workspace-panel data-panel">
      <h3>{t("Calendar files", "日历文件")}</h3>
      <p>
        {t(
          "Choose a file to preview before importing.",
          "选择文件，预览后再导入。",
        )}
      </p>
      <div className="workspace-form-grid">
        <label className="field">
          {t("From", "开始日期")}
          <input
            type="date"
            required
            value={start}
            onInput={(e) => setStart(e.currentTarget.value)}
          />
        </label>
        <label className="field">
          {t("Until (not included)", "结束日期（不含当天）")}
          <input
            type="date"
            required
            value={end}
            onInput={(e) => setEnd(e.currentTarget.value)}
          />
        </label>
      </div>
      <details className="workspace-details">
        <summary>{t("Import rules", "导入说明")}</summary>
        <p className="workspace-hint">
          {t(
            "ICS imports expand recurring events into individual entries within this range (up to 62 days). Future occurrences require another import.",
            "ICS导入会将最多62天内的重复事项展开为单次记录，更远的事项需再次导入。",
          )}
        </p>
      </details>
      <div className="workspace-inline-actions">
        <label className="secondary file-choice">
          <Upload size={17} />
          {t("Choose ICS file", "选择ICS文件")}
          <input
            type="file"
            accept=".ics,text/calendar"
            disabled={busy}
            onChange={(e) => {
              void importFile(e.target.files?.[0], "ics");
              e.target.value = "";
            }}
          />
        </label>
        {owner && (
          <ExportLink
            path="/exchange/calendar.ics"
            filename="desk-calendar.ics"
            disabled={busy}
            onError={setError}
          >
            <Download size={17} />
            {t("Export calendar", "导出日历")}
          </ExportLink>
        )}
      </div>
      {owner && (
        <details className="workspace-details">
          <summary>Google Calendar</summary>
          <p>
            {t(
              "Preview your primary calendar, or check copies already imported for the dates above.",
              "预览 Google 主日历，或检查上方日期内已导入的副本。",
            )}
          </p>
          <div className="workspace-inline-actions">
            {google?.connected ? (
              <>
                <button
                  className="secondary"
                  disabled={busy || !canReview}
                  onClick={() => previewGoogle("/google/preview")}
                >
                  {t("Preview date range", "预览所选日期")}
                </button>
                <button
                  className="secondary"
                  disabled={busy || !canReview}
                  onClick={() => previewGoogle("/google/refresh")}
                >
                  {t("Refresh imported events", "刷新已导入事项")}
                </button>
                <button
                  className="text-button danger"
                  disabled={busy || !online}
                  onClick={() =>
                    void act(async () => {
                      const result = await request<{
                        provider_revocation_confirmed: boolean;
                      }>("/apps/calendar/disconnect", {
                        method: "POST",
                        body: JSON.stringify({ expected_version: google.version }),
                      });
                      if (epoch !== fence.capture()) return;
                      if (isGoogle) setPreview(null);
                      setNotice({
                        session,
                        text: result.provider_revocation_confirmed
                          ? t("Google disconnected.", "已断开Google。")
                          : t(
                              "Disconnected locally. Remove this app in your Google account to finish revoking access.",
                              "本地已断开，请到Google账号移除此应用以完成撤销。",
                            ),
                      });
                      await load();
                    }, true)
                  }
                >
                  {t("Disconnect", "断开")}
                </button>
              </>
            ) : (
              <button
                className="secondary"
                disabled={busy || !online || !google?.configured}
                onClick={() =>
                  void act(async () => {
                    const result = await request<{ url: string }>(
                      "/google/connect",
                      { method: "POST", body: "{}" },
                    );
                    if (epoch !== fence.capture()) return;
                    window.open(result.url, "_blank", "noopener");
                    setNotice({
                      session,
                      text: t(
                        "Complete consent in the browser, then refresh status.",
                        "在浏览器完成授权后刷新状态。",
                      ),
                    });
                  }, true)
                }
              >
                {t("Connect Google", "连接Google")}
              </button>
            )}
            <button className="text-button" onClick={() => void load()}>
              {t("Refresh status", "刷新状态")}
            </button>
          </div>
          {google?.connected && !data?.personal_context_visible && <p className="workspace-hint">
            {t("Show private details to review Google events.", "显示私人详情后即可检查 Google 事项。")}
          </p>}
          {lastRefresh && <p className="workspace-hint">
            {t("Last confirmed refresh", "最近确认的刷新")} · {DateTime.fromISO(lastRefresh.at).toLocaleString(DateTime.DATETIME_SHORT)}
            {" · "}{lastRefresh.start} → {lastRefresh.end}
            {" · "}{refreshCounts(lastRefresh, t)}
            {lastRefresh.conflicts > 0 && t(` · ${lastRefresh.conflicts} locally edited`, ` · ${lastRefresh.conflicts} 项有本地修改`)}
            {lastRefresh.unresolved > 0 && t(` · ${lastRefresh.unresolved} unverified`, ` · ${lastRefresh.unresolved} 项未核实`)}
          </p>}
          {google?.connected && <details>
            <summary>{t("Which copies can refresh?", "哪些副本可刷新？")}</summary>
            <p className="workspace-hint">{t(
              "Choose up to 31 days and 50 imported events. Older copies can be matched by ID in these dates if this desk has only ever connected one Google Calendar grant. Unverified copies stay on the desk.",
              "可选最多 31 天和 50 项已导入事项。若本桌面仅授权连接过一次 Google 日历，可在所选日期内按 ID 匹配旧副本。无法核实的副本保留在本地。",
            )}</p>
          </details>}
          {google && !google.configured && (
            <p className="workspace-hint">
              {t(
                "Google connection is not configured.",
                "尚未配置 Google 连接。",
              )}
            </p>
          )}
          {reviewingRefresh && review}
        </details>
      )}
      {!reviewingRefresh && review}
      {owner ? (
        <>
          <details className="workspace-details">
            <summary>
              <FileClock size={18} /> {t("Backup & recovery", "备份与恢复")}
            </summary>
            <p>
              {t(
                "Backups contain calendar details, tasks and their latest 20 progress records, saved facts, plus settings. Login and provider secrets are excluded. Store the file privately.",
                "备份包含日历、事务及各事务最近20条进展、已保存的事实与设置，不含登录或服务密钥。请妥善保存文件。",
              )}
            </p>
            <div className="workspace-inline-actions">
              <ExportLink
                path="/exchange/backup.json"
                filename="desk-backup.json"
                disabled={busy}
                onError={setError}
              >
                <Download size={17} />
                {t("Download backup", "下载备份")}
              </ExportLink>
              <label className="secondary file-choice">
                <Upload size={17} />
                {t("Preview recovery", "预览恢复")}
                <input
                  type="file"
                  accept=".json,application/json"
                  disabled={busy}
                  onChange={(e) => {
                    void importFile(e.target.files?.[0], "backup");
                    e.target.value = "";
                  }}
                />
              </label>
            </div>
          </details>
          <details className="workspace-details">
            <summary>
              <Link2 size={18} /> {t("Share a date range", "分享一段日期")}
            </summary>
            <p>
              {t(
                "Uses the dates above, up to 31 days. Anyone with the link can read the chosen view until it expires in seven days. They must be able to reach this desk’s address.",
                "使用上方日期，最多31天。链接持有人可在七天有效期内查看所选内容，并需能访问本设备地址。",
              )}
            </p>
            <label className="field">
              {t("What to share", "分享内容")}
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="busy">
                  {t(
                    "Busy times only, including private events",
                    "仅忙闲时间（包含私人事项的时间）",
                  )}
                </option>
                <option value="displayable">
                  {t("Titles of displayable events only", "仅可展示事项的标题")}
                </option>
              </select>
            </label>
            <button
              className="secondary"
              disabled={busy}
              onClick={() =>
                void act(async () => {
                  const result = await write<{ token: string }>("/shares", {
                    start,
                    end,
                    mode,
                    expires_days: 7,
                  });
                  setLink(`${apiOrigin()}/?surface=share#${result.token}`);
                  await load();
                })
              }
            >
              {t("Create read-only link", "创建只读链接")}
            </button>
            {link && (
              <label className="field share-link">
                {t("Share link", "分享链接")}
                <input
                  readOnly
                  value={link}
                  onFocus={(e) => e.target.select()}
                />
                <button
                  type="button"
                  className="text-button"
                  onClick={() =>
                    void act(async () => {
                      await navigator.clipboard.writeText(link);
                      setNotice(t("Link copied.", "链接已复制。"));
                    })
                  }
                >
                  {t("Copy link", "复制链接")}
                </button>
              </label>
            )}
            <div className="workspace-list">
              {shares.map((s) => (
                <div className="workspace-list-row" key={s.id}>
                  <div>
                    <strong>
                      {s.start} → {s.end}
                    </strong>
                    <small>
                      {s.mode === "busy"
                        ? t("Busy times", "忙闲时间")
                        : t("Displayable titles", "可展示标题")}
                    </small>
                  </div>
                  <button
                    className="text-button danger"
                    disabled={busy}
                    onClick={() =>
                      void act(async () => {
                        await write(`/shares/${s.id}/revoke`, {});
                        setLink("");
                        await load();
                      })
                    }
                  >
                    {t("Revoke", "撤销")}
                  </button>
                </div>
              ))}
            </div>
          </details>
        </>
      ) : (
        <p className="workspace-hint">
          {t(
            "Open your main desk for exports, backup and sharing.",
            "请在主桌面导出、备份和分享。",
          )}
        </p>
      )}
      {!owner && <OwnerAccess t={t} />}
      {message && <p role="status">{message}</p>}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </div>
  );
}
