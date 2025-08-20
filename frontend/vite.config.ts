import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import fs from 'fs';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      allowedHosts: true,
      https: {
        key: fs.readFileSync('./key.pem'),
        cert: fs.readFileSync('./cert.pem'),
      },
      proxy: {
        '/api/v1.0': {
          target: env.VITE_USER_SERVICE,
          changeOrigin: true,
          secure: false,
        },
      
        '/api/v2.0': {
          target: env.VITE_KUBECONFIG_SERVICE,
          changeOrigin: true,
          secure: false,
        },
        '/api/v3.0': {
          target: env.VITE_CHAT_SERVICE,
          changeOrigin: true,
          secure: false,
        },
        '/api/v4.0': {
          target: env.VITE_REMEDIATION_SERVICE,
          changeOrigin: true,
          secure: false,
        },
        '/api/v5.0': {
          target: env.VITE_SECURITY_SERVICE,
          changeOrigin: true,
          secure: false,
        },
        // Add proxy for Grafana if needed
        '/grafana': {
          target: 'https://10.0.2.13:3000',
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/grafana/, ''),
        }
      }
    },
  };
});

