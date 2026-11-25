import type { EventInput } from "../types";
import type { Task, TaskInput } from "./taskTypes";
import type { QuoteRequest } from "./CommerceQuote";

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
    | "memory_consolidate"
    | "mailbox_reply"
    | "email_send"
    | "browser_research"
    | "mail_followup"
    | "followed_reply_draft"
    | "routine_skip"
    | "shopping_advice"
    | "calendar_advice";
  expires_at: string;
  data: {
    choices?: {
      routine_id: string;
      title: string;
      occurrence_key: string;
      timezone: string;
    }[];
    mail_followup?: {
      provider: "gmail" | "outlook";
      account_email: string;
      selected: { subject: string; sender: string; at: string };
      task_title: string;
      interval_minutes: number;
      duration_days: number;
      request: { task_id: string | null };
    };
    browser?: {
      quote_request?: QuoteRequest;
      engine: "local" | "managed";
      title: string;
      goal: string;
      start_url: string;
      allowed_origins: string[];
      task_id: string | null;
      task_version: number | null;
      source_job_id: string | null;
    };
    from?: string;
    reply?: { message_id: string; thread_id: string; subject: string; to: string };
    to?: string;
    subject?: string;
    title?: string;
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
    summary?: string;
    reply_draft?: string | null;
    mail_id?: string;
    event_uid?: string;
    observed_at?: string;
    shopping?: {
      fixture_id: string;
      event_id: string;
      observed_at: string;
      note: string;
      provided_fields?: Partial<
        Pick<TaskInput, "status" | "waiting_for" | "next_step" | "title">
      >;
    };
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
export interface ProposalDecisionOptions {
  routine_id?: string;
  share_screen?: boolean;
  share_itinerary?: boolean;
  follow_mail_thread?: boolean;
}
export interface ProposalDecisionReply {
  paused?: boolean;
  queued?: boolean;
  kind?: string;
  job?: { id: string };
}
export interface Reply {
  history_ids?: [string, string];
  history_at?: string;
  catch_up_ref?: string;
  google_refresh_scope?: { review_version: string; last_refresh_ref: string };
  approval_summary?: string;
  live_flight_checkout?: import("./LiveFlightCheckout").LiveCheckout;
  delivery?: import("../companion/delivery").Delivery;
  commerce_note?: boolean;
  flight_shortlist_chat?: string | null;
  flight_alternatives?: import("./commercePresentation").FlightAlternatives;
  shopping_order?: import("./SandboxShopOrder").SandboxShop;
  flight_booking?: import("./SandboxFlightBooking").SandboxFlight;
  permission_error?: string;
  conversation_id?: string;
  mode: string;
  kind: string;
  message: string;
  plan?: string;
  proposal?: Proposal | null;
  job?: { id: string };
  open_time?: {
    openings: Array<{ start: string; end: string }>;
    booked: false;
  };
}
