import { useEffect, useState } from "react";
import { A1Canvas } from "../companion/A1Canvas";
import "./avatar.css";

/** Public character-only output: no workspace, calendar or provider subscription. */
export function CleanAvatar() {
  const params = new URLSearchParams(location.search);
  const mirror = params.get("mirror") === "1";
  const zh = params.get("lang") === "zh";
  const [paused] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const title = document.title;
    document.title = zh
      ? "角色独立输出 · Desk Companion"
      : "Character output · Desk Companion";
    document.documentElement.lang = zh ? "zh-Hans" : "en";
    return () => {
      document.title = title;
    };
  }, [zh]);
  return (
    <main className="a1-studio clean">
      <div
        className={`a1-studio-viewport ${mirror ? "mirror" : ""}`}
        aria-label={zh ? "完整人物独立输出" : "Complete character output"}
      >
        <A1Canvas active={!paused} action="Idle" state="idle" framing="full" />
      </div>
      <a className="a1-clean-return" href="/">
        {zh ? "返回日历" : "Back to calendar"}
      </a>
    </main>
  );
}
