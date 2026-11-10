import { useCallback, useEffect, useState } from "react";
import { ApiError, errorText, request, write } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import type { MemoryFact } from "./MemoryFactList";
import {
  draftIsUnarmed,
  followUpActions,
  followUpErrorCopy,
  memoriesWithoutOpenFollowUp,
  type FollowUpAction,
  type FollowUpDraft,
  type FollowUpView,
} from "./memoryFollowUp";

function message(error: unknown, t: Translate) {
  const code = error instanceof ApiError ? error.code : "";
  const known = followUpErrorCopy(code);
  return known ? t(known[0], known[1]) : errorText(error, t);
}

export function MemoryFollowUpDraftCard({
  draft,
  t,
  busy,
  onApprove,
  onDiscard,
}: {
  draft: FollowUpDraft;
  t: Translate;
  busy: boolean;
  onApprove: () => void;
  onDiscard: () => void;
}) {
  return (
    <div className="memory-followup-draft">
      <p>{draft.body}</p>
      <p>
        {t(
          `Alice would raise this at ${draft.due_local} (${draft.timezone}).`,
          `Alice 会在 ${draft.due_local}（${draft.timezone}）提醒。`,
        )}
      </p>
      <p>
        {t(
          "Nothing is scheduled until you approve.",
          "在你批准之前，不会安排提醒。",
        )}
      </p>
      <div className="workspace-inline-actions">
        <button className="primary" type="button" disabled={busy} onClick={onApprove}>
          {t("Approve follow-up", "批准跟进")}
        </button>
        <button className="secondary" type="button" disabled={busy} onClick={onDiscard}>
          {t("Discard", "放弃")}
        </button>
      </div>
    </div>
  );
}

export function MemoryFollowUpCard({
  item,
  t,
  busy,
  onResolve,
}: {
  item: FollowUpView;
  t: Translate;
  busy: boolean;
  onResolve: (action: FollowUpAction) => void;
}) {
  const actions = followUpActions(item.state);
  return (
    <article className="memory-followup">
      {item.body && <p>{item.body}</p>}
      <p>{t(item.reason_en, item.reason_zh)}</p>
      {!!actions.length && (
        <div className="workspace-inline-actions">
          {actions.includes("handled") && (
            <button
              className="primary"
              type="button"
              disabled={busy}
              onClick={() => onResolve("handled")}
            >
              {t("Handled", "已处理")}
            </button>
          )}
          {actions.includes("snooze") && (
            <button
              className="secondary"
              type="button"
              disabled={busy}
              onClick={() => onResolve("snooze")}
            >
              {t("Remind me in an hour", "一小时后再提醒")}
            </button>
          )}
          {actions.includes("dismissed") && (
            <button
              className="secondary"
              type="button"
              disabled={busy}
              onClick={() => onResolve("dismissed")}
            >
              {t("Dismiss", "关闭")}
            </button>
          )}
        </div>
      )}
    </article>
  );
}

export function MemoryFollowUps({
  t,
  facts,
  onMemoryChange,
}: {
  t: Translate;
  facts: MemoryFact[];
  onMemoryChange?: () => void;
}) {
  const [followups, setFollowups] = useState<FollowUpView[]>([]);
  const [memoryId, setMemoryId] = useState("");
  const [dueLocal, setDueLocal] = useState("");
  const [draft, setDraft] = useState<FollowUpDraft | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  useDraftGuard(Boolean(dueLocal || draft), busy);
  const load = useCallback(async () => {
    const next = await request<{ followups: FollowUpView[] }>("/memory-followups");
    setFollowups(next.followups);
  }, []);
  useEffect(() => {
    void load().catch((reason) => setError(reason));
  }, [load]);
  useEffect(() => {
    if (draft && !facts.some((fact) => fact.id === draft.memory_id)) setDraft(null);
  }, [draft, facts]);
  useEffect(() => {
    const recovered = (event: Event) => {
      const path = (event as CustomEvent<{ operation: { path: string } }>).detail
        .operation.path;
      if (!path.startsWith("/memory-followups")) return;
      setDraft(null);
      setDueLocal("");
      void load().catch(setError);
    };
    window.addEventListener("desk:write-recovered", recovered);
    return () => window.removeEventListener("desk:write-recovered", recovered);
  }, [load]);

  const choices = memoriesWithoutOpenFollowUp(facts, followups);
  const open = followups.filter((item) => item.armed);
  const closed = followups.filter((item) => !item.armed);

  async function prepare() {
    setBusy(true);
    setError(null);
    try {
      const prepared = await request<{
        draft: FollowUpDraft;
        saved: boolean;
        armed: boolean;
      }>("/memory-followups/drafts", {
        method: "POST",
        body: JSON.stringify({ memory_id: memoryId, due_local: dueLocal }),
      });
      if (!draftIsUnarmed(prepared)) {
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
    if (!draft) return;
    setBusy(true);
    setError(null);
    try {
      await write("/memory-followups", {
        memory_id: draft.memory_id,
        memory_version: draft.memory_version,
        due_local: draft.due_local,
        timezone: draft.timezone,
      });
      setDraft(null);
      setDueLocal("");
      setMemoryId("");
      await load();
    } catch (reason) {
      if (reason instanceof ApiError && reason.code === "VERSION_CONFLICT")
        onMemoryChange?.();
      setError(reason);
    } finally {
      setBusy(false);
    }
  }

  async function resolve(item: FollowUpView, action: FollowUpAction) {
    setBusy(true);
    setError(null);
    try {
      await write(`/memory-followups/${item.id}/resolutions`, {
        action,
        expected_version: item.version,
      });
      await load();
    } catch (reason) {
      if (reason instanceof ApiError && reason.code === "VERSION_CONFLICT")
        void load().catch(setError);
      setError(reason);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label={t("Memory follow-ups", "记忆跟进")}>
      <h2>{t("Follow up on a memory", "跟进一条记忆")}</h2>
      <p className="workspace-hint">
        {t(
          "Alice raises it at the time you approve. Quiet hours hold it until they end.",
          "Alice 会在你批准的时间提醒。安静时段会等到结束。",
        )}
      </p>
      {!!facts.length && (
        <form
          className="memory-followup-form"
          onSubmit={(event) => {
            event.preventDefault();
            void prepare();
          }}
        >
          <label className="field">
            {t("Memory", "记忆")}
            <select
              value={memoryId}
              disabled={busy || !!draft}
              onChange={(event) => {
                setMemoryId(event.target.value);
                setDraft(null);
              }}
            >
              <option value="">{t("Choose a memory", "选择一条记忆")}</option>
              {choices.map((fact) => (
                <option key={fact.id} value={fact.id}>
                  {fact.body}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            {t("When", "时间")}
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
          <button
            className="secondary"
            type="submit"
            disabled={busy || !!draft || !memoryId || !dueLocal}
          >
            {t("Prepare follow-up", "准备跟进")}
          </button>
        </form>
      )}
      {draft && (
        <MemoryFollowUpDraftCard
          draft={draft}
          t={t}
          busy={busy}
          onApprove={() => void approve()}
          onDiscard={() => setDraft(null)}
        />
      )}
      {!!error && (
        <p className="error-message" role="alert">
          {message(error, t)}
        </p>
      )}
      {open.map((item) => (
        <MemoryFollowUpCard
          key={item.id}
          item={item}
          t={t}
          busy={busy}
          onResolve={(action) => void resolve(item, action)}
        />
      ))}
      {!!closed.length && (
        <details>
          <summary>{t("Closed follow-ups", "已结束的跟进")}</summary>
          {closed.map((item) => (
            <MemoryFollowUpCard
              key={item.id}
              item={item}
              t={t}
              busy={busy}
              onResolve={(action) => void resolve(item, action)}
            />
          ))}
        </details>
      )}
    </section>
  );
}
