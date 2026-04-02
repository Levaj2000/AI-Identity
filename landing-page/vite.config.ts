import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Vendor: React core
          if (id.includes("node_modules/react/") || id.includes("node_modules/react-dom/") || id.includes("node_modules/react-router") || id.includes("node_modules/react-helmet-async")) {
            return "vendor-react";
          }
          // Vendor: Framer Motion
          if (id.includes("node_modules/framer-motion")) {
            return "vendor-framer";
          }
          // Framer design components (large)
          if (id.includes("/framer/")) {
            return "framer-components";
          }
        },
      },
    },
  },
});
