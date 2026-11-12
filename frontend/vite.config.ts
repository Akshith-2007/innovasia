/// <reference types="vitest/config" />
import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv, type Plugin } from "vite";

const ROUTES = ["/", "/about", "/technology", "/market-intelligence", "/research", "/contact"];

/** Emits sitemap.xml at build time from VITE_SITE_URL (skipped with a warning if unset). */
function sitemap(siteUrl: string | undefined): Plugin {
  return {
    name: "kcl-sitemap",
    apply: "build",
    generateBundle() {
      if (!siteUrl) {
        this.warn("VITE_SITE_URL not set; sitemap.xml not generated.");
        return;
      }
      const base = siteUrl.replace(/\/$/, "");
      const urls = ROUTES.map((r) => `  <url><loc>${base}${r}</loc></url>`).join("\n");
      this.emitFile({
        type: "asset",
        fileName: "sitemap.xml",
        source: `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  return {
    plugins: [react(), tailwindcss(), sitemap(env.VITE_SITE_URL)],
    resolve: { alias: { "@": path.resolve(__dirname, "src") } },
    server: { host: "127.0.0.1", port: 5173, strictPort: true },
    // Pre-bundle deps used by lazy routes so Vite never reloads the page mid-session discovering them.
    optimizeDeps: {
      include: ["recharts", "motion/react", "lucide-react", "@tanstack/react-query", "react-router-dom", "clsx", "tailwind-merge", "class-variance-authority", "@radix-ui/react-slot"],
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            react: ["react", "react-dom", "react-router-dom"],
            motion: ["motion"],
            data: ["@tanstack/react-query"],
          },
        },
      },
    },
    test: {
      globals: true,
      include: ["src/**/*.test.{ts,tsx}"],
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      css: false,
    },
  };
});
