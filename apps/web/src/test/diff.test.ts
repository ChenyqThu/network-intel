import { describe, expect, it } from 'vitest';
import { diffReport, diffWords } from '../pages/admin/diff';
import type { Report } from '../types';

describe('diffWords', () => {
  it('returns a single same-segment for identical text', () => {
    expect(diffWords('同一段文字', '同一段文字')).toEqual([
      { kind: 'same', text: '同一段文字' },
    ]);
  });

  it('marks CJK edits at character granularity', () => {
    const segs = diffWords('导语很平淡', '导语很犀利');
    expect(segs.map((s) => s.kind)).toEqual(['same', 'del', 'add']);
    expect(segs[1]).toEqual({ kind: 'del', text: '平淡' });
    expect(segs[2]).toEqual({ kind: 'add', text: '犀利' });
  });

  it('keeps latin words whole and round-trips both sides', () => {
    const segs = diffWords('UniFi launched a router', 'UniFi shipped a router');
    const del = segs.filter((s) => s.kind === 'del').map((s) => s.text).join('');
    const add = segs.filter((s) => s.kind === 'add').map((s) => s.text).join('');
    expect(del).toBe('launched');
    expect(add).toBe('shipped');
    // reconstruct: same+del = a, same+add = b
    const a = segs.filter((s) => s.kind !== 'add').map((s) => s.text).join('');
    const b = segs.filter((s) => s.kind !== 'del').map((s) => s.text).join('');
    expect(a).toBe('UniFi launched a router');
    expect(b).toBe('UniFi shipped a router');
  });

  it('handles empty sides', () => {
    expect(diffWords('', '新增')).toEqual([{ kind: 'add', text: '新增' }]);
    expect(diffWords('删除', '')).toEqual([{ kind: 'del', text: '删除' }]);
    expect(diffWords('', '')).toEqual([]);
  });
});

const baseReport = (over: Partial<Report> = {}): Report =>
  ({
    report_id: 'r',
    type: 'daily',
    date: '2026-06-09',
    date_range: '2026-06-09',
    generated_at: '2026-06-09T08:00:00+08:00',
    lead: { text: '导语', strong: '结论', cite_refs: [] },
    sections: [],
    items: [
      {
        id: 'd1', cite_id: 1, subject: 'competitor', source: 'reddit',
        source_domain: 'reddit.com', source_tier: 'community', title: '条目一',
        summary: '摘要一', category: 'sentiment', omada_impact: 'threat',
        date: '2026-06-09', url: 'https://x/1',
      },
    ],
    references: [],
    stats: { total_items: 1 },
    ...over,
  }) as unknown as Report;

describe('diffReport', () => {
  it('reports no changes for identical docs', () => {
    expect(diffReport(baseReport(), baseReport())).toEqual([]);
  });

  it('detects lead and item-field edits', () => {
    const b = baseReport();
    b.lead = { ...b.lead, text: '新导语' };
    b.items = [{ ...b.items[0], summary: '新摘要' }];
    const changes = diffReport(baseReport(), b);
    const labels = changes.map((c) => c.label);
    expect(labels).toContain('导语');
    expect(labels.some((l) => l.includes('摘要'))).toBe(true);
  });

  it('detects added and removed items', () => {
    const b = baseReport();
    b.items = [
      { ...b.items[0], id: 'd2', title: '条目二', url: 'https://x/2' },
    ];
    const changes = diffReport(baseReport(), b);
    expect(changes.some((c) => c.kind === 'removed' && c.label.includes('条目一'))).toBe(true);
    expect(changes.some((c) => c.kind === 'added' && c.label.includes('条目二'))).toBe(true);
  });

  it('detects insight edits by id', () => {
    const mk = (body: string) =>
      baseReport({
        insights: [
          { id: 'i1', subject: 'competitor', title: '洞察A', body, cite_refs: [1] },
        ],
      } as Partial<Report>);
    const changes = diffReport(mk('旧正文'), mk('新正文'));
    expect(changes).toHaveLength(1);
    expect(changes[0].label).toContain('洞察「洞察A」正文');
  });
});
