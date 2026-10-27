import { useCallback, useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { ApiError, errorText, request, write } from "../api";
import type { PendingWrite } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";

interface Persona {
  body: string;
  version: number;
  source: "default" | "owner";
}

export function PersonaPanel({ t }: { t: Translate }) {
  const { data, offline, refresh } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [persona, setPersona] = useState<Persona | null>(null);
  const [body, setBody] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(false);
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
  useEffect(() => {
    const recovered = (event: Event) => {
      const { operation, result } = (
        event as CustomEvent<{
          operation: PendingWrite;
          result: { persona: Persona };
        }>
      ).detail;
      if (
        operation.path !== "/persona/revisions" &&
        operation.path !== "/persona/reset"
      )
        return;
      setPersona(result.persona);
      if (
        operation.path === "/persona/reset" ||
        (operation.body as { body?: string }).body === body
      )
        setBody(result.persona.body);
      setError(null);
    };
    window.addEventListener("desk:write-recovered", recovered);
    return () => window.removeEventListener("desk:write-recovered", recovered);
  }, [body]);
  if (!data) {
    return (
      <section className="workspace-section">
        <h1>{t("Assistant style", "助理风格")}</h1>
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
      <section className="workspace-section">
        <h1>{t("Assistant style", "助理风格")}</h1>
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
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="workspace-section persona-page"
      aria-label={t("Assistant style", "助理风格")}
    >
      <div className="workspace-state">
        <Sparkles />
        <div>
          <h1>{t("Assistant style", "助理风格")}</h1>
          <p>
            {t(
              "Choose how your assistant responds in text and voice. Actions still need your confirmation.",
              "设定助理在文字和语音中的回应方式，实际操作仍然由你确认。",
            )}
          </p>
        </div>
      </div>
      <div className="persona-summary">
        <h2>
          {persona?.source === "owner"
            ? t("Your custom instructions", "你的自定义指令")
            : t("Built-in assistant style", "内置助理风格")}
        </h2>
        <p>
          {persona
            ? persona.source === "default"
              ? t(
                  "Concise, natural replies that follow your language.",
                  "简洁自然地回应，并跟随你的语言。",
                )
              : t(
                  "Your saved instructions apply to both text and voice.",
                  "你保存的指令会同时用于文字与语音。",
                )
            : t("Loading instructions…", "正在读取指令…")}
        </p>
        <button
          className="secondary"
          type="button"
          aria-expanded={expanded}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded
            ? t("Collapse editor", "收起编辑器")
            : t("Edit instructions", "编辑指令")}
        </button>
        {dirty && (
          <span className="unsaved-label" role="status">
            {t("Unsaved changes", "有未保存的修改")}
          </span>
        )}
      </div>
      <form onSubmit={save} hidden={!expanded} className="persona-editor">
        <label className="field">
          {t("Assistant instructions", "助理指令")}
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            maxLength={4000}
            rows={8}
            required
            disabled={busy || !persona}
          />
        </label>
        <div className="workspace-inline-actions">
          <button
            className="primary"
            disabled={busy || !persona || !body.trim() || !dirty}
          >
            {t("Save instructions", "保存指令")}
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
      {error instanceof ApiError && error.code === "VERSION_CONFLICT" && (
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={async () => {
            try {
              await reload();
              setError(null);
            } catch (reason) {
              setError(reason);
            }
          }}
        >
          {t(
            "Discard draft and load current persona",
            "放弃草稿并加载当前人格",
          )}
        </button>
      )}
    </section>
  );
}
