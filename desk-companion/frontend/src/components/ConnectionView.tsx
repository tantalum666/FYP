import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { errorText } from "../api";
import type { Language, Translate } from "../types";
import { isNative } from "../native";
import { Modal } from "./Dialogs";
import { PairDeviceForm } from "../workspace/ConnectionsPanel";

export function ConnectionView({
  t,
  language,
  setLanguage,
  onReconnect,
  error,
}: {
  t: Translate;
  language: Language;
  setLanguage: (value: Language) => void;
  onReconnect: () => Promise<void>;
  error?: unknown;
}) {
  const [busy, setBusy] = useState(false);
  const [pairing, setPairing] = useState(false);
  const reconnect = async () => {
    setBusy(true);
    try {
      await onReconnect();
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="connection-page">
      <div className="connection-top">
        <strong>Desk Companion</strong>
        <select
          value={language}
          aria-label="Language"
          onChange={(event) => setLanguage(event.target.value as Language)}
        >
          <option value="en">English</option>
          <option value="zh">简体中文</option>
        </select>
      </div>
      <section className="connection-card">
        <h1>{t("Connect to your desk", "连接你的桌面")}</h1>
        <p>
          {t(
            "Your workspace will open when the connection is ready.",
            "连接恢复后会直接打开工作空间。",
          )}
        </p>
        {!!error && (
          <p className="error-message" role="alert">
            {errorText(error, t)}
          </p>
        )}
        <button
          className="primary"
          disabled={busy}
          onClick={() => void reconnect()}
        >
          <RefreshCw size={18} />
          {busy ? t("Connecting…", "正在连接…") : t("Reconnect", "重新连接")}
        </button>
        {isNative && (
          <button
            className="text-button"
            onClick={() =>
              window.dispatchEvent(new Event("desk:change-server"))
            }
          >
            {t("Choose desk", "选择桌面")}
          </button>
        )}
        <button className="text-button" onClick={() => setPairing(true)}>
          {t("Connect another device", "连接另一台设备")}
        </button>
      </section>
      {pairing && (
        <Modal
          title={t("Connect this screen", "连接本终端")}
          closeLabel={t("Close", "关闭")}
          onClose={() => setPairing(false)}
        >
          <PairDeviceForm
            t={t}
            onPaired={() => {
              setPairing(false);
              void reconnect();
            }}
          />
        </Modal>
      )}
    </main>
  );
}
