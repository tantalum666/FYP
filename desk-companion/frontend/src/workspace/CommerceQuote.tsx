import type { Translate } from "../types";

type Budget = { currency?: string | null; budget_minor?: number | null };
export type QuoteRequest = Budget &
  (
    | {
        kind: "shopping";
        product: string;
        quantity: number;
        fulfilment: "delivery" | "pickup";
      }
    | {
        kind: "flight";
        provider?: "kiwi";
        nonstop?: boolean;
        origin: string;
        destination: string;
        departure: string;
        return_date?: string | null;
        adults: number;
        checked_bag_kg: number;
      }
  );

type Offer = {
  label: string;
  source_url: string;
  currency: string;
  price_minor: number;
  priced_units: number;
  basis: "listed" | "from" | "conditional" | "quantity_offer";
  availability: "available" | "unavailable" | "unknown";
  price_evidence: string;
  extras_minor: number | null;
  extras_evidence: string | null;
  extras_source_url: string | null;
  conditions: string | null;
  origin?: string | null;
  destination?: string | null;
  departure?: string | null;
  return_date?: string | null;
  journey?: "one_way" | "round_trip" | "unknown";
  checked_bag_kg_per_adult?: number | null;
};
export type Quote = {
  request: QuoteRequest;
  observed_at: string;
  approved_page?: string;
  supplier?: {
    provider: string;
    checked_bags_for_party: number | null;
    terms_url: string;
    airline_bag_rules: string | null;
  };
  note: string;
  offer: Offer | null;
  subtotal_minor: number | null;
  total_minor: number | null;
  budget_status: "within" | "over" | "unknown";
};

function money(value: number, currency: string, t: Translate) {
  const format = new Intl.NumberFormat(t("en-HK", "zh-HK"), {
    style: "currency",
    currency,
    currencyDisplay: "code",
  });
  return format.format(
    value / 10 ** (format.resolvedOptions().maximumFractionDigits ?? 2),
  );
}

export function QuoteScope({
  request,
  t,
}: {
  request: QuoteRequest;
  t: Translate;
}) {
  const details =
    request.kind === "shopping"
      ? [
          `${request.product} × ${request.quantity}`,
          request.fulfilment === "delivery"
            ? t("Delivery", "送货")
            : t("Pickup", "自取"),
        ]
      : [
          `${request.origin} → ${request.destination}`,
          request.departure,
          request.return_date
            ? `${t("Return", "回程")} ${request.return_date}`
            : t("One way", "单程"),
          t(`${request.adults} adult(s)`, `${request.adults} 名成人`),
          t(
            `${request.checked_bag_kg} kg checked per adult`,
            `每人托运行李 ${request.checked_bag_kg} 公斤`,
          ),
        ];
  if (request.kind === "flight" && request.nonstop)
    details.push(t("Nonstop", "直飞"));
  if (request.currency && request.budget_minor != null) {
    details.push(
      `${t("Budget", "预算")} ${money(request.budget_minor, request.currency, t)}`,
    );
  }
  return <p className="quote-scope">{details.join(" · ")}</p>;
}

export function CommerceQuote({ quote, t }: { quote: Quote; t: Translate }) {
  const { request, offer } = quote;
  const retail = request.kind === "shopping";
  return (
    <section
      className="computer-use-report commerce-quote"
      aria-label={t("Public quote", "公开报价")}
    >
      <h4>
        {retail
          ? t("Shopping quote", "购物报价")
          : t("Flight quote", "机票报价")}
      </h4>
      <QuoteScope request={request} t={t} />
      {quote.supplier && offer && (
        <p>
          {quote.supplier.provider} ·{" "}
          {t("Checked bags included for this party", "此报价所含托运行李件数")}{" "}
          {quote.supplier.checked_bags_for_party} ·{" "}
          {t("Weight pending seller confirmation", "重量待卖方确认")}
        </p>
      )}
      {!offer && (
        <strong>
          {retail
            ? t(
                "No matching product price verified",
                "尚未核实符合条件的商品价格",
              )
            : t("No matching fare verified", "尚未核实符合行程的票价")}
        </strong>
      )}
      {offer && (
        <>
          <strong>{offer.label}</strong>
          {offer.journey && (
            <p>
              {[
                [offer.origin, offer.destination].filter(Boolean).join(" → "),
                offer.departure,
                offer.return_date,
                offer.journey === "one_way"
                  ? t("One way", "单程")
                  : offer.journey === "round_trip"
                    ? t("Round trip", "往返")
                    : null,
                offer.checked_bag_kg_per_adult != null
                  ? t(
                      `${offer.checked_bag_kg_per_adult} kg checked per adult`,
                      `每人可托运 ${offer.checked_bag_kg_per_adult} 公斤`,
                    )
                  : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
          <dl>
            <dt>
              {offer.basis === "from"
                ? t("Advertised from", "宣传起价")
                : offer.basis === "quantity_offer"
                  ? t("Multi-buy price", "多件优惠价")
                  : offer.basis === "conditional"
                    ? t("Conditional price", "有条件价格")
                    : t("Listed price", "网页标价")}
            </dt>
            <dd>
              {money(offer.price_minor, offer.currency, t)} ·{" "}
              {retail
                ? t(
                    `${offer.priced_units} selling unit(s)`,
                    `${offer.priced_units} 个销售单位`,
                  )
                : t(
                    `${offer.priced_units} adult(s)`,
                    `${offer.priced_units} 名成人`,
                  )}
            </dd>
            {quote.subtotal_minor !== null && (
              <>
                <dt>{t("Subtotal for this request", "本次小计")}</dt>
                <dd>{money(quote.subtotal_minor, offer.currency, t)}</dd>
              </>
            )}
            <dt>
              {retail
                ? t("Delivery / required fees", "取送货及必付费用")
                : t("Taxes, baggage and required fees", "税费、行李及必付费用")}
            </dt>
            <dd>
              {offer.extras_minor === null
                ? t("Unconfirmed", "待核实")
                : money(offer.extras_minor, offer.currency, t)}
            </dd>
            <dt>{t("Total for this request", "本次总价")}</dt>
            <dd>
              {quote.total_minor === null
                ? t("Unconfirmed", "待核实")
                : money(quote.total_minor, offer.currency, t)}
            </dd>
            <dt>{retail ? t("Stock", "库存") : t("Seats", "座位")}</dt>
            <dd>
              {offer.availability === "available"
                ? t("Shown as available", "网页显示有货或有位")
                : offer.availability === "unavailable"
                  ? t("Unavailable", "不可用")
                  : t("Unconfirmed", "待核实")}
            </dd>
            {quote.budget_status !== "unknown" && (
              <>
                <dt>{t("Budget", "预算")}</dt>
                <dd>
                  {quote.budget_status === "within"
                    ? t("Within budget", "预算内")
                    : t("Over budget", "超出预算")}
                </dd>
              </>
            )}
          </dl>
          <p>{offer.price_evidence}</p>
          {offer.conditions && <p>{offer.conditions}</p>}
          {offer.extras_evidence && <p>{offer.extras_evidence}</p>}
          <a href={offer.source_url} target="_blank" rel="noopener noreferrer">
            {t("Open original listing", "打开报价原页")}
          </a>
          {offer.extras_source_url &&
            offer.extras_source_url !== offer.source_url && (
              <>
                {" "}
                ·{" "}
                <a
                  href={offer.extras_source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t("Fee terms", "费用说明")}
                </a>
              </>
            )}
        </>
      )}
      {quote.supplier ? (
        <p>
          <a
            href={quote.supplier.terms_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {t("Seller pricing terms", "卖方计价条款")}
          </a>
          {quote.supplier.airline_bag_rules && (
            <>
              {" "}
              ·{" "}
              <a
                href={quote.supplier.airline_bag_rules}
                target="_blank"
                rel="noopener noreferrer"
              >
                {t("Airline baggage rules", "航空公司行李规则")}
              </a>
            </>
          )}
        </p>
      ) : (
        <p>{quote.note}</p>
      )}
      {!offer && quote.approved_page && (
        <p>
          <a
            href={quote.approved_page}
            target="_blank"
            rel="noopener noreferrer"
          >
            {t("Open approved website", "打开本次查阅的网站")}
          </a>
        </p>
      )}
      <small>
        {t("Checked", "查阅于")}{" "}
        <time dateTime={quote.observed_at}>
          {new Date(quote.observed_at).toLocaleString(t("en-HK", "zh-HK"))}
        </time>{" "}
        · {t("Recheck before purchasing", "购买前请复核")}
      </small>
    </section>
  );
}
