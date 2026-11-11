import { ApiError, errorText } from "../api";
import type { Translate } from "../types";
import type { Substitution } from "./purchaseCardFields";

export interface PurchaseOffer {
  offer_id: string;
  state: string;
  reason: string | null;
  total_minor: number;
  card_version: number;
  merchant: string;
  sku: string;
  quantity: number;
  unit: string;
  unit_price_minor: number;
  shipping_minor: number;
  currency: string;
  same_spec: boolean;
  address_scope: string;
  observed_at: string;
  task_id: string | null;
  receipt_id: string | null;
  purchased: false;
  live_purchase: false;
}

export interface PurchaseCard {
  id: string;
  state: "draft" | "confirmed" | "revoked";
  version: number;
  label: string;
  sku: string;
  quantity: number;
  unit: string;
  merchants: string[];
  budget_minor: number;
  currency: string;
  substitution: Substitution;
  address_scope: string;
  task_id: string | null;
  offers: PurchaseOffer[];
  purchased: false;
  live_purchase: false;
}

export interface PurchaseList {
  cards: PurchaseCard[];
  purchased: false;
  live_purchase: false;
}

export function purchaseError(error: unknown, t: Translate): string {
  const code = error instanceof ApiError ? error.code : "";
  const known: Record<string, [string, string]> = {
    FIELD_NOT_CLEARABLE: [
      "Leave a field blank to keep it. This form does not clear a saved value.",
      "留空表示保持原值。此表不会清除已保存的内容。",
    ],
    PURCHASE_CARD_NOT_CONFIRMED: [
      "Confirm the card before checking an offer.",
      "先确认卡片，再核对报价。",
    ],
    PURCHASE_CARD_REVOKED: [
      "This card is revoked. Offers are no longer checked.",
      "此卡片已撤销，不再核对报价。",
    ],
    PURCHASE_OFFER_CONFLICT: [
      "That offer id was already used for a different price or item.",
      "这个报价编号已经用于另一组价格或商品。",
    ],
    PURCHASE_APPROVAL_NOT_READY: [
      "This offer is not waiting for approval.",
      "这次报价现在不需要批准。",
    ],
    PURCHASE_RECEIPT_NOT_READY: [
      "Approve the offer before recording a receipt.",
      "记录回执前需要先批准报价。",
    ],
    PURCHASE_RECEIPT_CONFLICT: [
      "A different receipt is already recorded for this offer.",
      "这次报价已经记录了另一张回执。",
    ],
    STALE_CARD: [
      "The card changed. Check the offer again before approving it.",
      "卡片已改。请重新核对报价后再批准。",
    ],
    OPERATION_ID_CONFLICT: [
      "That save was already used for different details.",
      "这次保存已经用于另一组内容。",
    ],
  };
  if (known[code]) return t(...known[code]);
  return errorText(error, t);
}

export function offerReason(reason: string | null, t: Translate): string {
  const known: Record<string, [string, string]> = {
    currency_mismatch: [
      "Currency does not match the card.",
      "货币与卡片不一致。",
    ],
    merchant_not_allowed: [
      "That merchant is not on the card.",
      "商家不在卡片上。",
    ],
    address_scope_mismatch: [
      "Address label does not match.",
      "地址标签不一致。",
    ],
    spec_mismatch: [
      "Quantity, unit, or item does not match.",
      "数量、单位或商品不一致。",
    ],
    over_budget: [
      "Total including shipping is over the budget.",
      "含运费的总额超出预算。",
    ],
    not_cheaper: [
      "The substitute must cost less than the original item, including shipping.",
      "替代品的含运费总额必须低于原商品。",
    ],
    reference_price_required: [
      "Enter the original item's total to compare prices.",
      "请提供原商品的总额以比较价格。",
    ],
    card_changed: [
      "The card changed and needs a new check.",
      "卡片已改，需要重新核对。",
    ],
    card_revoked: ["The card was revoked.", "卡片已撤销。"],
  };
  if (reason && known[reason]) return t(...known[reason]);
  return reason ?? "";
}
