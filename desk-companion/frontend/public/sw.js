/* Shows one Web Push message. The server sends nothing unless DESK_WEB_PUSH=1. */
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (_error) {
    data = {};
  }
  event.waitUntil(
    self.registration.showNotification(data.title || "Desk Companion", {
      body: data.body || "",
      tag: data.tag || "desk",
    }),
  );
});
