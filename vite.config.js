import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server runs on port 5173. The Flask backend allows this origin via CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
  },
});
