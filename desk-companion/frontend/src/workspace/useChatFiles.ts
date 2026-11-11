import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, request } from "../api";
import {
  CHAT_FILE_COUNT,
  encodeChatFile,
  validateChatFile,
  type PickedChatFile,
  type ChatFileReference,
} from "./chatFiles";

/** Selection stays on the client. Only Send uploads into session-scoped chat RAM. */
export function useChatFiles() {
  const [files, setFiles] = useState<PickedChatFile[]>([]);
  const current = useRef<PickedChatFile[]>([]);
  const revision = useRef(0);
  const [error, setError] = useState<unknown>(null);
  const replace = useCallback((next: PickedChatFile[]) => {
    for (const item of current.current)
      if (!next.some((file) => file.key === item.key) && item.preview)
        URL.revokeObjectURL(item.preview);
    current.current = next;
    setFiles(next);
    revision.current += 1;
  }, []);
  const clear = useCallback(() => {
    replace([]);
    setError(null);
  }, [replace]);
  useEffect(
    () => () => {
      revision.current += 1;
      for (const file of current.current)
        if (file.preview) URL.revokeObjectURL(file.preview);
      current.current = [];
    },
    [],
  );
  function add(selected: File[]) {
    try {
      const unique = selected.filter(
        (file) => !current.current.some((item) => item.file === file),
      );
      if (current.current.length + unique.length > CHAT_FILE_COUNT)
        throw new ApiError("CHAT_FILE_COUNT");
      for (const file of unique) validateChatFile(file);
      replace([
        ...current.current,
        ...unique.map((file) => ({
          key: crypto.randomUUID(),
          file,
          preview: file.type.startsWith("image/")
            ? URL.createObjectURL(file)
            : undefined,
        })),
      ]);
      setError(null);
    } catch (failure) {
      setError(
        failure instanceof ApiError
          ? failure
          : new ApiError(
              failure instanceof Error ? failure.message : "CHAT_FILE_FORMAT",
            ),
      );
    }
  }
  async function upload(
    conversationId: string | undefined,
    taskId: string | undefined,
    accepts: () => boolean,
    onConversation: (id: string) => void,
  ) {
    const selected = current.current.slice(),
      epoch = revision.current;
    const references: ChatFileReference[] = [];
    let id = conversationId;
    for (const item of selected) {
      const data = await encodeChatFile(item.file);
      if (!accepts() || epoch !== revision.current)
        throw new ApiError("CHAT_FILES_CHANGED");
      const result = await request<{
        conversation_id: string;
        attachment: ChatFileReference;
      }>("/assistant/attachments", {
        method: "POST",
        body: JSON.stringify({
          ...data,
          conversation_id: id ?? null,
          task_id: taskId ?? null,
        }),
      });
      if (!accepts() || epoch !== revision.current)
        throw new ApiError("CHAT_FILES_CHANGED");
      id = result.conversation_id;
      onConversation(id);
      if (!references.some((file) => file.id === result.attachment.id))
        references.push(result.attachment);
    }
    return {
      conversationId: id,
      references,
      keys: selected.map((item) => item.key),
    };
  }
  const sent = useCallback(
    (keys: string[]) => {
      replace(current.current.filter((file) => !keys.includes(file.key)));
    },
    [replace],
  );
  return {
    files,
    error,
    add,
    clear,
    upload,
    sent,
    remove: (key: string) => {
      replace(current.current.filter((file) => file.key !== key));
      setError(null);
    },
  };
}
