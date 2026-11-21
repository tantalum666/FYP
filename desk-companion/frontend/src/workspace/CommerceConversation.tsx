import { useId } from "react";
import type { Translate } from "../types";
import { SandboxShopCard } from "./SandboxShopOrder";
import { SandboxFlightCard } from "./SandboxFlightBooking";
import {
  hkd,
  calendarFitLabel,
  optionTime,
  needsDecision,
  orderKey,
  orderStatus,
  type CommerceReview,
  type CommerceRef,
  type FlightAlternatives,
  type CalendarFlightChoice,
} from "./commercePresentation";
import "./commerce-conversation.css";

type Props = {
  t: Translate;
  busy: boolean;
  onDecision: (message: string, ref: CommerceRef) => void;
};

export function OrderCard({ row, ...props }: Props & { row: CommerceReview }) {
  return row.kind === "shop" ? (
    <SandboxShopCard order={row} {...props} />
  ) : (
    <SandboxFlightCard flight={row} {...props} />
  );
}

export function OtherOrders({
  rows,
  current,
  ...props
}: Props & { rows: CommerceReview[]; current: boolean }) {
  const group = useId();
  if (!rows.length) return null;
  return (
    <details className="commerce-history">
      <summary>
        {current
          ? props.t("Other orders", "其他订单")
          : props.t("Orders", "订单")}{" "}
        ({rows.length})
      </summary>
      {rows.map((row) =>
        needsDecision(row) ? (
          <details key={orderKey(row)} name={group}>
            <summary>{orderStatus(row, props.t)}</summary>
            <OrderCard row={row} {...props} />
          </details>
        ) : (
          <OrderCard key={orderKey(row)} row={row} {...props} />
        ),
      )}
    </details>
  );
}

export function FlightChoices({
  result,
  t,
  busy,
  onSelect,
}: {
  result: FlightAlternatives;
  t: Translate;
  busy: boolean;
  onSelect: (
    message: string,
    label: string,
    calendarChoice?: CalendarFlightChoice,
  ) => void;
}) {
  const first = result.alternatives[0]?.segment;
  if (!first) return null;
  const day = first.departs.slice(0, 10);
  return (
    <div
      className="commerce-choices"
      aria-label={t("Available test flights", "可选测试航班")}
    >
      <p>
        {result.requested_calendar_fit
          ? `${result.unavailable_flight} · ${calendarFitLabel(result.requested_calendar_fit, t)}`
          : t(
              `${result.unavailable_flight} unavailable`,
              `${result.unavailable_flight} 无票`,
            )}{" "}
        · {first.origin} → {first.destination}
      </p>
      <small>
        {day} · {t("Local times · Test fares", "当地时间 · 模拟票价")}
        {result.avoid_calendar_conflicts && (
          <> · {calendarFitLabel("clear", t)}</>
        )}
      </small>
      {result.alternatives.map(({ segment, total_minor, calendar_choice }) => {
        const budget =
          result.max_minor == null
            ? ""
            : t(
                ` My budget is ${hkd(result.max_minor)}.`,
                ` 预算上限 ${hkd(result.max_minor)}。`,
              );
        const selection =
          t(
            `Recheck test flight ${segment.flight} from ${segment.origin} to ${segment.destination} on ${day} on the same terms and show me the quote.`,
            `选 ${segment.flight}，${day} 从 ${segment.origin} 到 ${segment.destination}，请按原条件重新核价给我确认。`,
          ) +
          budget +
          (result.avoid_calendar_conflicts
            ? t(" Recheck my desk calendar too.", " 仍需避开我的桌面日程。")
            : "");
        return (
          <button
            type="button"
            className="commerce-choice"
            key={segment.flight + segment.departs}
            disabled={busy}
            aria-label={t(
              `Recheck ${segment.flight}, ${segment.departs.replace("T", " ")} to ${segment.arrives.replace("T", " ")}, ${hkd(total_minor)}`,
              `重新核价 ${segment.flight}，${segment.departs.replace("T", " ")} 至 ${segment.arrives.replace("T", " ")}，${hkd(total_minor)}`,
            )}
            onClick={() =>
              onSelect(
                selection,
                t(`Select ${segment.flight}`, `选 ${segment.flight}`),
                result.avoid_calendar_conflicts
                  ? (calendar_choice ?? {
                      origin: segment.origin,
                      destination: segment.destination,
                      departure: day,
                      flight_number: segment.flight,
                      nonstop: true,
                      avoid_calendar_conflicts: true,
                      ...(result.max_minor != null
                        ? { max_hkd: result.max_minor / 100 }
                        : {}),
                    })
                  : undefined,
              )
            }
          >
            <strong>{segment.flight}</strong>
            <span>{optionTime(segment, t)}</span>
            <b>{hkd(total_minor)}</b>
          </button>
        );
      })}
    </div>
  );
}
