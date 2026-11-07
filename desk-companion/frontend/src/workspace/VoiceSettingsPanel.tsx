import { useEffect, useRef, useState } from "react";
import { ApiError, errorText, request, write, type PendingWrite } from "../api";
import { apiOrigin } from "../native";
import type { Translate } from "../types";
import { useDraftGuard } from "../components/DraftGuard";

type VoiceChoice = {
  id: string;
  name: string;
  description: string;
  custom: boolean;
  preview: boolean;
};
type VoicePreferences = {
  version: number;
  voice: string;
  delivery: string;
  supported: boolean;
  choices: VoiceChoice[];
};

function VoicePreview({ id, t }: { id: string; t: Translate }) {
  const player = useRef<HTMLAudioElement>(null);
  useEffect(() => {
    const node = player.current;
    return () => {
      if (node) {
        node.pause();
        node.removeAttribute("src");
        node.load();
      }
    };
  }, [id]);
  return (
    <audio
      ref={player}
      controls
      preload="none"
      aria-label={t("Voice preview", "音色试听")}
      src={
        new URL(
          `/api/voice/settings/sample/${encodeURIComponent(id)}`,
          apiOrigin(),
        ).href
      }
    />
  );
}

export function VoiceSettingsPanel({ t }: { t: Translate }) {
  const [saved, setSaved] = useState<VoicePreferences>();
  const [voice, setVoice] = useState("");
  const [delivery, setDelivery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const alive = useRef(true);
  const dirty =
    !!saved && (voice !== saved.voice || delivery !== saved.delivery);
  useDraftGuard(dirty, busy);
  function accept(value: VoicePreferences) {
    setSaved(value);
    setVoice(value.voice);
    setDelivery(value.delivery);
  }
  useEffect(() => {
    alive.current = true;
    void request<VoicePreferences>("/voice/settings")
      .then((value) => {
        if (alive.current) accept(value);
      })
      .catch((reason) => {
        if (alive.current) setError(reason);
      });
    return () => {
      alive.current = false;
    };
  }, []);
  useEffect(() => {
    const recovered = (event: Event) => {
      const { operation, result } = (
        event as CustomEvent<{
          operation: PendingWrite;
          result: Pick<VoicePreferences, "version" | "voice" | "delivery">;
        }>
      ).detail;
      if (operation.path !== "/voice/settings") return;
      setSaved((current) => (current ? { ...current, ...result } : current));
      const requested = operation.body as { voice?: string; delivery?: string };
      if (requested.voice === voice && requested.delivery === delivery) {
        setVoice(result.voice);
        setDelivery(result.delivery);
      }
      setError(null);
    };
    window.addEventListener("desk:write-recovered", recovered);
    return () => window.removeEventListener("desk:write-recovered", recovered);
  }, [voice, delivery]);
  const choice = saved?.choices.find((item) => item.id === voice);
  return (
    <section
      className="persona-summary voice-preferences"
      aria-label={t("Alice's voice", "Alice 的声音")}
    >
      <h2>{t("Alice's voice", "Alice 的声音")}</h2>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          if (!saved) return;
          setBusy(true);
          setError(null);
          setNotice("");
          try {
            const result = await write<{
              version: number;
              voice: string;
              delivery: string;
            }>("/voice/settings", {
              expected_version: saved.version,
              voice,
              delivery,
            });
            if (alive.current) {
              accept({ ...saved, ...result });
              setNotice(
                t(
                  "Saved for your next conversation.",
                  "已保存，下次语音对话生效。",
                ),
              );
            }
          } catch (reason) {
            if (alive.current) setError(reason);
          } finally {
            if (alive.current) setBusy(false);
          }
        }}
      >
        <label className="field">
          {t("Voice", "音色")}
          <select
            value={voice}
            onChange={(event) => setVoice(event.target.value)}
            disabled={busy || !saved?.supported}
          >
            {saved?.choices.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        {choice?.preview && (
          <VoicePreview key={choice.id} id={choice.id} t={t} />
        )}
        <details>
          <summary>{t("Speaking style", "说话方式")}</summary>
          <label className="field">
            {t("How Alice should speak", "希望 Alice 怎样说话")}
            <textarea
              rows={4}
              value={delivery}
              maxLength={1600}
              disabled={busy || !saved?.supported}
              onChange={(event) => setDelivery(event.target.value)}
              placeholder={t(
                "Natural phrasing, a gentle tone, and the language I speak…",
                "自然连贯，语气轻柔，跟随我说的语言…",
              )}
            />
          </label>
        </details>
        <button
          className="primary"
          disabled={busy || !saved?.supported || !dirty}
        >
          {t("Save voice", "保存声音")}
        </button>
      </form>
      {saved && !saved.supported && (
        <p>
          {t(
            "These voice choices apply when GPT Live is selected.",
            "这些音色用于 GPT Live。",
          )}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {!!error && (
        <p role="alert" className="error-message">
          {errorText(error, t)}
        </p>
      )}
      {error instanceof ApiError && error.code === "VERSION_CONFLICT" && (
        <button
          className="secondary"
          onClick={() =>
            void request<VoicePreferences>("/voice/settings")
              .then((value) => {
                if (alive.current) {
                  accept(value);
                  setError(null);
                }
              })
              .catch(setError)
          }
        >
          {t("Load saved voice", "加载已保存的声音")}
        </button>
      )}
    </section>
  );
}
