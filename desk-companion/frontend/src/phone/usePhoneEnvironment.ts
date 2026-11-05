import { useEffect, useState } from "react";
import { DateTime } from "luxon";
import { useSceneActivity } from "../companion/useSceneActivity";

export function usePhoneEnvironment() {
  const { visible, blocked, motion } = useSceneActivity();
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
      if (!document.hidden) setNow(DateTime.now());
    };
    visualViewport?.addEventListener("resize", resize);
    visualViewport?.addEventListener("scroll", resize);
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", visibility);
    const timer = setInterval(() => {
      if (!document.hidden) setNow(DateTime.now());
    }, 15000);
    return () => {
      document.documentElement.classList.remove("phone-surface");
      clearInterval(timer);
      visualViewport?.removeEventListener("resize", resize);
      visualViewport?.removeEventListener("scroll", resize);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);
  return { visible, blocked, motion, now, viewport };
}
