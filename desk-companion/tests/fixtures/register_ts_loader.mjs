import { register } from "node:module";

register(new URL("./ts_resolve_loader.mjs", import.meta.url), {
  parentURL: import.meta.url,
});
