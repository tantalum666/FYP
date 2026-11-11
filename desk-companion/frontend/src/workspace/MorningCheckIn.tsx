import { useCallback, useEffect, useState } from "react";
import { ApiError, errorText, request, write } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { followUpErrorCopy } from "./memoryFollowUp";
import {
  morningErrorCopy,
  type MorningCheckInView,
  type MorningDraft,
} from "./morningCheckInFacts";

function message(error: unknown, t: Translate) {
  const code = error instanceof ApiError ? error.code : "";
  const known = morningErrorCopy(code) ?? followUpErrorCopy(code);
  return known ? t(known[0], known[1]) : errorText(error, t);
}

export function MorningDraftCard({
  draft,
  t,
  busy,
  onApprove,
  onDiscard,
}: {
  draft: MorningDraft;
  t: Translate;
  busy: boolean;
  onApprove: () => void;
  onDiscard: () => void;
}) {
  const facts = draft.citations.filter((item) => item.body.trim());
  return (
    <div className="memory-followup-draft">
      {facts.length > 0 && (
        <ul className="morning-checkin-facts">
          {facts.map((fact) => (
            <li key={fact.followup_id}>{fact.body}</li>
          ))}
        </ul>
      )}
      <p>
        {t(
          `Alice would send one notice at ${draft.due_local} (${draft.timezone}).`,
          `Alice 会在 ${draft.due_local}（${draft.timezone}）发出一条提醒。`,
        )}
      </p>
      <p>
        {t(
          "Nothing is scheduled until you approve.",
          "在你批准之前，不会安排提醒。",
        )}
      </p>
      {!draft.ready && (
        <p>
          {t(
            "That time covers fewer than two follow-ups.",
            "这个时间覆盖的跟进少于两条。",
          )}
        </p>
      )}
      <div className="workspace-inline-actions">
        {draft.ready && (
          <button className="primary" type="button" disabled={busy} onClick={onApprove}>
            {t("Approve check-in", "批准核对")}
          </button>
        )}
        <button className="secondary" type="button" disabled={busy} onClick={onDiscard}>
          {t("Discard", "放弃")}
        </button>
      </div>
    </div>
  );
}

export function MorningCheckInCard({
  item,
  t,
  busy,
  onDismiss,
}: {
  item: MorningCheckInView;
  t: Translate;
  busy: boolean;
  onDismiss: () => void;
}) {
  const facts = item.armed ? item.citations.filter((fact) => fact.body.trim()) : [];
  return (
    <article className="memory-followup">
      {facts.length > 0 && (
        <ul className="morning-checkin-facts">
          {facts.map((fact) => (
            <li key={fact.followup_id}>{fact.body}</li>
          ))}
        </ul>
      )}
      <p>{t(item.reason_en, item.reason_zh)}</p>
      {item.armed && (
        <div className="workspace-inline-actions">
          <button className="secondary" type="button" disabled={busy} onClick={onDismiss}>
            {t("Dismiss", "关闭")}
          </button>
        </div>
      )}
    </article>
  );
}

export function MorningCheckIn({
  t,
  waiting,
  onChange,
}: {
  t: Translate;
  waiting: number;
  onChange?: () => void;
}) {
  const [checkin, setCheckin] = useState<MorningCheckInView | null>(null);
  const [dueLocal, setDueLocal] = useState("");
  const [draft, setDraft] = useState<MorningDraft | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  useDraftGuard(Boolean(dueLocal || draft), busy);
  const load = useCallback(async () => {
    const next = await request<{ checkin: MorningCheckInView | null }>(
      "/memory-followups/morning",
    );
    setCheckin(next.checkin);
    setLoaded(true);
  }, []);
  useEffect(() => {
    void load().catch((reason) => setError(reason));
  }, [load]);
  useEffect(() => {
    setDraft(null);
  }, [waiting]);
  useEffect(() => {
    const recovered = (event: Event) => {
      const path = (event as CustomEvent<{ operation: { path: string } }>).detail.operation
        .path;
      if (!path.startsWith("/memory-followups/morning")) return;
      setDraft(null);
      setDueLocal("");
      void load().catch(setError);
    };
    window.addEventListener("desk:write-recovered", recovered);
    return () => window.removeEventListener("desk:write-recovered", recovered);
  }, [load]);

  async function prepare() {
    setBusy(true);
    setError(null);
    try {
      const prepared = await request<{
        draft: MorningDraft;
        saved: boolean;
        armed: boolean;
      }>("/memory-followups/morning/drafts", {
        method: "POST",
        body: JSON.stringify({ due_local: dueLocal }),
      });
      if (prepared.saved || prepared.armed || prepared.draft.armed !== false) {
        setError(new ApiError("REQUEST_FAILED"));
        return;
      }
      setDraft(prepared.draft);
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!draft?.ready) return;
    setBusy(true);
    setError(null);
    try {
      await write("/memory-followups/morning", {
        due_local: draft.due_local,
        timezone: draft.timezone,
      });
      setDraft(null);
      setDueLocal("");
      await load();
      onChange?.();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }

  async function dismiss() {
    if (!checkin) return;
    setBusy(true);
    setError(null);
    try {
      await write(`/memory-followups/morning/${checkin.id}/dismissals`, {
        expected_version: checkin.version,
      });
      await load();
      onChange?.();
    } catch (reason) {
      if (reason instanceof ApiError && reason.code === "VERSION_CONFLICT")
        void load().catch(setError);
      setError(reason);
    } finally {
      setBusy(false);
    }
  }

  const showForm = loaded && !checkin?.armed && waiting >= 2;

  return (
    <section aria-label={t("Morning check-in", "早晨核对")}>
      <h2>{t("Morning check-in", "早晨核对")}</h2>
      <p className="workspace-hint">
        {t(
          "One notice cites every follow-up that is due by the time you approve.",
          "一条提醒会提起在你批准的时间之前到期的跟进。",
        )}
      </p>
      {!checkin?.armed && waiting < 2 && (
        <p className="workspace-hint">
          {t(
            "Approve two follow-ups first.",
            "请先批准两条跟进。",
          )}
        </p>
      )}
      {showForm && (
        <form
          className="memory-followup-form"
          onSubmit={(event) => {
            event.preventDefault();
            void prepare();
          }}
        >
          <label className="field">
            {t("Check-in", "核对时间")}
            <input
              type="datetime-local"
              value={dueLocal}
              disabled={busy || !!draft}
              onChange={(event) => {
                setDueLocal(event.target.value);
                setDraft(null);
              }}
            />
          </label>
          <button className="secondary" type="submit" disabled={busy || !!draft || !dueLocal}>
            {t("Prepare check-in", "准备核对")}
          </button>
        </form>
      )}
      {draft && (
        <MorningDraftCard
          draft={draft}
          t={t}
          busy={busy}
          onApprove={() => void approve()}
          onDiscard={() => setDraft(null)}
        />
      )}
      {checkin && (
        <MorningCheckInCard
          item={checkin}
          t={t}
          busy={busy}
          onDismiss={() => void dismiss()}
        />
      )}
      {!!error && (
        <p className="error-message" role="alert">
          {message(error, t)}
        </p>
      )}
    </section>
  );
}
