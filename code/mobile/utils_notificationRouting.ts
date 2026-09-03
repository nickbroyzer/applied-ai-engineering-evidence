import { router } from 'expo-router';

import { getClaimByListing } from '@/utils/claims';
import type { NotificationItem } from '@/utils/notifications';

// The shape routeNotification actually needs. NotificationItem satisfies it; a push payload
// can be shimmed into it without the fields only the list carries.
export type RoutableNotification = Pick<
  NotificationItem,
  'id' | 'notification_type' | 'target_kind' | 'target_id' | 'listing_id' | 'listing_title' | 'listing_photo_url' | 'body' | 'created_at'
>;

// The single destination resolver for a notification, shared by the in-app list and the
// OS push-tap listener so the two surfaces can never drift apart.
export async function routeNotification(item: RoutableNotification): Promise<void> {
  const kind = item.target_kind;
  const targetId = item.target_id;
  if (kind === 'notice') {
    // The notice covers the list as its own full-screen presentation; closing it comes
    // straight back, so there is nothing to restore.
    router.push({
      pathname: '/notification/[id]',
      params: {
        id: item.id,
        notification_type: item.notification_type,
        listing_title: item.listing_title ?? '',
        listing_photo_url: item.listing_photo_url ?? '',
        body: item.body,
        created_at: item.created_at,
        listing_id: item.listing_id ?? '',
      },
    });
  } else if (kind === 'claim' && targetId && item.listing_id) {
    // "Giver proposed 3 pickup times" is an action, not a status update — it goes
    // straight to the screen where the picker acts. Every other claim notification
    // opens the hub.
    if (
      item.notification_type === 'pickup_times_proposed' ||
      item.notification_type === 'porch_pickup_set' ||
      item.notification_type === 'pickup_select_reminder_picker'
    ) {
      // Hub first, action screen on top. Both are fullScreenModals: replacing one with
      // the other dismisses downward and flashes the list before the next presents.
      // Stacking means the action screen's own dismissal reveals the hub directly.
      router.push(`/handoff/${targetId}?listingId=${item.listing_id}`);
      setTimeout(() => {
        router.push(`/listing/pickup-time?claim_id=${targetId}&listing_id=${item.listing_id}`);
      }, 0);
    } else {
      router.push(`/handoff/${targetId}?listingId=${item.listing_id}`);
    }
  } else if (kind === 'saved') {
    // A removed listing's own page is a dead end. Saved is where the consequence lives,
    // and the highlight param tells that screen which card to scroll to and pulse once.
    router.dismissAll();
    router.replace(
      `/(app)/saved${targetId ? `?highlight=${targetId}` : ''}` as Parameters<typeof router.replace>[0],
    );
  } else if (kind === 'discover') {
    router.dismissAll();
    router.replace('/(app)/home?sort=newest');
  } else if (kind === 'thread' && targetId) {
    // The hub is the message surface. The row carries only a listing id, so the claim is
    // resolved here; if there is no claim the listing is the only sensible fallback.
    try {
      const c = await getClaimByListing(targetId);
      if (c?.id) {
        router.push(`/handoff/${c.id}?listingId=${targetId}&focusComposer=1`);
        return;
      }
    } catch {
      // fall through to the listing below
    }
    router.push(`/listing/${targetId}`);
    return;
  } else if (kind === 'listing' && targetId) {
    router.push(`/listing/${targetId}`);
  } else if (item.listing_id) {
    router.push(`/listing/${item.listing_id}`);
  }
}
