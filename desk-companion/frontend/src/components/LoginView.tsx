import { useState } from "react";
import { CalendarDays } from "lucide-react";
import { ApiError, errorText, request } from "../api";
import type { Language, Session, Translate } from "../types";
import { isNative } from "../native";
import { Modal } from "./Dialogs";
import { sessionExpiredNotice } from "../surfaceNotice";
import { PairDeviceForm } from "../workspace/ConnectionsPanel";

export function LoginView({
  t,
  language,
  setLanguage,
  onLogin,
  expired = false,
  startupError = null,
}: {
  t: Translate;
  language: Language;
  setLanguage: (l: Language) => void;
  onLogin: (s: Session) => void;
  expired?: boolean;
  startupError?: unknown;
}) {
  const [username, setUsername] = useState("owner"),
    [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(startupError);
  const [pairing, setPairing] = useState(false);
  const invalidCredentials = error instanceof ApiError && error.code === "INVALID_LOGIN";
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await request("/session", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      onLogin(await request<Session>("/session"));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <div className="login-top">
        <strong>Desk Companion</strong>
        <select
          value={language}
          aria-label="Language"
          onChange={(e) => setLanguage(e.target.value as Language)}
        >
          <option value="en">English</option>
          <option value="zh">简体中文</option>
        </select>
      </div>
      <form className="login-form" onSubmit={submit}>
        <CalendarDays size={34} strokeWidth={1.5} />
        <h1>{t("Your day starts here.", "从容安排每一天。")}</h1>
        <p>
          {t(
            "Sign in to your local desk workspace.",
            "登录你的本地桌面工作空间。",
          )}
        </p>
        {expired && sessionExpiredNotice(t("Your owner session expired. Sign in again.", "拥有者会话已过期，请重新登录。"))}
        <label className="field">
          {t("Username", "账号")}
          <input
            autoComplete="username"
            required
            aria-invalid={invalidCredentials}
            aria-describedby={error ? "owner-login-error" : undefined}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label className="field">
          {t("Password", "密码")}
          <input
            type="password"
            autoComplete="current-password"
            required
            aria-invalid={invalidCredentials}
            aria-describedby={error ? "owner-login-error" : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {!!error && (
          <p id="owner-login-error" className="error-message" role="alert">
            {errorText(error, t)}
          </p>
        )}
        <button className="primary" disabled={busy} aria-busy={busy}>
          {busy ? t("Signing in…", "登录中…") : t("Sign in", "登录")}
        </button>
      </form>
      <button
        className="text-button pair-login-link"
        onClick={() => setPairing(true)}
      >
        {t("Pair with an existing desk", "与已有桌面设备配对")}
      </button>
      {pairing && (
        <>
          <Modal
            title={t("Pair this screen", "配对本终端")}
            closeLabel={t("Close", "关闭")}
            onClose={() => setPairing(false)}
          >
            <PairDeviceForm t={t} onPaired={onLogin} />
          </Modal>
        </>
      )}
      {isNative && (
        <button
          className="text-button pair-login-link"
          onClick={() => window.dispatchEvent(new Event("desk:change-server"))}
        >
          {t("Change desk address", "更换桌面地址")}
        </button>
      )}
    </main>
  );
}
