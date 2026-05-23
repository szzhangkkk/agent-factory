import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/providers': 'http://localhost:8000',
      '/config': 'http://localhost:8000',
      '/test-connection': 'http://localhost:8000',
      '/agents': 'http://localhost:8000',
      '/documents': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
