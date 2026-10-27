export type Language = "en" | "zh";
export type Page =
  | "today"
  | "calendar"
  | "tasks"
  | "memory"
  | "persona"
  | "records"
  | "device"
  | "diagnostics";
export type View = "day" | "week" | "month";
export type Frequency = "none" | "daily" | "weekly" | "monthly" | "yearly";
export type EventColor = "lavender" | "blue" | "sage" | "peach";
export interface EventInput {
  title: string;
  start_local: string;
  end_local: string;
  timezone: string;
  all_day: boolean;
  calendar: "personal" | "study";
  color: EventColor;
  visibility: "private" | "displayable";
  busy: boolean;
  location: string;
  notes: string;
  recurrence: { frequency: Frequency; interval: number; until: string | null };
  reminder_minutes: number[];
}
export interface Occurrence extends EventInput {
  id: string;
  version: number;
  occurrence_key: string;
  start: string;
  end: string;
  completed: boolean;
  is_exception: boolean;
  conflicts: string[];
  redacted?: boolean;
  origin: "manual" | "sample";
  series_recurrence: EventInput["recurrence"];
}
export interface Settings {
  timezone: string;
  hide_private: boolean;
  version: number;
}
export interface Reminder {
  visibility?: "private" | "displayable";
  id: string;
  title: string;
  redacted: boolean;
  status: string;
  due_at: string;
  snooze_until: string | null;
  version: number;
}
export interface Snapshot {
  revision: number;
  server_time: string;
  settings: Settings;
  occurrences: Occurrence[];
  event_count: number;
  has_samples: boolean;
  reminders: Reminder[];
  device: Record<string, string>;
}
export interface RecordEntry {
  sequence: number;
  at: string;
  action: string;
  title: string | null;
  details: Record<string, unknown>;
}
export interface Session {
  username: string;
  settings: Settings;
}
export type Translate = (en: string, zh: string) => string;

export function editable(event: EventInput): EventInput {
  return {
    title: event.title,
    start_local: event.start_local.slice(0, 16),
    end_local: event.end_local.slice(0, 16),
    timezone: event.timezone,
    all_day: event.all_day,
    calendar: event.calendar,
    color: event.color,
    visibility: event.visibility,
    busy: event.busy,
    location: event.location,
    notes: event.notes,
    recurrence: { ...event.recurrence },
    reminder_minutes: [...event.reminder_minutes],
  };
}
