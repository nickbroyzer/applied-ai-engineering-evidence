import { api } from '@/utils/api';

/** Mirrors backend `MessageRead` (backend/app/schemas/messages.py). */
export type MessageRead = {
  id: string;
  listing_id: string;
  sender_id: string;
  recipient_id: string;
  content: string;
  image_url: string | null;
  created_at: string;
  read_at: string | null;
  edited_at: string | null;
  deleted_at: string | null;
  deflect_category: string | null;
};

/** Mirrors backend `ThreadResponse` (backend/app/schemas/messages.py). */
export type ThreadResponse = {
  messages: MessageRead[];
  next_cursor: string | null;
  other_user_id: string | null;
  other_user_name: string | null;
  other_user_avatar_url: string | null;
  other_user_last_active_at: string | null;
};

export async function fetchThread(
  listingId: string,
  opts?: { after?: string; limit?: number; newest?: boolean },
): Promise<ThreadResponse> {
  const params: Record<string, string | number | boolean> = {};
  if (opts?.after) params.after = opts.after;
  if (opts?.limit) params.limit = opts.limit;
  if (opts?.newest) params.newest = true;
  const res = await api.get<ThreadResponse>(`/messages/${listingId}`, {
    params: Object.keys(params).length ? params : undefined,
  });
  return res.data;
}

/** POST `/messages/{listing_id}` — backend `MessageCreate`. */
export async function sendMessage(listingId: string, content: string, imageUrl?: string | null): Promise<MessageRead> {
  const res = await api.post<MessageRead>(`/messages/${listingId}`, { content, image_url: imageUrl ?? null });
  return res.data;
}

export async function markRead(messageId: string): Promise<MessageRead> {
  const res = await api.put<MessageRead>(`/messages/${messageId}/read`);
  return res.data;
}

export async function editMessage(messageId: string, content: string): Promise<MessageRead> {
  const res = await api.patch<MessageRead>(`/messages/${messageId}`, { content });
  return res.data;
}

export async function deleteMessage(messageId: string): Promise<MessageRead> {
  const res = await api.delete<MessageRead>(`/messages/${messageId}`);
  return res.data;
}
