import { useEffect, useState } from "react";
import { ArrowLeft, Pause, Play, RotateCcw } from "lucide-react";
import { A1Canvas } from "../companion/A1Canvas";
import type { ActionName } from "../companion/renderer";
import { useWorkspace } from "./WorkspaceContext";
import "./avatar.css";
export function Avatar({
  standalone = false,
  language,
  blocked = false,
}: {
  standalone?: boolean;
  blocked?: boolean;
  language?: "en" | "zh";
}) {
  const { data, offline, stale } = useWorkspace();
  const [lang, setLang] = useState(language ?? "en");
  const t = (en: string, zh: string) => (lang === "zh" ? zh : en);
  const [action, setAction] = useState<ActionName>("Idle"),
    [nonce, setNonce] = useState(0),
    [paused, setPaused] = useState(
      () => matchMedia("(prefers-reduced-motion: reduce)").matches,
    ),
    [angle, setAngle] = useState(0),
    [attempt, setAttempt] = useState(0),
    [error, setError] = useState(false);
  const params = new URLSearchParams(location.search),
    clean = standalone && params.get("clean") === "1",
    mirror = standalone && params.get("mirror") === "1";
  const state =
    !data || offline || stale
      ? "disconnected"
      : data.voice.active
        ? data.voice.state
        : "idle";
  useEffect(() => {
    if (standalone)
      document.documentElement.lang = lang === "en" ? "en" : "zh-Hans";
  }, [lang, standalone]);
  const canvas = (
    <A1Canvas
      key={attempt}
      active={!paused && !blocked}
      action={action}
      nonce={nonce}
      state={state}
      review={standalone && !clean}
      angle={angle}
      onError={() => setError(true)}
    />
  );
  if (!standalone)
    return (
      <div className="device-a1-stage">
        {canvas}
        {error && <p>{t("Character could not load", "角色未能加载")}</p>}
      </div>
    );
  return (
    <main className={`a1-studio ${clean ? "clean" : ""}`}>
      {!clean && (
        <header className="a1-studio-header">
          <a href="/">
            <ArrowLeft size={18} />
            {t("Back to calendar", "返回日历")}
          </a>
          <div className="a1-studio-identity">
            <strong>A1</strong>
            <span>{t("3D study", "3D 形象稿")}</span>
          </div>
          <button
            className="text-button"
            onClick={() => setLang(lang === "en" ? "zh" : "en")}
          >
            {lang === "en" ? "简体中文" : "English"}
          </button>
        </header>
      )}
      <div
        className={`a1-studio-viewport ${mirror ? "mirror" : ""}`}
        aria-label={t(
          "A1 3D model. Drag to orbit; scroll to zoom.",
          "A1 3D 模型。拖动旋转视角，滚轮缩放。",
        )}
      >
        {canvas}
      </div>
      {error && (
        <div className="a1-studio-error" role="alert">
          <p>{t("The 3D view could not load.", "3D 画面未能加载。")}</p>
          <button
            className="secondary"
            onClick={() => {
              setError(false);
              setAttempt((n) => n + 1);
            }}
          >
            {t("Retry", "重试")}
          </button>
        </div>
      )}
      {!clean && (
        <>
          <div className="a1-studio-controls">
            <p>
              {t(
                "Drag to orbit · scroll to zoom",
                "拖动查看各个角度 · 滚轮缩放",
              )}
            </p>
            <div className="a1-view-choices">
              {[
                [0, t("Front", "正面")],
                [Math.PI / 2, t("Side", "侧面")],
                [Math.PI, t("Back", "背面")],
              ].map(([a, label]) => (
                <button
                  key={a}
                  className="text-button"
                  onClick={() => setAngle(Number(a))}
                >
                  {label}
                </button>
              ))}
              <button
                className="icon-button"
                aria-label={t("Reset view", "重置视角")}
                onClick={() => {
                  setAngle(0);
                  setAttempt((n) => n + 1);
                }}
              >
                <RotateCcw size={17} />
              </button>
            </div>
            <div className="a1-action-choices">
              {(
                ["Idle", "Wave", "Turn", "Stretch", "Walk", "Gesture"] as const
              ).map((a) => (
                <button
                  key={a}
                  aria-pressed={action === a}
                  disabled={paused}
                  onClick={() => {
                    setAction(a);
                    setNonce((n) => n + 1);
                  }}
                >
                  {t(
                    {
                      Idle: "Rest",
                      Wave: "Wave",
                      Turn: "Turn around",
                      Stretch: "Stretch",
                      Walk: "Walk in place",
                      Gesture: "Gesture study",
                    }[a],
                    {
                      Idle: "待机",
                      Wave: "挥手",
                      Turn: "转身",
                      Stretch: "伸展",
                      Walk: "原地走动",
                      Gesture: "动作研究",
                    }[a],
                  )}
                </button>
              ))}
              <button
                className="a1-pause"
                aria-pressed={paused}
                onClick={() => setPaused(!paused)}
              >
                {paused ? <Play size={16} /> : <Pause size={16} />}{" "}
                {paused ? t("Resume", "继续") : t("Pause", "暂停")}
              </button>
            </div>
          </div>
          <footer className="a1-studio-footer">
            <span>
              {t(
                "Visual & motion draft · A1 likeness still being refined",
                "外形与动作草稿 · A1 相似度仍在细化",
              )}
            </span>
            <a href="/companion/source.json" target="_blank" rel="noreferrer">
              {t("Model sources & licence", "模型来源与许可")}
            </a>
          </footer>
        </>
      )}
      {clean && (
        <a className="a1-clean-return" href="/">
          {t("Back to calendar", "返回日历")}
        </a>
      )}
    </main>
  );
}
