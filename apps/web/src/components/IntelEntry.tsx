/* ============================================================
   IntelEntry — dossier ledger row + its parts.
   Ports project/components.jsx IntelEntry MERGED with the v2/v3
   ds-components: subject-aware ImpactPill (fix/feat/strength with
   wrench/bulb/star icons + labels), SentimentMeta, subject-aware
   Research labels, provenance tags, and the mandatory CitationLine.
   ============================================================ */
import { Icon, SourceGlyph } from './Icon';
import {
  impactClass,
  impactLabel,
  impactMeta,
  researchLabel,
  nodeClass,
  sourceGlyph,
  sourceDisplayLabel,
  defaultTierLabel,
  provenanceLabel,
  sentimentLabel,
  fmtNum,
} from '../lib/intel';
import { jumpTo } from '../lib/jump';
import type { IntelItem, Impact, Metrics as MetricsT } from '../types';

/* ---- SourceBadge (glyph identity + credibility tier) ---- */
export function SourceBadge({ item }: { item: IntelItem }) {
  const tier = item.source_tier || 'community';
  const label = sourceDisplayLabel(item.source, item.source_label);
  return (
    <span className={'src ' + tier}>
      <span className="src-ico">
        <SourceGlyph kind={sourceGlyph(item.source, item.glyph)} />
      </span>
      <span className="src-name">{label}</span>
      <span className={'tier ' + tier}>
        {item.tier_label || defaultTierLabel(tier)}
      </span>
    </span>
  );
}

/* ---- ImpactPill (subject-aware; icon for own-product impacts) ---- */
export function ImpactPill({ impact }: { impact: Impact }) {
  const m = impactMeta(impact);
  return (
    <span className={'impact-pill ' + m.cls}>
      {m.icon ? <Icon name={m.icon} size={13} /> : <span className="pd" />}
      {impactLabel(impact)}
    </span>
  );
}

/* ---- Research note (subject-aware keyword) ---- */
export function Research({ impact, note }: { impact: Impact; note?: string | null }) {
  if (!note) return null;
  return (
    <div className={'research ' + impactClass(impact)}>
      <span className="rk">{researchLabel(impact)} · </span>
      {note}
    </div>
  );
}

/* ---- SentimentMeta (情感 / 相关性 / 切换意图) ---- */
export function SentimentMeta({ item }: { item: IntelItem }) {
  const senti = item.sentiment;
  const rel = item.relevance;
  const intent = item.switch_intent;
  if (!senti && rel == null && !intent) return null;
  return (
    <>
      {senti && (
        <span className={'senti ' + senti}>
          <span className="sd" />
          {sentimentLabel(senti)}
        </span>
      )}
      {rel != null && <span className="senti rel">相关性 {rel}</span>}
      {intent && <span className="senti intent">切换意图</span>}
    </>
  );
}

/* ---- Metrics ---- */
export function Metrics({ m }: { m?: MetricsT | null }) {
  if (!m) return null;
  const out: React.ReactNode[] = [];
  if (m.likes)
    out.push(
      <span className="metric" key="l">
        <Icon name="up" size={14} />
        {fmtNum(m.likes)}
      </span>,
    );
  if (m.comments)
    out.push(
      <span className="metric" key="c">
        <Icon name="chat" size={14} />
        {fmtNum(m.comments)}
      </span>,
    );
  if (m.views)
    out.push(
      <span className="metric" key="v">
        <Icon name="eye" size={14} />
        {fmtNum(m.views)}
      </span>,
    );
  if (m.note)
    out.push(
      <span className="metric" key="n" style={{ opacity: 0.9 }}>
        {m.note}
      </span>,
    );
  if (!out.length) return null;
  return <span className="metrics">{out}</span>;
}

/* ---- CitationLine (mandatory, PRD §7.8.1) ---- */
export function CitationLine({
  item,
  citeId,
}: {
  item: IntelItem;
  citeId?: number | null;
}) {
  const official = (item.source_tier || 'community') === 'official';
  return (
    <a
      className={'cite ' + (official ? 'official' : 'community')}
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
    >
      {citeId != null && <span className="cnum">{citeId}</span>}
      <span className="clk">
        <Icon name="link" size={14} />
      </span>
      <span className="cdom">{item.source_domain}</span>
      <span className="cflag">
        {item.tier_label || (official ? '一手官方' : '社区二手')}
      </span>
      <span className="csep">·</span>
      <span className="cdate tnum">{item.date}</span>
      <span className="cgo">
        查看原文
        <Icon name="external" size={13} />
      </span>
    </a>
  );
}

/* ---- IntelEntry (dossier ledger row) ---- */
export function IntelEntry({
  item,
  idx,
  citeId = null,
  delay = 0,
}: {
  item: IntelItem;
  idx?: number | null;
  citeId?: number | null;
  delay?: number;
}) {
  return (
    <article
      id={citeId != null ? 'item-' + citeId : undefined}
      className="entry fade-up"
      style={{ animationDelay: delay + 'ms' }}
    >
      <div className="entry-rail">
        <span className="entry-idx tnum">
          {idx != null ? String(idx).padStart(2, '0') : ''}
        </span>
        <span className={'entry-node ' + nodeClass(item.omada_impact)} />
        <span className="rail-line" />
      </div>
      <div className="entry-main">
        <div className="entry-head">
          <SourceBadge item={item} />
          <ImpactPill impact={item.omada_impact} />
        </div>
        <div className="entry-title-row">
          <a
            className="entry-title"
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {item.title}
            <span className="ext">↗</span>
          </a>
          {item.stage && <span className="stage">{item.stage}</span>}
        </div>
        <div className="tags">
          {(item.badges || []).map((b, i) => (
            <span className="tag" key={i}>
              {b}
            </span>
          ))}
          <span className="tag src-a">{provenanceLabel(item.provenance)}</span>
          <SentimentMeta item={item} />
        </div>
        <p className="entry-sum">{item.summary}</p>
        <Research impact={item.omada_impact} note={item.impact_note} />
        <div className="entry-foot">
          <Metrics m={item.metrics} />
          {citeId != null && (
            <span
              className="cite-jump"
              role="link"
              tabIndex={0}
              onClick={() => jumpTo('ref-' + citeId)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') jumpTo('ref-' + citeId);
              }}
            >
              [{citeId}] 溯源
            </span>
          )}
        </div>
        <CitationLine item={item} citeId={citeId} />
      </div>
    </article>
  );
}
