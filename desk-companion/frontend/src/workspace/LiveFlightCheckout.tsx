import { useEffect, useRef, useState } from "react";
import "./live-flight-checkout.css";
import { LiveFlightPassengerForm } from "./LiveFlightPassengerForm";
import { ApiError, request } from "../api";
import type { Translate } from "../types";

export type LiveLeg = {
  origin: string;
  destination: string;
  departs?: string;
  arrives?: string;
  flight?: string;
};
type Trip = {
  origin: string;
  destination: string;
  departure: string;
  return_date?: string;
  adults: number;
  checked_bag_kg: number;
  nonstop?: boolean;
};
type Published = {
  label: string;
  request: Trip;
  currency: string;
  listed_minor: number;
};
type Source = Published & {
  url: string;
  bags: number | null;
  outbound: LiveLeg[];
  inbound: LiveLeg[];
};
type Option = {
  number: number;
  outbound: LiveLeg[];
  inbound: LiveLeg[];
  fare_minor: number | null;
  total_minor: number | null;
  currency: string;
  checked_bags: number | null;
  checked_bag_kg: number | null;
  payable: boolean;
  reason?: string;
  booking_url?: string;
  fare_conditions?: { refundable?: string; changeable?: string };
  conditions_source?: string;
};
export type LiveCheckout = {
  id?: string;
  version?: number;
  state: string;
  connected?: boolean;
  source?: Source;
  sources?: (Published & { proposal_id: string })[];
  choices?: Option[];
  selected?: number;
  reason?: string;
  required_fields?: string[];
  receipt?: {
    pnr?: string;
    held_minor?: number;
    charged_minor?: number;
    currency?: string;
    reason?: string;
    action_url?: string;
  };
};
export type LiveCheckoutReply = {
  conversation_id: string;
  live_flight_checkout: LiveCheckout;
};
const root = "/assistant/flight-checkouts";
const currency = (value: number, iso: string) => {
  const format = new Intl.NumberFormat("en-HK", {
    style: "currency",
    currency: iso,
    currencyDisplay: "code",
  });
  return format.format(
    value / 10 ** (format.resolvedOptions().maximumFractionDigits ?? 2),
  );
};
const dates = (r: Trip) =>
  [r.departure, r.return_date].filter(Boolean).join(" / ");
const flights = (legs: LiveLeg[]) =>
  legs
    .map((s) => s.flight)
    .filter(Boolean)
    .join(" / ");
export const startsFlightCheckout = (text: string) =>
  /(?:买|買|购|購|订|訂).{0,16}(?:机票|機票|航班)|\b(?:buy|book|purchase)\b.{0,30}\b(?:flight|ticket|fare|itinerary|one)\b/i.test(
    text,
  );
export function selectFlightSource(
  chat: string | undefined,
  task: string | undefined,
  source: { proposal_id?: string; job_id?: string },
) {
  return request<LiveCheckoutReply>(`${root}/source`, {
    method: "POST",
    body: JSON.stringify({ conversation_id: chat, task_id: task, ...source }),
  });
}
export function getFlightCheckout(chat: string, id: string) {
  return request<LiveCheckout>(
    `${root}/${id}?conversation_id=${encodeURIComponent(chat)}`,
  );
}

function action(
  view: LiveCheckout,
  chat: string,
  name: string,
  number?: number,
) {
  return request<LiveCheckout>(`${root}/${view.id}/actions`, {
    method: "POST",
    body: JSON.stringify({
      conversation_id: chat,
      version: view.version,
      action: name,
      number,
    }),
  });
}

export function LiveFlightCheckout({
  view,
  chat,
  t,
  onUpdate,
  onSource,
}: {
  view: LiveCheckout;
  chat: string;
  t: Translate;
  onUpdate: (chat: string, view: LiveCheckout) => void;
  onSource: (id: string) => Promise<void>;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [authUrl, setAuthUrl] = useState("");
  const alive = useRef(true),
    current = useRef(view),
    inFlight = useRef(false);
  current.current = view;
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const reload = async () => {
    if (view.id) onUpdate(chat, await getFlightCheckout(chat, view.id));
  };
  async function run(job: () => Promise<void>) {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      await job();
    } catch (e) {
      if (alive.current) {
        const code = e instanceof ApiError ? e.code : "";
        setError(
          code === "FLIGHT_PASSENGER_DETAILS_REQUIRED" ||
            code === "VALIDATION_FAILED"
            ? t(
                "Check the passenger and contact fields.",
                "请核对乘客和联系方式。",
              )
            : code === "FLIGHT_LIVE_REVIEW_CHANGED"
              ? t(
                  "The review changed. Check the current terms.",
                  "这份确认已更新，请核对当前条款。",
                )
              : t(
                  "I couldn’t verify the result. Reopen this review to check the original record.",
                  "暂未核实结果，请重新查看这份确认。",
                ),
        );
        if (view.id) await reload().catch(() => {});
      }
    } finally {
      inFlight.current = false;
      if (alive.current) setBusy(false);
    }
  }
  const act = (name: string, n?: number) =>
    run(async () => {
      const next = await action(view, chat, name, n);
      if (alive.current) onUpdate(chat, next);
    });
  useEffect(() => {
    if (!view.id) return;
    let valid = true,
      pending = false;
    const refresh = async () => {
      if (!valid || pending || inFlight.current || document.hidden) return;
      pending = true;
      const prior = current.current;
      try {
        const next = ["searching", "held", "processing"].includes(prior.state)
          ? await action(prior, chat, "status")
          : await getFlightCheckout(chat, prior.id!);
        if (valid && current.current === prior) onUpdate(chat, next);
      } catch {
        /* A manual status check remains available. */
      } finally {
        pending = false;
      }
    };
    const timer = [
      "waiting_source",
      "searching",
      "held",
      "processing",
    ].includes(view.state)
      ? window.setInterval(() => void refresh(), 5000)
      : undefined;
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      valid = false;
      if (timer !== undefined) window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [chat, view.id, view.state, onUpdate]);
  const src = view.source,
    selected = view.choices?.find((o) => o.number === view.selected),
    receipt = view.receipt;
  const passport = !!view.required_fields?.some((k) =>
    k.startsWith("passport_"),
  );
  function connect() {
    const popup = window.open("about:blank", "_blank");
    if (popup) popup.opener = null;
    void run(async () => {
      try {
        const res = await request<{ url: string }>("/apps/letsfg/connect", {
          method: "POST",
          body: "{}",
        });
        const url = new URL(res.url);
        if (
          url.protocol !== "https:" ||
          (url.hostname !== "letsfg.co" && !url.hostname.endsWith(".letsfg.co"))
        )
          throw Error("oauth");
        if (popup) popup.location.href = url.href;
        else setAuthUrl(url.href);
      } catch (e) {
        popup?.close();
        throw e;
      }
    });
  }
  const sourceLink = src && (
    <a href={src.url} target="_blank" rel="noopener noreferrer">
      {t("Open original Kiwi offer", "打开 Kiwi 原报价")}
    </a>
  );
  return (
    <section
      className="commerce-order live-flight-checkout"
      aria-label={t("Real flight purchase", "真实机票购买")}
    >
      {view.state === "no_source" && (
        <p>
          {t(
            "Open the original Kiwi flight result and select Prepare purchase.",
            "请打开原来的 Kiwi 航班结果，选择「准备购买这张机票」。",
          )}
        </p>
      )}
      {["source_unavailable", "source_changed"].includes(view.state) && (
        <p>
          {t(
            "The original listing could not be verified. Reopen its search result.",
            "原报价无法核实，请重新查看原查询结果。",
          )}
        </p>
      )}
      {src && (
        <>
          <strong>
            {src.request.origin} → {src.request.destination}
            {src.request.return_date ? ` → ${src.request.origin}` : ""}
          </strong>
          <p>
            {dates(src.request)} ·{" "}
            {t(
              `${src.request.adults} ${src.request.adults === 1 ? "adult" : "adults"}`,
              `${src.request.adults} 名成人`,
            )}
          </p>
          <p>
            {src.label} · Kiwi.com {currency(src.listed_minor, src.currency)}{" "}
            {t("listed", "原报价")}
          </p>
          <p>
            {t(
              `Required checked baggage: ${src.bags ?? "?"} bag(s), ${src.request.checked_bag_kg} kg per adult.`,
              `所需托运行李：${src.bags ?? "待核实"} 件，每人 ${src.request.checked_bag_kg} 公斤。`,
            )}
          </p>
        </>
      )}
      {view.state === "choose_source" && (
        <p>
          {t(
            "Which original Kiwi fare should I recheck?",
            "请选择你刚才看到的 Kiwi 原报价。",
          )}
        </p>
      )}
      {view.state === "choose_source" &&
        view.sources?.map((s) => (
          <button
            type="button"
            className="secondary"
            disabled={busy}
            key={s.proposal_id}
            onClick={() => void run(() => onSource(s.proposal_id))}
          >
            {s.label} · {dates(s.request)} ·{" "}
            {currency(s.listed_minor, s.currency)}
          </button>
        ))}
      {["waiting_source", "searching"].includes(view.state) && (
        <p role="status">
          {t("Checking the original itinerary…", "正在核对原行程…")}
        </p>
      )}
      {view.state === "source" && (
        <>
          <p>
            {t(
              "LetsFG will recheck this exact itinerary as a different seller.",
              "LetsFG 是另一家卖方，会按原行程重新核价。",
            )}
          </p>
          {view.connected ? (
            <button
              type="button"
              className="primary"
              disabled={busy}
              onClick={() => void act("search")}
            >
              {t("Check LetsFG fare", "核对 LetsFG 总价")}
            </button>
          ) : (
            <button
              type="button"
              className="primary"
              disabled={busy}
              onClick={connect}
            >
              {t("Connect LetsFG for checkout", "连接 LetsFG 购票")}
            </button>
          )}
        </>
      )}
      {authUrl && (
        <a href={authUrl} target="_blank" rel="noopener noreferrer">
          {t("Continue secure connection", "继续安全连接")}
        </a>
      )}
      {view.state === "offers" &&
        view.choices?.map((o) => (
          <button
            className="secondary"
            type="button"
            key={o.number}
            disabled={busy}
            onClick={() => void act("select", o.number)}
          >
            {flights(o.outbound)}
            {o.inbound.length ? ` / ${flights(o.inbound)}` : ""} ·{" "}
            {o.total_minor != null
              ? currency(o.total_minor, o.currency)
              : t("Total unverified", "总价待核实")}
          </button>
        ))}
      {selected && ["review", "seller_only"].includes(view.state) && (
        <div>
          <p>
            <b>LetsFG</b> ·{" "}
            {selected.total_minor != null
              ? currency(selected.total_minor, selected.currency)
              : t("Total unverified", "总价待核实")}
          </p>
          {[...selected.outbound, ...selected.inbound].map((seg, i) => (
            <p key={i}>
              {seg.flight} · {seg.origin} {seg.departs?.replace("T", " ")} →{" "}
              {seg.destination} {seg.arrives?.replace("T", " ")}
            </p>
          ))}
          <p>
            {t("Checked baggage included", "已核实包含的托运行李")} ·{" "}
            {selected.checked_bags ?? "?"} × {selected.checked_bag_kg ?? "?"} kg
          </p>
        </div>
      )}
      {selected?.fare_conditions?.refundable && (
        <p>
          {t("Refund terms", "退票条款")} ·{" "}
          {selected.fare_conditions.refundable}
        </p>
      )}
      {selected?.fare_conditions?.changeable && (
        <p>
          {t("Change terms", "改签条款")} ·{" "}
          {selected.fare_conditions.changeable}
        </p>
      )}
      {selected?.booking_url && view.state === "seller_only" && (
        <p>
          <a
            href={selected.booking_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {t("Check baggage on the seller’s offer", "在卖方报价中核实行李")}
          </a>
        </p>
      )}
      {view.state === "review" &&
        selected?.payable &&
        selected.total_minor != null &&
        src && (
          <>
            {view.reason === "terms_changed" && (
              <p role="status">
                {t(
                  "The seller changed the terms. Review the revised fare before paying.",
                  "卖方已更改条款，请核对新总价后再确认。",
                )}
              </p>
            )}
            {window.isSecureContext ? (
              <details>
                <summary>
                  {t(
                    "Passenger details and payment confirmation",
                    "乘客资料与付款确认",
                  )}
                </summary>
                <LiveFlightPassengerForm
                  adults={src.request.adults}
                  passport={passport}
                  busy={busy}
                  t={t}
                  total={currency(selected.total_minor, selected.currency)}
                  onConfirm={async (passengers, email) => {
                    let submitted = false;
                    await run(async () => {
                      const next = await request<LiveCheckout>(
                        `${root}/${view.id}/confirm`,
                        {
                          method: "POST",
                          body: JSON.stringify({
                            conversation_id: chat,
                            version: view.version,
                            amount_minor: selected.total_minor,
                            currency: selected.currency,
                            confirm_purchase: true,
                            passengers,
                            contact_email: email,
                          }),
                        },
                      );
                      submitted = next.state !== "review";
                      if (alive.current) onUpdate(chat, next);
                    });
                    return submitted;
                  }}
                />
              </details>
            ) : (
              <p>
                {t(
                  "Open this review on the secure desk or HTTPS to enter passenger details.",
                  "请在本机桌面或 HTTPS 页面中填写乘客资料。",
                )}
              </p>
            )}
          </>
        )}
      {view.state === "seller_only" && (
        <p>
          {t(
            "LetsFG could not verify a payable match with the required flights and baggage.",
            "LetsFG 暂未核实符合原班次及行李要求的可付总价。",
          )}
        </p>
      )}
      {receipt?.pnr && (
        <p>
          <b>
            {t("Booking reference", "订座编号")} {receipt.pnr}
          </b>
        </p>
      )}
      {receipt?.charged_minor != null && (
        <p>
          {t("Verified charge", "已核实扣款")}{" "}
          {currency(receipt.charged_minor, receipt.currency ?? "HKD")}
        </p>
      )}
      {receipt?.held_minor != null && (
        <p>
          {t("Authorized hold", "预授权")}{" "}
          {currency(receipt.held_minor, receipt.currency ?? "HKD")}
        </p>
      )}
      {receipt?.action_url && (
        <a href={receipt.action_url} target="_blank" rel="noopener noreferrer">
          {view.state === "bank_approval"
            ? t("Complete bank verification", "完成银行验证")
            : t("Open supplier action", "打开卖方操作")}
        </a>
      )}
      {["card_required", "missing_details", "seller_only"].includes(
        view.state,
      ) && (
        <button
          className="secondary"
          type="button"
          disabled={busy}
          onClick={() => void act("search")}
        >
          {t("Recheck available fare", "重新核对报价")}
        </button>
      )}
      {[
        "bank_approval",
        "held",
        "processing",
        "submitting",
        "uncertain",
        "needs_attention",
      ].includes(view.state) && (
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() => void act("status")}
        >
          {t("Check original booking", "查回原订单")}
        </button>
      )}
      {sourceLink && <p>{sourceLink}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
