import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import fs from 'fs';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      allowedHosts: true,
      https: {
        key: fs.readFileSync('./key.pem'),
        cert: fs.readFileSync('./cert.pem'),
      },
      proxy: {
        '/auth': {
          target: env.VITE_USER_SERVICE_URL,
          changeOrigin: true,
          secure: false,
        },
        '/api': {
        target: 'https://10.0.32.108:8005',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        secure: false // If using self-signed certificates
      },
        '/kubeconfig': {
          target: env.VITE_KUBECONFIG_SERVICE_URL,
          changeOrigin: true,
          secure: false,
        },
        '/chat': {
          target: env.VITE_CHAT_SERVICE_URL,
          changeOrigin: true,
          secure: false,
        },
        // Add proxy for Grafana if needed
        '/grafana': {
          target: 'https://10.0.32.103:3000',
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/grafana/, ''),
        }
      }
    },
  };
});
