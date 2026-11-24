import { useEffect, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";

export function BrowserReminders({ t }: { t: Translate }) {
  const [key, setKey] = useState<string | null>(null);
  const [id, setId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const supported =
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window;
  useEffect(() => {
    if (!supported) return;
    let current = true;
    async function read() {
      const capability = await request<{ public_key: string | null }>("/push");
      const registration = await navigator.serviceWorker.getRegistration();
      const subscription = await registration?.pushManager.getSubscription();
      const stored =
        capability.public_key && subscription
          ? await request<{ id: string | null }>("/push/subscriptions/lookup", {
              method: "POST",
              body: JSON.stringify({ endpoint: subscription.endpoint }),
            })
          : null;
      if (current) {
        setKey(capability.public_key);
        setId(stored?.id ?? null);
      }
    }
    void read().catch((e) => {
      if (current) setError(e);
    });
    return () => {
      current = false;
    };
  }, [supported]);
  if (!supported || (!key && !error)) return null;
  async function toggle() {
    if (!key || busy) return;
    setBusy(true);
    setError(null);
    try {
      if (!id && (await Notification.requestPermission()) !== "granted") {
        throw new Error(
          t(
            "Allow notifications for this site in your browser settings.",
            "请在浏览器的网站设置中允许通知。",
          ),
        );
      }
      const worker = await navigator.serviceWorker.getRegistration();
      if (!worker?.active)
        throw new Error(
          t(
            "Reopen Alice so this browser can receive notifications.",
            "请重新打开 Alice，完成本浏览器的提醒设置。",
          ),
        );
      let subscription = await worker.pushManager.getSubscription();
      if (id) {
        await write(
          "/push/subscriptions/" + encodeURIComponent(id) + "/revocations",
          {},
        );
        await subscription?.unsubscribe();
        setId(null);
      } else {
        const bytes = Uint8Array.from(
          atob(key.replace(/-/g, "+").replace(/_/g, "/")),
          (c) => c.charCodeAt(0),
        );
        const existingKey = subscription?.options.applicationServerKey;
        if (
          subscription &&
          (!existingKey || new Uint8Array(existingKey).join() !== bytes.join())
        ) {
          await subscription.unsubscribe();
          subscription = null;
        }
        subscription ??= await worker.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: bytes,
        });
        const values = subscription.toJSON();
        const saved = await write<{ id: string }>("/push/subscriptions", {
          endpoint: subscription.endpoint,
          p256dh: values.keys?.p256dh,
          auth: values.keys?.auth,
        });
        setId(saved.id);
      }
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      <button
        type="button"
        className="secondary"
        disabled={busy || !key}
        onClick={() => void toggle()}
      >
        {id
          ? t("Turn off notifications on this browser", "关闭此浏览器的提醒")
          : t("Notify me when Alice is closed", "关闭 Alice 页面后也提醒我")}
      </button>
      {!!error && (
        <p role="alert">
          {error instanceof Error ? error.message : errorText(error, t)}
        </p>
      )}
    </div>
  );
}
