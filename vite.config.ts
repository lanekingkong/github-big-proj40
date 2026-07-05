import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { readFileSync } from 'fs';

const packageJson = JSON.parse(
  readFileSync(resolve(__dirname, 'package.json'), 'utf-8')
);

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const isDev = mode === 'development';

  return {
    plugins: [react()],

    // Resolve aliases matching tsconfig paths
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
        '@main': resolve(__dirname, 'src/main'),
        '@renderer': resolve(__dirname, 'src/renderer'),
        '@shared': resolve(__dirname, 'src/shared'),
        '@components': resolve(__dirname, 'src/renderer/components'),
        '@pages': resolve(__dirname, 'src/renderer/pages'),
        '@stores': resolve(__dirname, 'src/renderer/stores'),
        '@hooks': resolve(__dirname, 'src/renderer/hooks'),
        '@styles': resolve(__dirname, 'src/renderer/styles'),
        '@assets': resolve(__dirname, 'src/renderer/assets'),
      },
    },

    // Root directory for the Vite dev server
    root: resolve(__dirname, 'src/renderer'),

    // Base public path
    base: isDev ? '/' : './',

    // Build configuration
    build: {
      outDir: resolve(__dirname, 'dist/renderer'),
      emptyOutDir: true,
      sourcemap: isDev,
      minify: !isDev,
      target: 'es2022',

      rollupOptions: {
        input: {
          main: resolve(__dirname, 'src/renderer/index.html'),
        },
        output: {
          manualChunks: {
            react: ['react', 'react-dom'],
            reactflow: ['reactflow'],
            zustand: ['zustand'],
          },
        },
      },

      // Chunk size warning limit (KB)
      chunkSizeWarningLimit: 1000,
    },

    // Dev server configuration for Electron
    server: {
      port: 5173,
      strictPort: true,
      host: '127.0.0.1',
      cors: true,
    },

    // Environment variables prefix
    envPrefix: 'AGENTFORGE_',

    // Define global constants
    define: {
      __APP_VERSION__: JSON.stringify(packageJson.version),
      __APP_NAME__: JSON.stringify(packageJson.name),
      __DEV__: JSON.stringify(isDev),
    },
  };
});
