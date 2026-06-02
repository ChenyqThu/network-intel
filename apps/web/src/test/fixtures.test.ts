import { describe, it, expect } from 'vitest';
import daily from '../fixtures/2026-06-01-daily.json';
import weekly from '../fixtures/2026-W22-weekly.json';
import archiveJson from '../fixtures/archive.json';
import type { Report, Archive } from '../types';
import { citeNumbers } from '../lib/intel';

const reports: Report[] = [
  daily as unknown as Report,
  weekly as unknown as Report,
];

describe('fixture reports validate shape', () => {
  it.each(reports)('$report_id has required top-level fields', (rep) => {
    expect(rep.report_id).toBeTruthy();
    expect(['daily', 'weekly']).toContain(rep.type);
    expect(rep.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(rep.date_range).toBeTruthy();
    expect(rep.generated_at).toBeTruthy();
    expect(rep.lead?.text).toBeTruthy();
    expect(Array.isArray(rep.sections)).toBe(true);
    expect(Array.isArray(rep.items)).toBe(true);
    expect(Array.isArray(rep.references)).toBe(true);
    expect(rep.stats).toBeTruthy();
  });

  it.each(reports)('$report_id items carry traceability fields', (rep) => {
    for (const it of rep.items) {
      expect(it.id).toBeTruthy();
      expect(typeof it.cite_id).toBe('number');
      expect(['omada_self', 'competitor', 'industry']).toContain(it.subject);
      expect(['official', 'community']).toContain(it.source_tier);
      expect(it.source_domain).toBeTruthy();
      expect(it.url).toMatch(/^https?:\/\//);
      expect(it.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect([
        'threat',
        'opportunity',
        'neutral',
        'needs_fix',
        'feature_input',
        'strength_confirm',
        'unknown',
      ]).toContain(it.omada_impact);
    }
  });

  it.each(reports)('$report_id section item-refs resolve to items', (rep) => {
    const ids = new Set(rep.items.map((i) => i.id));
    for (const sec of rep.sections) {
      for (const ref of sec.items) expect(ids.has(ref)).toBe(true);
    }
  });

  it.each(reports)('$report_id lead cites resolve to references', (rep) => {
    const refIds = new Set(rep.references.map((r) => r.cite_id));
    for (const n of citeNumbers(rep.lead.text)) {
      expect(refIds.has(n)).toBe(true);
    }
  });

  it('daily has no strategy; weekly has a strategy block with cites', () => {
    const d = daily as unknown as Report;
    const w = weekly as unknown as Report;
    expect(d.strategy ?? null).toBeNull();
    expect(w.strategy).toBeTruthy();
    expect(w.strategy!.cite_refs.length).toBeGreaterThan(0);
    // weekly carries the omada_self section + own-product impacts
    expect(w.items.some((i) => i.omada_impact === 'needs_fix')).toBe(true);
    expect(w.sections.some((s) => s.key === 'omada_self')).toBe(true);
  });

  it('archive index has entries with required fields', () => {
    const arch = archiveJson as unknown as Archive;
    expect(arch.reports.length).toBeGreaterThan(0);
    for (const a of arch.reports) {
      expect(a.id).toBeTruthy();
      expect(['daily', 'weekly']).toContain(a.type);
      expect(Array.isArray(a.themes)).toBe(true);
    }
  });
});
