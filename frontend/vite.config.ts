import react from "@vitejs/plugin-react";
import {defineConfig, loadEnv} from "vite";
import fs from 'fs';

import vitePluginInjectDataLocator from "./plugins/vite-plugin-inject-data-locator";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), vitePluginInjectDataLocator()],
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
    }
  },
});
