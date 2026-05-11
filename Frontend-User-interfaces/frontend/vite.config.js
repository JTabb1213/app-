import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Generate unique filenames with content hashes for cache busting
    rollupOptions: {
      output: {
        // Add content hash to all JS chunks
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
    // Add build timestamp to force cache invalidation
    define: {
      __BUILD_TIME__: JSON.stringify(new Date().getTime()),
    },
  },
  // Add version headers for development
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
    __BUILD_TIME__: JSON.stringify(new Date().getTime()),
  },
})
