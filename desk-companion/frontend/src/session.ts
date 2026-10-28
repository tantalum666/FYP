import { ApiError, request } from "./api";
import type { Session } from "./types";

// Shared by the web workspace and the native phone; no password is embedded.
export async function openSession(): Promise<Session> {
  try {
    return await request<Session>("/session");
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    const mode = await request<{ local_preview: boolean }>("/session-mode");
    if (!mode.local_preview) throw error;
    await request("/session/preview", { method: "POST", body: "{}" });
    return request<Session>("/session");
  }
}
