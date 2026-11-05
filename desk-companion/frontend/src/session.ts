import { ApiError, request } from "./api";
import type { Session } from "./types";

let opening: Promise<Session> | null = null;

// One bootstrap shared by web, phone/native and the device surface. No password
// is stored in the bundle, and ordinary business writes are never replayed here.
async function connectSession(): Promise<Session> {
  try {
    return await request<Session>("/session");
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    return request<Session>("/session/connect", { method: "POST", body: "{}" });
  }
}

export function openSession(): Promise<Session> {
  if (!opening) {
    opening = connectSession().finally(() => {
      opening = null;
    });
  }
  return opening;
}
