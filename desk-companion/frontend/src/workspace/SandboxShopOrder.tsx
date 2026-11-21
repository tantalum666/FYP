import type { Translate } from "../types";
import { hkd, reviewRef, type CommerceRef } from "./commerceReviews";

interface ShopQuote {
  name: string;
  unit_minor: number;
  shipping_name: string;
  destination: string | null;
  terms: {
    product_id: number;
    sku: string;
    quantity: number;
    currency: "HKD";
    subtotal_minor: number;
    discount_minor: number;
    shipping_minor: number;
    tax_minor: number;
    fees_minor: number;
    total_minor: number;
    rate_id: string;
  };
}
export interface SandboxShop {
  id: string;
  version: number;
  state: string;
  quote: ShopQuote;
  previous: ShopQuote | null;
  review_minor: number;
  approved_minor: number | null;
  cancel_unavailable?: boolean;
  receipt: {
    order: number;
    order_status: string;
    charged_minor: number;
    test_mode: boolean;
    can_cancel?: boolean;
    buyer_cancel_requested?: boolean;
    refunded_minor?: number;
    net_minor?: number;
  } | null;
}

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
  const q = order.quote,
    terms = q.terms;
  const revised = order.state === "reprice",
    retry = order.state === "retry";
  const pending = ["submitting", "checking"].includes(order.state);
  const canDecide = ["quoted", "reprice", "retry"].includes(order.state);
  const total = hkd(terms.total_minor);
  const confirm = retry
    ? t("Recover shop order", "恢复原购物订单")
    : revised
      ? t(`Pay new total ${total}`, `按新总价支付 ${total}`)
      : t(`Pay ${total}`, `确认支付 ${total}`);
  return (
    <section
      className="assistant-action-card assistant-proposal"
      aria-label={t("WooCommerce test order", "WooCommerce 测试购物订单")}
    >
      <strong>{t("WooCommerce test order", "WooCommerce 测试订单")}</strong>
      <p>
        {q.name} × {terms.quantity}
        <br />
        <small>
          {hkd(q.unit_minor)} {t("each", "每件")} · {terms.sku}
        </small>
      </p>
      <div>
        {t("Items", "商品小计")} {hkd(terms.subtotal_minor)}
      </div>
      <div>
        {t("Delivery", "运费")} {hkd(terms.shipping_minor)}
        {q.shipping_name ? ` · ${q.shipping_name}` : ""}
      </div>
      {terms.discount_minor > 0 && (
        <div>
          {t("Discount", "优惠")} −{hkd(terms.discount_minor)}
        </div>
      )}
      {terms.tax_minor > 0 && (
        <div>
          {t("Tax", "税费")} {hkd(terms.tax_minor)}
        </div>
      )}
      {terms.fees_minor > 0 && (
        <div>
          {t("Fees", "其他费用")} {hkd(terms.fees_minor)}
        </div>
      )}
      <p>
        {t("Total", "总价")} <strong>{total}</strong>
      </p>
      {revised && order.previous && (
        <p role="status">
          {t("Checkout changed", "结账报价已变")} ·{" "}
          {hkd(order.previous.terms.total_minor)} → <strong>{total}</strong>
          <br />
          {t(
            "No payment yet. Accept the new quote?",
            "尚未付款。是否接受新报价？",
          )}
        </p>
      )}
      {canDecide && (
        <div className="workspace-inline-actions">
          <button
            className="primary"
            type="button"
            disabled={busy}
            onClick={() => onDecision(confirm, reviewRef(order, "shop"))}
          >
            {confirm}
          </button>
          {!retry && (
            <button
              className="secondary"
              type="button"
              disabled={busy}
              onClick={() =>
                onDecision(t("Cancel", "取消购物"), reviewRef(order, "shop"))
              }
            >
              {revised
                ? t("Decline new total", "拒绝新总价")
                : t("Cancel", "取消")}
            </button>
          )}
        </div>
      )}
      {pending && (
        <p role="status">
          {t(
            "Checking the shop order and Stripe payment…",
            "正在查回商店订单和 Stripe 扣款…",
          )}
        </p>
      )}
      {order.state === "completed" && order.receipt && (
        <p role="status">
          {t("WooCommerce order", "WooCommerce 订单")}{" "}
          <strong>#{order.receipt.order}</strong>
          <br />
          {t("Stripe captured", "Stripe 模拟扣款")}{" "}
          <strong>{hkd(order.receipt.charged_minor)}</strong> ·{" "}
          {t("Real charge HK$0", "真实扣款 HK$0")}
        </p>
      )}
      {((order.state === "completed" &&
        order.receipt?.can_cancel &&
        !order.cancel_unavailable) ||
        order.state === "refund_retry") && (
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            onDecision(
              t(
                "Cancel this shopping order and request a full refund",
                "取消这笔购物订单并全额退款",
              ),
              reviewRef(order, "shop"),
            )
          }
        >
          {t("Cancel order and refund", "取消订单并退款")}{" "}
          {hkd(order.receipt!.charged_minor)}
        </button>
      )}
      {order.cancel_unavailable && order.state === "completed" && (
        <p role="status">
          {t(
            "The shop cannot accept pre-dispatch cancellation.",
            "商户无法受理发货前撤单。",
          )}
        </p>
      )}
      {order.state === "refund_pending" && (
        <p role="status">
          {t(
            "Checking the merchant cancellation and Stripe refund…",
            "正在核实商户撤单和 Stripe 退款…",
          )}
        </p>
      )}
      {order.state === "refund_review" && (
        <p role="status">
          {t("The refund needs merchant review.", "这笔退款需要商户核查。")}
        </p>
      )}
      {order.state === "refunded" &&
        order.receipt?.refunded_minor != null &&
        order.receipt.net_minor != null && (
          <p role="status">
            WooCommerce #{order.receipt.order} ·{" "}
            {order.receipt.buyer_cancel_requested
              ? t("Buyer cancellation accepted", "买家撤单已受理")
              : t("Merchant refunded", "商户已退款")}
            <br />
            {t("Original test charge", "原模拟扣款")}{" "}
            {hkd(order.receipt.charged_minor)} · {t("Refunded", "已退")}{" "}
            {hkd(order.receipt.refunded_minor)} · {t("Net", "净扣款")}{" "}
            {hkd(order.receipt.net_minor)}
          </p>
        )}
      {order.state === "cancelled" && (
        <p>{t("Cancelled without payment", "已取消，未付款")}</p>
      )}
      {order.state === "expired" && (
        <p>
          {t(
            "Quote expired. Ask for a fresh cart.",
            "报价已过期，请重新查询。",
          )}
        </p>
      )}
      {order.state === "failed" && (
        <p>{t("Test payment failed.", "测试付款未完成。")}</p>
      )}
      {order.state === "unverified" && (
        <p role="alert">
          {t("Payment could not be verified.", "无法核实扣款。")}
        </p>
      )}
    </section>
  );
}
