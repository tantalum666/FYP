import { useEffect, useRef, useState } from "react";
import { request } from "../api";
import { apiOrigin } from "../native";
import type { Translate } from "../types";
import type { LiveCheckout } from "./LiveFlightCheckout";
import { formatCurrencyMinor } from "./commercePresentation";

type CardSession = { publishable_key: string; client_secret: string };

function useTestCard() {
  const frame = useRef<HTMLIFrameElement>(null);
  const appOrigin = new URL(apiOrigin() || location.origin);
  const supported =
    ["localhost", "127.0.0.1", "[::1]"].includes(appOrigin.hostname) &&
    ["http:", "https:"].includes(appOrigin.protocol);
  const origin = supported
    ? appOrigin.protocol +
      "//nuitee-card.localhost" +
      (appOrigin.port ? ":" + appOrigin.port : "")
    : "";
  const pending = useRef<(() => void) | null>(null);
  useEffect(() => () => pending.current?.(), []);

  const confirm = (session: CardSession) =>
    new Promise<string>((resolve) => {
      const target = frame.current?.contentWindow;
      if (!target) return resolve("unknown");
      const channel = new MessageChannel();
      const finish = (state: string) => {
        clearTimeout(timer);
        pending.current = null;
        channel.port1.close();
        resolve(state);
      };
      const timer = window.setTimeout(() => finish("unknown"), 45000);
      pending.current = () => finish("unknown");
      channel.port1.onmessage = ({ data }) => {
        if (typeof data?.state === "string") finish(data.state);
      };
      target.postMessage({ type: "alice-nuitee-sandbox", ...session }, origin, [
        channel.port2,
      ]);
    });
  return { frame, origin, confirm };
}

export function NuiteeSandboxCard({
  view,
  chat,
  amount,
  currency,
  t,
  onUpdate,
}: {
  view: LiveCheckout;
  chat: string;
  amount: number;
  currency: string;
  t: Translate;
  onUpdate: (chat: string, next: LiveCheckout) => void;
}) {
  const { frame, origin, confirm } = useTestCard();
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const sending = useRef(false);
  const alive = useRef(true);
  const price = formatCurrencyMinor(amount, currency);
  const confirmation = view.state === "reconfirm_original"
    ? t("Reconfirm original fare " + price, "再次确认原票价 " + price)
    : t("Confirm test Visa payment " + price, "确认测试 Visa 付款 " + price);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  async function pay() {
    if (sending.current || !view.id || !loaded) return;
    sending.current = true;
    setBusy(true);
    setMessage("");
    const path = "/assistant/flight-checkouts/" + view.id;
    try {
      const result = await request<{ view: LiveCheckout; card?: CardSession }>(
        path + "/test-card",
        {
          method: "POST",
          body: JSON.stringify({
            conversation_id: chat,
            version: view.version,
            amount_minor: amount,
            currency,
            confirm_purchase: true,
          }),
        },
      );
      if (!alive.current) return;
      if (!result.card) {
        onUpdate(chat, result.view);
        return;
      }
      const cardResult = await confirm(result.card);
      if (!alive.current) return;
      onUpdate(
        chat,
        await request<LiveCheckout>(path + "/actions", {
          method: "POST",
          body: JSON.stringify({
            action: "status",
            conversation_id: chat,
            version: result.view.version,
          }),
        }),
      );
      if (
        cardResult === "error" ||
        cardResult === "unknown" ||
        cardResult === "invalid"
      ) {
        setMessage(
          t(
            "Check the original test payment status.",
            "请查回这笔原测试付款的状态。",
          ),
        );
      }
    } catch {
      if (alive.current)
        setMessage(
          t(
            "Check the original booking before retrying.",
            "请先查回原订单，再决定是否重试。",
          ),
        );
    } finally {
      sending.current = false;
      if (alive.current) setBusy(false);
    }
  }
  return (
    <>
      {origin && (
        <iframe
          ref={frame}
          sandbox="allow-scripts allow-same-origin allow-forms"
          allow="payment"
          title={t("Test Visa processor", "测试 Visa 支付组件")}
          src={origin + "/nuitee-sandbox-card.html"}
          hidden
          onLoad={() => setLoaded(true)}
        />
      )}
      <button
        type="button"
        className="primary"
        disabled={!loaded || busy || !window.isSecureContext}
        onClick={() => void pay()}
      >
        {busy ? t("Checking payment…", "正在核对付款…") : confirmation}
      </button>
      {!origin && (
        <p role="status">
          {t(
            "Open the connected local desk to use the test Visa.",
            "请在已连接的本机桌面使用测试 Visa。",
          )}
        </p>
      )}
      {message && <p role="status">{message}</p>}
    </>
  );
}
