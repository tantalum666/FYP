import { useEffect, useRef, useState } from "react";
import { DateTime } from "luxon";
import { ApiError, pendingWrite, request } from "../api";
import { editable } from "../types";
import type { EventInput, Occurrence } from "../types";
import type { EditorState } from "./Dialogs";

/** Shared web/phone editing state; a late detail read cannot reopen a closed dialog. */
export function useCalendarEditor({
  selectedDate,
  now,
  zone,
  onError,
}: {
  selectedDate: string;
  now: DateTime;
  zone: string;
  onError: (error: unknown) => void;
}) {
  const [editor, updateEditor] = useState<EditorState | null>(null);
  const [detail, updateDetail] = useState<Occurrence | null>(null);
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );
  const setEditor = (value: EditorState | null) => {
    generation.current++;
    updateEditor(value);
  };
  const setDetail = (value: Occurrence | null) => {
    generation.current++;
    updateDetail(value);
  };
  function newEventOnDate(onDate: string) {
    if (pendingWrite()) {
      onError(new ApiError("PENDING_WRITE"));
      return;
    }
    const start = DateTime.fromISO(onDate, { zone }).set({
      hour: Math.min(22, Math.max(9, now.setZone(zone).hour + 1)),
      minute: 0,
    });
    setEditor({
      scope: "series",
      initial: {
        title: "",
        start_local: start.toFormat("yyyy-MM-dd'T'HH:mm"),
        end_local: start.plus({ hours: 1 }).toFormat("yyyy-MM-dd'T'HH:mm"),
        timezone: zone,
        all_day: false,
        calendar: "personal",
        color: "lavender",
        visibility: "private",
        busy: true,
        location: "",
        notes: "",
        recurrence: { frequency: "none", interval: 1, until: null },
        reminder_minutes: [10],
      },
    });
  }
  async function editEvent(scope: "series" | "occurrence") {
    if (!detail) return;
    const current = ++generation.current;
    try {
      const initial =
        scope === "series"
          ? await request<EventInput>(`/events/${detail.id}`)
          : {
              ...editable(detail),
              recurrence: {
                frequency: "none" as const,
                interval: 1,
                until: null,
              },
            };
      if (current !== generation.current) return;
      setEditor({
        initial,
        scope,
        id: detail.id,
        version: detail.version,
        occurrenceKey: detail.occurrence_key,
        repeating: detail.series_recurrence.frequency !== "none",
      });
      setDetail(null);
    } catch (error) {
      if (current === generation.current) onError(error);
    }
  }
  return {
    editor,
    setEditor,
    detail,
    setDetail,
    newEvent: () => newEventOnDate(selectedDate),
    newEventOnDate,
    editEvent,
  };
}
