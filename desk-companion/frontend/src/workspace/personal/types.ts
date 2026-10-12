export interface ContextDestination {
  id: string;
  kind: "text" | "voice";
  provider: string;
  endpoint: string;
  configured: boolean;
}
export interface ContextSettings {
  version: number;
  save_text_history: boolean;
  use_text_history_in_ai: boolean;
  use_memory_in_ai: boolean;
  share_business_context: boolean;
  approved_destinations: string[];
  authorization_current: boolean;
  destinations: ContextDestination[];
}
export interface Conversation {
  id: string;
  title: string;
  language: string;
  version: number;
  created_at: string;
  updated_at: string;
  message_count: number;
}
export interface SavedMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  mode?: string;
  proposal_id?: string | null;
  proposal_kind?: string | null;
  proposal_state?: string | null;
}
export interface ConversationDetail {
  conversation: Conversation;
  messages: SavedMessage[];
}
export type MemoryCategory = "fact" | "preference" | "decision";
export interface PersonalMemory {
  id: string;
  content: string;
  category: MemoryCategory;
  version: number;
  source: "owner" | "confirmed_assistant";
  created_at: string;
  updated_at: string;
}
export function personalContextVisible(
  owner: boolean,
  visible: boolean | undefined,
  offline: boolean,
  stale: boolean,
) {
  return owner && visible === true && !offline && !stale;
}
export function canSendText(
  text: string,
  locked: boolean,
  conversationId: string | null,
  settings: ContextSettings | null,
  visible: boolean,
) {
  return (
    !!text.trim() &&
    !locked &&
    (!conversationId || (visible && settings?.save_text_history === true))
  );
}
export function contextChoices(settings: ContextSettings) {
  return {
    expected_version: settings.version,
    save_text_history: settings.save_text_history,
    use_text_history_in_ai: settings.use_text_history_in_ai,
    use_memory_in_ai: settings.use_memory_in_ai,
    share_business_context: settings.share_business_context,
    approved_destinations:
      settings.use_text_history_in_ai ||
      settings.use_memory_in_ai ||
      settings.share_business_context
        ? settings.destinations.filter((x) => x.configured).map((x) => x.id)
        : [],
  };
}
export function replyMode(mode?: string): "local" | "ai" | "unknown" {
  return ["local", "local_rules"].includes(mode ?? "")
    ? "local"
    : ["cloud", "ai"].includes(mode ?? "")
      ? "ai"
      : "unknown";
}

export function conversationSwitch(
  current: string | null,
  next: string | null,
  dirty: boolean,
  locked: boolean,
  voiceActive: boolean,
): "stay" | "confirm" | "switch" {
  if (current === next || locked || voiceActive) return "stay";
  return dirty ? "confirm" : "switch";
}
