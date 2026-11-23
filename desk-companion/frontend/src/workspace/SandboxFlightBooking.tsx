import type { Translate } from "../types";
import {
  hkd,
  reviewRef,
  needsDecision,
  flightStatus,
  calendarFitLabel,
  legTime,
  type CommerceRef,
  type SandboxFlight,
} from "./commercePresentation";
export type { SandboxFlight } from "./commercePresentation";

export function SandboxFlightCard({
  flight,
  t,
  busy,
  onDecision,
}: {
  flight: SandboxFlight;
  t: Translate;
  busy: boolean;
  onDecision: (text: string, review: CommerceRef) => void;
}) {
  const total = hkd(flight.review_minor),
    revised = flight.state === "reprice",
    retry = flight.state === "submit_unknown";
  const end = flight.review_deadline_ms,
    expired = end != null && Date.now() >= end;
  const blocked =
    flight.calendar_fit !== undefined && flight.calendar_fit !== "clear";
  const choose = (message: string) =>
    onDecision(message, reviewRef(flight, "flight"));
  const legs = flight.segments.map((leg, i) => (
    <div className="commerce-leg" key={i}>
      <strong>
        {leg.flight} · {leg.origin} → {leg.destination}
      </strong>
      <div>
        {legTime(leg)} {t("local", "当地")}
      </div>
    </div>
  ));
  const canStop =
    (["processing", "answering"].includes(flight.state) &&
      !flight.stop_status) ||
    (flight.state === "stopping" &&
      ["requested", "unconfirmed"].includes(flight.stop_status ?? ""));
  return (
    <section
      className="assistant-action-card commerce-order sandbox-flight-card"
      aria-label={t("Test flight booking", "测试机票")}
    >
      {needsDecision(flight) ? (
        <>
          {legs}
          <p>
            {t("Test fare", "模拟票价")}
            {blocked && flight.can_find_other ? " " + total : ""} ·{" "}
            {flight.adults} {t("adult", "位成人")}
            {flight.calendar_fit && (
              <>
                {" "}
                ·{" "}
                <span role={blocked ? "status" : undefined}>
                  {calendarFitLabel(flight.calendar_fit, t)}
                </span>
              </>
            )}
          </p>
          {revised && flight.previous_minor != null && (
            <p role="status">
              {t("New fare", "票价已变")} · {hkd(flight.previous_minor)} →{" "}
              {total}
              {end != null && (
                <>
                  {" "}
                  ·{" "}
                  {expired
                    ? t("Expired", "已到期")
                    : t("By ", "截止 ") +
                      new Date(end).toLocaleTimeString(t("en-HK", "zh-HK"), {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                        hour12: false,
                      })}
                </>
              )}
            </p>
          )}
          {retry && <p role="status">{flightStatus(flight, t)}</p>}
          <div className="workspace-inline-actions">
            {blocked && flight.can_find_other ? (
              <button
                type="button"
                className="primary"
                disabled={busy}
                onClick={() => choose(t("Find another flight", "查其他航班"))}
              >
                {t("Find another flight", "查其他航班")}
              </button>
            ) : (
              <button
                type="button"
                disabled={busy || expired || blocked}
                className="primary"
                onClick={() =>
                  choose(
                    retry
                      ? t("Recover this test booking", "恢复原测试单")
                      : revised
                        ? t(`Accept new total ${total}`, `确认新总价 ${total}`)
                        : t(
                            `Confirm test booking at ${total}`,
                            `确认按 ${total} 预订测试航班`,
                          ),
                  )
                }
              >
                {retry
                  ? t("Recover original booking", "恢复原订单")
                  : revised
                    ? t(`Accept ${total}`, `接受 ${total}`)
                    : t(`Book for ${total}`, `确认预订 ${total}`)}
              </button>
            )}
            {!retry && (
              <button
                type="button"
                className="secondary"
                disabled={busy || expired}
                onClick={() =>
                  choose(
                    revised
                      ? t("Decline the increase", "拒绝加价")
                      : t("Cancel", "取消预订"),
                  )
                }
              >
                {revised ? t("Decline", "拒绝新价") : t("Cancel", "取消")}
              </button>
            )}
          </div>
        </>
      ) : (
        <>
          <details className="commerce-receipt">
            <summary>{flightStatus(flight, t)}</summary>
            <div className="commerce-detail-body">
              {legs}
              <div>
                LetsFG · {t("Test fare", "模拟票价")}{" "}
                {hkd(flight.approved_minor ?? flight.quoted_minor)}
              </div>
              {flight.charged_minor != null && (
                <div>
                  {t("Test charge", "模拟扣款")} {hkd(flight.charged_minor)}
                </div>
              )}
              {flight.released && (
                <div>
                  {t(
                    "Hold released · Test charge HK$0.00",
                    "预授权已释放 · 模拟扣款 HK$0.00",
                  )}
                </div>
              )}
              {flight.state === "completed" &&
                flight.pnr &&
                flight.charged_minor != null &&
                !flight.calendar_preview && (
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      choose(
                        flight.calendar_linked
                          ? t(
                              "Check this flight on my calendar",
                              "查看航班日程",
                            )
                          : t(
                              "Add this flight to my desk calendar",
                              "把这趟航班加入我的桌面日历",
                            ),
                      )
                    }
                  >
                    {flight.calendar_linked
                      ? t("Check calendar", "查看日程")
                      : t("Add to calendar", "加入日历")}
                  </button>
                )}
              {flight.stop_status === "too_late" && (
                <div>
                  {t(
                    "Ticket refunds depend on the seller’s fare rules.",
                    "已过停止窗口，退票须查卖家票规。",
                  )}
                </div>
              )}
              {["completed", "stopped", "failed", "manual"].includes(
                flight.state,
              ) && (
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    choose(t("Check my flight hold", "查回这张机票的取消结果"))
                  }
                >
                  {t("Check original booking", "查原订座")}
                </button>
              )}
            </div>
          </details>
          {flight.calendar_preview && flight.state === "completed" && (
            <div className="commerce-detail-body">
              <strong>{flight.calendar_preview.title}</strong>
              <div>
                {flight.calendar_preview.start_local
                  .replace("T", " ")
                  .slice(0, 16)}{" "}
                →{" "}
                {flight.calendar_preview.end_local
                  .replace("T", " ")
                  .slice(0, 16)}{" "}
                · {flight.calendar_preview.timezone}
              </div>
              {flight.calendar_preview.fit &&
                flight.calendar_preview.fit !== "clear" && (
                  <span role="status">
                    {calendarFitLabel(flight.calendar_preview.fit, t)}
                  </span>
                )}
              <div className="workspace-inline-actions">
                <button
                  className="primary"
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    choose(
                      t(
                        "Confirm adding this flight to my calendar",
                        "确认加入日历",
                      ),
                    )
                  }
                >
                  {t("Save to calendar", "确认加入日历")}
                </button>
                <button
                  className="secondary"
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    choose(
                      t(
                        "Skip adding this flight to my calendar",
                        "暂不加入日历",
                      ),
                    )
                  }
                >
                  {t("Skip", "暂不加入")}
                </button>
              </div>
            </div>
          )}
          {canStop && (
            <button
              className="secondary"
              type="button"
              disabled={busy}
              onClick={() =>
                choose(t("Stop this flight booking", "停止这次订票"))
              }
            >
              {t("Stop booking", "停止订票")}
            </button>
          )}
        </>
      )}
    </section>
  );
}
