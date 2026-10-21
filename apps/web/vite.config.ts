import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8007" } },
  // Rollup's recursive analysis exhausted this 4 GiB demo host. Direct icon
  // imports keep the bundle small; esbuild still minifies the production output.
  build: { rollupOptions: { treeshake: false } },
});
