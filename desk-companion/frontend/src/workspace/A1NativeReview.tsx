import { useEffect, useRef, useState } from "react";
import type { VrmExpression, VrmViewer } from "../companion/vrm-viewer";
import "./existing-avatar.css";

/** A fixed authored character review; source authoring controls stay in VRoid. */
export function A1NativeReview() {
  const [lang, setLang] = useState(() =>
    new URLSearchParams(location.search).get("lang") === "zh" ? "zh" : "en",
  );
  const t = (en: string, zh: string) => (lang === "zh" ? zh : en);
  const host = useRef<HTMLDivElement>(null);
  const engine = useRef<VrmViewer | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [attempt, setAttempt] = useState(0);
  const [compare, setCompare] = useState(true);
  const [framing, setFraming] = useState<"portrait" | "full">("portrait");
  const [angle, setAngle] = useState(Math.PI / 6);
  const [expression, setExpression] = useState<VrmExpression>("smile");
  const [nonce, setNonce] = useState(0);
  const [paused, setPaused] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    const oldTitle = document.title;
    const oldLang = document.documentElement.lang;
    document.title = t("A1 · rejected v1 archive", "A1 · 已否决 v1 归档");
    document.documentElement.lang = lang === "zh" ? "zh-Hans" : "en";
    return () => {
      document.title = oldTitle;
      document.documentElement.lang = oldLang;
    };
  }, [lang]);

  useEffect(() => {
    let dead = false;
    let viewer: VrmViewer | null = null;
    setStatus("loading");
    void import("../companion/vrm-viewer")
      .then(({ VrmViewer: Viewer }) => {
        if (dead || !host.current) return;
        viewer = new Viewer(
          host.current,
          "/avatars/a1-native-v1/a1-native-v1.vrm",
          () => {
            if (!dead) setStatus("ready");
          },
          () => {
            if (!dead) setStatus("error");
          },
        );
        engine.current = viewer;
      })
      .catch(() => {
        if (!dead) setStatus("error");
      });
    return () => {
      dead = true;
      viewer?.dispose();
      engine.current = null;
    };
  }, [attempt]);

  useEffect(() => {
    engine.current?.framing(framing);
  }, [framing, status]);
  useEffect(() => {
    engine.current?.view(angle);
  }, [angle, framing, status]);
  useEffect(() => {
    engine.current?.setExpression(expression);
  }, [expression, nonce, status]);
  useEffect(() => {
    engine.current?.setPaused(paused);
  }, [paused, status]);

  return (
    <main className={`existing-avatar${compare ? " is-comparing" : ""}`}>
      <header>
        <a href="/?surface=models&lang=zh&compare=a1">
          ← {t("Base models", "底模对照")}
        </a>
        <strong>
          A1 · {t("Rejected v1 · archive", "已否决 v1 · 历史归档")}
        </strong>
        <button onClick={() => setLang(lang === "zh" ? "en" : "zh")}>
          {lang === "zh" ? "English" : "简体中文"}
        </button>
      </header>
      <div className="existing-avatar-layout">
        <section
          className="existing-avatar-stage"
          aria-label={t("A1 comparison", "A1 精修对照")}
        >
          <div className="existing-avatar-comparison">
            {compare && (
              <figure className="existing-avatar-reference">
                <img
                  src={
                    framing === "portrait"
                      ? "/companion/a1-reference-face.png"
                      : "/companion/a1-reference-full.png"
                  }
                  alt={t("A1 original illustration", "A1 原画目标")}
                />
                <figcaption>
                  {t("A1 · original art", "A1 · 原画目标")}
                </figcaption>
              </figure>
            )}
            <div className="existing-avatar-current">
              <div
                className="existing-avatar-canvas"
                ref={host}
                aria-label={t(
                  "3D character. Drag to orbit, scroll to zoom.",
                  "三维人物，拖动旋转，滚轮缩放",
                )}
              />
              {compare && (
                <p className="existing-avatar-caption">
                  {t("Native refinement v1", "原生精修 v1")}
                </p>
              )}
            </div>
          </div>
          {status === "loading" && (
            <p className="existing-avatar-loading" role="status">
              {t("Loading A1…", "正在加载 A1…")}
            </p>
          )}
          {status === "error" && (
            <div className="existing-avatar-loading" role="alert">
              <p>{t("A1 could not load.", "A1 模型未能加载。")}</p>
              <button onClick={() => setAttempt((n) => n + 1)}>
                {t("Retry", "重试")}
              </button>
            </div>
          )}
          <div
            className="existing-avatar-angles"
            role="group"
            aria-label={t("View angle", "视角")}
          >
            {(
              [
                [0, "Front", "正面"],
                [Math.PI / 6, "30°", "30°"],
                [Math.PI / 2, "Side", "侧面"],
                [Math.PI, "Back", "背面"],
              ] as const
            ).map(([value, en, zh]) => (
              <button
                key={en}
                disabled={status !== "ready"}
                aria-pressed={angle === value}
                onClick={() => {
                  setAngle(value);
                  engine.current?.view(value);
                }}
              >
                {t(en, zh)}
              </button>
            ))}
            <button aria-pressed={compare} onClick={() => setCompare(!compare)}>
              {t("Original comparison", "原画对照")}
            </button>
            <button
              disabled={status !== "ready"}
              onClick={() =>
                setFraming(framing === "portrait" ? "full" : "portrait")
              }
            >
              {framing === "portrait"
                ? t("Full body", "查看全身")
                : t("Face detail", "查看脸部")}
            </button>
          </div>
        </section>
        <aside>
          <p className="existing-avatar-kicker">
            A1 · {t("Native edit", "原生编辑")}
          </p>
          <h1>
            {t("Archived draft, rejected by the user.", "已被否决的历史试稿。")}
          </h1>
          <p>
            {t(
              "Work on this draft has stopped. The current direction is to choose a complete creator-made character.",
              "这版已停止精修，当前改为选择作者制作好的完整角色。",
            )}
          </p>
          <div
            className="existing-avatar-expression"
            role="group"
            aria-label={t("Expression checks", "表情检查")}
          >
            {(
              [
                ["neutral", "Neutral", "中性"],
                ["smile", "Soft smile", "轻笑"],
                ["blink", "Blink", "眨眼"],
                ["speak", "Mouth test", "模拟口型"],
              ] as const
            ).map(([value, en, zh]) => (
              <button
                key={value}
                disabled={status !== "ready"}
                aria-pressed={expression === value}
                onClick={() => {
                  setExpression(value);
                  setNonce((n) => n + 1);
                }}
              >
                {t(en, zh)}
              </button>
            ))}
            <button
              disabled={status !== "ready"}
              aria-pressed={paused}
              onClick={() => setPaused(!paused)}
            >
              {paused ? t("Resume", "继续") : t("Pause", "暂停")}
            </button>
          </div>
          <p className="existing-avatar-note">
            {t(
              "Review the face, eyes and hair in this version. The plain high-neck outfit is temporary; clothing, the ring clip and earrings remain unfinished. Mouth movement is simulated.",
              "本版先看脸型、眼神和头发。素色高领用于审阅；完整服装、圆环发夹和耳钉尚未还原。口型为模拟演示。",
            )}
          </p>
          <p className="existing-avatar-note">
            {t(
              "Base: pixiv Inc. Hair: Dahlia / Reira’s Items. Adapted for Group 2.",
              "底模：pixiv Inc.；发型：Dahlia／Reira’s Items；Group 2 改装。",
            )}
          </p>
          <a
            href="/avatars/a1-native-v1/source.json"
            target="_blank"
            rel="noreferrer"
          >
            {t("Sources and changes", "来源与修改记录")} ↗
          </a>
        </aside>
      </div>
    </main>
  );
}
