import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies API calls to the FastAPI backend on :8000, so there's
// no CORS to configure — fetch("/loans") from React just works.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/loans": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
