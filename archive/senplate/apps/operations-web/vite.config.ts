import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(({ mode }) => {
  const qa = mode === "meals-qa";
  const api = `http://127.0.0.1:${qa ? 8800 : 8799}`;
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: qa ? 5178 : 5177,
      strictPort: true,
      proxy: {
        "/v1": { target: api, ws: true },
        "/health": api,
      },
    },
  };
});
