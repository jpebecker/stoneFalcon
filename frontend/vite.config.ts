import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// O front chama /api; em desenvolvimento o Vite repassa para o backend FastAPI.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.STONEFALCON_API ?? "http://127.0.0.1:8765",
      "/demo": process.env.STONEFALCON_API ?? "http://127.0.0.1:8765",
      "/avatares": process.env.STONEFALCON_API ?? "http://127.0.0.1:8765",
    },
  },
});
