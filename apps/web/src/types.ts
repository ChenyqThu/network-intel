/* ============================================================
   Network Intel — TypeScript types
   Mirrors contract/report.schema.json (PRD v1.3 §7.9) exactly.
   The engine produces report.json; the frontend only renders it.
   ============================================================ */

export type ReportType = 'daily' | 'weekly';

export type SourceTier = 'official' | 'community';

export type Subject = 'omada_self' | 'competitor' | 'industry';

export type Source =
  | 'omada_community'
  | 'unifi_community'
  | 'unifi_product'
  | 'unifi_store'
  | 'unifi_release'
  | 'blog'
  | 'reddit'
  | 'youtube'
  | 'rss'
  | 'x';

export type Provenance = 'A' | 'B' | 'C' | 'D';

export type Category =
  | 'bug'
  | 'feature_request'
  | 'praise'
  | 'pain_point'
  | 'new_product'
  | 'pricing'
  | 'firmware'
  | 'competitor'
  | 'sentiment'
  | 'industry'
  | 'industry_trend';

export type SignalStrength = 'high' | 'medium' | 'low';

/** All 7 impact enums: competitor-view (threat/opportunity/neutral) +
 *  omada_self-view (needs_fix/feature_input/strength_confirm) + unknown. */
export type Impact =
  | 'threat'
  | 'opportunity'
  | 'neutral'
  | 'needs_fix'
  | 'feature_input'
  | 'strength_confirm'
  | 'unknown';

export type Sentiment = 'pos' | 'neg' | 'neu' | null;

export type Glyph = 'unifi' | 'reddit' | 'youtube' | 'rss' | 'x';

export type SectionKey =
  | 'omada_self'
  | 'competitor'
  | 'sentiment'
  | 'industry'
  | 'store'
  | 'dashboard';

export interface Metrics {
  likes?: number | null;
  comments?: number | null;
  views?: number | null;
  score?: number | null;
  note?: string | null;
  [k: string]: number | string | null | undefined;
}

export interface IntelItem {
  id: string;
  cite_id: number;
  subject: Subject;
  source: Source;
  source_domain: string;
  source_tier: SourceTier;
  source_label?: string;
  tier_label?: string;
  glyph?: string;
  provenance?: Provenance;
  title: string;
  stage?: string | null;
  badges?: string[];
  summary: string;
  category: Category;
  signal_strength?: SignalStrength;
  omada_impact: Impact;
  impact_note?: string | null;
  metrics?: Metrics | null;
  sentiment?: Sentiment;
  relevance?: number | null;
  switch_intent?: boolean | null;
  date: string;
  url: string;
}

export interface Lead {
  text: string;
  strong?: string | null;
  cite_refs: number[];
}

export interface StrategyPara {
  0: string;
  1: string;
}

export interface Strategy {
  title: string;
  period?: string;
  paras?: [string, string][];
  body: string;
  cite_refs: number[];
}

export interface Tally {
  signals?: number;
  threat?: number;
  opp?: number;
  neutral?: number;
  official?: number;
}

export interface Section {
  key: SectionKey;
  title: string;
  icon?: string;
  desc?: string;
  items: string[];
}

export interface Reference {
  cite_id: number;
  title: string;
  source_domain: string;
  source_tier?: SourceTier;
  tier_label?: string;
  date: string;
  url: string;
}

export type StoreDir = 'up' | 'down' | 'flat' | 'new';
export type StockState = 'in' | 'low' | 'out';

export interface StoreRow {
  product: string;
  cat?: string;
  from?: number | null;
  to?: number | null;
  change?: string;
  dir?: StoreDir;
  stock: StockState;
}

export interface TopHot {
  id?: string;
  title?: string;
  score?: number;
}

export interface Stats {
  total_items?: number;
  by_source?: Record<string, number>;
  by_impact?: Record<string, number>;
  top_hot?: TopHot[];
  [k: string]: unknown;
}

export interface DashboardSource {
  key: string;
  label: string;
  count: number;
}

export interface SentimentTrendPoint {
  wk: string;
  omada: number;
  unifi: number;
}

export interface PainPoint {
  name: string;
  count: number;
  of: number;
}

export interface TopHeatPoint {
  id: string;
  v: number;
  fmt?: string;
}

export interface Dashboard {
  signals: number;
  signalsDelta: number;
  threats: number;
  opps: number;
  neutral: number;
  newCompetitor: number;
  newCompetitorDelta: number;
  avgHeat: number;
  avgHeatDelta: number;
  sources: DashboardSource[];
  sentimentTrend: SentimentTrendPoint[];
  vs: { omada: number; unifi: number };
  pains: PainPoint[];
  topHeat: TopHeatPoint[];
  [k: string]: unknown;
}

export interface Report {
  report_id: string;
  type: ReportType;
  date: string;
  date_range: string;
  generated_at: string;
  title?: string;
  lead: Lead;
  strategy?: Strategy | null;
  tally?: Tally | null;
  sections: Section[];
  items: IntelItem[];
  references: Reference[];
  store?: StoreRow[];
  stats: Stats;
  dashboard?: Dashboard | null;
}

/** Archive index entry (contract/archive.json). */
export type ArchiveTheme =
  | 'omada_self'
  | 'competitor'
  | 'sentiment'
  | 'industry'
  | 'pricing'
  | 'new_product';

export interface ArchiveEntry {
  id: string;
  type: ReportType;
  date: string;
  title: string;
  excerpt: string;
  signals: number;
  threats: number;
  opps: number;
  themes: ArchiveTheme[];
  empty?: boolean;
}

export interface Archive {
  reports: ArchiveEntry[];
}
