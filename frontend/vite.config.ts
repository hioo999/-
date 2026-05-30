import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

declare const process: { env: Record<string, string | undefined> }

const backendTarget = process.env.VITE_DEV_API_PROXY || 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': backendTarget,
    },
  },
})
