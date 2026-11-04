import { useDraftGuard } from "../components/DraftGuard";
import { ExportLink } from "./ExportLink";
import { useEffect, useState } from "react";
import { DateTime } from "luxon";
import { Download, Upload, Link2, FileClock } from "lucide-react";
import { errorText, request, write } from "../api";
import type { EventInput, Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { OwnerAccess } from "./OwnerAccess";
import { apiOrigin } from "../native";

interface Preview {
  preview_id: string;
  kind: string;
  rows: Array<{ event: EventInput; status: string }>;
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

export function DataPanel({ t }: { t: Translate }) {
  const { data, refresh } = useWorkspace();
  const [start, setStart] = useState(DateTime.now().toISODate()!),
    [end, setEnd] = useState(DateTime.now().plus({ days: 30 }).toISODate()!);
  const [preview, setPreview] = useState<Preview | null>(null),
    [replace, setReplace] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null),
    [notice, setNotice] = useState("");
  const [shares, setShares] = useState<Share[]>([]),
    [mode, setMode] = useState("busy"),
    [link, setLink] = useState("");
  const [google, setGoogle] = useState<{
    configured: boolean;
    connected: boolean;
    last_read: string | null;
  } | null>(null);
  const owner = data?.principal.kind === "owner";
  useDraftGuard(!!preview, busy);
  async function load() {
    if (owner)
      try {
        const [s, g] = await Promise.all([
          request<{ shares: Share[] }>("/shares"),
          request<{
            configured: boolean;
            connected: boolean;
            last_read: string | null;
          }>("/google/status"),
        ]);
        setShares(s.shares);
        setGoogle(g);
      } catch (e) {
        setError(e);
      }
  }
  useEffect(() => {
    void load();
  }, [owner]);
  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      return await action();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
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
              "Import a copy of your Google calendar. Changes here do not sync back.",
              "导入 Google 日历副本，本地修改不会同步回去。",
            )}
          </p>
          <div className="workspace-inline-actions">
            {google?.connected ? (
              <>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      setPreview(
                        await write<Preview>("/google/preview", {
                          start,
                          end,
                          mode: "busy",
                          expires_days: 7,
                        }),
                      );
                      setReplace(false);
                    })
                  }
                >
                  {t("Preview Google updates", "预览Google更新")}
                </button>
                <button
                  className="text-button danger"
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      const result = await request<{
                        provider_revocation_confirmed: boolean;
                      }>("/google/disconnect", { method: "POST", body: "{}" });
                      setNotice(
                        result.provider_revocation_confirmed
                          ? t("Google disconnected.", "已断开Google。")
                          : t(
                              "Disconnected locally. Remove this app in your Google account to finish revoking access.",
                              "本地已断开，请到Google账号移除此应用以完成撤销。",
                            ),
                      );
                      await load();
                    })
                  }
                >
                  {t("Disconnect", "断开")}
                </button>
              </>
            ) : (
              <button
                className="secondary"
                disabled={busy || !google?.configured}
                onClick={() =>
                  void act(async () => {
                    const result = await request<{ url: string }>(
                      "/google/connect",
                      { method: "POST", body: "{}" },
                    );
                    window.open(result.url, "_blank", "noopener");
                    setNotice(
                      t(
                        "Complete consent in the browser, then refresh status.",
                        "在浏览器完成授权后刷新状态。",
                      ),
                    );
                  })
                }
              >
                {t("Connect Google", "连接Google")}
              </button>
            )}
            <button className="text-button" onClick={() => void load()}>
              {t("Refresh status", "刷新状态")}
            </button>
          </div>
          {!google?.configured && (
            <p className="workspace-hint">
              {t(
                "Google connection is not configured.",
                "尚未配置 Google 连接。",
              )}
            </p>
          )}
        </details>
      )}
      {preview && (
        <section className="workspace-section">
          <h3>{t("Review import", "检查导入")}</h3>
          {preview.kind !== "backup" && (
            <p>
              {t(
                "New events are private, with reminders off.",
                "新增事项默认私人，提醒关闭。",
              )}
            </p>
          )}
          <p>
            {preview.rows.length} {t("entries", "项")} ·{" "}
            {preview.rows.filter((r) => r.status === "new").length}{" "}
            {t("new", "新增")} ·{" "}
            {preview.rows.filter((r) => r.status === "changed").length}{" "}
            {t("changed", "已有变化")}
          </p>
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
            {preview.rows.map((r, i) => (
              <div key={i}>
                <strong>{r.event.title}</strong>
                <small>
                  {r.event.start_local.replace("T", " ")} · {r.event.timezone} ·{" "}
                  {r.status === "new"
                    ? t("New", "新增")
                    : r.status === "changed"
                      ? t("Changed", "已有变化")
                      : t("Unchanged", "无变化")}
                </small>
              </div>
            ))}
          </div>
          {preview.warnings.map((message, i) => (
            <p className="error-message" key={i}>
              {message}
            </p>
          ))}
          {preview.kind !== "backup" &&
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
                (!preview.rows.length &&
                  !Number(preview.metadata.tasks_count) &&
                  !Number(preview.metadata.memories_count))
              }
              onClick={() =>
                void act(async () => {
                  const result = await write<{
                    created: number;
                    updated: number;
                    kept: number;
                    tasks_created: number;
                    tasks_kept: number;
                    memories_created?: number;
                    memories_kept?: number;
                  }>(`/exchange/${preview.preview_id}/apply`, {
                    replace_matching: replace,
                  });
                  setNotice(
                    t(
                      `Imported: ${result.created} added, ${result.updated} updated; ${result.kept} kept. Tasks: ${result.tasks_created} added, ${result.tasks_kept} kept. Facts: ${result.memories_created ?? 0} added, ${result.memories_kept ?? 0} kept.`,
                      `导入完成：新增${result.created}项，更新${result.updated}项，保留${result.kept}项。事务：新增${result.tasks_created}项，保留${result.tasks_kept}项。事实：新增${result.memories_created ?? 0}条，保留${result.memories_kept ?? 0}条。`,
                    ),
                  );
                  setPreview(null);
                  await refresh();
                })
              }
            >
              {t("Apply import", "确认导入")}
            </button>
            <button
              className="secondary"
              onClick={() => setPreview(null)}
              disabled={busy}
            >
              {t("Discard preview", "放弃预览")}
            </button>
          </div>
        </section>
      )}
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
            "Owner sign-in is needed for exports, backup and sharing.",
            "导出、备份与分享需要拥有者登录。",
          )}
        </p>
      )}
      {!owner && <OwnerAccess t={t} />}
      {notice && <p role="status">{notice}</p>}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </div>
  );
}
