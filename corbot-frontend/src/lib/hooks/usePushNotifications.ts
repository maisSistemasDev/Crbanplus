import { useEffect, useRef } from 'react';
import { api } from '../api/client';
import { ENDPOINTS } from '../api/endpoints';

/**
 * Hook que solicita permissão de notificação e registra a Web Push subscription
 * no backend. Deve ser montado uma vez no layout principal após autenticação.
 *
 * Requer:
 *   - VITE_VAPID_PUBLIC_KEY na env do frontend
 *   - Service worker registrado pelo vite-plugin-pwa
 */
export function usePushNotifications() {
  const subscribed = useRef(false);

  useEffect(() => {
    if (subscribed.current) return;
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    const vapidPublicKey = import.meta.env.PUBLIC_VAPID_PUBLIC_KEY as string | undefined;
    if (!vapidPublicKey) return;

    async function subscribe() {
      try {
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') return;

        const registration = await navigator.serviceWorker.ready;
        let sub = await registration.pushManager.getSubscription();

        if (!sub) {
          sub = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapidPublicKey!),
          });
        }

        const json = sub.toJSON();
        await api.post(ENDPOINTS.PUSH_SUBSCRIBE, {
          endpoint: sub.endpoint,
          p256dh: (json.keys as Record<string, string>).p256dh,
          auth: (json.keys as Record<string, string>).auth,
        });

        subscribed.current = true;
      } catch (err) {
        // Push é best-effort — falhas não afetam o app
        console.debug('[push] subscription failed:', err);
      }
    }

    subscribe();
  }, []);
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}
