import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { CalendarDays } from "lucide-react";
import { configureNative, isNative, loadNativeConfig, native } from "../native";

export function NativeSetup({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(!isNative),
    [loading, setLoading] = useState(isNative),
    [address, setAddress] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [language, setLanguage] = useState("en");
  const t = (en: string, zh: string) => (language === "en" ? en : zh);
  useEffect(() => {
    if (!isNative) return;
    const applyRoute = (route: string) => {
      if (!["today", "new"].includes(route)) return;
      const query = new URLSearchParams(location.search);
      query.set("page", "today");
      if (route === "new") query.set("action", "new");
      else query.delete("action");
      history.replaceState(null, "", "?" + query.toString());
      window.dispatchEvent(new CustomEvent("desk:route", { detail: route }));
    };
    const listener = native.addListener("route", (event) =>
      applyRoute(event.route),
    );
    void loadNativeConfig()
      .then((c) => {
        if ("route" in c && typeof c.route === "string") applyRoute(c.route);
        setReady(!!c.origin);
        setAddress(c.origin);
        setLoading(false);
      })
      .catch(() => {
        setError("Could not read the device configuration.");
        setLoading(false);
      });
    const reset = () => setReady(false);
    window.addEventListener("desk:change-server", reset);
    return () => {
      window.removeEventListener("desk:change-server", reset);
      void listener.then((handle) => handle.remove());
    };
  }, []);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await configureNative(address);
      sessionStorage.removeItem("desk.pending-write");
      location.reload();
    } catch {
      setError(
        t(
          "Use the trusted HTTPS address of your desk. Local HTTP is only supported in the simulator.",
          "请输入桌面设备可信的HTTPS地址，本地HTTP仅供模拟器使用。",
        ),
      );
    } finally {
      setBusy(false);
    }
  }
  if (ready) return children;
  if (loading)
    return <div className="app-loading">Opening Desk Companion…</div>;
  return (
    <main className="login-page">
      <div className="login-top">
        <strong>Desk Companion</strong>
        <select
          aria-label="Language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        >
          <option value="en">English</option>
          <option value="zh">简体中文</option>
        </select>
      </div>
      <form className="login-form" onSubmit={submit}>
        <CalendarDays size={34} />
        <h1>{t("Connect to your desk.", "连接你的桌面。")}</h1>
        <p>
          {t(
            "Your phone is a control screen. Your calendar and devices stay connected to your desk.",
            "手机用于远程控制，日历与硬件运行在桌面主机。",
          )}
        </p>
        <label className="field">
          {t("Desk address", "桌面设备地址")}
          <input
            inputMode="url"
            autoCapitalize="none"
            autoCorrect="off"
            placeholder="https://desk.example.com"
            required
            value={address}
            onChange={(e) => setAddress(e.target.value)}
          />
        </label>
        {error && (
          <p className="error-message" role="alert">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy}>
          {t("Continue", "继续")}
        </button>
      </form>
    </main>
  );
}
