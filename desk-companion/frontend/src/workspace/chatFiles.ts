export const CHAT_FILE_BYTES = 2 * 1024 * 1024;
export const CHAT_FILE_COUNT = 4;
export const CHAT_FILE_ACCEPT =
  ".pdf,.txt,.md,.markdown,.csv,.json,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.webp";
export interface ChatFileReference {
  id: string;
  name: string;
  mime: string;
  bytes: number;
}
export interface PickedChatFile {
  key: string;
  file: File;
  preview?: string;
}

export function validateChatFile(file: Pick<File, "name" | "size">) {
  const extension = file.name.split(".").at(-1)?.toLowerCase();
  if (
    !extension ||
    !CHAT_FILE_ACCEPT.split(",").includes(`.${extension}`) ||
    file.name.length > 160 ||
    /[\x00-\x1f\x7f/\\]/.test(file.name)
  )
    throw new Error("CHAT_FILE_FORMAT");
  if (!file.size || file.size > CHAT_FILE_BYTES)
    throw new Error("CHAT_FILE_SIZE");
}

export function fileBytesLabel(bytes: number) {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export async function encodeChatFile(file: File) {
  validateChatFile(file);
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (bytes.byteLength !== file.size || bytes.byteLength > CHAT_FILE_BYTES)
    throw new Error("CHAT_FILE_SIZE");
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 8192)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
  return { name: file.name, data: btoa(binary) };
}
