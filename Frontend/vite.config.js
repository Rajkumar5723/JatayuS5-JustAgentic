import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (value) => value.replace(/^\/api/, ""),
      },
      "/test-api": {
        target: "http://127.0.0.1:8002",
        changeOrigin: true,
        rewrite: (value) => value.replace(/^\/test-api/, ""),
      },
      "/coding-api": {
        target: "http://127.0.0.1:8003",
        changeOrigin: true,
        rewrite: (value) => value.replace(/^\/coding-api/, ""),
      },
      "/livehr-api": {
        target: "http://127.0.0.1:8004",
        changeOrigin: true,
        ws: true,
        rewrite: (value) => value.replace(/^\/livehr-api/, ""),
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.js",
  },
});
