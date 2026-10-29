import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        // Use loopback directly: local DNS/proxy tools may rewrite localhost.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        // Use loopback directly: local DNS/proxy tools may rewrite localhost.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
