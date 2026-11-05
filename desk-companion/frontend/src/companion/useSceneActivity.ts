import { useEffect, useState } from "react";

/** Shared scene/media suspension for the phone and the dedicated desk display. */
export function useSceneActivity() {
  const [visible, setVisible] = useState(() => !document.hidden);
  const [blocked, setBlocked] = useState(false);
  const [motion, setMotion] = useState(
    () => !matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const visibility = () => setVisible(!document.hidden);
    const modal = () =>
      setBlocked(
        !!document.querySelector(
          'dialog[open][data-companion-blocking="true"]',
        ),
      );
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const reduce = () => setMotion(!media.matches);
    modal();
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("desk:modal-state", modal);
    media.addEventListener("change", reduce);
    return () => {
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("desk:modal-state", modal);
      media.removeEventListener("change", reduce);
    };
  }, []);
  return { visible, blocked, motion };
}
