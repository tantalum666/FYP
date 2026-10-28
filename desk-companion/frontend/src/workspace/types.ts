export interface PosturePreferences {
  enabled: boolean;
  persistence_seconds: number;
  reassess_seconds: number;
  cooldown_seconds: number;
  movement_minutes: number;
  privacy_when_away: boolean;
}
export interface PostureSnapshot {
  connected: boolean;
  source: "live" | "replay" | null;
  status: string;
  reason: string | null;
  preferences: PosturePreferences;
  paused: boolean;
  calibration: {
    completed: string[];
    phase: string | null;
    samples: number;
    result: string | null;
    version: number;
    source: string | null;
  };
  candidate_seconds: number;
  valid_observed_seconds: number;
  continuous_presence_seconds: number;
  snooze_until: number;
  movement_feedback: {
    kind: string;
    created_at: number;
    outcome: string;
    source: string;
    assessed_at?: number;
  } | null;
  feedback: {
    kind: string;
    created_at: number;
    reassess_at: number;
    outcome: string;
    assessed_at?: number;
    source: string;
  } | null;
}
export interface WorkspaceSnapshot {
  text_ai: {
    configured: boolean;
    provider: string;
    model: string;
    background: boolean;
  };
  tasks: {
    active_count: number;
    due_count: number;
    attention: import("./taskTypes").Task[];
  };
  output_history: Array<{
    id: string;
    state: string;
    kind: string;
    preset: string;
    source: string;
    created_at: string;
  }>;
  posture: PostureSnapshot;
  principal: {
    kind: "owner" | "display" | "controller";
    id: string;
    name: string;
  };
  outputs: {
    connected: boolean;
    source: "live" | "replay" | null;
    hardware_verified: boolean;
    stopped: boolean;
    capabilities: string[];
    last_seen: string | null;
  };
  pairing?: {
    clients: Array<{
      id: string;
      name: string;
      kind: string;
      last_seen: string;
    }>;
    requests: Array<{
      id: string;
      name: string;
      check_code: string;
      expires_at: string;
    }>;
  };
  voice: {
    configured: boolean;
    state: string;
    provider: string;
    model: string;
    active: boolean;
    supports_images?: boolean;
    configuration_error?: string;
  };
  calendar_extras: {
    preferences: WorkspacePreferences;
    weather: {
      status: string;
      temperature_c?: number;
      observed_at?: string;
      source?: string;
      source_url?: string;
    };
    holidays: { en: Record<string, string>; zh: Record<string, string> };
    holiday_coverage: number[];
    quiet_now: boolean;
  };
  google: { configured: boolean; connected: boolean; last_read: string | null };
  replay_available: boolean;
  runtime: string;
}

export interface WorkspacePreferences {
  version: number;
  weather_location: "none" | "hong_kong";
  holiday_region: "none" | "hong_kong";
  show_lunar: boolean;
  reminder_strength: "silent" | "chime";
  quiet_enabled: boolean;
  quiet_start: string;
  quiet_end: string;
  daily_brief_time: string;
  daily_brief_enabled: boolean;
  evening_check_time: string;
  evening_check_enabled: boolean;
  avatar_display: "calendar" | "companion";
  voice_enabled: boolean;
}
