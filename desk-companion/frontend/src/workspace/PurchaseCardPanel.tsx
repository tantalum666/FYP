import { useCallback, useEffect, useState } from "react";
import { request, write } from "../api";
import type { Translate } from "../types";
import { formatMinor, merchantList, minorUnits } from "./purchaseCardFields";
import {
  offerReason,
  purchaseError,
  type PurchaseCard,
  type PurchaseList,
  type PurchaseOffer,
} from "./purchaseCards";
import "./purchase-cards.css";

const emptyCard = {
  label: "",
  sku: "",
  quantity: "2",
  unit: "box",
  merchants: "",
  budget: "",
  currency: "HKD",
  substitution: "none" as const,
  address: "home",
};

const emptyOffer = {
  offerId: "offer-1",
  merchant: "",
  sku: "",
  quantity: "2",
  unit: "box",
  price: "",
  shipping: "0",
  sameSpec: false,
  referenceTotal: "",
  address: "home",
};

export function PurchaseCardPanel({ t }: { t: Translate }) {
  const [cards, setCards] = useState<PurchaseCard[]>([]);
  const [adding, setAdding] = useState(true);
  const [cardForm, setCardForm] = useState<{
    label: string;
    sku: string;
    quantity: string;
    unit: string;
    merchants: string;
    budget: string;
    currency: string;
    substitution: "none" | "same_spec_cheaper";
    address: string;
  }>(emptyCard);
  const [offerForms, setOfferForms] = useState<
    Record<string, typeof emptyOffer>
  >({});
  const [receipts, setReceipts] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const body = await request<PurchaseList>("/purchase-cards");
    setCards(body.cards);
    setAdding(body.cards.length === 0);
  }, []);

  useEffect(() => {
    void load().catch((reason) => setError(purchaseError(reason, t)));
  }, [load, t]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
      await load();
    } catch (reason) {
      setError(purchaseError(reason, t));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="purchase-card" id="purchase-card">
      <h2>{t("Usual purchase", "常买的东西")}</h2>
      <p>
        {t(
          "Save what you will accept. Nothing is bought from this page.",
          "保存你接受的条件。此页不会购买。",
        )}
      </p>
      {cards.map((card) => (
        <CardBlock
          key={card.id}
          card={card}
          t={t}
          busy={busy}
          offer={
            offerForms[card.id] ?? {
              ...emptyOffer,
              merchant: card.merchants[0] ?? "",
            }
          }
          receiptId={receipts[card.id] ?? ""}
          onOffer={(next) =>
            setOfferForms((old) => ({ ...old, [card.id]: next }))
          }
          onReceipt={(value) =>
            setReceipts((old) => ({ ...old, [card.id]: value }))
          }
          onRun={run}
          onInvalid={setError}
        />
      ))}
      {adding ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const budget = minorUnits(cardForm.budget);
            const quantity = Number(cardForm.quantity);
            if (
              budget === null ||
              !Number.isInteger(quantity) ||
              quantity < 1
            ) {
              setError(
                t("Check the quantity and budget.", "请检查数量和预算。"),
              );
              return;
            }
            void run(async () => {
              await write("/purchase-cards", {
                label: cardForm.label.trim(),
                sku: cardForm.sku.trim().toLowerCase(),
                quantity,
                unit: cardForm.unit.trim().toLowerCase(),
                merchants: merchantList(cardForm.merchants),
                budget_minor: budget,
                currency: cardForm.currency.trim().toUpperCase(),
                substitution: cardForm.substitution,
                address_scope: cardForm.address.trim().toLowerCase(),
              });
              setCardForm(emptyCard);
            });
          }}
        >
          <label>
            {t("Item", "物品")}
            <input
              aria-label={t("Item", "物品")}
              value={cardForm.label}
              onChange={(event) =>
                setCardForm({ ...cardForm, label: event.target.value })
              }
              required
            />
          </label>
          <label>
            {t("SKU", "商品编号")}
            <input
              aria-label={t("SKU", "商品编号")}
              value={cardForm.sku}
              onChange={(event) =>
                setCardForm({ ...cardForm, sku: event.target.value })
              }
              required
            />
          </label>
          <label>
            {t("Quantity", "数量")}
            <input
              aria-label={t("Quantity", "数量")}
              inputMode="numeric"
              value={cardForm.quantity}
              onChange={(event) =>
                setCardForm({ ...cardForm, quantity: event.target.value })
              }
              required
            />
          </label>
          <label>
            {t("Unit", "单位")}
            <input
              aria-label={t("Unit", "单位")}
              value={cardForm.unit}
              onChange={(event) =>
                setCardForm({ ...cardForm, unit: event.target.value })
              }
              required
            />
          </label>
          <label>
            {t("Merchants", "商家")}
            <input
              aria-label={t("Merchants", "商家")}
              value={cardForm.merchants}
              onChange={(event) =>
                setCardForm({ ...cardForm, merchants: event.target.value })
              }
              required
            />
          </label>
          <label>
            {t("Budget including shipping", "含运费预算")}
            <input
              aria-label={t("Budget including shipping", "含运费预算")}
              inputMode="decimal"
              value={cardForm.budget}
              onChange={(event) =>
                setCardForm({ ...cardForm, budget: event.target.value })
              }
              required
            />
          </label>
          <label>
            {t("Currency", "货币")}
            <input
              aria-label={t("Currency", "货币")}
              value={cardForm.currency}
              onChange={(event) =>
                setCardForm({ ...cardForm, currency: event.target.value })
              }
              required
            />
          </label>
          <label>
            {t("Substitute", "替代")}
            <select
              aria-label={t("Substitute", "替代")}
              value={cardForm.substitution}
              onChange={(event) =>
                setCardForm({
                  ...cardForm,
                  substitution: event.target.value as
                    "none" | "same_spec_cheaper",
                })
              }
            >
              <option value="none">
                {t("Exact item only", "只要完全相同的商品")}
              </option>
              <option value="same_spec_cheaper">
                {t("Same spec if cheaper", "同规格且更便宜可以")}
              </option>
            </select>
          </label>
          <label>
            {t("Address label", "地址标签")}
            <input
              aria-label={t("Address label", "地址标签")}
              value={cardForm.address}
              onChange={(event) =>
                setCardForm({ ...cardForm, address: event.target.value })
              }
              required
            />
          </label>
          <div className="purchase-actions">
            <button className="primary" type="submit" disabled={busy}>
              {t("Save purchase card", "保存购买卡片")}
            </button>
          </div>
        </form>
      ) : (
        <button
          className="text-button"
          type="button"
          onClick={() => setAdding(true)}
        >
          {t("Add another item", "再加一件")}
        </button>
      )}
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

function CardBlock({
  card,
  t,
  busy,
  offer,
  receiptId,
  onOffer,
  onReceipt,
  onRun,
  onInvalid,
}: {
  card: PurchaseCard;
  t: Translate;
  busy: boolean;
  offer: typeof emptyOffer;
  receiptId: string;
  onOffer: (next: typeof emptyOffer) => void;
  onReceipt: (value: string) => void;
  onRun: (action: () => Promise<void>) => Promise<void>;
  onInvalid: (message: string) => void;
}) {
  const latest = card.offers[0];
  return (
    <article aria-label={card.label}>
      <h3>{card.label}</h3>
      <p>
        {card.quantity} {card.unit} · {card.sku} · {card.merchants.join(", ")} ·{" "}
        {formatMinor(card.budget_minor, card.currency)} · {card.address_scope}
      </p>
      <p role="status">
        {card.state === "draft"
          ? t(
              "Not confirmed. No offer is checked yet.",
              "尚未确认。还不会核对报价。",
            )
          : card.state === "revoked"
            ? t("Revoked.", "已撤销。")
            : t("Confirmed. Nothing has been bought.", "已确认。没有购买。")}
      </p>
      {card.state === "draft" && (
        <button
          className="primary"
          type="button"
          disabled={busy}
          onClick={() =>
            void onRun(() =>
              write(`/purchase-cards/${card.id}/confirmation`, {
                expected_version: card.version,
              }),
            )
          }
        >
          {t("Confirm purchase card", "确认购买卡片")}
        </button>
      )}
      {card.state === "confirmed" && (
        <OfferForm
          card={card}
          offer={offer}
          latest={latest}
          receiptId={receiptId}
          t={t}
          busy={busy}
          onOffer={onOffer}
          onReceipt={onReceipt}
          onRun={onRun}
          onInvalid={onInvalid}
        />
      )}
    </article>
  );
}

function OfferForm({
  card,
  offer,
  latest,
  receiptId,
  t,
  busy,
  onOffer,
  onReceipt,
  onRun,
  onInvalid,
}: {
  card: PurchaseCard;
  offer: typeof emptyOffer;
  latest: PurchaseOffer | undefined;
  receiptId: string;
  t: Translate;
  busy: boolean;
  onOffer: (next: typeof emptyOffer) => void;
  onReceipt: (value: string) => void;
  onRun: (action: () => Promise<void>) => Promise<void>;
  onInvalid: (message: string) => void;
}) {
  return (
    <>
      {latest && (
        <p role="status">
          {latest.state === "needs_approval"
            ? t(
                "Needs your approval. Nothing has been bought.",
                "需要你批准。没有购买。",
              )
            : latest.state === "approved"
              ? t(
                  "Approved. Waiting for a fixture receipt. This is not a purchase.",
                  "已批准。等待夹具回执。这不是购买。",
                )
              : latest.state === "receipt_recorded"
                ? t(
                    "Fixture receipt recorded. This is not a live purchase.",
                    "已记录夹具回执。这不是真实购买。",
                  )
                : latest.state === "opened"
                  ? t(
                      "The check stopped before it finished. Nothing was approved.",
                      "核对在完成前停止了。没有批准。",
                    )
                  : latest.state === "needs_reapproval"
                    ? t(
                        "The card changed. Check the offer again.",
                        "卡片已改。请重新核对报价。",
                      )
                    : offerReason(latest.reason, t)}
        </p>
      )}
      {latest?.state === "needs_approval" && (
        <button
          className="primary"
          type="button"
          disabled={busy}
          onClick={() =>
            void onRun(() =>
              write(
                `/purchase-cards/${card.id}/offers/${latest.offer_id}/approval`,
                { expected_version: latest.card_version },
              ),
            )
          }
        >
          {t("Approve this offer", "批准这次报价")}
        </button>
      )}
      {latest?.state === "approved" && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void onRun(() =>
              write(
                `/purchase-cards/${card.id}/offers/${latest.offer_id}/receipt`,
                {
                  receipt_id: receiptId.trim().toLowerCase(),
                },
              ),
            );
          }}
        >
          <label>
            {t("Receipt id", "回执编号")}
            <input
              aria-label={t("Receipt id", "回执编号")}
              value={receiptId}
              onChange={(event) => onReceipt(event.target.value)}
              required
            />
          </label>
          <div className="purchase-actions">
            <button className="primary" type="submit" disabled={busy}>
              {t("Record fixture receipt", "记录夹具回执")}
            </button>
          </div>
        </form>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          const price = minorUnits(offer.price, true);
          const shipping = minorUnits(offer.shipping, true);
          const quantity = Number(offer.quantity);
          if (
            price === null ||
            shipping === null ||
            !Number.isInteger(quantity) ||
            quantity < 1
          ) {
            onInvalid(
              t(
                "Check the price, shipping, and quantity.",
                "请检查单价、运费和数量。",
              ),
            );
            return;
          }
          void onRun(() =>
            write(`/purchase-cards/${card.id}/offers`, {
              offer_id: offer.offerId.trim().toLowerCase(),
              merchant: offer.merchant.trim().toLowerCase(),
              sku: offer.sku.trim().toLowerCase(),
              quantity,
              unit: offer.unit.trim().toLowerCase(),
              unit_price_minor: price,
              shipping_minor: shipping,
              currency: card.currency,
              address_scope: offer.address.trim().toLowerCase(),
              observed_at: new Date().toISOString(),
              same_spec: offer.sameSpec,
              ...(offer.referenceTotal.trim()
                ? { reference_total_minor: minorUnits(offer.referenceTotal) }
                : {}),
            }),
          );
        }}
      >
        <label>
          {t("Offer id", "报价编号")}
          <input
            aria-label={t("Offer id", "报价编号")}
            value={offer.offerId}
            onChange={(event) =>
              onOffer({ ...offer, offerId: event.target.value })
            }
            required
          />
        </label>
        <label>
          {t("Offer merchant", "报价商家")}
          <input
            aria-label={t("Offer merchant", "报价商家")}
            value={offer.merchant}
            onChange={(event) =>
              onOffer({ ...offer, merchant: event.target.value })
            }
            required
          />
        </label>
        <label>
          {t("Offer SKU", "报价商品编号")}
          <input
            aria-label={t("Offer SKU", "报价商品编号")}
            value={offer.sku}
            onChange={(event) => onOffer({ ...offer, sku: event.target.value })}
            required
          />
        </label>
        <label>
          {t("Offer quantity", "报价数量")}
          <input
            aria-label={t("Offer quantity", "报价数量")}
            inputMode="numeric"
            value={offer.quantity}
            onChange={(event) =>
              onOffer({ ...offer, quantity: event.target.value })
            }
            required
          />
        </label>
        <label>
          {t("Offer unit", "报价单位")}
          <input
            aria-label={t("Offer unit", "报价单位")}
            value={offer.unit}
            onChange={(event) =>
              onOffer({ ...offer, unit: event.target.value })
            }
            required
          />
        </label>
        <label>
          {t("Unit price", "单价")}
          <input
            aria-label={t("Unit price", "单价")}
            inputMode="decimal"
            value={offer.price}
            onChange={(event) =>
              onOffer({ ...offer, price: event.target.value })
            }
            required
          />
        </label>
        <label>
          {t("Shipping", "运费")}
          <input
            aria-label={t("Shipping", "运费")}
            inputMode="decimal"
            value={offer.shipping}
            onChange={(event) =>
              onOffer({ ...offer, shipping: event.target.value })
            }
            required
          />
        </label>
        <label>
          {t("Offer address label", "报价地址标签")}
          <input
            aria-label={t("Offer address label", "报价地址标签")}
            value={offer.address}
            onChange={(event) =>
              onOffer({ ...offer, address: event.target.value })
            }
            required
          />
        </label>
        <label className="purchase-check">
          <input
            type="checkbox"
            aria-label={t("Same spec substitute", "同规格替代")}
            checked={offer.sameSpec}
            onChange={(event) =>
              onOffer({ ...offer, sameSpec: event.target.checked })
            }
          />
          {t("Same spec substitute", "同规格替代")}
        </label>
        {offer.sameSpec && (
          <label>
            {t("Original item total including shipping", "原商品含运费总额")}
            <input
              inputMode="decimal"
              required
              value={offer.referenceTotal}
              onChange={(event) =>
                onOffer({ ...offer, referenceTotal: event.target.value })
              }
            />
          </label>
        )}
        <div className="purchase-actions">
          <button className="secondary" type="submit" disabled={busy}>
            {latest?.state === "opened"
              ? t("Finish checking this offer", "完成这次核对")
              : t("Check this offer", "核对这次报价")}
          </button>
        </div>
      </form>
    </>
  );
}
