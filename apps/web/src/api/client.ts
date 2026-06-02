/* ============================================================
   Network Intel — typed API client
   Base URL from VITE_API_BASE (default "/api"); Vite dev proxies
   /api -> http://localhost:8000. Every call falls back to the
   bundled contract fixtures when the network/API is unavailable,
   so the UI is fully demonstrable standalone.
   ============================================================ */
import type { Report, ArchiveEntry, IntelItem } from '../types';

import dailyFixture from '../fixtures/2026-06-01-daily.json';
import weeklyFixture from '../fixtures/2026-W22-weekly.json';
import archiveFixture from '../fixtures/archive.json';

const DAILY = dailyFixture as unknown as Report;
const WEEKLY = weeklyFixture as unknown as Report;
const ARCHIVE = (archiveFixture as { reports: ArchiveEntry[] }).reports;

/** Reports available from fixtures, keyed by report_id. */
const FIXTURE_REPORTS: Record<string, Report> = {
  [DAILY.report_id]: DAILY,
  [WEEKLY.report_id]: WEEKLY,
};

export const API_BASE: string =
  (import.meta.env?.VITE_API_BASE as string | undefined) ?? '/api';

let warnedOffline = false;
function noteOffline(what: string, err: unknown): void {
  if (!warnedOffline) {
    // One concise note; subsequent fallbacks stay quiet.
    console.info(
      '[nintel] API unavailable — serving bundled contract fixtures (offline mode).',
    );
    warnedOffline = true;
  }
  console.debug(`[nintel] fixture fallback for ${what}:`, err);
}

/** True when the most recent fetch fell back to fixtures. */
export let usingFixtures = false;

async function getJson<T>(path: string): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return (await res.json()) as T;
}

/* ---------- fixture-derived helpers ---------- */

/** The latest report of a given cadence (from fixtures). */
function latestFixtureByType(type: 'daily' | 'weekly'): Report {
  return type === 'weekly' ? WEEKLY : DAILY;
}

/* ---------- public API ---------- */

/** GET /api/reports/{id} — a single report by id. */
export async function fetchReport(id: string): Promise<Report> {
  try {
    const r = await getJson<Report>(`/reports/${encodeURIComponent(id)}`);
    usingFixtures = false;
    return r;
  } catch (err) {
    noteOffline(`report ${id}`, err);
    usingFixtures = true;
    const fx = FIXTURE_REPORTS[id];
    if (fx) return fx;
    // Unknown id offline: fall back to the latest daily so the UI still renders.
    return DAILY;
  }
}

/** GET /api/reports/latest?type= — latest report of a cadence. */
export async function fetchLatestReport(
  type: 'daily' | 'weekly',
): Promise<Report> {
  try {
    const r = await getJson<Report>(`/reports/latest?type=${type}`);
    usingFixtures = false;
    return r;
  } catch (err) {
    noteOffline(`latest ${type}`, err);
    usingFixtures = true;
    return latestFixtureByType(type);
  }
}

/** GET /api/archive — the report index for the Archive page. */
export async function fetchArchive(): Promise<ArchiveEntry[]> {
  try {
    const r = await getJson<{ reports: ArchiveEntry[] } | ArchiveEntry[]>(
      `/archive`,
    );
    usingFixtures = false;
    return Array.isArray(r) ? r : r.reports;
  } catch (err) {
    noteOffline('archive', err);
    usingFixtures = true;
    return ARCHIVE;
  }
}

/** GET /api/items — flat stream of all intel items across reports. */
export async function fetchAllItems(): Promise<IntelItem[]> {
  try {
    const r = await getJson<{ items: IntelItem[] } | IntelItem[]>(`/items`);
    usingFixtures = false;
    return Array.isArray(r) ? r : r.items;
  } catch (err) {
    noteOffline('items', err);
    usingFixtures = true;
    // Merge items from both seed reports, dedupe by id (latest wins).
    const map = new Map<string, IntelItem>();
    for (const it of [...DAILY.items, ...WEEKLY.items]) map.set(it.id, it);
    return [...map.values()];
  }
}

/** The email endpoint URL for a report (opened in a new tab). */
export function emailUrl(id: string): string {
  return `${API_BASE}/reports/${encodeURIComponent(id)}/email`;
}

export { DAILY as fixtureDaily, WEEKLY as fixtureWeekly, ARCHIVE as fixtureArchive };
