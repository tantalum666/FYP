/** Check a self-contained local VRM before passing its bytes to the viewer. */
export function validateLocalVrm(bytes: ArrayBuffer): void {
  if (bytes.byteLength < 28 || bytes.byteLength > 64 * 1024 * 1024)
    throw new Error("VRM_SIZE");
  const view = new DataView(bytes);
  const jsonLength = view.getUint32(12, true);
  if (
    view.getUint32(0, true) !== 0x46546c67 ||
    view.getUint32(4, true) !== 2 ||
    view.getUint32(8, true) !== bytes.byteLength ||
    view.getUint32(16, true) !== 0x4e4f534a ||
    jsonLength > bytes.byteLength - 20
  )
    throw new Error("VRM_FORMAT");
  const data = JSON.parse(
    new TextDecoder().decode(new Uint8Array(bytes, 20, jsonLength)),
  );
  if (!data?.extensions?.VRM && !data?.extensions?.VRMC_vrm)
    throw new Error("VRM_EXTENSION");
  // Only self-contained files: importing a local character must not fetch
  // texture/buffer URLs embedded by a third party.
  for (const resource of [...(data.buffers ?? []), ...(data.images ?? [])]) {
    if (resource.uri) throw new Error("VRM_EXTERNAL_RESOURCE");
  }
}

export type LocalVrm = { name: string; bytes: ArrayBuffer };

/** The model stays in this browser, outside the app server and source tree. */
async function localModelStore<T>(
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open("desk-companion.local-vrm.v1", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("model");
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error("VRM_STORAGE_BLOCKED"));
  });
  try {
    return await new Promise<T>((resolve, reject) => {
      const transaction = db.transaction("model", mode);
      const request = operation(transaction.objectStore("model"));
      transaction.oncomplete = () => resolve(request.result);
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally {
    db.close();
  }
}

export async function readLocalVrm(): Promise<LocalVrm | null> {
  const value: unknown = await localModelStore("readonly", (store) =>
    store.get("selected"),
  );
  if (!value) return null;
  const candidate = value as Partial<LocalVrm>;
  if (
    typeof candidate.name !== "string" ||
    !(candidate.bytes instanceof ArrayBuffer)
  )
    throw new Error("VRM_STORAGE_FORMAT");
  validateLocalVrm(candidate.bytes);
  return { name: candidate.name, bytes: candidate.bytes };
}

export function saveLocalVrm(value: LocalVrm): Promise<IDBValidKey> {
  return localModelStore("readwrite", (store) => store.put(value, "selected"));
}

export function clearLocalVrm(): Promise<undefined> {
  return localModelStore("readwrite", (store) => store.delete("selected"));
}
