/** Pure SSE reducer for one assistant reply. No DOM and no network. */

export interface ToolProgress {
  tool: string;
  phase: "started" | "finished";
  saved?: boolean;
  outcome?: string;
}

export interface StreamReply {
  mode?: string;
  kind?: string;
  message: string;
  plan?: string;
  saved?: boolean;
  error?: string;
  proposal?: unknown;
  [key: string]: unknown;
}

export type StreamEvent =
  | {
      type: "tool";
      phase: "started" | "finished";
      tool: string;
      saved?: boolean;
      outcome?: string;
    }
  | { type: "delta"; text: string }
  | { type: "preview"; text: string }
  | { type: "done"; reply: StreamReply }
  | { type: "error"; code: string; status?: number };

export interface StreamState {
  message: string;
  tools: ToolProgress[];
  reply: StreamReply | null;
  error: string | null;
  status: number | null;
  done: boolean;
}

export function emptyStream(): StreamState {
  return { message: "", tools: [], reply: null, error: null, status: null, done: false };
}

export function progressLabel(phase: "started" | "finished", language: string): string {
  if (phase === "started") return language === "zh" ? "进行中" : "Working";
  return language === "zh" ? "完成" : "Done";
}

export function reduceReply(state: StreamState, event: StreamEvent): StreamState {
  if (event.type === "delta") {
    return { ...state, message: state.message + event.text };
  }
  if (event.type === "preview") {
    return { ...state, message: event.text };
  }
  if (event.type === "tool") {
    const tools = state.tools.slice();
    const row: ToolProgress = {
      tool: event.tool,
      phase: event.phase,
      saved: event.saved,
      outcome: event.outcome,
    };
    if (event.phase === "finished") {
      let index = -1;
      for (let cursor = tools.length - 1; cursor >= 0; cursor -= 1) {
        if (tools[cursor].tool === event.tool && tools[cursor].phase === "started") {
          index = cursor;
          break;
        }
      }
      if (index >= 0) tools[index] = row;
      else tools.push(row);
    } else {
      tools.push(row);
    }
    return { ...state, tools };
  }
  if (event.type === "done") {
    const message =
      typeof event.reply?.message === "string" ? event.reply.message : state.message;
    return {
      ...state,
      message,
      reply: { ...event.reply, message },
      done: true,
      error: null,
    };
  }
  if (event.type === "error") {
    return { ...state, error: event.code, status: event.status ?? 500, done: true };
  }
  return state;
}

export function parseSse(buffer: string): { events: StreamEvent[]; rest: string } {
  const parts = buffer.replace(/\r\n/g, "\n").split("\n\n");
  const rest = parts.pop() ?? "";
  const events: StreamEvent[] = [];
  for (const part of parts) {
    const data = part
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) continue;
    const parsed = JSON.parse(data) as StreamEvent;
    if (
      parsed &&
      (parsed.type === "tool" ||
        parsed.type === "delta" ||
        parsed.type === "preview" ||
        parsed.type === "done" ||
        parsed.type === "error")
    ) {
      events.push(parsed);
    }
  }
  return { events, rest };
}

export function consumeChunk(
  state: StreamState,
  buffer: string,
  chunk: string,
): { state: StreamState; buffer: string } {
  const parsed = parseSse(buffer + chunk);
  return { state: parsed.events.reduce(reduceReply, state), buffer: parsed.rest };
}

/** Read a Response body, one chunk at a time. A buffered phone body is one chunk. */
export async function readBody(
  response: Response,
  onChunk: (text: string) => void,
): Promise<void> {
  if (!response.body) throw new Error("NO_BODY");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      const tail = decoder.decode();
      if (tail) onChunk(tail);
      return;
    }
    onChunk(decoder.decode(value, { stream: true }));
  }
}
