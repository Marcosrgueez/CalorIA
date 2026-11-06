import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/diet':     { target: 'http://localhost:8001', changeOrigin: true },
      '/diets':    { target: 'http://localhost:8001', changeOrigin: true },
      '/products': { target: 'http://localhost:8001', changeOrigin: true },
      '/ml':       { target: 'http://localhost:8001', changeOrigin: true },
      '/health':   { target: 'http://localhost:8001', changeOrigin: true },
      '/scan':     { target: 'http://localhost:8001', changeOrigin: true },
      '/auth':     { target: 'http://localhost:8001', changeOrigin: true },
      '/api':      { target: 'http://localhost:8001', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
  },
})
