import assert from "node:assert/strict";
import test from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import {
  failureNotice,
  loadingNotice,
  offlineNotice,
  sessionExpiredNotice,
} from "../src/surfaceNotice.ts";
import { classifyFailure } from "../src/surfaceStatus.ts";

test("a lost connection, a server error, and an expired session stay distinct", () => {
  assert.equal(
    classifyFailure({ code: "OWNER_SIGN_IN_REQUIRED", status: 401 }, true),
    "session-expired",
  );
  assert.equal(
    classifyFailure({ code: "AUTH_REQUIRED", status: 401 }, false),
    "signed-out",
  );
  assert.equal(
    classifyFailure({ code: "REQUEST_FAILED", status: 500 }, true),
    "error",
  );
  assert.equal(
    classifyFailure({ code: "CONNECTION_LOST", status: 0 }, true),
    "offline",
  );
  assert.equal(classifyFailure(new Error("socket"), true), "offline");
});

test("loading, offline, error, and session-expiry notices expose their roles", () => {
  const loading = renderToStaticMarkup(loadingNotice("Opening your workspace…"));
  assert.match(loading, /role="status"/);
  assert.match(loading, /aria-live="polite"/);
  assert.match(loading, /Opening your workspace…/);

  const offline = renderToStaticMarkup(
    offlineNotice(
      "Offline. Showing your last loaded calendar.",
      "Reconnect",
      () => undefined,
    ),
  );
  assert.match(offline, /role="status"/);
  assert.match(offline, /Reconnect/);
  assert.doesNotMatch(offline, /role="alert"/);

  const failure = renderToStaticMarkup(
    failureNotice("The desk could not load this calendar.", "Dismiss", () => undefined),
  );
  assert.match(failure, /role="alert"/);
  assert.match(failure, /Dismiss/);

  const expired = renderToStaticMarkup(
    sessionExpiredNotice("Your owner session expired. Sign in again."),
  );
  assert.match(expired, /role="alert"/);
  assert.match(expired, /Sign in again/);
  assert.doesNotMatch(expired, /Offline/);
});
