import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Escucha en todas las interfaces (0.0.0.0) para entrar desde el móvil en la misma WiFi: http://IP-DE-TU-PC:5173
    host: true,
    port: 5173,
    // localhost, ngrok y cualquier IP LAN (192.168.x.x) sin listar cada una
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
