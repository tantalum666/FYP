import { useId, useRef, useState } from "react";
import { ChevronDown, ShieldCheck } from "lucide-react";
import { ApiError, errorText, request } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import type { PermissionState } from "./types";
import "./permissions.css";

export function PermissionsPanel({
  t,
  compact = false,
  onApplied,
}: {
  t: Translate;
  compact?: boolean;
  onApplied?: () => void;
}) {
  const { data, offline, stale, refresh, acceptPermissions } = useWorkspace();
  const current = data?.permissions;
  const owner = data?.principal.kind === "owner";
  const name = useId();
  const [draft, setDraft] = useState<PermissionState | null>(null);
  const [busy, setBusy] = useState(false);
  const requestKey = useRef<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);
  useDraftGuard(!compact && !!draft, busy);
  const chosen = draft?.mode ?? current?.mode;
  function chooseMode(mode: PermissionState["mode"]) {
    if (!current) return;
    const unconfirmed = requestKey.current !== null;
    requestKey.current = null;
    setDraft(
      current.mode === mode && !unconfirmed ? null : { ...current, mode },
    );
    setSaved(false);
    setError(null);
  }
  async function save() {
    if (!draft) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      requestKey.current ??= crypto.randomUUID();
      const result = await request<{ permissions: PermissionState }>(
        "/permissions",
        {
          method: "POST",
          body: JSON.stringify({
            mode: draft.mode,
            expected_version: draft.version,
          }),
          headers: { "X-Operation-Id": requestKey.current },
        },
      );
      acceptPermissions(result.permissions);
      setDraft(null);
      requestKey.current = null;
      setSaved(true);
      onApplied?.();
      void refresh();
    } catch (reason) {
      setError(reason);
      // Permission control is independent of pending business writes. Re-read
      // the effective policy after a lost response instead of assuming failure.
      try {
        const latest = await request<PermissionState>("/permissions");
        acceptPermissions(latest);
        if (latest.version > draft.version && latest.mode === draft.mode) {
          setDraft(null);
          requestKey.current = null;
          setError(null);
          setSaved(true);
          onApplied?.();
        }
      } catch {
        /* Keep the uncertain choice visible until connectivity returns. */
      }
    } finally {
      setBusy(false);
    }
  }
  if (!owner) return null;
  return (
    <section
      className={`permissions-panel ${compact ? "compact" : "settings-section"}`}
      aria-label={t("Assistant permissions", "助理权限")}
    >
      {compact ? (
        <h3>{t("Permissions", "权限")}</h3>
      ) : (
        <h2>{t("Assistant permissions", "助理权限")}</h2>
      )}
      <p>
        {t(
          "Choose how Alice handles changes in this workspace.",
          "选择 Alice 如何处理工作空间中的修改。",
        )}
      </p>
      {!current ? (
        <p role="status">
          {t(
            "Permissions are unavailable. Reconnect to load them.",
            "暂时无法读取权限，请恢复连接后重试。",
          )}
        </p>
      ) : (
        <fieldset disabled={busy || offline || stale}>
          <legend className="sr-only">
            {t("Permission mode", "权限模式")}
          </legend>
          <label className="permission-choice">
            <input
              type="radio"
              name={name}
              value="ask"
              checked={chosen === "ask"}
              onChange={() => chooseMode("ask")}
            />
            <span>
              <strong>{t("Ask first", "每次询问")}</strong>
              <small>
                {t(
                  "Review each proposed change in the conversation before it runs.",
                  "每次修改会先在对话中交给你核对，再执行。",
                )}
              </small>
            </span>
          </label>
          <label className="permission-choice">
            <input
              type="radio"
              name={name}
              value="full"
              checked={chosen === "full"}
              onChange={() => chooseMode("full")}
            />
            <span>
              <strong>{t("Full access", "完整权限")}</strong>
              <small>
                {t(
                  "Let Alice apply supported software actions automatically and report the result.",
                  "让 Alice 自动执行已支持的软件操作，并向你报告结果。",
                )}
              </small>
            </span>
          </label>
        </fieldset>
      )}
      <details className="permission-scope">
        <summary>{t("What this covers", "权限包含哪些操作")}</summary>
        <ul>
          <li>
            {t(
              "Calendar and tasks: create, update, complete or remove items.",
              "日历与事务：创建、修改、完成或移除项目。",
            )}
          </li>
          <li>
            {t(
              "Memory: save, correct or forget personal facts.",
              "记忆：保存、更正或忘掉个人事实。",
            )}
          </li>
          <li>
            {t(
              "Files: create and verify files in the destinations already enabled for this desk.",
              "文件：在本桌面已经启用的目标位置创建与核验文件。",
            )}
          </li>
        </ul>
        <p>
          {t(
            "Connections, microphone, camera and physical outputs keep their separate controls. Full access does not turn on an unavailable tool.",
            "连接、麦克风、摄像头和实体输出仍有独立控制。完整权限不会启用尚不可用的工具。",
          )}
        </p>
      </details>
      <p className="workspace-hint">
        {t(
          "For new requests on your signed-in screens. Earlier pending actions still need your decision.",
          "适用于已登录界面的新请求，之前的待确认操作仍由你单独决定。",
        )}
      </p>
      {draft && (
        <div className="workspace-inline-actions">
          <button
            className="primary"
            disabled={busy || offline || stale}
            onClick={() => void save()}
          >
            {chosen === "full"
              ? t("Use full access", "启用完整权限")
              : t("Use ask first", "启用每次询问")}
          </button>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => {
              setDraft(null);
              requestKey.current = null;
              setError(null);
            }}
          >
            {error && requestKey.current
              ? t("Close", "关闭")
              : t("Cancel", "取消")}
          </button>
        </div>
      )}
      {saved && (
        <p role="status">
          {t(
            "Permissions updated across your connected screens.",
            "权限已更新，各个连接界面会同步使用。",
          )}
        </p>
      )}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
      {error instanceof ApiError && error.code === "VERSION_CONFLICT" && (
        <button
          className="secondary"
          onClick={() => {
            setDraft(null);
            setError(null);
            void refresh();
          }}
        >
          {t("Load current permissions", "加载当前权限")}
        </button>
      )}
    </section>
  );
}

export function PermissionControl({ t }: { t: Translate }) {
  const { data, offline, stale } = useWorkspace();
  const [open, setOpen] = useState(false);
  if (data?.principal.kind !== "owner") return null;
  const disabled = !data.permissions || offline || stale;
  return (
    <details
      className="permission-control"
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary
        aria-disabled={disabled}
        onClick={(e) => {
          if (disabled) e.preventDefault();
        }}
      >
        <ShieldCheck size={14} />
        {data.permissions?.mode === "full"
          ? t("Full access", "完整权限")
          : t("Ask first", "每次询问")}
        <ChevronDown size={13} />
      </summary>
      {open && (
        <div className="permission-popover">
          <PermissionsPanel t={t} compact onApplied={() => setOpen(false)} />
        </div>
      )}
    </details>
  );
}
