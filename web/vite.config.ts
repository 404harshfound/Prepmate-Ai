import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    sourcemap: false, // don't ship readable source to every visitor
  },
  test: {
    environment: "node",
  },
});
