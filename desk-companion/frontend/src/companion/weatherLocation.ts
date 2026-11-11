/** Permission-aware, shared location read. Automatic updates never request consent. */
export type CoarseLocation = { latitude: number; longitude: number };
type StorageFlag = Pick<Storage, "getItem" | "setItem" | "removeItem">;
type Options = {
  permission: () => Promise<PermissionState>;
  locate: () => Promise<CoarseLocation>;
  storage: () => StorageFlag;
  now?: () => number;
};
const FAILED = "desk.weather.location-unavailable.v1";

export function createWeatherLocationReader(options: Options) {
  const now = options.now ?? Date.now;
  let pending: Promise<CoarseLocation | null> | null = null;
  let cached: { value: CoarseLocation; until: number } | null = null;
  let failed = false;
  function rememberFailure(value: boolean) {
    failed = value;
    try {
      if (value) options.storage().setItem(FAILED, "1");
      else options.storage().removeItem(FAILED);
    } catch {
      /* Memory-only fallback when browser storage is unavailable. */
    }
  }
  async function read(interactive = false): Promise<CoarseLocation | null> {
    if (pending) return pending;
    if (interactive) rememberFailure(false);
    else {
      try {
        failed ||= options.storage().getItem(FAILED) === "1";
      } catch {}
      if (failed) return null;
      let permission: PermissionState;
      try {
        permission = await options.permission();
      } catch {
        return null;
      }
      if (permission !== "granted") {
        cached = null;
        return null;
      }
      if (cached && now() < cached.until) return cached.value;
    }
    // The permission check itself is asynchronous: recheck the shared request.
    if (pending) return pending;
    pending = options
      .locate()
      .then((value) => {
        if (
          !Number.isFinite(value.latitude) ||
          !Number.isFinite(value.longitude)
        )
          throw new Error("Invalid location");
        const coarse = {
          latitude: Math.round(value.latitude * 10) / 10,
          longitude: Math.round(value.longitude * 10) / 10,
        };
        cached = { value: coarse, until: now() + 600000 };
        rememberFailure(false);
        return coarse;
      })
      .catch(() => {
        cached = null;
        rememberFailure(true);
        return null;
      })
      .finally(() => {
        pending = null;
      });
    return pending;
  }
  return read;
}

export function locateOnce(
  geolocation: Pick<Geolocation, "watchPosition" | "clearWatch">,
  timeoutMs = 5000,
): Promise<CoarseLocation> {
  return new Promise((resolve, reject) => {
    let watch: number | undefined;
    let settled = false;
    const finish = (value?: CoarseLocation) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (watch !== undefined) geolocation.clearWatch(watch);
      if (value) resolve(value);
      else reject(new Error("Location unavailable"));
    };
    // Browser geolocation timeouts can exclude time waiting on the permission
    // prompt. This application deadline covers the entire attempt and cancels it.
    const timer = setTimeout(() => finish(), timeoutMs);
    try {
      watch = geolocation.watchPosition(
        (position) =>
          finish({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          }),
        () => finish(),
        { enableHighAccuracy: false, timeout: 4000, maximumAge: 600000 },
      );
      if (settled) geolocation.clearWatch(watch);
    } catch {
      finish();
    }
  });
}

export const weatherLocation = createWeatherLocationReader({
  permission: async () =>
    (await navigator.permissions.query({ name: "geolocation" })).state,
  storage: () => localStorage,
  locate: () => locateOnce(navigator.geolocation),
});
