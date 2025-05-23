import { resolve } from 'node:path';
import { defineConfig, loadEnv } from 'vite';
import { createVitePlugins } from './build/plugins';
import { createViteProxy } from './build/proxy';
import { serviceConfig } from './service.config';
import fs from 'fs'; // Import fs for reading SSL certificates

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load the .env file based on the current mode
  const env = loadEnv(mode, __dirname, '') as ImportMetaEnv;
  const envConfig = serviceConfig[mode as ServiceEnvType];

  return {
    base: env.VITE_BASE_URL,
    plugins: createVitePlugins(env),
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    server: {
      host: '0.0.0.0',
      proxy: env.VITE_HTTP_PROXY === 'Y' ? createViteProxy(envConfig) : undefined,
      https: {
        key: fs.readFileSync('./key.pem'), // Path to your private key file
        cert: fs.readFileSync('./cert.pem'), // Path to your certificate file
      },
    },
    build: {
      target: 'esnext',
      reportCompressedSize: false, // Enable/Disable gzip compressed size reporting
    },
    optimizeDeps: {
      include: ['echarts', 'md-editor-v3', 'quill'],
    },
    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern',
        },
      },
    },
  };
});


