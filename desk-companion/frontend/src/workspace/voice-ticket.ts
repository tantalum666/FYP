/** Local slot handover only. This never retries a model/provider connection. */
export async function handoverTicket(
  request: () => Promise<string>,
  active: () => boolean,
  options: { now?: () => number; sleep?: (ms: number) => Promise<void> } = {},
) {
  const now = options.now ?? (() => performance.now());
  const sleep =
    options.sleep ??
    ((ms) => new Promise<void>((resolve) => setTimeout(resolve, ms)));
  const started = now();
  for (let attempt = 0; ; attempt++) {
    if (!active()) throw new Error("VOICE_CONNECTION_CANCELLED");
    try {
      return await request();
    } catch (error) {
      const code =
        error && typeof error === "object" && "code" in error
          ? error.code
          : null;
      if (code !== "VOICE_BUSY" || attempt >= 19 || now() - started >= 5000)
        throw error;
      await sleep(250);
    }
  }
}
