import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const root = new URL("../public/", import.meta.url);

function read(name) {
  return fs.readFileSync(new URL(name, root));
}

function pngSize(name) {
  const bytes = read(name);
  assert.equal(bytes.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
}

test("owner and device manifests are installable and do not name the API", () => {
  const owner = JSON.parse(read("manifest.webmanifest").toString());
  const device = JSON.parse(read("manifest-device.webmanifest").toString());
  assert.equal(owner.start_url, "/");
  assert.equal(owner.display, "standalone");
  assert.equal(device.start_url, "/?surface=device");
  assert.equal(device.scope, "/");
  assert.equal(device.display, "standalone");
  assert.deepEqual(
    owner.icons.map((icon) => icon.sizes),
    ["192x192", "512x512"],
  );
  assert.equal(pngSize("icon-192.png").width, 192);
  assert.equal(pngSize("icon-512.png").width, 512);
  const text = JSON.stringify(owner) + JSON.stringify(device);
  assert.equal(text.includes("/api"), false);
});

test("the boot script selects a manifest and registers the shell worker", () => {
  const source = read("pwa.js").toString();
  const html = fs.readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /src="\/pwa.js"/);
  assert.match(source, /manifest-device\.webmanifest/);
  assert.match(source, /manifest\.webmanifest/);
  assert.match(source, /serviceWorker\.register\("\/sw\.js"\)/);
  assert.equal(source.includes("/api"), false);
  assert.equal(source.includes("caches"), false);
});

test("the service worker does not cache authenticated API responses", async () => {
  const puts = [];
  const added = [];
  const deleted = [];
  const cache = {
    async match(request) {
      const url = typeof request === "string" ? request : request.url;
      return url.endsWith("/index.html") ? { url: "/index.html", body: "shell" } : undefined;
    },
    async put(request) {
      puts.push(new URL(request.url).pathname);
    },
    async addAll(files) {
      added.push(...files);
    },
  };
  const sandbox = {
    self: {
      location: { origin: "http://127.0.0.1:8831" },
      listeners: {},
      addEventListener(type, fn) {
        this.listeners[type] = fn;
      },
      skipWaiting() {},
      clients: { claim() {} },
    },
    caches: {
      async open() {
        return cache;
      },
      async match(request) {
        return cache.match(request);
      },
      async keys() {
        return ["desk-shell-v1", "desk-shell-old"];
      },
      async delete(key) {
        deleted.push(key);
      },
    },
    fetch(request) {
      const url = typeof request === "string" ? request : request.url;
      if (url.includes("offline=1")) return Promise.reject(new Error("offline"));
      return Promise.resolve({
        ok: true,
        type: "basic",
        url,
        clone() {
          return this;
        },
      });
    },
    URL,
    Response: { error() { return { error: true }; } },
  };
  vm.runInNewContext(read("sw.js").toString(), sandbox, { filename: "sw.js" });

  function dispatch(url, method = "GET") {
    let pending;
    sandbox.self.listeners.fetch({
      request: { url, method },
      respondWith(value) {
        pending = value;
      },
    });
    return pending;
  }

  assert.equal(dispatch("http://127.0.0.1:8831/api/diagnostics?token=secret"), undefined);
  assert.equal(dispatch("http://127.0.0.1:8831/api/session", "POST"), undefined);
  assert.deepEqual(puts, []);

  const asset = await dispatch("http://127.0.0.1:8831/assets/index-abc.js");
  assert.equal(asset.ok, true);
  assert.deepEqual(puts, ["/assets/index-abc.js"]);

  const offline = await dispatch("http://127.0.0.1:8831/?surface=device&offline=1");
  assert.equal(offline.body, "shell");
  assert.equal(puts.includes("/"), false);
  assert.equal(puts.some((path) => path.startsWith("/api")), false);

  let installed;
  sandbox.self.listeners.install({
    waitUntil(value) {
      installed = value;
    },
  });
  await installed;
  assert.equal(added.includes("/api"), false);
  assert.equal(added.some((path) => String(path).startsWith("/api")), false);
  assert.ok(added.includes("/index.html"));

  let activated;
  sandbox.self.listeners.activate({
    waitUntil(value) {
      activated = value;
    },
  });
  await activated;
  assert.deepEqual(deleted, ["desk-shell-old"]);
});
