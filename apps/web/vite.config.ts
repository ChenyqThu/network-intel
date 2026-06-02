/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Vite blocks unknown Host headers by default (>=5.4.12, DNS-rebinding
    // protection). Allow the Cloudflare tunnel domain. Use '.omada.ink' to
    // permit all *.omada.ink subdomains instead of listing each one.
    allowedHosts: ['daily.omada.ink'],
    proxy: {
      // Dev proxy: forward API calls to the FastAPI backend.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
