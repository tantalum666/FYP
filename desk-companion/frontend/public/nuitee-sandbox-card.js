/* This document has its own loopback origin. Its host cannot serve the desk API. */
function allowedParent(origin) {
  if (location.hostname !== "nuitee-card.localhost") return false;
  if (origin === "capacitor://localhost") return true;
  try {
    const parentUrl = new URL(origin);
    return (
      parentUrl.protocol === location.protocol &&
      parentUrl.port === location.port &&
      ["127.0.0.1", "localhost", "[::1]"].includes(parentUrl.hostname)
    );
  } catch {
    return false;
  }
}

let active = false;
window.addEventListener("message", async (event) => {
  const data = event.data;
  if (
    event.source !== parent ||
    !allowedParent(event.origin) ||
    data?.type !== "alice-nuitee-sandbox" ||
    event.ports.length !== 1
  )
    return;
  const port = event.ports[0];
  if (
    active ||
    !/^pk_test_[A-Za-z0-9_-]+$/.test(data.publishable_key) ||
    !/^pi_[A-Za-z0-9]+_secret_[A-Za-z0-9]+$/.test(data.client_secret)
  ) {
    port.postMessage({ state: "invalid" });
    port.close();
    return;
  }
  active = true;
  try {
    if (!window.Stripe) {
      await new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = "https://js.stripe.com/v3/";
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }
    const processor = window.Stripe(data.publishable_key);
    const result = await processor.confirmCardPayment(data.client_secret, {
      payment_method: "pm_card_visa",
    });
    port.postMessage({ state: result.paymentIntent?.status || "error" });
  } catch {
    port.postMessage({ state: "unknown" });
  } finally {
    active = false;
    port.close();
  }
});
