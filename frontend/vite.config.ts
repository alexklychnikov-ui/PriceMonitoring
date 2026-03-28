import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const repoRoot = path.resolve(__dirname, "..");
  const env = loadEnv(mode, repoRoot, "");
  const subscriptionWebKey = (env.SUBSCRIPTION_WEB_KEY || env.VITE_SUBSCRIPTION_WEB_KEY || "").trim();

  return {
    plugins: [react()],
    define: {
      "import.meta.env.VITE_SUBSCRIPTION_WEB_KEY": JSON.stringify(subscriptionWebKey),
    },
    resolve: {
      extensions: [".tsx", ".ts", ".jsx", ".js", ".mjs", ".json"],
    },
    server: {
      port: 5173,
      proxy: {
        "/api": "http://localhost:8000",
      },
    },
  };
});
