import type { ComputerJobSummary } from "./jobTypes";

export interface TaskStep {
  title: string;
  done: boolean;
}
export interface TaskInput {
  title: string;
  timezone: string;
  due_local: string | null;
  status: "todo" | "in_progress" | "waiting";
  next_step: string;
  waiting_for: string;
  steps: TaskStep[];
  visibility: "private" | "displayable";
  follow_up_enabled: boolean;
  check_in_local: string | null;
  interval_minutes: number;
}
export interface Task extends Omit<TaskInput, "status"> {
  id: string;
  version: number;
  status: TaskInput["status"] | "completed" | "cancelled";
  completion_source?: string | null;
  paused: boolean;
  next_check_at: string | null;
  due_at: string | null;
  created_at: string;
  updated_at: string;
  overdue: boolean;
  redacted: boolean;
  followup: null | {
    id: string;
    created_at: string;
    en: string;
    zh: string;
    mode: string;
    ai_status: string;
    reason_en?: string;
    reason_zh?: string;
  };
}
export interface TaskEvidence {
  id: number;
  at: string;
  kind: string;
  note: string;
  source: string;
  task_version: number;
}
export interface TaskList {
  tasks: Task[];
  timezone: string;
  revision: number;
  server_time: string;
}

export interface TaskDetail {
  task: Task;
  evidence: TaskEvidence[];
  jobs: ComputerJobSummary[];
  application?: import("./applicationTypes").ApplicationState | null;
}
