import { useEffect, useRef } from 'react';

import { routeNotification, type RoutableNotification } from '@/utils/notificationRouting';
import { fetchNotifications } from '@/utils/notifications';

// A tapped push banner must land where the in-app row lands. The push payload carries the
// destination but not the row's title, photo or body, which a notice needs — so the row is
// fetched from the list and handed to the same resolver the list uses.
// expo-notifications is imported lazily, matching utils/pushToken.ts, and every failure is
// swallowed: a routing miss must never stop the app from opening.
async function handleTap(data: Record<string, unknown> | undefined): Promise<void> {
  try {
    if (!data) return;
    const notificationId = typeof data.notification_id === 'string' ? data.notification_id : null;

    if (notificationId) {
      try {
        const list = await fetchNotifications();
        const row = list.find((n) => n.id === notificationId);
        if (row) {
          await routeNotification(row);
          return;
        }
      } catch {
        // fall through to the payload-only path below
      }
    }

    // No row available — route from the payload alone. A notice cannot be rendered this way,
    // so it falls back to the notifications list rather than opening an empty sheet.
    const fallback: RoutableNotification = {
      id: notificationId ?? '',
      notification_type: typeof data.notification_type === 'string' ? data.notification_type : '',
      target_kind: typeof data.target_kind === 'string' ? data.target_kind : null,
      target_id: typeof data.target_id === 'string' ? data.target_id : null,
      listing_id: typeof data.listing_id === 'string' ? data.listing_id : null,
      listing_title: null,
      listing_photo_url: null,
      body: '',
      created_at: '',
    };
    if (fallback.target_kind === 'notice') {
      const { router } = await import('expo-router');
      router.push('/notifications');
      return;
    }
    await routeNotification(fallback);
  } catch {
    // never let a routing failure surface to the user
  }
}

export function usePushTapRouting(): void {
  const coldStartHandled = useRef(false);

  useEffect(() => {
    let subscription: { remove: () => void } | null = null;
    let cancelled = false;

    void (async () => {
      try {
        const Notifications = await import('expo-notifications');

        // Cold launch: the tap happened before this listener existed, so it is asked for.
        if (!coldStartHandled.current) {
          coldStartHandled.current = true;
          const last = await Notifications.getLastNotificationResponseAsync();
          if (last && !cancelled) {
            await handleTap(last.notification.request.content.data as Record<string, unknown>);
          }
        }

        if (cancelled) return;

        // Warm path: app already running, backgrounded or foregrounded.
        subscription = Notifications.addNotificationResponseReceivedListener((response) => {
          void handleTap(response.notification.request.content.data as Record<string, unknown>);
        });
      } catch {
        // expo-notifications unavailable — no routing, app unaffected
      }
    })();

    return () => {
      cancelled = true;
      subscription?.remove();
    };
  }, []);
}
