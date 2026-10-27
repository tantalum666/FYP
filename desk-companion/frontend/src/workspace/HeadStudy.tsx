import { useEffect, useRef, useState } from "react";
import type { HeadPose, HeadRenderer } from "../companion/head-renderer";
import "./head-study.css";

export function HeadStudy() {
  const host = useRef<HTMLDivElement>(null);
  const viewer = useRef<HeadRenderer | null>(null);
  const [lang, setLang] = useState(() => new URLSearchParams(location.search).get("lang") === "zh" ? "zh" : "en");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0);
  const [pose, setPose] = useState<HeadPose>("neutral");
  const [nonce, setNonce] = useState(0);
  const [angle, setAngle] = useState(0);
  const [reference, setReference] = useState(true);
  const [overlay, setOverlay] = useState(false);
  const [opacity, setOpacity] = useState(0.4);
  const [paused, setPaused] = useState(() => matchMedia("(prefers-reduced-motion: reduce)").matches);
  const t = (en: string, zh: string) => lang === "zh" ? zh : en;

  useEffect(() => {
    document.documentElement.lang = lang === "zh" ? "zh-Hans" : "en";
    const previous = document.title;
    document.title = lang === "zh" ? "A1 头部试稿 · Desk Companion" : "A1 Head Study · Desk Companion";
    return () => { document.title = previous; };
  }, [lang]);

  useEffect(() => {
    let dead = false;
    let instance: HeadRenderer | null = null;
    setStatus("loading");
    void import("../companion/head-renderer").then(({ HeadRenderer: Renderer }) => {
      if (dead || !host.current) return;
      instance = new Renderer(host.current, () => { if (!dead) setStatus("ready"); }, () => { if (!dead) setStatus("error"); });
      viewer.current = instance;
    }).catch(() => { if (!dead) setStatus("error"); });
    return () => { dead = true; instance?.dispose(); viewer.current = null; };
  }, [attempt]);

  useEffect(() => { viewer.current?.setPose(pose); }, [pose, nonce, status]);
  useEffect(() => { viewer.current?.view(angle); }, [angle, status, reference]);
  useEffect(() => { viewer.current?.matchReference(reference); }, [reference, angle, status]);
  useEffect(() => { viewer.current?.setOverlay(overlay); }, [overlay, status]);
  useEffect(() => { viewer.current?.setPaused(paused); }, [paused, status]);

  return (
    <main className="head-study">
      <header>
        <a href="/">← {t("Calendar", "返回日历")}</a>
        <div><strong>A1</strong><span>{t("Rejected head study", "已否决的头部试稿")}</span></div>
        <button onClick={() => setLang(lang === "zh" ? "en" : "zh")}>{lang === "zh" ? "English" : "简体中文"}</button>
      </header>
      <div className="head-study-intro">
        <h1>{t("Rejected study — work stopped.", "已否决，停止继续制作这套头部。")}</h1>
        <p><a href="/?surface=models">{t("Open the complete-model adaptation instead →", "查看现成完整模型的改装 →")}</a></p>
      </div>
      <div className="head-study-comparison">
        <figure className="head-study-model">
          <div className="head-study-frame">
            <div className="head-study-canvas" ref={host} aria-label={t("3D A1 head. Drag to orbit, scroll to zoom.", "A1三维头部。拖动查看角度，滚轮缩放。")} />
            {overlay && <img className="head-study-original-overlay" src="/companion/a1-reference-face.png" alt="" aria-hidden="true" style={{ opacity }} />}
          </div>
          {status === "loading" && <p className="head-study-status" role="status">{t("Loading head…", "正在加载头部…")}</p>}
          {status === "error" && <div className="head-study-status" role="alert"><p>{t("The 3D view could not load.", "3D画面未能加载。")}</p><button onClick={() => setAttempt((n) => n + 1)}>{t("Retry", "重试")}</button></div>}
          <figcaption>{t("3D draft · drag to orbit · scroll to zoom", "三维试稿 · 拖动查看各个角度 · 滚轮缩放")}</figcaption>
        </figure>
        <figure className="head-study-reference">
          <img src="/companion/a1-reference-face.png" alt={t("Selected A1 original artwork", "已确定的A1原画")} />
          <figcaption>{t("A1 original · reference", "A1原画 · 对照")}</figcaption>
        </figure>
      </div>
      <div className="head-study-tools">
        <div role="group" aria-label={t("View angle", "查看角度")}>
          <button disabled={status !== "ready"} aria-pressed={reference} onClick={() => { setReference(true); setOverlay(false); viewer.current?.matchReference(true); }}>{t("Original pose", "原画角度")}</button>
          {([[0, "Front", "正面"], [Math.PI / 6, "30°", "30°"], [Math.PI / 2, "Side", "侧面"], [Math.PI, "Back", "背面"]] as const).map(([value, en, zh]) => <button key={en} disabled={status !== "ready"} aria-pressed={!reference && angle === value} onClick={() => { setReference(false); setOverlay(false); setAngle(value); viewer.current?.view(value); }}>{t(en, zh)}</button>)}
          <button disabled={status !== "ready"} aria-pressed={overlay} onClick={() => { setReference(true); setOverlay(!overlay); }}>{t("Overlay original", "原画叠加")}</button>
        </div>
        <div role="group" aria-label={t("Expression checks", "表情检查")}>
          {([["neutral", "Neutral", "中性"], ["smile", "Soft smile", "轻笑"], ["blink", "Blink", "眨眼"], ["speak", "Mouth test", "口型测试"]] as const).map(([value, en, zh]) => <button key={value} disabled={status !== "ready"} aria-pressed={pose === value} onClick={() => { setPose(value); setNonce((n) => n + 1); }}>{t(en, zh)}</button>)}
          <button disabled={status !== "ready"} aria-pressed={paused} onClick={() => setPaused(!paused)}>{paused ? t("Resume", "继续") : t("Pause", "暂停")}</button>
        </div>
      </div>
      {overlay && <label className="head-study-opacity">{t("Original opacity", "原画透明度")}<input type="range" min="0" max="0.8" step="0.05" value={opacity} onChange={(event) => setOpacity(Number(event.target.value))} /></label>}
      <footer>
        <p>{t("Appearance review in progress. Mouth test is simulated; no microphone or voice service is started.", "外形仍在检查中。口型测试使用模拟变化，不会打开麦克风或语音服务。")}</p>
        <a href="/companion/a1-head-source.json" target="_blank" rel="noreferrer">{t("Sources and licence", "来源与许可")}</a>
      </footer>
    </main>
  );
}
