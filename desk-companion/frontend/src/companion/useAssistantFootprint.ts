import { useLayoutEffect, useRef } from "react";

/** Keep the phone agenda above the actual conversation, including long captions. */
export function useAssistantFootprint(enabled: boolean) {
  const panel = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (!enabled || !panel.current) return;
    const element = panel.current;
    const home = element.closest<HTMLElement>(".alice-home");
    if (!home) return;
    const measure = () => {
      const bottom = Number.parseFloat(getComputedStyle(element).bottom) || 0;
      home.style.setProperty(
        "--alice-conversation-space",
        `${Math.ceil(element.getBoundingClientRect().height + bottom + 12)}px`,
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => {
      observer.disconnect();
      home.style.removeProperty("--alice-conversation-space");
    };
  }, [enabled]);
  return panel;
}
