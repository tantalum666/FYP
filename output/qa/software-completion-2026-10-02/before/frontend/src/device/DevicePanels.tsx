import { useEffect, useState } from "react";
import { Moon, Sun, Sunset } from "lucide-react";
import type { ReactNode } from "react";
import { errorText, request, write } from "../api";
import type { Language, Session, Settings, Translate } from "../types";
import { Modal } from "../components/Dialogs";
import type { Appearance } from "./model";

export function DevicePanel({
  title,
  onClose,
  children,
  t,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  t: Translate;
  wide?: boolean;
}) {
  return (
    <div
      className={`device-panel-wrapper ${wide ? "calendar-panel-wrapper" : ""}`}
    >
      <Modal
        title={title}
        onClose={onClose}
        closeLabel={t("Close panel", "关闭面板")}
        wide={wide}
      >
        {children}
      </Modal>
    </div>
  );
}

export function DeviceLogin({
  t,
  onLogin,
}: {
  t: Translate;
  onLogin: (session: Session) => void;
}) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  async function login(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await request("/session", {
        method: "POST",
        body: JSON.stringify({ username: "owner", password }),
      });
      onLogin(await request<Session>("/session"));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="device-login" onSubmit={login}>
      <p>
        {t(
          "Sign in to show your calendar on this screen.",
          "登录后在这块屏幕展示你的日历。",
        )}
      </p>
      <label className="field">
        {t("Username", "账号")}
        <input value="owner" readOnly autoComplete="username" />
      </label>
      <label className="field">
        {t("Password", "密码")}
        <input
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
      <button className="primary" disabled={busy}>
        {busy ? t("Signing in…", "登录中…") : t("Sign in", "登录")}
      </button>
    </form>
  );
}

export function AppearanceChoices({
  value,
  onChange,
  t,
}: {
  value: Appearance;
  onChange: (value: Appearance) => void;
  t: Translate;
}) {
  return (
    <div
      className="appearance-options"
      aria-label={t("Display appearance", "显示外观")}
    >
      {(
        [
          { value: "auto", Icon: Sunset, en: "Automatic", zh: "自动" },
          { value: "day", Icon: Sun, en: "Day", zh: "日间" },
          { value: "night", Icon: Moon, en: "Night", zh: "夜间" },
        ] as const
      ).map(({ value: v, Icon, en, zh }) => (
        <button
          key={v}
          aria-pressed={value === v}
          className={value === v ? "selected" : ""}
          onClick={() => onChange(v)}
        >
          <Icon />
          {t(en, zh)}
        </button>
      ))}
    </div>
  );
}

export function DevicePreferences({
  settings,
  language,
  setLanguage,
  onSaved,
  onDirty,
  onLogout,
  t,
}: {
  settings: Settings;
  language: Language;
  setLanguage: (value: Language) => void;
  onSaved: () => void;
  onDirty: (value: boolean) => void;
  onLogout: () => void;
  t: Translate;
}) {
  const [form, setForm] = useState(() => ({ ...settings }));
  const [baseline] = useState(() => ({ ...settings }));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const dirty =
    form.timezone !== baseline.timezone ||
    form.hide_private !== baseline.hide_private;
  useEffect(() => {
    onDirty(dirty || busy);
    return () => onDirty(false);
  }, [dirty, busy, onDirty]);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await write("/settings", {
        expected_version: baseline.version,
        timezone: form.timezone,
        hide_private: form.hide_private,
      });
      onSaved();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={save} className="device-preferences">
      <label className="field">
        {t("Language on this display", "本屏幕语言")}
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value as Language)}
        >
          <option value="en">English</option>
          <option value="zh">简体中文</option>
        </select>
      </label>
      <label className="field">
        {t("Calendar timezone", "日历时区")}
        <select
          value={form.timezone}
          onChange={(e) => setForm({ ...form, timezone: e.target.value })}
          disabled={busy}
        >
          {Array.from(
            new Set([
              form.timezone,
              "Asia/Hong_Kong",
              "Asia/Shanghai",
              "Asia/Tokyo",
              "Europe/London",
              "America/New_York",
              "UTC",
            ]),
          ).map((z) => (
            <option key={z}>{z}</option>
          ))}
        </select>
      </label>
      <label className="device-check">
        <input
          type="checkbox"
          checked={form.hide_private}
          disabled={busy}
          onChange={(e) => setForm({ ...form, hide_private: e.target.checked })}
        />
        <span>
          {t("Hide private event details", "隐藏私人日程详情")}
          <small>
            {t(
              "Applies to your connected calendar screens.",
              "应用到已连接的日历界面。",
            )}
          </small>
        </span>
      </label>
      {!!error && (
        <p role="alert" className="error-message">
          {errorText(error, t)}
        </p>
      )}
      <div className="device-preferences-actions">
        <button
          className="secondary"
          type="button"
          disabled={busy || dirty}
          onClick={onLogout}
        >
          {t("Sign out", "退出登录")}
        </button>
        <button className="primary" disabled={busy}>
          {busy ? t("Saving…", "保存中…") : t("Save preferences", "保存偏好")}
        </button>
      </div>
      <div className="device-connections">
        <h3>{t("Connections", "连接状态")}</h3>
        <p>
          {t("Camera & posture", "摄像头与坐姿")}
          <span>{t("Not connected", "未连接")}</span>
        </p>
        <p>
          {t("Voice assistant", "语音助理")}
          <span>{t("Not connected", "未接入")}</span>
        </p>
        <p>
          {t("Robotic arm", "机械臂")}
          <span>{t("Not connected", "未连接")}</span>
        </p>
      </div>
    </form>
  );
}
