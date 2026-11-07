import assert from "node:assert/strict";
import test from "node:test";
import {
  createWeatherLocationReader,
  locateOnce,
} from "../src/companion/weatherLocation.ts";
function fixture(permission: PermissionState = "prompt") {
  const flags = new Map<string, string>();
  let calls = 0;
  const storage = {
    getItem: (key: string) => flags.get(key) ?? null,
    setItem: (key: string, value: string) => {
      flags.set(key, value);
    },
    removeItem: (key: string) => {
      flags.delete(key);
    },
  };
  return {
    storage,
    flags,
    count: () => calls,
    options: {
      permission: async () => permission,
      storage: () => storage,
      locate: async () => {
        calls++;
        return { latitude: 22.31987, longitude: 114.17234 };
      },
    },
  };
}
test("automatic weather reads never show a permission prompt when permission is prompt or denied", async () => {
  for (const state of ["prompt", "denied"] as PermissionState[]) {
    const f = fixture(state);
    const read = createWeatherLocationReader(f.options);
    assert.equal(await read(), null);
    assert.equal(await read(), null);
    assert.equal(f.count(), 0);
  }
});
test("already granted location is coarsened and concurrent updates share one request", async () => {
  const f = fixture("granted");
  const read = createWeatherLocationReader(f.options);
  const values = await Promise.all([read(), read(), read()]);
  assert.deepEqual(values[0], { latitude: 22.3, longitude: 114.2 });
  assert.equal(f.count(), 1);
  assert.deepEqual(await read(), values[0]);
  assert.equal(f.count(), 1);
  assert.equal(f.flags.size, 0); // No coordinates persisted.
});
test("failure survives a component/module restart and needs an explicit retry", async () => {
  const f = fixture("granted");
  let attempts = 0;
  const options = {
    ...f.options,
    locate: async () => {
      attempts++;
      throw new Error("Unavailable");
    },
  };
  assert.equal(await createWeatherLocationReader(options)(), null);
  const next = createWeatherLocationReader(options);
  assert.equal(await next(), null);
  assert.equal(attempts, 1);
  assert.equal(await next(true), null);
  assert.equal(attempts, 2);
});
test("manual location action may request permission once", async () => {
  const f = fixture("prompt");
  const read = createWeatherLocationReader(f.options);
  assert.deepEqual(await read(true), { latitude: 22.3, longitude: 114.2 });
  assert.equal(f.count(), 1);
});

test("unsupported permission querying falls back without requesting location", async () => {
  const f = fixture("granted");
  const read = createWeatherLocationReader({
    ...f.options,
    permission: async () => {
      throw new Error("Unsupported");
    },
  });
  assert.equal(await read(), null);
  assert.equal(f.count(), 0);
});

test("a stalled permission request has an application deadline and releases its watch", async () => {
  let cleared = 0;
  let late: PositionCallback | undefined;
  const location = {
    watchPosition: (success: PositionCallback) => {
      late = success;
      return 17;
    },
    clearWatch: (id: number) => {
      assert.equal(id, 17);
      cleared++;
    },
  };
  await assert.rejects(locateOnce(location, 5), /Location unavailable/);
  assert.equal(cleared, 1);
  late?.({
    coords: { latitude: 22.3, longitude: 114.2 },
  } as GeolocationPosition);
  assert.equal(cleared, 1);
});
