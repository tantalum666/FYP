import { useEffect, useState } from "react";
import { DateTime } from "luxon";

export function usePhoneEnvironment() {
  const [visible, setVisible] = useState(!document.hidden);
  const [blocked, setBlocked] = useState(false);
  const [motion, setMotion] = useState(
    () => !matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [now, setNow] = useState(DateTime.now());
  const [viewport, setViewport] = useState(() => ({
    height: visualViewport?.height ?? innerHeight,
    top: visualViewport?.offsetTop ?? 0,
  }));
  useEffect(() => {
    document.documentElement.classList.add("phone-surface");
    const resize = () =>
      setViewport({
        height: visualViewport?.height ?? innerHeight,
        top: visualViewport?.offsetTop ?? 0,
      });
    const visibility = () => {
      setVisible(!document.hidden);
      if (!document.hidden) setNow(DateTime.now());
    };
    const modal = () =>
      setBlocked(
        !!document.querySelector(
          'dialog[open][data-companion-blocking="true"]',
        ),
      );
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const reduce = () => setMotion(!media.matches);
    visualViewport?.addEventListener("resize", resize);
    visualViewport?.addEventListener("scroll", resize);
    window.addEventListener("resize", resize);
    window.addEventListener("desk:modal-state", modal);
    document.addEventListener("visibilitychange", visibility);
    media.addEventListener("change", reduce);
    const timer = setInterval(() => {
      if (!document.hidden) setNow(DateTime.now());
    }, 15000);
    return () => {
      document.documentElement.classList.remove("phone-surface");
      clearInterval(timer);
      visualViewport?.removeEventListener("resize", resize);
      visualViewport?.removeEventListener("scroll", resize);
      window.removeEventListener("resize", resize);
      window.removeEventListener("desk:modal-state", modal);
      document.removeEventListener("visibilitychange", visibility);
      media.removeEventListener("change", reduce);
    };
  }, []);
  return { visible, blocked, motion, now, viewport };
}
