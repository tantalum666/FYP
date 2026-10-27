import { useEffect, useRef, useState } from "react";
import type { VrmViewer, VrmExpression } from "../companion/vrm-viewer";
import {
  validateLocalVrm,
  readLocalVrm,
  saveLocalVrm,
  clearLocalVrm,
  type LocalVrm,
} from "../companion/local-vrm";
import "./existing-avatar.css";
import {
  MODELS,
  readAppearance,
  saveAppearance,
} from "../companion/appearance";

const PREVIEW_KEY = "desk.companion.preview.v2";
function rememberPreview(value: "local" | "builtin") {
  try {
    localStorage.setItem(PREVIEW_KEY, value);
  } catch {
    /* Session still works. */
  }
}

export function ExistingAvatar() {
  const [lang, setLang] = useState(() =>
    new URLSearchParams(location.search).get("lang") === "zh" ? "zh" : "en",
  );
  const t = (en: string, zh: string) => (lang === "zh" ? zh : en);
  const host = useRef<HTMLDivElement>(null);
  const engine = useRef<VrmViewer | null>(null);
  const importSequence = useRef(0);
  const [restoring, setRestoring] = useState(true);
  const [cachedModel, setCachedModel] = useState<LocalVrm | null>(null);
  const [localModel, setLocalModel] = useState<LocalVrm | null>(null);
  const [remembered, setRemembered] = useState<"none" | "saved" | "failed">(
    "none",
  );
  const [importStatus, setImportStatus] = useState<
    "idle" | "reading" | "error"
  >("idle");
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [attempt, setAttempt] = useState(0);
  const [model, setModel] = useState<keyof typeof MODELS>(
    () => readAppearance().model,
  );
  const [applied, setApplied] = useState<"none" | "saved" | "failed">("none");
  const [framing, setFraming] = useState<"portrait" | "full">("portrait");
  const [compareA1, setCompareA1] = useState(
    () => new URLSearchParams(location.search).get("compare") === "a1",
  );
  const [angle, setAngle] = useState(0);
  const [expression, setExpression] = useState<VrmExpression>("neutral");
  const [nonce, setNonce] = useState(0);
  const [paused, setPaused] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [palette, setPalette] = useState<"original" | "silver">(
    () => readAppearance().palette,
  );
  const [headRatio, setHeadRatio] = useState(() => readAppearance().headRatio);

  useEffect(() => {
    const title = document.title;
    document.title = t(
      "Ready-made characters · Desk Companion",
      "现成角色预览 · Desk Companion",
    );
    document.documentElement.lang = lang === "zh" ? "zh-Hans" : "en";
    return () => {
      document.title = title;
    };
  }, [lang]);

  useEffect(() => {
    let active = true;
    const sequence = ++importSequence.current;
    void readLocalVrm()
      .then((value) => {
        if (!value || sequence !== importSequence.current) return;
        setCachedModel(value);
        if (localStorage.getItem(PREVIEW_KEY) === "local") {
          setLocalModel(value);
          setPalette("original");
          setHeadRatio(1);
          setRemembered("saved");
        }
      })
      .catch(() => {
        if (sequence === importSequence.current) setRemembered("failed");
      })
      .finally(() => {
        if (active) setRestoring(false);
      });
    return () => {
      active = false;
      importSequence.current += 1;
    };
  }, []);

  const openLocalModel = async (file: File) => {
    const sequence = ++importSequence.current;
    setImportStatus("reading");
    try {
      if (!/\.vrm$/i.test(file.name) || file.size > 64 * 1024 * 1024)
        throw new Error("VRM_FILE");
      const bytes = await file.arrayBuffer();
      validateLocalVrm(bytes);
      if (sequence !== importSequence.current) return;
      const value = { name: file.name, bytes };
      rememberPreview("local");
      setLocalModel(value);
      setPalette("original");
      setHeadRatio(1);
      setExpression("neutral");
      setApplied("none");
      setImportStatus("idle");
      try {
        await saveLocalVrm(value);
        if (sequence === importSequence.current) {
          setCachedModel(value);
          setRemembered("saved");
        }
      } catch {
        if (sequence === importSequence.current) setRemembered("failed");
      }
    } catch {
      if (sequence === importSequence.current) setImportStatus("error");
    }
  };

  const controls = useRef({
    framing,
    angle,
    expression,
    paused,
    palette,
    headRatio,
  });
  controls.current = { framing, angle, expression, paused, palette, headRatio };
  const applyControls = (viewer: VrmViewer) => {
    const current = controls.current;
    viewer.framing(current.framing);
    viewer.view(current.angle);
    viewer.setExpression(current.expression);
    viewer.setPaused(current.paused);
    viewer.setPalette(current.palette);
    viewer.setHeadRatio(current.headRatio);
  };

  useEffect(() => {
    if (restoring) return;
    let dead = false;
    let viewer: VrmViewer | null = null;
    setStatus("loading");
    void import("../companion/vrm-viewer")
      .then(({ VrmViewer: Viewer }) => {
        if (dead || !host.current) return;
        viewer = new Viewer(
          host.current,
          localModel?.bytes ?? MODELS[model].file,
          () => {
            if (!dead && viewer) {
              applyControls(viewer);
              setStatus("ready");
            }
          },
          () => {
            if (!dead) setStatus("error");
          },
        );
        engine.current = viewer;
        applyControls(viewer);
      })
      .catch(() => {
        if (!dead) setStatus("error");
      });
    return () => {
      dead = true;
      viewer?.dispose();
      engine.current = null;
    };
  }, [attempt, model, localModel, restoring]);

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
  useEffect(() => {
    engine.current?.setPalette(palette);
  }, [palette, status]);
  useEffect(() => {
    engine.current?.setHeadRatio(headRatio);
  }, [headRatio, status]);

  const restore = () => {
    setPalette("original");
    setHeadRatio(1);
    setExpression("neutral");
    setApplied("none");
  };
  return (
    <main className={`existing-avatar${compareA1 ? " is-comparing" : ""}`}>
      <header>
        <a href="/">← {t("Calendar", "返回日历")}</a>
        <strong>{t("Ready-made characters", "现成角色预览")}</strong>
        <button onClick={() => setLang(lang === "zh" ? "en" : "zh")}>
          {lang === "zh" ? "English" : "简体中文"}
        </button>
      </header>
      <div className="existing-avatar-layout">
        <section
          className="existing-avatar-stage"
          aria-label={t("Complete character preview", "完整人物预览")}
        >
          <div className="existing-avatar-comparison">
            {compareA1 && (
              <figure className="existing-avatar-reference">
                <img
                  src={
                    framing === "portrait"
                      ? "/companion/a1-reference-face.png"
                      : "/companion/a1-reference-full.png"
                  }
                  alt={t(
                    "A1 original art: side-parted silver waves, grey-blue almond eyes and a mature face.",
                    "A1 原画：侧分银灰波浪发、灰蓝杏眼和成熟脸型。",
                  )}
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
              {compareA1 && (
                <p className="existing-avatar-caption">
                  {t("Current complete model", "当前完整底模")}
                </p>
              )}
            </div>
          </div>
          {status === "loading" && (
            <p className="existing-avatar-loading" role="status">
              {t("Loading complete model…", "正在加载完整模型…")}
            </p>
          )}
          {status === "error" && (
            <div className="existing-avatar-loading" role="alert">
              <p>{t("Model could not load.", "模型未能加载。")}</p>
              <button onClick={() => setAttempt((value) => value + 1)}>
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
            <button
              aria-pressed={compareA1}
              onClick={() => setCompareA1(!compareA1)}
            >
              {t("Compare with A1", "A1 原画对照")}
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
          {compareA1 && (
            <p className="existing-avatar-comparison-note">
              {t(
                "A1 remains a visual reference. Choose a finished character on its own merits before making any changes.",
                "A1 保留作参考。先看完整成品的人物质量，再决定是否需要修改。",
              )}
            </p>
          )}
        </section>
        <aside>
          <p className="existing-avatar-kicker">
            {t(
              "Complete character · original appearance",
              "完整成品 · 作者原貌",
            )}
          </p>
          <h1>
            {localModel
              ? localModel.name
              : model === "alice"
                ? t("AliceChan, your companion.", "AliceChan，桌面伙伴。")
                : t(MODELS[model].nameEn, MODELS[model].name)}
          </h1>
          <p>
            {t(
              "AliceChan is the initial companion. Preview complete models with their creator’s face, hair, outfit and materials.",
              "AliceChan 是当前初用伙伴。预览保留作者原本的脸、头发、衣服和材质。",
            )}
          </p>
          {!localModel && model === "alice" && (
            <p className="existing-avatar-note">
              Alice Chan (Uniform ver.) ·{" "}
              <a
                href="https://github.com/yuna0x0/AliceChan"
                target="_blank"
                rel="noreferrer"
              >
                edisonlee55 / yuna0x0
              </a>
              {" · "}
              <a
                href="/avatars/alice/LICENSE.md"
                target="_blank"
                rel="noreferrer"
              >
                CC BY-SA 4.0
              </a>
              {" · "}
              {t(
                "Original appearance; compatibility metadata adjusted.",
                "作者原版外观；已整理兼容元数据。",
              )}
            </p>
          )}
          <div className="existing-avatar-panel">
            {cachedModel && !localModel && (
              <button
                onClick={() => {
                  importSequence.current += 1;
                  rememberPreview("local");
                  setLocalModel(cachedModel);
                  setPalette("original");
                  setHeadRatio(1);
                  setRemembered("saved");
                }}
              >
                {t("Open saved local preview", "打开之前保存的本地预览")}
              </button>
            )}
            <label>
              {t("Open a local VRM", "打开本地 VRM")}
              <input
                type="file"
                accept=".vrm"
                onChange={(event) => {
                  const file = event.currentTarget.files?.[0];
                  event.currentTarget.value = "";
                  if (file) void openLocalModel(file);
                }}
              />
            </label>
            {localModel && (
              <p className="existing-avatar-filename" role="status">
                {localModel.name}
              </p>
            )}
            <p className="existing-avatar-note">
              {t(
                "Saved in this browser only, with no upload. Use the model under its creator’s terms.",
                "仅保存在当前浏览器，不上传文件。按原作者条款使用。",
              )}
            </p>
            {localModel && remembered === "saved" && (
              <p className="existing-avatar-note" role="status">
                {t(
                  "Remembered on this device; reopening this page restores the model.",
                  "已在本机记住，重新打开页面仍可查看。",
                )}
              </p>
            )}
            {remembered === "failed" && (
              <p className="existing-avatar-note" role="status">
                {t(
                  "Browser storage is unavailable. Reopen the local file after reloading.",
                  "浏览器未能保存模型；刷新后请重新选择本地文件。",
                )}
              </p>
            )}
            {localModel && (
              <button
                onClick={() => {
                  importSequence.current += 1;
                  const sequence = importSequence.current;
                  void clearLocalVrm()
                    .then(() => {
                      if (sequence !== importSequence.current) return;
                      rememberPreview("builtin");
                      setCachedModel(null);
                      setLocalModel(null);
                      setRemembered("none");
                      setImportStatus("idle");
                    })
                    .catch(() => {
                      if (sequence === importSequence.current)
                        setRemembered("failed");
                    });
                }}
              >
                {t("Remove browser copy", "移除浏览器副本")}
              </button>
            )}
            {importStatus === "reading" && (
              <p role="status">{t("Reading model…", "正在读取模型…")}</p>
            )}
            {importStatus === "error" && (
              <p role="alert">
                {t(
                  "Choose a self-contained VRM under 64 MiB. The current preview has been kept.",
                  "请选择 64 MiB 以内、纹理内嵌的有效 VRM；当前预览已保留。",
                )}
              </p>
            )}
          </div>
          <details className="existing-avatar-options">
            <summary>{t("Built-in model options", "内置模型选项")}</summary>
            <div className="existing-avatar-panel">
              <label>
                {t("Base model", "人物底模")}
                <select
                  value={localModel ? "local" : model}
                  onChange={(event) => {
                    if (event.target.value === "local") return;
                    importSequence.current += 1;
                    setLocalModel(null);
                    setImportStatus("idle");
                    setRemembered("none");
                    rememberPreview("builtin");
                    setPalette("original");
                    setHeadRatio(1);
                    setStatus("loading");
                    setApplied("none");
                    setModel(event.target.value as keyof typeof MODELS);
                  }}
                >
                  {localModel && (
                    <option value="local">
                      {t("Local model", "本地完整模型")}
                    </option>
                  )}
                  {Object.entries(MODELS).map(([value, item]) => (
                    <option key={value} value={value}>
                      {t(item.nameEn, item.name)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t("Hair palette", "外观配色")}
                <select
                  value={palette}
                  onChange={(event) => {
                    setPalette(event.target.value as "original" | "silver");
                    setApplied("none");
                  }}
                  disabled={status !== "ready" || !!localModel}
                >
                  <option value="original">{t("Original", "作者原版")}</option>
                  <option value="silver">{t("Silver ash", "银灰方向")}</option>
                </select>
              </label>
              <label>
                {t("Head proportion", "头部比例")}{" "}
                <output>{Math.round(headRatio * 100)}%</output>
                <input
                  type="range"
                  min="0.92"
                  max="1.08"
                  step="0.01"
                  value={headRatio}
                  onChange={(event) => {
                    setHeadRatio(Number(event.target.value));
                    setApplied("none");
                  }}
                  disabled={status !== "ready" || !!localModel}
                />
              </label>
              <button
                onClick={restore}
                disabled={status !== "ready" || !!localModel}
              >
                {t("Restore original appearance", "恢复作者原版")}
              </button>
              <button
                disabled={status !== "ready" || !!localModel}
                onClick={() =>
                  setApplied(
                    saveAppearance({ model, palette, headRatio })
                      ? "saved"
                      : "failed",
                  )
                }
              >
                {t("Apply to page companion", "应用到常驻伙伴")}
              </button>
              {applied !== "none" && (
                <p role="status">
                  {applied === "saved"
                    ? t(
                        "Saved. Open companion pages will update.",
                        "已保存，已打开的页面伙伴会同步更新。",
                      )
                    : t(
                        "Browser preferences could not be saved. The preview remains available.",
                        "浏览器未能保存偏好，当前预览仍可使用。",
                      )}
                </p>
              )}
            </div>
          </details>
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
                aria-pressed={expression === value}
                disabled={status !== "ready"}
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
              "Local files are previewed here only. AliceChan is already available on companion pages. Mouth movement here is simulated.",
              "本地文件仅在这里预览；AliceChan 已接入常驻伙伴。此页口型为模拟演示。",
            )}
          </p>
          <div className="existing-avatar-candidates">
            <h2>{t("AliceChan source", "AliceChan 来源")}</h2>
            <a
              href="https://github.com/yuna0x0/AliceChan/releases/tag/v1.0.4"
              target="_blank"
              rel="noreferrer"
            >
              GitHub · {t("Original download", "作者原始下载")} ↗
            </a>
            <a
              href="/avatars/alice/source.json"
              target="_blank"
              rel="noreferrer"
            >
              {t("Version, source & checksum", "版本、来源与校验记录")} ↗
            </a>
            <a
              href="/avatars/open-models/source.json"
              target="_blank"
              rel="noreferrer"
            >
              {t("Other built-in model sources", "其他内置模型来源")} ↗
            </a>
          </div>
        </aside>
      </div>
    </main>
  );
}
