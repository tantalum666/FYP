import { useEffect, useRef, useState } from "react";
import { DateTime } from "luxon";
import { request } from "../api";
import type { Translate } from "../types";
interface Announcement {
  kind: "reminder" | "brief" | "posture" | "task";
  position?: string;
  title?: string;
  redacted?: boolean;
  events?: Array<{ title: string; start: string; all_day: boolean }>;
  total?: number;
  timezone: string;
}

export function useDeskSound(t: Translate) {
  const [enabled, setEnabled] = useState(false),
    [notice, setNotice] = useState("");
  const context = useRef<AudioContext | null>(null),
    client = useRef(crypto.randomUUID());
  async function toggle() {
    if (enabled) {
      setEnabled(false);
      speechSynthesis.cancel();
      await context.current?.close();
      context.current = null;
      return;
    }
    try {
      const value = new AudioContext();
      await value.resume();
      context.current = value;
      setEnabled(true);
      setNotice("");
    } catch {
      setNotice(t("Sound could not be enabled.", "未能启用声音。"));
    }
  }
  useEffect(() => {
    if (!enabled) return;
    let alive = true,
      working = false;
    const poll = async () => {
      if (working || document.hidden) return;
      working = true;
      try {
        const result = await request<{ announcement: Announcement | null }>(
          "/announcements/claim",
          {
            method: "POST",
            body: JSON.stringify({ client_id: client.current }),
          },
        );
        if (!alive || !result.announcement) return;
        const a = result.announcement;
        const ctx = context.current;
        if (!ctx || ctx.state !== "running") {
          setNotice(
            t(
              "Tap Enable sound again to resume playback.",
              "请重新启用声音以恢复播报。",
            ),
          );
          setEnabled(false);
          return;
        }
        const oscillator = ctx.createOscillator(),
          gain = ctx.createGain();
        oscillator.type = "sine";
        oscillator.frequency.value = 660;
        gain.gain.setValueAtTime(0, ctx.currentTime);
        gain.gain.linearRampToValueAtTime(0.06, ctx.currentTime + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.45);
        oscillator.connect(gain).connect(ctx.destination);
        oscillator.start();
        oscillator.stop(ctx.currentTime + 0.5);
        if (a.kind === "brief" || a.kind === "posture" || a.kind === "task") {
          const text = (a.events ?? [])
            .map(
              (e) =>
                `${e.all_day ? t("All day", "全天") : DateTime.fromISO(e.start).setZone(a.timezone).toFormat("HH:mm")} ${e.title || t("Private event", "私人事项")}`,
            )
            .join(". ");
          const full =
            a.kind === "task"
              ? t(
                  "A task is ready for a progress update.",
                  "有一件事需要更新进展。",
                )
              : a.kind === "posture"
                ? a.position === "forward"
                  ? t(
                      "Ease back toward your usual position.",
                      "请回到平时的位置，调整与屏幕的距离。",
                    )
                  : t(
                      "Return toward your usual centred position.",
                      "请回到平时较居中的位置。",
                    )
                : text ||
                  t(
                    "No events are recorded for today.",
                    "今天没有记录的日程。",
                  );
          setNotice(full);
          const voice = speechSynthesis
            .getVoices()
            .find((v) => v.localService && v.lang.startsWith(t("en", "zh")));
          if (voice) {
            const utterance = new SpeechSynthesisUtterance(full);
            utterance.voice = voice;
            speechSynthesis.speak(utterance);
          }
        }
      } catch {
        /* Screen reminders stay available. A claimed sound is not retried. */
      } finally {
        working = false;
      }
    };
    void poll();
    const timer = setInterval(() => void poll(), 2500);
    return () => {
      alive = false;
      clearInterval(timer);
      speechSynthesis.cancel();
    };
  }, [enabled, t]);
  useEffect(
    () => () => {
      void context.current?.close();
      speechSynthesis.cancel();
    },
    [],
  );
  return { enabled, toggle, notice };
}
