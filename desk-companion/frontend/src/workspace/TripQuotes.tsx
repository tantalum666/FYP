import { useEffect, useState } from "react";
import { ApiError, errorText, request } from "../api";
import type { Translate } from "../types";
import { useDraftGuard } from "../components/DraftGuard";
import { MutationFeedback } from "./personal/MutationFeedback";
import { usePrivateMutation } from "./personal/usePrivateMutation";
import { useWorkspace } from "./WorkspaceContext";
import {
  canApproveQuote,
  formatFare,
  tripStatus,
  type TripItinerary,
} from "./tripQuoteState";

interface TripConnection {
  id: string;
  fixture_id: string;
  state: string;
  cursor_seq: number;
  task_id: string | null;
}

interface TripSnapshot {
  connection: TripConnection;
  itinerary: TripItinerary | null;
  task_version: number | null;
  purchase: string;
  saved?: boolean;
}

function tripError(error: unknown, t: Translate) {
  const code = error instanceof ApiError ? error.code : "";
  const known: Record<string, [string, string]> = {
    TRIP_QUOTE_CHANGED: [
      "This fare changed. Read the fixture again before approving.",
      "票价已变化。请重新读取夹具后再同意。",
    ],
    TRIP_ALREADY_TICKETED: [
      "A fixture receipt already covers this fare.",
      "夹具回执已经覆盖这份票价。",
    ],
    VERSION_CONFLICT: [
      "This trip changed. Read it again, then approve the fare you see.",
      "行程已变化。请重新读取，再同意当前看到的票价。",
    ],
    TRIP_ITINERARY_INVALID: [
      "The arrival is not after departure. Nothing was held.",
      "到达时间不晚于出发。没有保留。",
    ],
    PRIVATE_CONTEXT_HIDDEN: [
      "Trip details are hidden.",
      "行程详情已隐藏。",
    ],
  };
  const message = known[code];
  return message ? t(message[0], message[1]) : errorText(error, t);
}

export function TripQuotes({ t }: { t: Translate }) {
  const { data, offline, stale } = useWorkspace();
  const visible = !!data?.personal_context_visible && !offline && !stale;
  const mutation = usePrivateMutation();
  const [fixtureId, setFixtureId] = useState("hkg-tyo");
  const [snapshot, setSnapshot] = useState<TripSnapshot | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loadedId, setLoadedId] = useState("");
  useDraftGuard(visible && fixtureId !== (snapshot?.connection.fixture_id ?? loadedId), mutation.busy);

  useEffect(() => {
    if (!visible) setSnapshot(null);
  }, [visible]);

  async function load(connectionId: string) {
    const next = await request<TripSnapshot>(`/trips/connections/${connectionId}`);
    setSnapshot(next);
    setLoadedId(next.connection.fixture_id);
    window.dispatchEvent(new Event("desk:tasks"));
    return next;
  }

  async function readFixture(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    const listed = await request<{ connections: TripConnection[] }>("/trips/connections");
    const existing = listed.connections.find(
      (row) => row.fixture_id === fixtureId && row.state === "connected",
    );
    if (existing) {
      await request(`/trips/connections/${existing.id}/sync`, { method: "POST", body: "{}" });
      await load(existing.id);
      return;
    }
    await mutation.run<{ connection: TripConnection }>(
      "/trips/connections",
      { fixture_id: fixtureId },
      async (created) => {
        await request(`/trips/connections/${created.connection.id}/sync`, {
          method: "POST",
          body: "{}",
        });
        await load(created.connection.id);
      },
    );
  }

  if (!visible) return <p>{t("Trip details are hidden.", "行程详情已隐藏。")}</p>;
  const itinerary = snapshot?.itinerary;
  const connection = snapshot?.connection;
  const approve = itinerary ? canApproveQuote(itinerary) : false;
  return (
    <form className="workspace-panel" onSubmit={(event) => void readFixture(event).catch(setError)}>
      <label className="field">
        {t("Fixture", "夹具")}
        <input
          value={fixtureId}
          onChange={(event) => setFixtureId(event.target.value)}
          autoComplete="off"
          spellCheck={false}
        />
      </label>
      <button className="secondary" type="submit" disabled={mutation.busy}>
        {t("Read fixture", "读取夹具")}
      </button>
      {connection?.state === "revoked" && <p>{t("Reading stopped.", "已停止读取。")}</p>}
      {itinerary && snapshot?.purchase === "not_performed" && (
        <section>
          <p>
            {itinerary.terms.origin} to {itinerary.terms.destination}
          </p>
          <p>
            {itinerary.terms.depart_local} {itinerary.terms.timezone}
            {" → "}
            {itinerary.terms.arrive_local} {itinerary.terms.arrive_timezone}
          </p>
          <p>
            {t(
              `${itinerary.terms.passengers} passengers, ${itinerary.terms.baggage_kg} kg baggage`,
              `${itinerary.terms.passengers} 位乘客，行李 ${itinerary.terms.baggage_kg} 公斤`,
            )}
          </p>
          <p>{formatFare(itinerary.terms.total_cents, itinerary.terms.currency)}</p>
          <p>{tripStatus(itinerary, t)}</p>
          <details>
            <summary>{t("Fare rules", "票价规则")}</summary>
            <p>{itinerary.terms.fare_rules}</p>
          </details>
          {approve && connection && (
            <button
              className="primary"
              type="button"
              disabled={mutation.busy}
              onClick={() => {
                setError(null);
                void mutation
                  .run(
                    `/trips/connections/${connection.id}/holds`,
                    {
                      quote_id: itinerary.quote_id,
                      expected_task_version: snapshot.task_version,
                    },
                    async () => {
                      await load(connection.id);
                    },
                  )
                  .catch(setError);
              }}
            >
              {t("Approve this quote", "同意这份报价")}
            </button>
          )}
          {approve && <p>{t("No card is charged.", "不会扣款。")}</p>}
        </section>
      )}
      {connection?.state === "connected" && (
        <button
          className="secondary"
          type="button"
          disabled={mutation.busy}
          onClick={() => {
            setError(null);
            void mutation
              .run(`/trips/connections/${connection.id}/revocation`, {}, async () => {
                await load(connection.id);
              })
              .catch(setError);
          }}
        >
          {t("Stop reading", "停止读取")}
        </button>
      )}
      {!!error && <p role="alert">{tripError(error, t)}</p>}
      <MutationFeedback mutation={mutation} t={t} />
    </form>
  );
}
