import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Porta e proxy próprios do Portal (v6.18.0) — irmão de frontend/, nunca
// compartilha origem/porta com o painel do analista. Ver CORS em
// backend/app/core/config.py (BACKEND_CORS_ORIGINS).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
