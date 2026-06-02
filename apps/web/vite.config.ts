/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite rejects unknown Host headers by default (>=5.4.12, DNS-rebinding
// protection). Permit the Cloudflare tunnel domain on both the dev server and
// the production `vite preview` server. Use '.omada.ink' to allow all subdomains.
const allowedHosts = ['daily.omada.ink'];

// Forward API calls to the FastAPI backend, in both dev and preview.
const proxy = {
  '/api': { target: 'http://localhost:8000', changeOrigin: true },
};

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Dev server (`vite` / make web): on-the-fly transforms + HMR.
  server: { port: 5173, allowedHosts, proxy },
  // Production preview (`vite preview`): serves the optimized dist/ build.
  // SPA history fallback is on by default (appType 'spa'), so BrowserRouter
  // deep links like /archive resolve to index.html.
  preview: { port: 5173, allowedHosts, proxy },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
