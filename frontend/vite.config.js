import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: the browser talks to Vite (5173); /api is proxied to FastAPI (8000).
// Prod (Docker): FastAPI serves the built files itself, so /api is same-origin.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
