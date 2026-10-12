export class BrowserExportError extends Error {
  code: string;
  constructor(code: string) {
    super(code);
    this.code = code;
  }
}
function requireCurrent(current: () => boolean) {
  if (!current()) throw new BrowserExportError("BROWSER_VIEW_CHANGED");
}
/** Bound and verify real response bytes before exposing them to a download UI. */
export async function verifiedExportBytes(
  response: Response,
  expected: { byte_count: number; sha256: string },
  current: () => boolean,
) {
  requireCurrent(current);
  if (!response.ok) throw new BrowserExportError("BROWSER_EXPORT_UNAVAILABLE");
  if (
    !/^(text\/plain|text\/markdown|application\/octet-stream)(;|$)/i.test(
      response.headers.get("Content-Type") ?? "",
    )
  )
    throw new BrowserExportError("BROWSER_EXPORT_MISMATCH");
  if (
    Number(response.headers.get("Content-Length")) > 65536 ||
    expected.byte_count < 1 ||
    expected.byte_count > 65536
  )
    throw new BrowserExportError("BROWSER_EXPORT_MISMATCH");
  const reader = response.body?.getReader();
  if (!reader) throw new BrowserExportError("BROWSER_EXPORT_MISMATCH");
  const chunks: Uint8Array[] = [];
  let size = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (!current() || (value && size + value.byteLength > 65536)) {
      await reader.cancel();
      requireCurrent(current);
      throw new BrowserExportError("BROWSER_EXPORT_MISMATCH");
    }
    if (done) break;
    size += value.byteLength;
    chunks.push(value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  requireCurrent(current);
  if (bytes.byteLength !== expected.byte_count)
    throw new BrowserExportError("BROWSER_EXPORT_MISMATCH");
  const digest = Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
  requireCurrent(current);
  if (digest !== expected.sha256)
    throw new BrowserExportError("BROWSER_EXPORT_MISMATCH");
  return bytes;
}
