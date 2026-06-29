import { auth } from "./firebase";
import { API_URL } from "./config";

async function authHeaders(): Promise<HeadersInit> {
  const token = await auth.currentUser?.getIdToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface ChatMessageRow {
  id: string;
  content: string;
  is_bot: boolean;
  created_at: string;
}

/** Load persisted chat history (paginated; see GET /chat/ limit/offset). */
export async function fetchHistory(limit = 50, offset = 0): Promise<ChatMessageRow[]> {
  const res = await fetch(`${API_URL}/chat/?limit=${limit}&offset=${offset}`, {
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to load history: ${res.status}`);
  return res.json();
}

/** Ensure a User row exists for the signed-in Firebase identity (idempotent). */
export async function ensureUserProfile(email: string): Promise<void> {
  const headers = { ...(await authHeaders()), "Content-Type": "application/json" };
  const me = await fetch(`${API_URL}/users/me`, { headers });
  if (me.ok) return;
  await fetch(`${API_URL}/users/`, {
    method: "POST",
    headers,
    body: JSON.stringify({ email }),
  });
}
