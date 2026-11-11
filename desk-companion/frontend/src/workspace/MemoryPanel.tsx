import { useCallback, useEffect, useState } from "react";
import { Brain } from "lucide-react";
import { ApiError, errorText, request, write } from "../api";
import type { PendingWrite } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { CheckIns } from "./CheckIns";
import { GoalList } from "./GoalList";
import { DigestPanel } from "./DigestPanel";
import { SourceBriefPanel } from "./SourceBriefPanel";
import { AliasList } from "./AliasList";
import { ProfileSummary } from "./ProfileSummary";
import { actionsFor, knowledgeCopy } from "./knowledge";
import { MemoryFactList } from "./MemoryFactList";
import { MemoryFollowUps } from "./MemoryFollowUps";
import type { MemoryFact, MemoryEdit } from "./MemoryFactList";
import { useWorkspace } from "./WorkspaceContext";

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

export function MemoryPanel({ t }: { t: Translate }) {
  const { data, offline, refresh } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [facts, setFacts] = useState<MemoryFact[]>([]);
  const [expired, setExpired] = useState<MemoryFact[]>([]);
  const [retired, setRetired] = useState<MemoryFact[]>([]);
  const [suggestions, setSuggestions] = useState<MemorySuggestion[]>([]);
  const [review, setReview] = useState<ReviewDraft | null>(null);
  const [body, setBody] = useState("");
  const [editing, setEditing] = useState<MemoryEdit | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<MemoryFact | null>(null);
  useDraftGuard(!!(body.trim() || editing), busy);
  const reload = useCallback(async () => {
    if (!owner) return;
    try {
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
    } finally {
      setLoading(false);
    }
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
      setDeleting(null);
      setNotice(t(knowledgeCopy.forgot[0], knowledgeCopy.forgot[1]));
      await reload();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  if (!data) {
    return (
      <section className="workspace-section">
        <h1>{t("Saved memories", "已保存记忆")}</h1>
        <p role="status">
          {offline
            ? t("Unable to connect to your desk.", "暂时无法连接桌面主机。")
            : t("Loading your workspace…", "正在读取工作空间…")}
        </p>
        {offline && (
          <button className="secondary" onClick={() => void refresh()}>
            {t("Reconnect", "重新连接")}
          </button>
        )}
      </section>
    );
  }
  if (!owner) {
    return (
      <section
        className="workspace-section memory-page"
        aria-label={t("Memory", "记忆")}
      >
        <h1>{t("Memory", "记忆")}</h1>
        <p>
          {t(
            "Open your main desk to view or edit saved memories.",
            "请在主桌面查看或编辑已保存记忆。",
          )}
        </p>
      </section>
    );
  }
  return (
    <section
      className="workspace-section memory-page"
      aria-label={t("Memory", "记忆")}
    >
      <div className="workspace-state">
        <Brain />
        <div>
          <h1>{t(knowledgeCopy.title[0], knowledgeCopy.title[1])}</h1>
          <p className="workspace-hint">
            {t(
              "Details Alice can use in future chats.",
              "Alice 可以在之后的对话中使用这些记忆。",
            )}
          </p>
        </div>
      </div>
      <SourceBriefPanel t={t} />
      <form
        className="memory-compose"
        onSubmit={(event) => {
          event.preventDefault();
          void add();
        }}
      >
        <label className="field">
          {t("New memory", "新记忆")}
          <textarea
            value={body}
            maxLength={1000}
            rows={3}
            disabled={busy || !!editing}
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
            disabled={busy || !!editing || !body.trim()}
          >
            {t("Save", "保存")}
          </button>
        </div>
      </form>
      {loading && (
        <p role="status">
          {t("Loading saved memories…", "正在读取已保存记忆…")}
        </p>
      )}
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
      <MemoryFactList
        t={t}
        facts={facts}
        loading={loading}
        busy={busy}
        editing={editing}
        onEdit={setEditing}
        onSave={saveEdit}
        onDelete={setDeleting}
        onExpiry={expire}
      />
      <MemoryFollowUps t={t} facts={facts} onMemoryChange={() => void reload()} />
      {!loading && !error && !facts.length && (
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
          <ul className="memory-list">
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
                    onClick={() => setDeleting(fact)}
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
          <ul className="memory-list">
            {retired.map((fact) => (
              <li key={fact.id}>
                <p>{fact.body}</p>
              </li>
            ))}
          </ul>
        </details>
      )}
      <details className="knowledge-section">
        <summary>{t("Recent activity", "近期活动")}</summary>
        <DigestPanel t={t} />
      </details>
      <details className="knowledge-section">
        <summary>
          {t("Words Alice should recognize", "让 Alice 理解你的用词")}
        </summary>
        <AliasList t={t} />
      </details>
      <details className="knowledge-section">
        <summary>{t("Your profile", "你的档案")}</summary>
        <ProfileSummary
          key={facts.map((f) => `${f.id}:${f.version}`).join(",")}
          t={t}
        />
      </details>
      <details className="knowledge-section">
        <summary>{t("Goals and commitments", "目标与承诺")}</summary>
        <GoalList t={t} />
      </details>
      <details className="knowledge-section">
        <summary>{t("Check-in history", "提醒记录")}</summary>
        <CheckIns t={t} />
      </details>
      {deleting && (
        <div className="memory-delete-confirm" role="alert">
          <p>{t("Delete this saved memory?", "删除这条已保存记忆？")}</p>
          <blockquote>{deleting.body}</blockquote>
          <div className="workspace-inline-actions">
            <button
              className="danger-button"
              disabled={busy}
              onClick={() => void remove(deleting)}
            >
              {t("Delete memory", "删除记忆")}
            </button>
            <button
              className="secondary"
              disabled={busy}
              onClick={() => setDeleting(null)}
            >
              {t("Keep memory", "保留记忆")}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
