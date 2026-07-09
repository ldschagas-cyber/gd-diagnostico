import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// O proxy encaminha as chamadas /api para o backend FastAPI em dev,
// evitando problemas de CORS e mantendo o mesmo caminho em produção.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        // Separa bibliotecas grandes em chunks próprios para acelerar o carregamento.
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          mui: ["@mui/material", "@mui/icons-material", "@mui/x-data-grid"],
          charts: ["recharts"],
        },
      },
    },
  },
});
