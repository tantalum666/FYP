import type { PrivateOperation } from "../personal/privateWrite.ts";
import { sourceFormat } from "./types.ts";
export const SOURCE_BYTE_LIMIT = 1024 * 1024;
export async function readSourceFile(
  file: Pick<File, "name" | "size" | "arrayBuffer">,
) {
  const format = sourceFormat(file.name);
  if (!format || file.name.length > 160 || /[\x00-\x1f/\\]/.test(file.name))
    throw new Error("SOURCE_FORMAT_INVALID");
  if (file.size > SOURCE_BYTE_LIMIT) throw new Error("SOURCE_TOO_LARGE");
  const bytes = await file.arrayBuffer();
  if (bytes.byteLength > SOURCE_BYTE_LIMIT) throw new Error("SOURCE_TOO_LARGE");
  let content: string;
  try {
    content = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(
      bytes,
    );
  } catch {
    throw new Error("SOURCE_FORMAT_INVALID");
  }
  if (!content.trim() || content.includes("\0"))
    throw new Error("INVALID_SOURCE_TEXT");
  const path = `/sources/upload?${new URLSearchParams({ name: file.name, format })}`;
  return { path, body: { content } };
}
/** Adapt the existing memory-only queue to the raw UTF-8 upload endpoint. */
export function rawUpload(operation: Readonly<PrivateOperation>) {
  const parsed: unknown = JSON.parse(operation.serialized);
  if (
    !parsed ||
    typeof parsed !== "object" ||
    !("content" in parsed) ||
    typeof parsed.content !== "string"
  )
    throw new Error("SOURCE_FORMAT_INVALID");
  if (new TextEncoder().encode(parsed.content).byteLength > SOURCE_BYTE_LIMIT)
    throw new Error("SOURCE_TOO_LARGE");
  return {
    path: operation.path,
    body: parsed.content,
    headers: {
      "Content-Type": "text/plain;charset=utf-8",
      "X-Operation-Id": operation.key,
    },
  };
}
