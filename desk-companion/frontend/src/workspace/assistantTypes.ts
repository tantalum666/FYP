import type { EventInput } from "../types";
import type { Task, TaskInput } from "./taskTypes";

export interface Proposal {
  id: string;
  kind:
    | "create"
    | "change"
    | "output"
    | "task_create"
    | "task_change"
    | "memory_save"
    | "memory_replace"
    | "memory_delete"
    | "memory_consolidate";
  expires_at: string;
  data: {
    task?: TaskInput;
    original_task?: Task;
    event?: EventInput;
    additional_dates?: string[];
    event_id?: string;
    original?: Pick<
      EventInput,
      | "title"
      | "start_local"
      | "end_local"
      | "timezone"
      | "visibility"
      | "all_day"
    >;
    output?: { kind: string; preset: string };
    body?: string;
    previous?: string;
    keep_body?: string;
    retire?: Array<{ body: string }>;
    reason_en?: string;
    reason_zh?: string;
    goal?: boolean;
    change?: {
      action: string;
      scope?: string;
      event?: EventInput;
      task?: TaskInput;
      note?: string;
      minutes?: number;
    };
  };
}
export interface Reply {
  permission_error?: string;
  conversation_id?: string;
  mode: string;
  kind: string;
  message: string;
  plan?: string;
  proposal?: Proposal | null;
  job?: { id: string };
}
