import { describe, it, expect } from 'vitest';
import {
  parseCites,
  citeNumbers,
  impactMeta,
  impactClass,
  impactLabel,
  researchLabel,
  nodeClass,
  isOwnProductImpact,
  sourceGlyph,
  sourceDisplayLabel,
  defaultTierLabel,
  SOURCE_REGISTRY,
  categoryLabel,
} from '../lib/intel';
import type { Impact, Source } from '../types';

describe('cite superscript parser', () => {
  it('splits text and cite tokens in order', () => {
    const toks = parseCites('A{{cite:1}}B{{cite:12}}');
    expect(toks).toEqual([
      { kind: 'text', value: 'A' },
      { kind: 'cite', n: 1 },
      { kind: 'text', value: 'B' },
      { kind: 'cite', n: 12 },
    ]);
  });

  it('handles leading/adjacent cites and plain text', () => {
    expect(parseCites('{{cite:3}}{{cite:4}} tail')).toEqual([
      { kind: 'cite', n: 3 },
      { kind: 'cite', n: 4 },
      { kind: 'text', value: ' tail' },
    ]);
    expect(parseCites('no cites here')).toEqual([
      { kind: 'text', value: 'no cites here' },
    ]);
  });

  it('does not treat malformed placeholders as cites', () => {
    expect(parseCites('{{cite:}} {{cite:x}}')).toEqual([
      { kind: 'text', value: '{{cite:}} {{cite:x}}' },
    ]);
  });

  it('citeNumbers returns distinct numbers in first-appearance order', () => {
    expect(citeNumbers('{{cite:4}}{{cite:5}}{{cite:4}}{{cite:1}}')).toEqual([
      4, 5, 1,
    ]);
    expect(citeNumbers('none')).toEqual([]);
  });
});

describe('impact mapping (all 7 enums)', () => {
  const cases: Array<[Impact, string, string, string, string]> = [
    // impact, class, pill-label, research-label, node-class
    ['threat', 'threat', '威胁', '威胁研判', 'n-threat'],
    ['opportunity', 'opportunity', '机会', '机会研判', 'n-opportunity'],
    ['neutral', 'neutral', '中性', '中性研判', 'n-neutral'],
    ['needs_fix', 'fix', '待修复', '修复建议', 'n-fix'],
    ['feature_input', 'feat', '功能需求', '需求信号', 'n-feat'],
    ['strength_confirm', 'strength', '优势确认', '优势确认', 'n-strength'],
    ['unknown', 'neutral', '待判', '中性研判', 'n-neutral'],
  ];

  it.each(cases)(
    '%s -> class/label/research/node',
    (impact, cls, label, research, node) => {
      expect(impactClass(impact)).toBe(cls);
      expect(impactLabel(impact)).toBe(label);
      expect(researchLabel(impact)).toBe(research);
      expect(nodeClass(impact)).toBe(node);
    },
  );

  it('attaches icons only to own-product impacts', () => {
    expect(impactMeta('needs_fix').icon).toBe('wrench');
    expect(impactMeta('feature_input').icon).toBe('bulb');
    expect(impactMeta('strength_confirm').icon).toBe('star');
    expect(impactMeta('threat').icon).toBeNull();
    expect(impactMeta('opportunity').icon).toBeNull();
    expect(impactMeta('neutral').icon).toBeNull();
  });

  it('classifies own-product impacts', () => {
    expect(isOwnProductImpact('needs_fix')).toBe(true);
    expect(isOwnProductImpact('feature_input')).toBe(true);
    expect(isOwnProductImpact('strength_confirm')).toBe(true);
    expect(isOwnProductImpact('threat')).toBe(false);
    expect(isOwnProductImpact('unknown')).toBe(false);
  });
});

describe('source tier / glyph mapping', () => {
  it('every Source enum is registered with a tier + glyph', () => {
    const sources: Source[] = [
      'omada_community',
      'unifi_community',
      'unifi_product',
      'unifi_store',
      'unifi_release',
      'blog',
      'reddit',
      'youtube',
      'rss',
      'x',
    ];
    for (const s of sources) {
      const meta = SOURCE_REGISTRY[s];
      expect(meta, s).toBeDefined();
      expect(['official', 'community']).toContain(meta.tier);
      expect(meta.glyph).toBeTruthy();
    }
  });

  it('official tiers are the UniFi first-party + platform sources', () => {
    expect(SOURCE_REGISTRY.unifi_release.tier).toBe('official');
    expect(SOURCE_REGISTRY.blog.tier).toBe('official');
    expect(SOURCE_REGISTRY.unifi_community.tier).toBe('official');
    expect(SOURCE_REGISTRY.unifi_store.tier).toBe('official');
    expect(SOURCE_REGISTRY.reddit.tier).toBe('community');
    expect(SOURCE_REGISTRY.youtube.tier).toBe('community');
  });

  it('maps to the right glyph and honors explicit overrides', () => {
    expect(sourceGlyph('unifi_release')).toBe('unifi');
    expect(sourceGlyph('blog')).toBe('unifi');
    expect(sourceGlyph('reddit')).toBe('reddit');
    expect(sourceGlyph('youtube')).toBe('youtube');
    expect(sourceGlyph('rss')).toBe('rss');
    expect(sourceGlyph('reddit', 'youtube')).toBe('youtube');
  });

  it('builds display labels and tier flags', () => {
    expect(sourceDisplayLabel('reddit')).toBe('Reddit · r/Ubiquiti');
    expect(sourceDisplayLabel('reddit', 'Reddit · r/TPLink_Omada')).toBe(
      'Reddit · r/TPLink_Omada',
    );
    expect(sourceDisplayLabel('youtube')).toBe('YouTube');
    expect(defaultTierLabel('official')).toBe('一手官方');
    expect(defaultTierLabel('community')).toBe('社区二手');
  });

  it('labels categories', () => {
    expect(categoryLabel('bug')).toBe('固件 Bug');
    expect(categoryLabel('feature_request')).toBe('功能请求');
    expect(categoryLabel('pricing')).toBe('定价');
  });
});
