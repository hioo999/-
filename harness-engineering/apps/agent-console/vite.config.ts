import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 900
  },
  server: {
    port: 3000,
    proxy: {
      '/api/agent': 'http://127.0.0.1:8200',
      '/health': 'http://127.0.0.1:8200'
    }
  }
});
