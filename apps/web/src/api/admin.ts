/* ============================================================
   Network Intel — admin review-console API client.
   Password-gated (X-Admin-Token). The token IS the password
   (kept in sessionStorage). Talks to /api/admin/*.
   ============================================================ */
import type { Report } from '../types';
import { API_BASE } from './client';

const TOKEN_KEY = 'nintel_admin_token';

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null): void {
  if (t) sessionStorage.setItem(TOKEN_KEY, t);
  else sessionStorage.removeItem(TOKEN_KEY);
}

export interface PendingEntry {
  id: string;
  type: 'daily' | 'weekly';
  date: string;
  title: string | null;
  excerpt: string;
  item_count: number;
}

/** Raised on 401 so the UI can drop back to the login screen. */
export class AdminAuthError extends Error {}

async function adminFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}/admin${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Token': getToken() ?? '',
      ...(opts.headers ?? {}),
    },
  });
  if (res.status === 401) {
    setToken(null);
    throw new AdminAuthError('unauthorized');
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

/** Validate the password and store it as the token. */
export async function login(password: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  if (res.ok) {
    setToken(password);
    return true;
  }
  return false;
}

export const listPending = (): Promise<PendingEntry[]> =>
  adminFetch<{ pending: PendingEntry[] }>('/pending').then((r) => r.pending);

export const getPending = (id: string): Promise<Report> =>
  adminFetch<Report>(`/pending/${encodeURIComponent(id)}`);

/** Save edits → server re-finalizes (sections/cites) + returns the clean doc. */
export const savePending = (id: string, doc: Report): Promise<Report> =>
  adminFetch<Report>(`/pending/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(doc),
  });

/** LLM revise by instruction → returns a finalized PREVIEW (not yet saved). */
export const llmEdit = (id: string, instruction: string): Promise<Report> =>
  adminFetch<Report>(`/pending/${encodeURIComponent(id)}/llm-edit`, {
    method: 'POST',
    body: JSON.stringify({ instruction }),
  });

export const publishPending = (id: string): Promise<{ ok: boolean }> =>
  adminFetch<{ ok: boolean }>(`/pending/${encodeURIComponent(id)}/publish`, {
    method: 'POST',
  });

export const rejectPending = (id: string): Promise<{ ok: boolean }> =>
  adminFetch<{ ok: boolean }>(`/pending/${encodeURIComponent(id)}/reject`, {
    method: 'POST',
  });
