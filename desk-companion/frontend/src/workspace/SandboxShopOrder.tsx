import type { Translate } from "../types";
import {
  hkd,
  reviewRef,
  shopStatus,
  type CommerceRef,
  type SandboxShop,
} from "./commercePresentation";
export type { SandboxShop } from "./commercePresentation";

export function SandboxShopCard({
  order,
  t,
  busy,
  onDecision,
}: {
  order: SandboxShop;
  t: Translate;
  busy: boolean;
  onDecision: (text: string, review: CommerceRef) => void;
}) {
  const { quote: q, receipt: r } = order,
    terms = q.terms,
    total = hkd(order.review_minor);
  const revised = order.state === "reprice",
    retry = order.state === "retry",
    atCheckout = order.state === "quoted" || revised || retry;
  const choose = (message: string) =>
    onDecision(message, reviewRef(order, "shop"));
  const fields = (
    <>
      <div>
        {q.name} × {terms.quantity} · {hkd(q.unit_minor)} {t("each", "每件")}
      </div>
      <div>{terms.sku}</div>
      {q.shipping_name && <div>{q.shipping_name}</div>}
      <div>
        {t("Items", "商品")} {hkd(terms.subtotal_minor)} ·{" "}
        {t("Delivery", "运费")} {hkd(terms.shipping_minor)}
      </div>
      {terms.tax_minor > 0 && (
        <div>
          {t("Tax", "税费")} {hkd(terms.tax_minor)}
        </div>
      )}
      {terms.fees_minor > 0 && (
        <div>
          {t("Fees", "附加费")} {hkd(terms.fees_minor)}
        </div>
      )}
      {terms.discount_minor > 0 && (
        <div>
          {t("Discount", "优惠")} −{hkd(terms.discount_minor)}
        </div>
      )}
      {r && (
        <div>
          WooCommerce #{r.order} · Stripe · {t("Test charge", "模拟扣款")}{" "}
          {hkd(r.charged_minor)}
          {r.refunded_minor != null && r.net_minor != null && (
            <>
              {" "}
              · {t("Refunded", "已退")} {hkd(r.refunded_minor)} ·{" "}
              {t("Net", "净扣款")} {hkd(r.net_minor)}
            </>
          )}
        </div>
      )}
      {r?.buyer_cancel_requested && (
        <div>{t("Buyer cancellation received", "商户已受理买家撤单")}</div>
      )}
    </>
  );
  return (
    <section
      className="assistant-action-card commerce-order"
      aria-label={t("Test shop order", "测试购物订单")}
    >
      {atCheckout ? (
        <>
          <strong>
            {q.name} × {terms.quantity}
          </strong>
          <p>
            {t("Items", "商品")} {hkd(terms.subtotal_minor)} ·{" "}
            {q.destination === "HK"
              ? t("HK delivery", "香港运费")
              : t("Delivery", "运费")}{" "}
            {hkd(terms.shipping_minor)}
            {terms.tax_minor > 0 && (
              <>
                {" "}
                · {t("Tax", "税费")} {hkd(terms.tax_minor)}
              </>
            )}
            {terms.fees_minor > 0 && (
              <>
                {" "}
                · {t("Fees", "附加费")} {hkd(terms.fees_minor)}
              </>
            )}
            {terms.discount_minor > 0 && (
              <>
                {" "}
                · {t("Discount", "优惠")} −{hkd(terms.discount_minor)}
              </>
            )}
          </p>
          {revised && order.previous && (
            <p role="status">
              {t("New total", "总价已变")} ·{" "}
              {hkd(order.previous.terms.total_minor)} → {total}
            </p>
          )}
          {retry && <p role="status">{shopStatus(order, t)}</p>}
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="primary"
              disabled={busy}
              onClick={() =>
                choose(
                  retry
                    ? t("Recover shop order", "恢复原购物订单")
                    : revised
                      ? t(`Pay new total ${total}`, `按新总价支付 ${total}`)
                      : t(`Pay ${total}`, `确认支付 ${total}`),
                )
              }
            >
              {retry
                ? t("Recover original order", "恢复原订单")
                : t(`Pay ${total} · test`, `模拟支付 ${total}`)}
            </button>
            {!retry && (
              <button
                type="button"
                className="secondary"
                disabled={busy}
                onClick={() => choose(t("Cancel", "取消购物"))}
              >
                {revised ? t("Decline", "拒绝新价") : t("Cancel", "取消")}
              </button>
            )}
          </div>
          <details>
            <summary>{t("Order details", "订单明细")}</summary>
            {fields}
          </details>
        </>
      ) : (
        <details className="commerce-receipt">
          <summary>{shopStatus(order, t)}</summary>
          <div className="commerce-detail-body">
            {fields}
            {order.state === "refund_review" && (
              <p>
                {t(
                  "The merchant has not confirmed a full refund.",
                  "商户尚未确认全额退款。",
                )}
              </p>
            )}
            {order.state === "completed" &&
              r?.can_cancel &&
              !order.cancel_unavailable && (
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    choose(
                      t(
                        "Cancel this shopping order and request a full refund",
                        "取消这笔购物订单并全额退款",
                      ),
                    )
                  }
                >
                  {t("Cancel and refund", "撤单并退款")} {hkd(r.charged_minor)}
                </button>
              )}
            {["completed", "refunded", "refund_review"].includes(
              order.state,
            ) && (
              <button
                type="button"
                className="secondary"
                disabled={busy}
                onClick={() =>
                  choose(
                    t("Check my shopping refund", "查回这笔购物订单的退款结果"),
                  )
                }
              >
                {t("Check original payment", "查原付款")}
              </button>
            )}
          </div>
        </details>
      )}
      {order.state === "refund_retry" && r && (
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            choose(
              t(
                "Cancel this shopping order and request a full refund",
                "取消这笔购物订单并全额退款",
              ),
            )
          }
        >
          {t("Retry cancellation", "重试撤单")} {hkd(r.charged_minor)}
        </button>
      )}
    </section>
  );
}
