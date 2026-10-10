import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-v${Date.now()}.js`,
        chunkFileNames: `assets/[name]-v${Date.now()}.js`,
        assetFileNames: `assets/[name]-v${Date.now()}.[ext]`,
      },
    },
  },
  server: {
    port: 5173,
    host: true,
  },
});
