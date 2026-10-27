import { useCallback, useEffect, useState } from "react";
import { Brain } from "lucide-react";
import { ApiError, errorText, request, write } from "../api";
import type { PendingWrite } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";

interface MemoryFact {
  id: string;
  body: string;
  source: string;
  version: number;
  updated_at: string;
}

export function MemoryPanel({ t }: { t: Translate }) {
  const { data, offline, refresh } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [facts, setFacts] = useState<MemoryFact[]>([]);
  const [body, setBody] = useState("");
  const [editing, setEditing] = useState<{
    id: string;
    body: string;
    version: number;
  } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);
  useDraftGuard(!!(body.trim() || editing), busy);
  const reload = useCallback(async () => {
    if (!owner) return;
    try {
      const next = await request<{ memories: MemoryFact[] }>("/memory");
      setFacts(next.memories);
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
      await write("/memory", { body });
      setBody("");
      setNotice(t("Saved to memory.", "已保存到记忆。"));
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
      setNotice(
        t(
          "Memory deleted. Future assistant requests will not include this fact.",
          "记忆已删除，之后的助理请求不会再包含这条事实。",
        ),
      );
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
      <section className="workspace-section" aria-label={t("Memory", "记忆")}>
        <h1>{t("Saved memories", "已保存记忆")}</h1>
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
    <section
      className="workspace-section memory-page"
      aria-label={t("Saved memories", "已保存记忆")}
    >
      <div className="workspace-state">
        <Brain />
        <div>
          <h1>{t("Saved memories", "已保存记忆")}</h1>
          <p className="workspace-hint">
            {t(
              "Keep useful details for future conversations. You choose what to save, correct or remove.",
              "保存对未来对话有用的细节，由你决定保留、更正或删除。",
            )}
          </p>
        </div>
      </div>
      <form
        className="memory-compose"
        onSubmit={(event) => {
          event.preventDefault();
          void add();
        }}
      >
        <label className="field">
          {t("Add a memory", "添加记忆")}
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
        <p className="workspace-hint">
          {t(
            "Saved facts are included in later assistant requests. Deleting one stops it being included in future requests.",
            "已保存的事实会用于之后的助理请求；删除后，新的请求不再包含它。",
          )}
        </p>
      </form>
      {loading && (
        <p role="status">
          {t("Loading saved memories…", "正在读取已保存记忆…")}
        </p>
      )}
      <ul className="memory-list">
        {facts.map((fact) => (
          <li key={fact.id}>
            {editing?.id === fact.id ? (
              <textarea
                aria-label={t("Correct saved memory", "更正已保存记忆")}
                value={editing.body}
                maxLength={500}
                rows={3}
                disabled={busy}
                onChange={(event) =>
                  setEditing({ ...editing, body: event.target.value })
                }
              />
            ) : (
              <p>{fact.body}</p>
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
                    {t("Save correction", "保存更正")}
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
                    {t("Correct", "更正")}
                  </button>
                  <button
                    className="secondary"
                    type="button"
                    disabled={busy}
                    onClick={() => setDeleting(fact.id)}
                  >
                    {t("Delete", "删除")}
                  </button>
                </>
              )}
            </div>
            {deleting === fact.id && (
              <div className="memory-delete-confirm" role="alert">
                <p>{t("Delete this saved memory?", "删除这条已保存记忆？")}</p>
                <div className="workspace-inline-actions">
                  <button
                    className="danger-button"
                    disabled={busy}
                    onClick={() => void remove(fact)}
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
          </li>
        ))}
      </ul>
      {!loading && !error && !facts.length && (
        <p className="management-empty">
          {t(
            "No saved memories yet. Add a useful detail above to get started.",
            "还没有保存的记忆，可以先添加一条有用的细节。",
          )}
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
    </section>
  );
}
