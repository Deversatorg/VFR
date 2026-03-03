import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    // Aspire injects the PORT environment variable.
    // Vite needs to listen on this port for Aspire to proxy it.
    port: process.env.PORT ? parseInt(process.env.PORT) : 5173,
    strictPort: true,
    host: true, // Listen on all local IPs
  }
})
