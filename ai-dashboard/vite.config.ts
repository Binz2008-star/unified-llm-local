import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig(({ mode }) => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: true,
      port: 3000,
      strictPort: true,
    },
    preview: {
      host: true,
      port: 4173,
      strictPort: true,
    },
    css: {
      postcss: 'tailwind',
    },
    optimizeDeps: {
      include: [
        'lucide-react',
        'react',
        'react-dom',
        'recharts',
        'motion',
      ],
    },
    esbuild: {
      keepNames: true,
    },
    ssr: {
      noExternal: [
        '@google/genai',
        'express',
        'react',
        'react-dom',
      ],
    },
  };
});