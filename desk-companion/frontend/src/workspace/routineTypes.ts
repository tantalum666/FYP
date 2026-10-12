export type RoutineSkill = "day_briefing" | "task_review";
export type RoutineFrequency = "once" | "daily" | "weekly";
export type RoutineAction = "pause" | "resume" | "cancel";
export interface RoutineInput {
  title: string;
  skill: RoutineSkill;
  frequency: RoutineFrequency;
  start_local: string;
  timezone: string;
}
export interface Routine extends RoutineInput {
  id: string;
  version: number;
  status: "active" | "paused" | "completed" | "cancelled";
  next_run_at: string | null;
  last_scheduled_at: string | null;
  created_at: string;
  updated_at: string;
}
export interface RoutineItem {
  kind: "task" | "event";
  id: string;
  title: string;
  available: boolean;
  redacted: boolean;
  title_source: "current_record";
  visibility: "private" | "displayable";
  status?: string;
  due_at?: string | null;
  overdue?: boolean;
  start?: string;
  end?: string;
  occurrence_key?: string;
}
export interface RoutineRun {
  id: string;
  routine_id: string;
  occurrence_key: string;
  scheduled_at: string;
  created_at: string;
  delivery_state: "pending" | "claimed" | "suppressed" | "dismissed";
  result_run_id?: string;
  coalesced_delivery?: boolean;
  result: {
    status: "ready" | "failed";
    error_code?: string;
    source: "local_rules";
    skill: RoutineSkill;
    as_of: string;
    timezone: string;
    local_date: string;
    counts: {
      events: number;
      tasks: number;
      overdue_tasks: number;
      waiting_tasks: number;
    };
    items: RoutineItem[];
    suggested_action:
      "review_tasks" | "review_calendar_and_tasks" | "check_local_sources";
    truncated: boolean;
    catch_up: boolean;
  };
}
export interface RoutineList {
  routines: Routine[];
  pending_count: number;
  revision: number;
  server_time: string;
  limits: { routines: number; pending_deliveries: number };
}
export interface RoutineDetail {
  routine: Routine;
  runs: RoutineRun[];
  revision: number;
}
export interface RoutineClaim {
  claimed: number;
  deliveries: RoutineRun[];
  delivery_ids: string[];
  unavailable_delivery_ids: string[];
}
export function routineActions(status: Routine["status"]): RoutineAction[] {
  return status === "active"
    ? ["pause", "cancel"]
    : status === "paused"
      ? ["resume", "cancel"]
      : [];
}
export function canRevealRoutines(
  visible: boolean,
  fresh: boolean,
  locked: boolean,
  pending: number,
) {
  return visible && fresh && !locked && pending > 0;
}
export function routineItemTitle(
  item: RoutineItem,
  hidden: string,
  removed: string,
) {
  return !item.available ? removed : item.redacted ? hidden : item.title;
}
/** Stable delivery IDs are distinct from the latest coalesced result's run ID. */
export function uniqueDeliveries(deliveries: RoutineRun[]) {
  return [
    ...new Map(deliveries.map((delivery) => [delivery.id, delivery])).values(),
  ];
}
