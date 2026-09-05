import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Preserve Vite 7's browser baseline when upgrading the build toolchain.
  build: {
    target: ["chrome107", "edge107", "firefox104", "safari16"],
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  preview: {
    port: 4173,
    strictPort: true,
  },
});
