import { api } from '@/utils/api';

/** Mirrors backend `GiverSummary` (backend/app/routers/listings.py). */
export type GiverSummary = {
  display_name: string | null;
  avatar_url: string | null;
  bio?: string | null;
  trust_score: number;
  trust_level: string;
  eco_level?: string | null;
  eco_score: number;
  created_at: string;
  completed_giveaways: number;
  completed_pickups: number;
  neighborhood: string | null;
  last_active_at?: string | null;
};

/** Mirrors backend `ListingResponse` (backend/app/routers/listings.py). */
export type ListingResponse = {
  id: string;
  giver_id: string;
  title: string;
  description: string;
  category: string;
  photo_urls: string[];
  status: string;
  /**
   * Approximate-until-revealed. The backend returns approximate coordinates here
   * unless the requester is the giver or holds a claim in a reveal status, in
   * which case true coordinates are returned. The client cannot distinguish which.
   */
  location_lat: number;
  location_lng: number;
  neighborhood: string | null;
  expires_at: string;
  created_at: string;
  ai_generated: boolean;
  under_review: boolean;
  auto_relist: boolean;
  giver: GiverSummary | null;
  completed_at: string | null;
  /** IANA zone name (e.g. "America/Los_Angeles"). Only populated on the single-listing GET. */
  timezone?: string | null;
  /** Literal count of saved rows. Single-listing GET only; null for the giver. */
  saved_count?: number | null;
};

export type NearbyListingItem = {
  id: string;
  title: string;
  photo_url: string | null;
  category: string;
  giver_id: string;
  /** Always approximate. The nearby query aliases the approx columns to these names. */
  location_lat: number;
  location_lng: number;
  distance_m: number;
  neighborhood: string | null;
  created_at: string;
  expires_at: string;
  deadline_kind?: string;
  /** Optional so a feed from an older backend still parses. */
  auto_relist?: boolean;
};

/** Listings expiring within this window show the "AVAILABLE NOW" badge. */
export const EXPIRING_SOON_MS = 24 * 60 * 60 * 1000;

export function isExpiringSoon(expiresAt: string | undefined): boolean {
  if (!expiresAt) return false;
  const remaining = new Date(expiresAt).getTime() - Date.now();
  return remaining > 0 && remaining <= EXPIRING_SOON_MS;
}

export type NearbyListingsResponse = {
  items: NearbyListingItem[];
  next_cursor: string | null;
};

export type FetchNearbyParams = {
  lat: number;
  lng: number;
  radius_km?: number;
  limit?: number;
  cursor?: string;
  category?: string;
  q?: string;
  state?: string;
};

export async function fetchNearbyListings(
  params: FetchNearbyParams,
): Promise<NearbyListingsResponse> {
  const { lat, lng, radius_km = 2, limit = 20, cursor, category, q, state } = params;
  const res = await api.get<NearbyListingsResponse>('/listings/nearby', {
    params: {
      lat,
      lng,
      radius_km,
      limit,
      ...(cursor ? { cursor } : {}),
      ...(category ? { category } : {}),
      ...(q ? { q } : {}),
      ...(state ? { state } : {}),
    },
  });
  return res.data;
}

export async function getListing(id: string): Promise<ListingResponse> {
  const res = await api.get<ListingResponse>(`/listings/${id}`);
  return res.data;
}

export async function getListingsByUser(userId: string): Promise<ListingResponse[]> {
  const res = await api.get<ListingResponse[]>(`/listings/by-user/${userId}`);
  return res.data;
}

/** Takes a listing off Zelbi. Owner only, active listings only; the server refuses
 *  anything else with 409. Deletes the listing's photos as a side effect. */
export async function removeListing(listingId: string): Promise<void> {
  await api.delete(`/listings/${listingId}`);
}
