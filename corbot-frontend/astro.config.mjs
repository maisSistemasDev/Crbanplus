// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import node from '@astrojs/node';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  output: 'server',
  integrations: [react()],
  vite: {
    plugins: [
      tailwindcss(),
      VitePWA({
        registerType: 'autoUpdate',
        injectRegister: 'script',
        strategies: 'generateSW',
        workbox: {
          navigateFallback: null,
          globPatterns: ['**/*.{ico,png,svg,webp}'],
          runtimeCaching: [
            {
              urlPattern: /^\/api\/.*/i,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'api-cache',
                expiration: { maxEntries: 50, maxAgeSeconds: 60 * 5 },
              },
            },
          ],
        },
        manifest: {
          name: 'CorbanPlus',
          short_name: 'CorbanPlus',
          description: 'Sistema de Gestão de Comissões',
          theme_color: '#2c3e50',
          background_color: '#f3f4f6',
          display: 'standalone',
          orientation: 'portrait',
          start_url: '/dashboard',
          scope: '/',
          icons: [
            { src: '/icons/icon-72.png', sizes: '72x72', type: 'image/png' },
            { src: '/icons/icon-96.png', sizes: '96x96', type: 'image/png' },
            { src: '/icons/icon-128.png', sizes: '128x128', type: 'image/png' },
            { src: '/icons/icon-144.png', sizes: '144x144', type: 'image/png' },
            { src: '/icons/icon-152.png', sizes: '152x152', type: 'image/png' },
            { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any maskable' },
            { src: '/icons/icon-384.png', sizes: '384x384', type: 'image/png' },
            { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
          ],
          shortcuts: [
            { name: 'Comissões', url: '/commissions', icons: [{ src: '/icons/icon-96.png', sizes: '96x96' }] },
            { name: 'Saques', url: '/withdrawals/corbanpay', icons: [{ src: '/icons/icon-96.png', sizes: '96x96' }] },
          ],
        },
      }),
    ],
  },
  adapter: node({ mode: 'standalone' }),
  server: { port: 3000 },
});