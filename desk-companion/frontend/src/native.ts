import { Capacitor, registerPlugin } from "@capacitor/core";
import type { PluginListenerHandle } from "@capacitor/core";
export interface PhoneStatus {
  permission: "allowed" | "denied" | "not_requested";
  enabled: boolean;
  scheduled: number;
  widgetAvailable: boolean;
}

interface DeskNative {
  configuration(): Promise<{ origin: string; paired: boolean; route?: string }>;
  phoneStatus(): Promise<PhoneStatus>;
  enableNotifications(options: { enabled: boolean }): Promise<PhoneStatus>;
  syncPhone(options: {
    snapshot: Record<string, unknown>;
  }): Promise<PhoneStatus>;
  clearPhone(): Promise<void>;
  addListener(
    event: "route",
    listener: (event: { route: string }) => void,
  ): Promise<PluginListenerHandle>;
  configure(options: { origin: string }): Promise<{ origin: string }>;
  request(options: {
    path: string;
    method: string;
    body?: string;
    headers: Record<string, string>;
  }): Promise<{ status: number; bodyBase64: string; contentType: string }>;
  exportFile(options: {
    filename: string;
    bodyBase64: string;
  }): Promise<{ shared: boolean }>;
}
export const native = registerPlugin<DeskNative>("DeskNative");
export const isNative = Capacitor.isNativePlatform();
let serverOrigin = "";
export function apiOrigin() {
  return isNative ? serverOrigin : location.origin;
}
export async function loadNativeConfig() {
  if (!isNative) return { origin: location.origin, paired: false };
  const config = await native.configuration();
  serverOrigin = config.origin;
  return config;
}
export async function configureNative(origin: string) {
  const result = await native.configure({ origin });
  serverOrigin = result.origin;
  return result;
}
export async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  if (!isNative)
    return fetch("/api" + path, { ...options, credentials: "same-origin" });
  const result = await native.request({
    path,
    method: options.method ?? "GET",
    body: typeof options.body === "string" ? options.body : undefined,
    headers: Object.fromEntries(new Headers(options.headers).entries()),
  });
  const bytes = Uint8Array.from(atob(result.bodyBase64), (c) =>
    c.charCodeAt(0),
  );
  return new Response(bytes, {
    status: result.status,
    headers: { "Content-Type": result.contentType },
  });
}
