import { describe, it, expect } from 'vitest';
import { middleEllipsis } from '../lib/text';

describe('middleEllipsis', () => {
  it('returns the string unchanged when it already fits', () => {
    expect(middleEllipsis('short', 10)).toBe('short');
    expect(middleEllipsis('exactly-10', 10)).toBe('exactly-10');
  });

  it('truncates in the middle, keeping head and tail', () => {
    const out = middleEllipsis('abcdefghijklmnop', 9);
    expect(out.length).toBeLessThanOrEqual(9);
    expect(out).toContain('…');
    expect(out.startsWith('a')).toBe(true);
    expect(out.endsWith('p')).toBe(true);
    // the ellipsis sits between head and tail, never at an edge
    const i = out.indexOf('…');
    expect(i).toBeGreaterThan(0);
    expect(i).toBeLessThan(out.length - 1);
  });

  it('keeps a real report title readable at both ends', () => {
    const title = '第 22 周深度：低端围堵 + 高端降价，价格战全面铺开';
    const out = middleEllipsis(title, 18);
    expect(out.length).toBeLessThanOrEqual(18);
    expect(out.startsWith('第')).toBe(true);
    expect(out.endsWith('铺开')).toBe(true);
  });

  it('degrades gracefully at tiny limits', () => {
    expect(middleEllipsis('anything', 1)).toBe('…');
    expect(middleEllipsis('anything', 0)).toBe('…');
  });
});
