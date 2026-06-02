/* ============================================================
   Network Intel — centralized intel utilities (unit-tested)
   - {{cite:N}} superscript parsing
   - subject-aware impact -> css-class / label / research-label / node mapping
   - source glyph + tier mapping + display labels
   - category labels
   - number formatting
   ============================================================ */
import type {
  Impact,
  Source,
  SourceTier,
  Category,
  Sentiment,
  Glyph,
} from '../types';

/* ---------- {{cite:N}} parsing ---------- */

export type CiteToken =
  | { kind: 'text'; value: string }
  | { kind: 'cite'; n: number };

const CITE_RE = /(\{\{cite:\d+\}\})/g;
const CITE_ONE = /^\{\{cite:(\d+)\}\}$/;

/** Split a string with {{cite:N}} placeholders into ordered tokens. */
export function parseCites(text: string): CiteToken[] {
  const parts = String(text).split(CITE_RE);
  const out: CiteToken[] = [];
  for (const p of parts) {
    if (p === '') continue;
    const m = p.match(CITE_ONE);
    if (m) out.push({ kind: 'cite', n: Number(m[1]) });
    else out.push({ kind: 'text', value: p });
  }
  return out;
}

/** Distinct cite numbers in first-appearance order. */
export function citeNumbers(text: string): number[] {
  const seen = new Set<number>();
  const out: number[] = [];
  for (const tok of parseCites(text)) {
    if (tok.kind === 'cite' && !seen.has(tok.n)) {
      seen.add(tok.n);
      out.push(tok.n);
    }
  }
  return out;
}

/* ---------- impact mapping (subject-aware, all 7 enums) ---------- */

/** The css class suffix used by .impact-pill / .research / .entry-node. */
export type ImpactClass =
  | 'threat'
  | 'opportunity'
  | 'neutral'
  | 'fix'
  | 'feat'
  | 'strength';

interface ImpactMeta {
  cls: ImpactClass;
  /** pill label (zh) */
  label: string;
  /** research-note keyword label (zh) */
  research: string;
  /** lucide-ish icon name for own-product impacts; null => use the .pd dot */
  icon: 'wrench' | 'bulb' | 'star' | null;
}

const IMPACT_TABLE: Record<Exclude<Impact, 'unknown'>, ImpactMeta> = {
  threat: { cls: 'threat', label: '威胁', research: '威胁研判', icon: null },
  opportunity: { cls: 'opportunity', label: '机会', research: '机会研判', icon: null },
  neutral: { cls: 'neutral', label: '中性', research: '中性研判', icon: null },
  needs_fix: { cls: 'fix', label: '待修复', research: '修复建议', icon: 'wrench' },
  feature_input: { cls: 'feat', label: '功能需求', research: '需求信号', icon: 'bulb' },
  strength_confirm: { cls: 'strength', label: '优势确认', research: '优势确认', icon: 'star' },
};

const IMPACT_UNKNOWN: ImpactMeta = {
  cls: 'neutral',
  label: '待判',
  research: '中性研判',
  icon: null,
};

export function impactMeta(impact: Impact): ImpactMeta {
  if (impact === 'unknown') return IMPACT_UNKNOWN;
  return IMPACT_TABLE[impact] ?? IMPACT_UNKNOWN;
}

export function impactClass(impact: Impact): ImpactClass {
  return impactMeta(impact).cls;
}

export function impactLabel(impact: Impact): string {
  return impactMeta(impact).label;
}

export function researchLabel(impact: Impact): string {
  return impactMeta(impact).research;
}

/** entry-node modifier class (diamond on the meta rail). */
export function nodeClass(impact: Impact): string {
  return 'n-' + impactClass(impact);
}

/** True when this impact is an own-product (omada_self) signal. */
export function isOwnProductImpact(impact: Impact): boolean {
  return (
    impact === 'needs_fix' ||
    impact === 'feature_input' ||
    impact === 'strength_confirm'
  );
}

/* ---------- source registry (glyph + tier + labels) ---------- */

interface SourceMeta {
  label: string;
  chan: string;
  domain: string;
  tier: SourceTier;
  tierLabel: string;
  glyph: Glyph;
}

export const SOURCE_REGISTRY: Record<Source, SourceMeta> = {
  unifi_release: { label: 'UniFi 官方', chan: 'Release', domain: 'community.ui.com', tier: 'official', tierLabel: '一手官方', glyph: 'unifi' },
  blog: { label: 'UniFi 官方', chan: 'Blog', domain: 'blog.ui.com', tier: 'official', tierLabel: '一手官方', glyph: 'unifi' },
  unifi_community: { label: 'UniFi 社区', chan: 'Community', domain: 'community.ui.com', tier: 'official', tierLabel: '官方平台', glyph: 'unifi' },
  unifi_store: { label: 'UniFi Store', chan: 'Store', domain: 'store.ui.com', tier: 'official', tierLabel: '一手官方', glyph: 'unifi' },
  unifi_product: { label: 'UniFi Store', chan: 'Store', domain: 'store.ui.com', tier: 'official', tierLabel: '一手官方', glyph: 'unifi' },
  omada_community: { label: 'Omada 社区', chan: 'Community', domain: 'community.tp-link.com', tier: 'community', tierLabel: '社区一手', glyph: 'reddit' },
  reddit: { label: 'Reddit', chan: 'r/Ubiquiti', domain: 'reddit.com', tier: 'community', tierLabel: '社区二手', glyph: 'reddit' },
  youtube: { label: 'YouTube', chan: '', domain: 'youtube.com', tier: 'community', tierLabel: '社区二手', glyph: 'youtube' },
  rss: { label: 'RSS', chan: '行业', domain: 'rss', tier: 'community', tierLabel: '行业来源', glyph: 'rss' },
  x: { label: 'X', chan: '', domain: 'x.com', tier: 'community', tierLabel: '社区二手', glyph: 'x' },
};

export function sourceMeta(source: Source): SourceMeta | undefined {
  return SOURCE_REGISTRY[source];
}

/** Resolve the source glyph, honoring an explicit per-item glyph override. */
export function sourceGlyph(source: Source, explicit?: string): Glyph {
  if (explicit) return explicit as Glyph;
  return SOURCE_REGISTRY[source]?.glyph ?? 'rss';
}

/** Resolve the display label for the source badge. */
export function sourceDisplayLabel(
  source: Source,
  explicit?: string,
): string {
  if (explicit) return explicit;
  const s = SOURCE_REGISTRY[source];
  if (!s) return source;
  return s.chan ? `${s.label} · ${s.chan}` : s.label;
}

/** Default tier-flag label for a given tier (fallback when item omits one). */
export function defaultTierLabel(tier: SourceTier): string {
  return tier === 'official' ? '一手官方' : '社区二手';
}

/* ---------- category labels ---------- */

export const CATEGORY_LABELS: Record<Category, string> = {
  bug: '固件 Bug',
  feature_request: '功能请求',
  praise: '好评',
  pain_point: '痛点',
  new_product: '新品',
  pricing: '定价',
  firmware: '固件',
  competitor: '竞品',
  sentiment: '舆情',
  industry: '行业',
  industry_trend: '行业趋势',
};

export function categoryLabel(category: Category): string {
  return CATEGORY_LABELS[category] ?? category;
}

/* ---------- sentiment labels ---------- */

export const SENTI_LABELS: Record<'pos' | 'neg' | 'neu', string> = {
  pos: '情感:正面',
  neg: '情感:负面',
  neu: '情感:中性',
};

export function sentimentLabel(s: Exclude<Sentiment, null>): string {
  return SENTI_LABELS[s];
}

/* ---------- provenance label ---------- */

export function provenanceLabel(p?: string): string {
  switch (p) {
    case 'A':
      return '来源 A · 情报流';
    case 'B':
      return '来源 B · Supabase';
    case 'C':
      return '来源 C · 行业 RSS';
    case 'D':
      return '来源 D · 策略';
    default:
      return '来源 · 未标注';
  }
}

/* ---------- number formatting ---------- */

export function fmtNum(n: number): string {
  return n >= 1000
    ? (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(/\.0$/, '') + 'k'
    : '' + n;
}
