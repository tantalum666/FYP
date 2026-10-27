import { useCallback, useEffect, useState } from "react";
import { Brain } from "lucide-react";
import { ApiError, errorText, request, write } from "../api";
import type { PendingWrite } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { CheckIns } from "./CheckIns";
import { GoalList } from "./GoalList";
import { AliasList } from "./AliasList";
import { ProfileSummary } from "./ProfileSummary";
import {
  actionsFor,
  knowledgeCopy,
  noteCopy,
  sourceCopy,
} from "./knowledge";
import { useWorkspace } from "./WorkspaceContext";

interface MemoryFact {
  id: string;
  body: string;
  source: string;
  note: string;
  state: string;
  version: number;
  created_at: string;
  updated_at: string;
  expires_at: string | null;
  previous_body: string | null;
  retired_duplicates: number;
}

interface MemorySuggestion {
  reason_en: string;
  reason_zh: string;
  keep: MemoryFact;
  retire: MemoryFact[];
}

interface ReviewDraft {
  id: string;
  data: {
    keep_body?: string;
    retire?: Array<{ body: string }>;
    reason_en?: string;
    reason_zh?: string;
  };
}

function sourceLabel(source: string, t: Translate) {
  const [en, zh] = sourceCopy(source);
  return t(en, zh);
}

function noteLabel(note: string, t: Translate) {
  const copy = noteCopy(note);
  return copy ? t(copy[0], copy[1]) : "";
}

export function MemoryPanel({ t }: { t: Translate }) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [facts, setFacts] = useState<MemoryFact[]>([]);
  const [expired, setExpired] = useState<MemoryFact[]>([]);
  const [retired, setRetired] = useState<MemoryFact[]>([]);
  const [suggestions, setSuggestions] = useState<MemorySuggestion[]>([]);
  const [review, setReview] = useState<ReviewDraft | null>(null);
  const [body, setBody] = useState("");
  const [editing, setEditing] = useState<{
    id: string;
    body: string;
    version: number;
  } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  useDraftGuard(!!(body.trim() || editing), busy);
  const reload = useCallback(async () => {
    if (!owner) return;
    const next = await request<{
      memories: MemoryFact[];
      expired: MemoryFact[];
      retired: MemoryFact[];
      suggestions: MemorySuggestion[];
    }>("/memory");
    setFacts(next.memories);
    setExpired(next.expired);
    setRetired(next.retired);
    setSuggestions(next.suggestions);
  }, [owner]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
  useEffect(() => {
    const recovered = (event: Event) => {
      const { operation } = (event as CustomEvent<{ operation: PendingWrite }>)
        .detail;
      if (!operation.path.startsWith("/memory")) return;
      setError(null);
      setNotice(t("Memory save confirmed.", "记忆保存已确认。"));
      const payload = operation.body as { body?: string };
      if (operation.path === "/memory" && payload.body === body) setBody("");
      if (
        editing &&
        operation.path === `/memory/${editing.id}/revisions` &&
        payload.body === editing.body
      )
        setEditing(null);
      if (editing && operation.path === `/memory/${editing.id}/deletions`)
        setEditing(null);
      void reload().catch(setError);
    };
    window.addEventListener("desk:write-recovered", recovered);
    return () => window.removeEventListener("desk:write-recovered", recovered);
  }, [body, editing, reload, t]);
  async function add() {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const saved = await write<{ duplicate?: boolean }>("/memory", { body });
      setBody("");
      setNotice(
        saved.duplicate
          ? t("That fact is already saved.", "这条事实已经保存。")
          : t("Saved to memory.", "已保存到记忆。"),
      );
      await reload();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  async function saveEdit() {
    if (!editing) return;
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      await write(`/memory/${editing.id}/revisions`, {
        body: editing.body,
        expected_version: editing.version,
      });
      setEditing(null);
      setNotice(t("Memory updated.", "记忆已更新。"));
      await reload();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  async function expire(fact: MemoryFact, days: number | null) {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      await write(`/memory/${fact.id}/expiry`, {
        expected_version: fact.version,
        expires_at:
          days === null
            ? null
            : new Date(Date.now() + days * 86400000).toISOString(),
      });
      setNotice(
        days === null
          ? t("Expiry cleared.", "已取消到期。")
          : t("Expiry saved.", "已保存到期时间。"),
      );
      await reload();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  async function reviewSuggestion(suggestion: MemorySuggestion) {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const drafted = await write<{ proposal: ReviewDraft }>(
        "/memory/consolidation",
        {
          keep_id: suggestion.keep.id,
          retire_ids: suggestion.retire.map((fact) => fact.id),
        },
      );
      setReview(drafted.proposal);
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  async function decideReview(action: "confirm" | "cancel") {
    if (!review) return;
    setBusy(true);
    setError(null);
    try {
      await write(`/assistant/proposals/${review.id}/decisions`, { action });
      setReview(null);
      setNotice(
        action === "confirm"
          ? t("Duplicate facts retired.", "已停用重复事实。")
          : t("Review cancelled.", "已取消核对。"),
      );
      await reload();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  async function remove(fact: MemoryFact) {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      await write(`/memory/${fact.id}/deletions`, {
        expected_version: fact.version,
      });
      if (editing?.id === fact.id) setEditing(null);
      setNotice(t(knowledgeCopy.forgot[0], knowledgeCopy.forgot[1]));
      await reload();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  if (!owner) {
    return (
      <section className="workspace-section" aria-label={t("Memory", "记忆")}>
        <h2>{t("Memory", "记忆")}</h2>
        <p>
          {t(
            "Sign in as owner to read or change saved facts. A paired display cannot.",
            "请以拥有者身份登录后查看或修改记忆。已配对的显示屏不能访问。",
          )}
        </p>
      </section>
    );
  }
  return (
    <section className="workspace-section" aria-label={t("Memory", "记忆")}>
      <div className="workspace-state">
        <Brain />
        <div>
          <h2>{t(knowledgeCopy.title[0], knowledgeCopy.title[1])}</h2>
          <p className="workspace-hint">
            {t(
              "Facts you save here are sent with later assistant requests. The assistant can only propose a change; you confirm it. Forgetting a fact removes it from future requests. The same wording is kept once.",
              "你保存在这里的事实会随之后的助理请求发出。助理只能提出修改，由你确认。忘掉一条后，之后的请求不再包含它。相同文字只保留一次。",
            )}
          </p>
        </div>
      </div>
      <form
        className="workspace-form-grid"
        onSubmit={(event) => {
          event.preventDefault();
          void add();
        }}
      >
        <label>
          {t("New fact", "新事实")}
          <textarea
            value={body}
            maxLength={500}
            rows={3}
            disabled={busy}
            onChange={(event) => setBody(event.target.value)}
            placeholder={t(
              "Example: Friday’s report is waiting on the group’s figures.",
              "例如：周五的报告还在等组员的数据。",
            )}
          />
        </label>
        <div className="workspace-inline-actions">
          <button
            className="primary"
            type="submit"
            disabled={busy || !body.trim()}
          >
            {t("Save fact", "保存事实")}
          </button>
        </div>
      </form>
      <ul className="calibration-steps">
        {facts.map((fact) => {
          const actions = actionsFor("active", fact.expires_at);
          return (
          <li key={fact.id}>
            <span>{fact.version}</span>
            {editing?.id === fact.id ? (
              <textarea
                value={editing.body}
                maxLength={500}
                rows={3}
                disabled={busy}
                onChange={(event) =>
                  setEditing({ ...editing, body: event.target.value })
                }
              />
            ) : (
              <>
                <p>{fact.body}</p>
                <small>
                  {sourceLabel(fact.source, t)}
                  {noteLabel(fact.note, t) ? ` · ${noteLabel(fact.note, t)}` : ""}
                  {fact.expires_at
                    ? ` · ${t("Expires ", "到期 ")}${new Date(fact.expires_at).toLocaleString()}`
                    : ""}
                  {fact.retired_duplicates
                    ? ` · ${t("Kept after retiring a duplicate", "停用重复后保留")}`
                    : ""}
                </small>
                {fact.previous_body && (
                  <small>
                    {t("Corrected from: ", "更正前：")}
                    {fact.previous_body}
                  </small>
                )}
              </>
            )}
            <div className="workspace-inline-actions">
              {editing?.id === fact.id ? (
                <>
                  <button
                    className="primary"
                    type="button"
                    disabled={busy}
                    onClick={() => void saveEdit()}
                  >
                    {t(
                      knowledgeCopy.saveCorrection[0],
                      knowledgeCopy.saveCorrection[1],
                    )}
                  </button>
                  <button
                    className="secondary"
                    type="button"
                    disabled={busy}
                    onClick={() => setEditing(null)}
                  >
                    {t("Cancel", "取消")}
                  </button>
                </>
              ) : (
                <>
                  {actions.includes("correct") && (
                    <button
                      className="secondary"
                      type="button"
                      disabled={busy}
                      onClick={() =>
                        setEditing({
                          id: fact.id,
                          body: fact.body,
                          version: fact.version,
                        })
                      }
                    >
                      {t(knowledgeCopy.correct[0], knowledgeCopy.correct[1])}
                    </button>
                  )}
                  {actions.includes("forget") && (
                    <button
                      className="secondary"
                      type="button"
                      disabled={busy}
                      onClick={() => void remove(fact)}
                    >
                      {t(knowledgeCopy.forget[0], knowledgeCopy.forget[1])}
                    </button>
                  )}
                  {(actions.includes("expire_week") ||
                    actions.includes("clear_expiry")) && (
                    <button
                      className="secondary"
                      type="button"
                      disabled={busy}
                      onClick={() =>
                        void expire(fact, fact.expires_at ? null : 7)
                      }
                    >
                      {fact.expires_at
                        ? t(
                            knowledgeCopy.clearExpiry[0],
                            knowledgeCopy.clearExpiry[1],
                          )
                        : t(
                            knowledgeCopy.expireWeek[0],
                            knowledgeCopy.expireWeek[1],
                          )}
                    </button>
                  )}
                </>
              )}
            </div>
          </li>
          );
        })}
      </ul>
      {!facts.length && (
        <p>{t(knowledgeCopy.emptyFacts[0], knowledgeCopy.emptyFacts[1])}</p>
      )}
      {suggestions.map((suggestion) => (
        <div key={suggestion.keep.id}>
          <p>{t(suggestion.reason_en, suggestion.reason_zh)}</p>
          <button
            className="secondary"
            type="button"
            disabled={busy}
            onClick={() => void reviewSuggestion(suggestion)}
          >
            {t("Review duplicates", "核对重复项")}
          </button>
        </div>
      ))}
      {review && (
        <div>
          <p>{t(review.data.reason_en ?? "", review.data.reason_zh ?? "")}</p>
          <p>
            {t("Keep: ", "保留：")}
            {review.data.keep_body}
          </p>
          {(review.data.retire ?? []).map((row, index) => (
            <p key={index}>
              {t("Retire: ", "停用：")}
              {row.body}
            </p>
          ))}
          <div className="workspace-inline-actions">
            <button
              className="primary"
              type="button"
              disabled={busy}
              onClick={() => void decideReview("confirm")}
            >
              {t("Confirm and retire duplicates", "确认并停用重复项")}
            </button>
            <button
              className="secondary"
              type="button"
              disabled={busy}
              onClick={() => void decideReview("cancel")}
            >
              {t("Cancel", "取消")}
            </button>
          </div>
        </div>
      )}
      {!!expired.length && (
        <>
          <h3>{t("Expired", "已到期")}</h3>
          <ul className="calibration-steps">
            {expired.map((fact) => (
              <li key={fact.id}>
                <p>{fact.body}</p>
                <small>
                  {t(
                    "Expired facts are not sent to the assistant.",
                    "到期的事实不会发给助理。",
                  )}
                </small>
                {actionsFor("expired", fact.expires_at).includes("forget") && (
                  <button
                    className="secondary"
                    type="button"
                    disabled={busy}
                    onClick={() => void remove(fact)}
                  >
                    {t(knowledgeCopy.forget[0], knowledgeCopy.forget[1])}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
      {!!retired.length && (
        <details>
          <summary>{t("Retired wording", "已停用的文字")}</summary>
          <ul className="calibration-steps">
            {retired.map((fact) => (
              <li key={fact.id}>
                <p>{fact.body}</p>
              </li>
            ))}
          </ul>
        </details>
      )}
      <AliasList t={t} />
      <ProfileSummary t={t} />
      <GoalList t={t} />
      <CheckIns t={t} />
      {notice && <p role="status">{notice}</p>}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
      {error instanceof ApiError && error.code === "VERSION_CONFLICT" && (
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={async () => {
            try {
              await reload();
              setEditing(null);
              setError(null);
            } catch (reason) {
              setError(reason);
            }
          }}
        >
          {t(
            "Discard correction and load current facts",
            "放弃更正并加载当前事实",
          )}
        </button>
      )}
    </section>
  );
}
