import type { Snapshot } from "../types";
import type { PostureSnapshot } from "../workspace/types";

export function displayPrivacy(
  snapshot: Snapshot | null,
  posture: PostureSnapshot | undefined,
  stale: boolean,
) {
  if (!snapshot) return null;
  const hide =
    !posture ||
    (posture.preferences.enabled &&
      posture.preferences.privacy_when_away &&
      (stale ||
        !posture.connected ||
        ["absent", "unknown", "paused"].includes(posture.status)));
  if (!hide) return snapshot;
  return {
    ...snapshot,
    occurrences: snapshot.occurrences.map((event) =>
      event.visibility === "private"
        ? { ...event, title: "", location: "", notes: "", redacted: true }
        : event,
    ),
    reminders: snapshot.reminders.map((reminder) =>
      reminder.visibility === "displayable"
        ? reminder
        : { ...reminder, title: "", redacted: true },
    ),
  };
}
