import { useState } from "react";
import type { Translate } from "../types";
import { errorText, request } from "../api";
import { useWorkspace } from "./WorkspaceContext";

export function OwnerAccess({ t }: { t: Translate }) {
  const { refresh } = useWorkspace();
  const [open, setOpen] = useState(false),
    [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  if (!open)
    return (
      <button className="secondary" onClick={() => setOpen(true)}>
        {t("Owner sign-in", "拥有者登录")}
      </button>
    );
  async function signIn(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await request("/session", {
        method: "POST",
        body: JSON.stringify({ username: "owner", password }),
      });
      setPassword("");
      await refresh();
      setOpen(false);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="owner-access" onSubmit={signIn}>
      <label className="field">
        {t("Owner password", "拥有者密码")}
        <input
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </label>
      <div className="workspace-inline-actions">
        <button className="primary" disabled={busy}>
          {t("Sign in", "登录")}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => {
            setOpen(false);
            setPassword("");
          }}
        >
          {t("Cancel", "取消")}
        </button>
      </div>
      {!!error && <p className="error-message">{errorText(error, t)}</p>}
    </form>
  );
}
