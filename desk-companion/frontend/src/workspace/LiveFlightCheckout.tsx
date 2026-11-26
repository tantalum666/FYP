import freshQuote from "../../../backend/desk/data/fresh-flight-quote.json" with { type: "json" };
import { useEffect, useRef, useState } from "react";
import "./live-flight-checkout.css";
import { NuiteeSandboxCard } from "./NuiteeSandboxCard";
import { LiveFlightPassengerForm } from "./LiveFlightPassengerForm";
import { ApiError, request } from "../api";
import type { Translate } from "../types";
import { formatCurrencyMinor as currency } from "./commercePresentation";

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
  bag_kg: number | null;
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

function quoteLabel(option: Option, t: Translate) {
  if (option.total_minor != null) return currency(option.total_minor, option.currency);
  if (option.fare_minor == null) return t("Total unverified", "总价待核实");
  const fare = currency(option.fare_minor, option.currency);
  return t(`Fare ${fare} · total pending`, `票价 ${fare} · 总价待核实`);
}
export type LiveCheckout = {
  id?: string;
  version?: number;
  state: string;
  provider?: "letsfg" | "nuitee_sandbox";
  connected?: boolean;
  source?: Source;
  market?: Omit<Trip, "origin" | "destination"> & { origin: string[]; destination: string[] };
  routes?: { origin: string; destination: string; state: string; reason?: string }[];
  sources?: (Published & { proposal_id: string })[];
  choices?: Option[];
  selected?: number;
  reason?: string;
  required_fields?: string[];
  seller_check?: {
    seller?: string;
    status?: string;
    page_total_minor?: number;
    page_weight_kg?: number;
    observed_at?: string;
  };
  alternatives_checked?: number | null;
  checked_sellers?: string[];
  receipt?: {
    pnr?: string;
    ticket_numbers?: string[];
    processor_status?: string;
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
      ...(["verify_seller", "verify_original"].includes(name)
        ? { share_seller_page: true }
        : {}),
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
        const next = ["searching", "held", "processing", "card_pending", "paid_pending_ticket", "ticketed_payment_pending", "uncertain"].includes(prior.state)
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
      "seller_verification",
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
  const isNuitee = view.provider === "nuitee_sandbox";
  const choices = view.choices ?? [];
  const visibleChoices = view.market ? Math.max(3, view.routes?.filter(r => r.state === "offers").length ?? 0) : choices.length;
  const optionButton = (o: Option) => (
    <button className="secondary" type="button" key={o.number} disabled={busy}
      onClick={() => void act("select", o.number)}>
      {view.market && `${o.number}. ${o.outbound[0]?.origin} → ${o.outbound.at(-1)?.destination} · ${o.outbound[0]?.departs?.slice(11, 16) ?? ""} · `}
      {flights(o.outbound)}{o.inbound.length ? ` / ${flights(o.inbound)}` : ""} · {quoteLabel(o, t)}
    </button>
  );
  const inspected = view.checked_sellers ?? [];
  const verificationSeller =
    selected?.booking_url && !inspected.includes("LetsFG")
      ? "LetsFG"
      : "Kiwi.com";
  const canInspect = !isNuitee && !inspected.includes(verificationSeller) && (!view.market || verificationSeller === "LetsFG");
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
  const sourceLink = src?.url && (
    <a href={src.url} target="_blank" rel="noopener noreferrer">
      {view.market ? t("Open LetsFG offer", "打开 LetsFG 报价") : t("Open original Kiwi offer", "打开 Kiwi 原报价")}
    </a>
  );
  return (
    <section
      className="commerce-order live-flight-checkout"
      aria-label={isNuitee ? t("Nuitée test flight", "Nuitée 测试机票") : t("Real flight purchase", "真实机票购买")}
    >
      {["no_source", "source_unavailable", "source_changed"].includes(view.state) && (
        <p>{t(freshQuote.en, freshQuote.zh)}</p>
      )}
      {view.market && (
        <header>
          {isNuitee && <span>Nuitée · {t("Sandbox", "沙盒")}</span>}
          <strong>{view.market.origin.join(" / ")} → {view.market.destination.join(" / ")}</strong>
          <p>{[view.market.departure, view.market.return_date].filter(Boolean).join(" / ")} · {t(`${view.market.adults} adult(s)`, `${view.market.adults} 名成人`)}
            {view.market.checked_bag_kg > 0 && t(` · requested: ${view.market.checked_bag_kg} kg checked per adult`, ` · 要求每人托运 ${view.market.checked_bag_kg} 公斤`)}</p>
        </header>
      )}
      {src && !view.market && (
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
              `Required checked baggage: ${src.bags ?? "?"} ${src.bags === 1 ? "bag" : "bags"}, ${src.request.checked_bag_kg} kg per adult.`,
              `所需托运行李：${src.bags ?? "待核实"} 件，每人 ${src.request.checked_bag_kg} 公斤。`,
            )}
          </p>
        </>
      )}
      {src && !view.market &&
        view.state === "source" &&
        src.request.checked_bag_kg > 0 &&
        src.bag_kg == null && (
          <p>
            {t(
              "Kiwi has not verified the checked weight or final charge.",
              "Kiwi 原报价尚未核实托运重量和最终扣款。",
            )}
          </p>
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
          {view.market ? t("Checking live fares…", "正在查实时票价…") : t("Checking the original itinerary…", "正在核对原行程…")}
        </p>
      )}
      {view.state === "source" && (
        <>
          {!view.market && <p>
            {t(
              "LetsFG will recheck this exact itinerary as a different seller.",
              "LetsFG 是另一家卖方，会按原行程重新核价。",
            )}
          </p>}
          {isNuitee && !view.connected ? <p>{t("Nuitée sandbox is not connected on this desk.", "这台设备尚未连接 Nuitée 沙盒。")}</p> : view.connected ? (
            <button
              type="button"
              className="primary"
              disabled={busy}
              onClick={() => void act("search")}
            >
              {isNuitee ? t("Recheck sandbox fare", "重查沙盒总价") : t("Check LetsFG fare", "核对 LetsFG 总价")}
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
      {view.state === "source" &&
        !view.connected &&
        src && !view.market &&
        !inspected.includes("Kiwi.com") && (
          <>
            <p>
              {t(
                "You can first let Alice’s cloud browser read the original Kiwi listing to verify baggage and all mandatory fees for both flights. Only the public page and itinerary are shared.",
                "也可先允许 Alice 的云端浏览器只读核对原 Kiwi 报价的往返行李和所有必付费用，仅分享公开页面及行程。",
              )}
            </p>
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => void act("verify_original")}
            >
              {t(
                "Let Alice verify the original Kiwi offer",
                "让 Alice 核实原来的 Kiwi 报价",
              )}
            </button>
          </>
        )}
      {view.state === "seller_only" && !view.connected && (
        <button
          type="button"
          className="primary"
          disabled={busy}
          onClick={connect}
        >
          {t("Connect LetsFG for checkout", "连接 LetsFG 购票")}
        </button>
      )}
      {authUrl && (
        <a href={authUrl} target="_blank" rel="noopener noreferrer">
          {t("Continue secure connection", "继续安全连接")}
        </a>
      )}
      {view.market && view.routes?.filter(r => !["queued", "searching", "offers"].includes(r.state)).map(r =>
        <small key={r.origin + r.destination}>{r.origin} → {r.destination} · {
          r.state === "no_verified_offer" ? t("No matching fare", "暂无符合条件的报价") :
          r.reason === "FLIGHT_NUITEE_TEST_PARTY" ? t("The card sandbox uses one test adult", "此沙盒使用一位虚构成人") :
          r.reason === "LETSFG_CONNECT_REQUIRED" ? t("Reconnect LetsFG", "需要重新连接 LetsFG") :
          t("Fare unavailable", "未能核实票价")}</small>)}
      {view.state === "market_empty" && (
        <button type="button" className="secondary" disabled={busy} onClick={
          view.routes?.some(r => r.reason === "LETSFG_CONNECT_REQUIRED") ? connect : () => void act("search")
        }>{view.routes?.some(r => r.reason === "LETSFG_CONNECT_REQUIRED") ? t("Reconnect LetsFG", "重新连接 LetsFG") : t("Search again", "重新查价")}</button>
      )}
      {(view.state === "offers" || (view.market && view.state === "searching")) && <>
        {choices.slice(0, visibleChoices).map(optionButton)}
        {choices.length > visibleChoices && <details className="other-flight-fares">
          <summary>{t(`More flights (${choices.length - visibleChoices})`, `其他航班（${choices.length - visibleChoices}）`)}</summary>
          {choices.slice(visibleChoices).map(optionButton)}
        </details>}
      </>}
      {selected && (["review", "seller_only", "card_pending"].includes(view.state) || (isNuitee && receipt?.pnr)) && (
        <div>
          <p>
            <b>{isNuitee ? "Nuitée" : "LetsFG"}</b> · {quoteLabel(selected, t)}
          </p>
          {[...selected.outbound, ...selected.inbound].map((seg, i) => (
            <p key={i}>
              {seg.flight} · {seg.origin} {seg.departs?.replace("T", " ")} →{" "}
              {seg.destination} {seg.arrives?.replace("T", " ")}
            </p>
          ))}
          {selected.checked_bags != null && selected.checked_bag_kg != null && (
            <p>
              {t("Checked baggage included", "已核实包含的托运行李")} ·{" "}
              {selected.checked_bags} × {selected.checked_bag_kg} kg
            </p>
          )}
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
      {isNuitee && ["review", "card_pending"].includes(view.state) && selected?.payable && selected.total_minor != null && (
        <>
          {view.reason === "terms_changed" && <p role="status">{t("Review the changed fare before confirming.", "票价或条款有变，请核对后重新确认。")}</p>}
          <NuiteeSandboxCard view={view} chat={chat} amount={selected.total_minor} currency={selected.currency} t={t} onUpdate={onUpdate} />
        </>
      )}
      {!isNuitee && view.state === "review" &&
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
        <div>
          <p>
            {t(
              "The seller has not verified the required checked baggage and all-in total.",
              "卖方还没有核实所需托运行李和含费总价。",
            )}
          </p>
          {canInspect && (
            <>
              <p>
                {t(
                  `Alice can read the exact ${verificationSeller} listing in the cloud, for both directions. Only the public page and itinerary are shared.`,
                  `Alice 可以在云端只读核对这张 ${verificationSeller} 报价的往返条款，仅分享公开页面及行程。`,
                )}
              </p>
              <button
                type="button"
                className="primary"
                disabled={busy}
                onClick={() =>
                  void act(
                    verificationSeller === "Kiwi.com"
                      ? "verify_original"
                      : "verify_seller",
                    selected?.number,
                  )
                }
              >
                {verificationSeller === "Kiwi.com"
                  ? t(
                      "Let Alice verify the original Kiwi offer",
                      "让 Alice 核实原来的 Kiwi 报价",
                    )
                  : t(
                      "Let Alice verify this seller offer",
                      "让 Alice 核实这张卖方报价",
                    )}
              </button>
            </>
          )}
          {!canInspect && (
            <p>
              {t(
                "The current evidence does not establish an all-in fare for the requested baggage.",
                "当前报价仍未核实所需行李的含费总价。",
              )}
            </p>
          )}
          {(view.choices?.length ?? 0) > 1 && (
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => void act("other_offers")}
            >
              {view.market ? t("See other flights", "查看其他航班") : t("Check other matching offers", "核对其他符合原条件的报价")}
            </button>
          )}
        </div>
      )}
      {view.state === "seller_verification" && (
        <p role="status">
          {t(
            `Alice is checking the selected ${view.seller_check?.seller ?? "seller"} listing. The original fare will be repriced after this read.`,
            `Alice 正在核对选中的 ${view.seller_check?.seller ?? "卖方"} 报价，完成后会重新核实原选项。`,
          )}
        </p>
      )}
      {view.seller_check?.status === "unverified" && (
        <p>
          {t(
            "The exact listing did not establish all sectors, baggage and fees.",
            "这张卖方页面未能同时核实所有航段、行李和费用。",
          )}
        </p>
      )}
      {view.seller_check?.status === "page_verified" && (
        <p>
          {t("Verified on the selected listing", "已在所选页面核实")} ·{" "}
          {currency(
            view.seller_check.page_total_minor!,
            src?.currency ?? "HKD",
          )}{" "}
          · {view.seller_check.page_weight_kg} kg
        </p>
      )}
      {view.state === "bank_approval" && (
        <p role="status">
          {t(
            "Complete the seller’s bank verification, then check this original booking.",
            "请完成卖方的银行验证，然后查回这笔原订单。",
          )}
        </p>
      )}
      {view.state === "card_required" && (
        <p role="status">
          {t(
            "This wallet needs a valid payment method. Update it with LetsFG, then recheck the fare for fresh approval.",
            "这个钱包需要有效付款方式。请在 LetsFG 更新后重新核价并确认。",
          )}
        </p>
      )}
      {view.state === "missing_details" && (
        <p role="status">
          {t(
            "The supplier requested more passenger details. Recheck the fare to complete the private booking form.",
            "卖方需要补充乘客资料。请重新核价后在安全表格中补充。",
          )}
        </p>
      )}
      {["uncertain", "needs_attention"].includes(view.state) && (
        <p role="status">
          {t(
            "The original order needs verification. Check it before initiating another purchase.",
            "原订单仍待核实，请先查回结果。",
          )}
        </p>
      )}
      {view.state === "ticketed_payment_pending" && <p role="status">{t("Test ticket issued. Card capture pending.", "测试票已出票，实扣待核实。")}</p>}
      {view.state === "paid_pending_ticket" && <p role="status">{t("Test card charged. Ticket issuance pending.", "测试卡已扣款，等待票号。")}</p>}
      {receipt?.ticket_numbers?.map(number => <p key={number}>{t("Test e-ticket", "测试电子客票号")} <b>{number}</b></p>)}
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
        "card_pending",
        "ticketed_payment_pending",
        "paid_pending_ticket",
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
      {view.state === "seller_only" && selected?.booking_url ? (
        <details>
          <summary>{t("Original seller links", "原卖方链接")}</summary>
          <p>
            <a
              href={selected.booking_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {t("Selected LetsFG listing", "所选 LetsFG 报价")}
            </a>
          </p>
          <p>{sourceLink}</p>
        </details>
      ) : (
        sourceLink && <p>{sourceLink}</p>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
