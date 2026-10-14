import { useCallback, useEffect, useState } from "react";
import { Brain } from "lucide-react";
import { errorText, request, write } from "../api";
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
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [facts, setFacts] = useState<MemoryFact[]>([]);
  const [body, setBody] = useState("");
  const [editing, setEditing] = useState<{ id: string; body: string; version: number } | null>(
    null,
  );
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  useDraftGuard(!!(body.trim() || editing), busy);
  const reload = useCallback(async () => {
    if (!owner) return;
    const next = await request<{ memories: MemoryFact[] }>("/memory");
    setFacts(next.memories);
  }, [owner]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
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
      await write(`/memory/${fact.id}/deletions`, { expected_version: fact.version });
      if (editing?.id === fact.id) setEditing(null);
      setNotice(
        t(
          "Memory deleted. The assistant will not see it again.",
          "记忆已删除，助理之后不会再看到它。",
        ),
      );
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
          <h2>{t("Memory", "记忆")}</h2>
          <p className="workspace-hint">
            {t(
              "Facts you save here are sent with later assistant requests. The assistant can only propose a change; you confirm it. Deleting a fact removes it from future requests.",
              "你保存在这里的事实会随之后的助理请求发出。助理只能提出修改，由你确认。删除后，之后的请求不再包含这条事实。",
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
            onChange={(event) => setBody(event.target.value)}
            placeholder={t(
              "Example: Friday’s report is waiting on the group’s figures.",
              "例如：周五的报告还在等组员的数据。",
            )}
          />
        </label>
        <div className="workspace-inline-actions">
          <button className="primary" type="submit" disabled={busy || !body.trim()}>
            {t("Save fact", "保存事实")}
          </button>
        </div>
      </form>
      <ul className="calibration-steps">
        {facts.map((fact) => (
          <li key={fact.id}>
            <span>{fact.version}</span>
            {editing?.id === fact.id ? (
              <textarea
                value={editing.body}
                maxLength={500}
                rows={3}
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
                  <button className="primary" type="button" disabled={busy} onClick={() => void saveEdit()}>
                    {t("Save correction", "保存更正")}
                  </button>
                  <button className="secondary" type="button" disabled={busy} onClick={() => setEditing(null)}>
                    {t("Cancel", "取消")}
                  </button>
                </>
              ) : (
                <>
                  <button
                    className="secondary"
                    type="button"
                    disabled={busy}
                    onClick={() => setEditing({ id: fact.id, body: fact.body, version: fact.version })}
                  >
                    {t("Correct", "更正")}
                  </button>
                  <button className="secondary" type="button" disabled={busy} onClick={() => void remove(fact)}>
                    {t("Delete", "删除")}
                  </button>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
      {!facts.length && <p>{t("No saved facts yet.", "还没有保存的事实。")}</p>}
      {notice && <p role="status">{notice}</p>}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </section>
  );
}
