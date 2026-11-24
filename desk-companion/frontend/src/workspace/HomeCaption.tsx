import { useLayoutEffect, useRef } from "react";

/** Keep the full utterance for Conversation and accessibility, and page the Home
 * caption using the actual wrapped lines for this font, zoom and viewport. */
export function HomeCaption({ text }: { text: string }) {
  const content = useRef<HTMLSpanElement>(null);
  const position = useRef({ text: "", page: 0, since: 0 });

  useLayoutEffect(() => {
    const span = content.current;
    if (!span) {
      position.current.text = "";
      return;
    }
    const state = position.current;
    if (!state.text || !text.startsWith(state.text)) {
      state.page = 0;
      state.since = performance.now();
    }
    state.text = text;
    let timer: number | undefined;
    function layout() {
      window.clearTimeout(timer);
      if (!span || !span.isConnected) return;
      const line = Number.parseFloat(getComputedStyle(span).lineHeight);
      if (!line) return;
      const lines = Math.round(span.getBoundingClientRect().height / line);
      const last = Math.max(0, Math.ceil(lines / 2) - 1);
      state.page = Math.min(state.page, last);
      if (state.page < last) {
        // A final provider packet can contain a whole paragraph. Give each pair
        // reading time even when several lines arrive together.
        const dwell = Math.min(
          4800,
          Math.max(1400, (text.length / lines) * 105),
        );
        const remaining = state.since + dwell - performance.now();
        if (remaining <= 0) {
          state.page += 1;
          state.since = performance.now();
        }
        if (state.page < last)
          timer = window.setTimeout(
            layout,
            Math.max(1, remaining > 0 ? remaining : dwell),
          );
      }
      span.style.transform = `translateY(-${state.page * 2 * line}px)`;
    }
    layout();
    const resize = new ResizeObserver(layout);
    resize.observe(span);
    return () => {
      resize.disconnect();
      window.clearTimeout(timer);
    };
  }, [text]);

  return text ? (
    <p className="assistant-latest" aria-live="polite">
      <span className="home-caption-window">
        <span className="home-caption-text" ref={content}>
          {text}
        </span>
      </span>
    </p>
  ) : null;
}
