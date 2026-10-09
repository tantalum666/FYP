import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { Maximize2, RotateCcw, Settings2, Volume2 } from "lucide-react";
import { useWorkspace } from "./WorkspaceContext";
import {
  assistantState,
  inspectVrm,
  MAX_MODEL_BYTES,
  SAMPLE_MODEL,
} from "../avatar/model";
import type { AvatarState, PlaybackSample } from "../avatar/model";
import { previewVoice, subscribePlayback } from "../avatar/playback";
import "./avatar.css";

const AvatarScene = lazy(() => import("../avatar/AvatarScene"));
const LABELS: Record<AvatarState, [string, string]> = {
  idle: ["Here for your day", "陪你从容安排每一天"],
  listening: ["Listening", "正在聆听"],
  speaking: ["Speaking", "正在说话"],
  thinking: ["Thinking", "正在思考"],
  confirm: ["Review on your screen", "请在屏幕上确认"],
  connecting: ["Connecting", "正在连接"],
  alert: ["A small adjustment", "调整一下姿势"],
  disconnected: ["Desk not connected", "桌面主机未连接"],
};

export function Avatar({
  standalone = false,
  language,
}: {
  standalone?: boolean;
  language?: "en" | "zh";
}) {
  const { data, offline, stale } = useWorkspace();
  const [localLanguage, setLanguage] = useState(
    () =>
      localStorage.getItem("desk.avatar.language.v1") ??
      localStorage.getItem("desk.device.language.v1") ??
      "en",
  );
  const zh = (language ?? localLanguage) === "zh";
  const t = (en: string, cn: string) => (zh ? cn : en);
  const params = new URLSearchParams(location.search),
    clean = standalone && params.get("clean") === "1";
  const [mirrored, setMirrored] = useState(params.get("mirror") === "1");
  const [url, setUrl] = useState(SAMPLE_MODEL),
    [modelName, setModelName] = useState("pixiv sample");
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [retry, setRetry] = useState(0),
    [fileError, setFileError] = useState(false);
  const [preview, setPreview] = useState<AvatarState | null>(null),
    [paused, setPaused] = useState(false);
  const [visible, setVisible] = useState(!document.hidden),
    [reduced, setReduced] = useState(false);
  const stage = useRef<HTMLDivElement>(null),
    mouth = useRef<PlaybackSample | null>(null);
  const stopPreview = useRef<(() => void) | null>(null),
    previewGeneration = useRef(0);
  const fileGeneration = useRef(0);
  const actual = assistantState(data, offline || stale);
  const state = preview ?? actual;
  const onStatus = useCallback(
    (next: "loading" | "ready" | "error", name?: string) => {
      setStatus(next);
      if (name) setModelName(name);
    },
    [],
  );
  const stopAudio = useCallback(() => {
    previewGeneration.current++;
    stopPreview.current?.();
    stopPreview.current = null;
    mouth.current = null;
  }, []);

  useEffect(() => {
    let intersecting = true;
    const update = () => setVisible(!document.hidden && intersecting);
    const observer = new IntersectionObserver((entries) => {
      intersecting = entries[0]?.isIntersecting ?? false;
      update();
    });
    if (stage.current) observer.observe(stage.current);
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const motion = () => setReduced(media.matches);
    motion();
    media.addEventListener("change", motion);
    document.addEventListener("visibilitychange", update);
    return () => {
      observer.disconnect();
      media.removeEventListener("change", motion);
      document.removeEventListener("visibilitychange", update);
      stopAudio();
      fileGeneration.current++;
    };
  }, [stopAudio]);
  useEffect(
    () =>
      subscribePlayback((sample) => {
        if (preview === null) mouth.current = sample;
      }),
    [preview],
  );
  useEffect(() => {
    if (data?.voice.active) {
      stopAudio();
      setPreview(null);
    }
  }, [data?.voice.active, stopAudio]);
  useEffect(
    () => () => {
      if (url.startsWith("blob:")) URL.revokeObjectURL(url);
    },
    [url],
  );

  async function chooseModel(file?: File) {
    if (!file) return;
    const generation = ++fileGeneration.current;
    setFileError(false);
    try {
      if (
        !file.name.toLowerCase().endsWith(".vrm") ||
        file.size > MAX_MODEL_BYTES
      )
        throw new Error("MODEL_FILE");
      inspectVrm(await file.arrayBuffer());
      if (generation !== fileGeneration.current) return;
      stopAudio();
      setPreview(null);
      setStatus("loading");
      setUrl(URL.createObjectURL(file));
    } catch {
      if (generation === fileGeneration.current) setFileError(true);
    }
  }
  function choosePreview(next: AvatarState | null) {
    stopAudio();
    setPreview(next);
  }
  async function speakPreview() {
    stopAudio();
    setFileError(false);
    setPreview("speaking");
    const generation = previewGeneration.current;
    try {
      const stop = await previewVoice(
        (sample) => {
          if (generation === previewGeneration.current) mouth.current = sample;
        },
        () => {
          if (generation === previewGeneration.current) {
            mouth.current = null;
            setPreview("idle");
            stopPreview.current = null;
          }
        },
      );
      if (generation !== previewGeneration.current) stop();
      else stopPreview.current = stop;
    } catch {
      if (generation === previewGeneration.current) {
        mouth.current = null;
        setPreview("idle");
        setFileError(true);
      }
    }
  }
  return (
    <div
      ref={stage}
      className={`companion-stage ${standalone ? "standalone" : "embedded"} ${clean ? "clean" : ""}`}
      data-avatar-state={state}
      data-avatar-status={status}
    >
      {standalone && !clean && (
        <header className="avatar-header">
          <a href="/">
            Desk Companion
            <span>{t("A presence for your workspace", "桌面上的陪伴")}</span>
          </a>
          <button
            onClick={() => {
              const next = zh ? "en" : "zh";
              setLanguage(next);
              localStorage.setItem("desk.avatar.language.v1", next);
            }}
          >
            {zh ? "English" : "简体中文"}
          </button>
        </header>
      )}
      <div
        className={`avatar-viewport ${mirrored ? "mirrored" : ""}`}
        role="img"
        aria-label={t("Full-body 3D anime companion", "全身3D二次元伙伴")}
      >
        <Suspense fallback={null}>
          {status !== "error" && (
            <AvatarScene
              key={`${url}-${retry}`}
              url={url}
              state={state}
              active={visible && !paused}
              reduced={reduced}
              mouth={mouth}
              allowMouth={
                preview === "speaking" ||
                (!!data?.voice.active && !offline && !stale)
              }
              onStatus={onStatus}
            />
          )}
        </Suspense>
      </div>
      {status === "loading" && (
        <div className="avatar-placeholder" role="status">
          <span className="avatar-loading-orbit" />
          {t("Preparing your companion…", "正在准备你的伙伴…")}
        </div>
      )}
      {status === "error" && (
        <div className="avatar-placeholder" role="alert">
          <strong>{t("3D character unavailable", "暂时无法显示3D角色")}</strong>
          <p>
            {t(
              "Try again, use another VRM, or return to your calendar.",
              "可重试、更换VRM，或返回日历。",
            )}
          </p>
          <button
            onClick={() => {
              setStatus("loading");
              setRetry((n) => n + 1);
            }}
          >
            <RotateCcw size={16} />
            {t("Retry character", "重试加载")}
          </button>
          <a href="/">{t("Open calendar", "打开日历")}</a>
        </div>
      )}
      {!clean && (
        <div className="avatar-caption">
          <span className={`avatar-status-dot state-${state}`} />
          <span aria-live="polite">
            {preview !== null ? t("Preview · ", "预览 · ") : ""}
            {LABELS[state][zh ? 1 : 0]}
          </span>
          {paused && <small>{t("Animation paused", "动画已暂停")}</small>}
        </div>
      )}
      {standalone && !clean && (
        <details className="avatar-controls">
          <summary>
            <Settings2 size={16} />
            {t("Character controls", "角色设置")}
          </summary>
          <div className="avatar-controls-body">
            <p>
              {t("Development avatar", "开发示范角色")} ·{" "}
              {url === SAMPLE_MODEL ? "pixiv Inc." : modelName}
            </p>
            <fieldset disabled={!!data?.voice.active || status !== "ready"}>
              <legend>
                {t(
                  "Local motion preview — no AI call",
                  "本地动作预览，不调用AI",
                )}
              </legend>
              <div className="avatar-preview-buttons">
                <button
                  aria-pressed={preview === null}
                  onClick={() => choosePreview(null)}
                >
                  {t("Live", "实时")}
                </button>
                {(["idle", "listening", "thinking", "alert"] as const).map(
                  (s) => (
                    <button
                      key={s}
                      aria-pressed={preview === s}
                      onClick={() => choosePreview(s)}
                    >
                      {LABELS[s][zh ? 1 : 0]}
                    </button>
                  ),
                )}
                <button
                  aria-pressed={preview === "speaking"}
                  onClick={() => void speakPreview()}
                >
                  <Volume2 size={15} />
                  {t("Preview voice motion", "预览语音口型")}
                </button>
              </div>
              <small>
                {t(
                  "Plays a short synthetic vowel to check mouth motion. This is not an AI conversation.",
                  "播放一小段合成元音检查嘴部动作，非AI交谈。",
                )}
              </small>
            </fieldset>
            <div className="avatar-switches">
              <label>
                <input
                  type="checkbox"
                  checked={paused}
                  onChange={(e) => setPaused(e.target.checked)}
                />
                {t("Pause animation", "暂停动画")}
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={mirrored}
                  onChange={(e) => setMirrored(e.target.checked)}
                />
                {t("Mirror character", "镜像角色")}
              </label>
            </div>
            <label className="avatar-model-picker">
              {t("Replace with a local VRM", "使用本地VRM替换")}
              <input
                type="file"
                accept=".vrm"
                onChange={(e) => {
                  void chooseModel(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </label>
            <small>
              {t(
                "Self-contained VRM, up to 25 MB. Files stay in this browser; reloading restores the sample. Check your model’s usage licence.",
                "支持25MB以内的自包含VRM。文件仅在本浏览器使用，刷新恢复示范角色；请核对所用模型的许可。",
              )}
            </small>
            {fileError && (
              <p role="alert">
                {t(
                  "Could not use this preview or file. Choose a self-contained VRM or try again.",
                  "预览或文件未能使用，请选择自包含VRM或重试。",
                )}
              </p>
            )}
            <div className="avatar-control-links">
              <button
                onClick={() => {
                  fileGeneration.current++;
                  stopAudio();
                  setPreview(null);
                  setFileError(false);
                  setStatus("loading");
                  setUrl(SAMPLE_MODEL);
                  setRetry((n) => n + 1);
                }}
              >
                <RotateCcw size={15} />
                {t("Restore sample", "恢复示范角色")}
              </button>
              <a href={`?surface=avatar&clean=1${mirrored ? "&mirror=1" : ""}`}>
                <Maximize2 size={15} />
                {t("Clean black output", "纯黑输出")}
              </a>
              {url === SAMPLE_MODEL ? (
                <a
                  href="https://github.com/pixiv/three-vrm/tree/ff42fae4fcee1fcbca2cd262c7f5f8cbddeaf5ab/packages/three-vrm/examples/models"
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("Model source & licence", "模型来源与许可")}
                </a>
              ) : (
                <small>
                  {t(
                    "Local model: its own licence applies.",
                    "本地模型适用自身许可。",
                  )}
                </small>
              )}
            </div>
            <small>
              {t(
                "Start a configured voice conversation from Assistant. Mouth motion follows playback in this browser, including same-origin tabs; remote device audio is not linked yet.",
                "在助理页面连接已配置的语音。口型跟随本浏览器及同源标签页播放，尚未连接远端设备音频。",
              )}
            </small>
          </div>
        </details>
      )}
      {clean && (
        <a
          className="avatar-clean-exit"
          href={`?surface=avatar${mirrored ? "&mirror=1" : ""}`}
        >
          {t("Character controls", "角色设置")}
        </a>
      )}
    </div>
  );
}
