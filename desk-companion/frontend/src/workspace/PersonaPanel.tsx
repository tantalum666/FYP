import { useCallback, useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { errorText, request, write } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";

interface Persona {
  body: string;
  version: number;
  source: "default" | "owner";
}

export function PersonaPanel({ t }: { t: Translate }) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [persona, setPersona] = useState<Persona | null>(null);
  const [body, setBody] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const dirty = !!persona && body !== persona.body;
  useDraftGuard(dirty, busy);
  const reload = useCallback(async () => {
    if (!owner) return;
    const next = await request<{ persona: Persona }>("/persona");
    setPersona(next.persona);
    setBody(next.persona.body);
  }, [owner]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
  if (!owner) {
    return (
      <section className="workspace-section">
        <h3>{t("Persona", "人格")}</h3>
        <p>
          {t(
            "Sign in as owner to edit how the assistant speaks. Pairing alone does not change it.",
            "请以拥有者身份登录后再编辑助理的说话方式。配对身份不能修改。",
          )}
        </p>
      </section>
    );
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!persona) return;
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const saved = await write<{ persona: Persona }>("/persona/revisions", {
        body,
        expected_version: persona.version,
      });
      setPersona(saved.persona);
      setBody(saved.persona.body);
      setNotice(
        t(
          "Saved. Text and voice both use this persona. It does not confirm actions by itself.",
          "已保存。文字和语音都会使用这段人格。它本身不会确认任何动作。",
        ),
      );
    } catch (reason) {
      setError(reason);
      await reload().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  }
  async function reset() {
    if (!persona) return;
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const saved = await write<{ persona: Persona }>("/persona/reset", {
        expected_version: persona.version,
      });
      setPersona(saved.persona);
      setBody(saved.persona.body);
      setNotice(t("Restored the built-in persona.", "已恢复内置人格。"));
    } catch (reason) {
      setError(reason);
      await reload().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="workspace-section" aria-label={t("Persona", "人格")}>
      <div className="workspace-state">
        <Sparkles />
        <div>
          <h3>{t("Persona", "人格")}</h3>
          <p>
            {t(
              "One text for both the text assistant and voice. The desk still appends its tool rules, so editing this does not grant a confirmation or a file path.",
              "文字助理和语音共用这一段。桌面仍会附上工具规则，因此修改这里不会获得确认权或文件路径。",
            )}
          </p>
        </div>
      </div>
      {persona?.source === "default" && (
        <p className="workspace-hint">
          {t("Using the built-in persona.", "正在使用内置人格。")}
        </p>
      )}
      <form onSubmit={save}>
        <label className="field">
          {t("Persona text", "人格文本")}
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            maxLength={4000}
            rows={10}
            required
            disabled={busy || !persona}
          />
        </label>
        <div className="workspace-inline-actions">
          <button className="primary" disabled={busy || !persona || !body.trim() || !dirty}>
            {t("Save persona", "保存人格")}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={busy || !persona || persona.source === "default"}
            onClick={() => void reset()}
          >
            {t("Restore built-in text", "恢复内置文本")}
          </button>
        </div>
      </form>
      {notice && <p role="status">{notice}</p>}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </section>
  );
}
