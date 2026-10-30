import { useState } from "react";
import type { Translate } from "../types";
import { actionsFor, knowledgeCopy, noteCopy, sourceCopy } from "./knowledge";

export interface MemoryFact {
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

export type MemoryEdit = Pick<MemoryFact, "id" | "body" | "version">;

function sourceLabel(source: string, t: Translate) {
  const [en, zh] = sourceCopy(source);
  return t(en, zh);
}

function noteLabel(note: string, t: Translate) {
  const copy = noteCopy(note);
  return copy ? t(copy[0], copy[1]) : "";
}

interface Props {
  t: Translate;
  facts: MemoryFact[];
  loading: boolean;
  busy: boolean;
  editing: MemoryEdit | null;
  onEdit: (edit: MemoryEdit | null) => void;
  onSave: () => Promise<void>;
  onDelete: (fact: MemoryFact) => void;
  onExpiry: (fact: MemoryFact, days: number | null) => Promise<void>;
}

/** Browse current facts; MemoryPanel owns requests, versions and draft protection. */
export function MemoryFactList({
  t,
  facts,
  loading,
  busy,
  editing,
  onEdit,
  onSave,
  onDelete,
  onExpiry,
}: Props) {
  const [query, setQuery] = useState("");
  const terms = query
    .normalize("NFKC")
    .toLocaleLowerCase()
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  const visibleFacts = facts.filter((fact) => {
    const text = fact.body.normalize("NFKC").toLocaleLowerCase();
    return terms.every((term) => text.includes(term));
  });
  return (
    <>
      <div className="memory-search">
        <label className="field">
          {t("Search active memories", "搜索有效记忆")}
          <input
            type="search"
            value={query}
            maxLength={80}
            disabled={loading || busy || !!editing}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("Search a saved detail…", "查找已保存的细节…")}
          />
        </label>
        {!!query && (
          <button
            className="secondary"
            type="button"
            disabled={busy || !!editing}
            onClick={() => setQuery("")}
          >
            {t("Clear search", "清除搜索")}
          </button>
        )}
      </div>
      {!loading && facts.length > 0 && (
        <p className="workspace-hint" role="status">
          {t(
            `${visibleFacts.length} of ${facts.length} active memories`,
            `${facts.length} 条有效记忆中显示 ${visibleFacts.length} 条`,
          )}
        </p>
      )}
      {!loading && facts.length > 0 && visibleFacts.length === 0 && (
        <p>
          {t(
            "No active memories match. Try another word or clear the search.",
            "没有匹配的有效记忆。请换个词或清除搜索。",
          )}
        </p>
      )}
      <ul className="memory-list">
        {visibleFacts.map((fact) => {
          const actions = actionsFor("active", fact.expires_at);
          return (
            <li key={fact.id}>
              {editing?.id === fact.id ? (
                <textarea
                  aria-label={t("Correct saved memory", "更正已保存记忆")}
                  value={editing.body}
                  maxLength={1000}
                  rows={3}
                  disabled={busy}
                  onChange={(event) =>
                    onEdit({ ...editing, body: event.target.value })
                  }
                />
              ) : (
                <>
                  <p>{fact.body}</p>
                  <small>
                    {sourceLabel(fact.source, t)}
                    {noteLabel(fact.note, t)
                      ? ` · ${noteLabel(fact.note, t)}`
                      : ""}
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
                      disabled={busy || !editing.body.trim()}
                      onClick={() => void onSave()}
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
                      onClick={() => onEdit(null)}
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
                        disabled={busy || !!editing}
                        onClick={() =>
                          onEdit({
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
                        disabled={busy || !!editing}
                        onClick={() => onDelete(fact)}
                      >
                        {t(knowledgeCopy.forget[0], knowledgeCopy.forget[1])}
                      </button>
                    )}
                    {(actions.includes("expire_week") ||
                      actions.includes("clear_expiry")) && (
                      <button
                        className="secondary"
                        type="button"
                        disabled={busy || !!editing}
                        onClick={() =>
                          void onExpiry(fact, fact.expires_at ? null : 7)
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
    </>
  );
}
