/* ============================================================
   Lead + Tally, SectionHead (+ tones), References, ReportHeader,
   StrategyBlock (weekly), EmptyState.
   Ported 1:1 from project/components.jsx + ds-components.jsx.
   ============================================================ */
import { Icon, SourceGlyph } from './Icon';
import { CiteText } from './CiteText';
import { jumpTo } from './../lib/jump';
import { defaultTierLabel, sourceGlyph } from '../lib/intel';
import type {
  Report,
  Reference,
  Strategy,
  SectionKey,
  Insight,
  IntelItem,
} from '../types';

/* ---- Lead (导语 with {{cite:N}} superscripts + tally chips) ---- */
export function Lead({ report }: { report: Report }) {
  const t = report.tally;
  return (
    <div className="lead" id="lead">
      <div className="lead-eyebrow">
        本期导语 · <span className="opus">Opus 策展</span>
      </div>
      <p className="lead-text">
        <CiteText text={report.lead.text} />
        {report.lead.strong && (
          <span className="lead-strong">{report.lead.strong}</span>
        )}
      </p>
      {t && (
        <div className="tally">
          <span className="tchip">
            <span className="cd" />信号 {t.signals ?? 0}
          </span>
          <span className="tchip t-threat">
            <span className="cd" />威胁 {t.threat ?? 0}
          </span>
          <span className="tchip t-opp">
            <span className="cd" />机会 {t.opp ?? 0}
          </span>
          <span className="tchip">
            <span className="cd" />中性 {t.neutral ?? 0}
          </span>
          <span className="tchip t-accent">
            <span className="cd" />官方源 {t.official ?? 0}
          </span>
        </div>
      )}
    </div>
  );
}

/* ---- InsightEntry (synthesized multi-source insight, academic citations) ---- */
export function InsightEntry({
  insight,
  byCiteId,
  num,
}: {
  insight: Insight;
  byCiteId: Record<number, IntelItem>;
  num: string;
}) {
  const takeaway = (insight.takeaway || '').replace(/^\s*💡\s*/, '');
  const sources = (insight.cite_refs || [])
    .map((n) => byCiteId[n])
    .filter(Boolean) as IntelItem[];
  return (
    <article className="insight" id={'insight-' + insight.id}>
      <div className="insight-head">
        <span className="insight-num tnum">{num}</span>
        <h3 className="insight-title">{insight.title}</h3>
      </div>
      <div className="insight-body">
        <CiteText text={insight.body} />
      </div>
      {takeaway && (
        <div className="insight-take">
          <span className="take-bulb">💡</span>
          <span className="take-text">
            <CiteText text={takeaway} />
          </span>
        </div>
      )}
      {sources.length > 0 && (
        <div className="insight-src">
          <span className="src-label">来源</span>
          {sources.map((it, i) => (
            <span key={it.cite_id} style={{ display: 'contents' }}>
              {i > 0 && <span className="src-sep">·</span>}
              <a
                className="src-chip"
                href={it.url}
                target="_blank"
                rel="noopener noreferrer"
                title={it.title}
              >
                <SourceGlyph kind={sourceGlyph(it.source, it.glyph)} />
                <span className="src-name">
                  {it.title.length > 30 ? it.title.slice(0, 30) + '…' : it.title}
                </span>
              </a>
            </span>
          ))}
        </div>
      )}
    </article>
  );
}

/* ---- SectionHead (mark + index + solid keyline + section tone) ---- */
export function SectionHead({
  icon,
  num,
  title,
  count,
  desc,
  tone,
  id,
}: {
  icon?: string;
  num?: string;
  title: string;
  count?: number | null;
  desc?: string;
  tone?: SectionKey;
  id?: string;
}) {
  return (
    <div id={id} className={tone ? 'tone-' + tone : undefined}>
      <div className="sec-head">
        <span className="sec-mark">
          <Icon name={icon || 'activity'} size={18} />
        </span>
        <div className="sec-titles">
          <div className="sec-title">
            {num && <span className="sec-num">{num}</span>}
            {title}
            {count != null && <span className="sec-count tnum">{count} 条</span>}
          </div>
          {desc && <div className="sec-desc">{desc}</div>}
        </div>
      </div>
      <div className="sec-rule" />
    </div>
  );
}

/* ---- StrategyBlock (WEEKLY ONLY, pinned at top) ---- */
export function StrategyBlock({ strategy }: { strategy: Strategy }) {
  const paras: [string, string][] =
    strategy.paras && strategy.paras.length
      ? strategy.paras
      : [['洞察', strategy.body]];
  const refs = strategy.cite_refs || [];
  return (
    <div className="strategy" id="strategy">
      <div className="strategy-head">
        <span className="strategy-mark">
          <Icon name="target" size={20} />
        </span>
        <div className="strategy-titles">
          <div className="strategy-title">{strategy.title}</div>
          {strategy.period && (
            <div className="strategy-period">{strategy.period}</div>
          )}
        </div>
        <span className="opus-badge">OPUS 策展</span>
      </div>
      <div className="strategy-body">
        {paras.map((p, i) => (
          <div className="strat-para" key={i}>
            <div className="strat-label">{p[0]}</div>
            <div className="strat-text">
              <CiteText text={p[1]} />
            </div>
          </div>
        ))}
        {refs.length > 0 && (
          <div className="strat-refs">
            <span className="rl">依据</span>
            {refs.map((n) => (
              <span
                className="strat-ref"
                key={n}
                role="link"
                tabIndex={0}
                onClick={() => jumpTo('item-' + n)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') jumpTo('item-' + n);
                }}
              >
                [{n}]
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---- References (numbered end list, ties items <-> superscripts) ---- */
export function References({ refs }: { refs: Reference[] }) {
  return (
    <section className="refs" id="refs">
      <div className="ref-h">
        <h2>参考来源</h2>
        <span className="sub">References · 编号对应正文上标</span>
      </div>
      <div className="reflist">
        {refs.map((r) => {
          const official = (r.source_tier || 'community') === 'official';
          return (
            <div className="refitem" id={'ref-' + r.cite_id} key={r.cite_id}>
              <span
                className="rn"
                role="link"
                tabIndex={0}
                onClick={() => jumpTo('item-' + r.cite_id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') jumpTo('item-' + r.cite_id);
                }}
              >
                [{r.cite_id}]
              </span>
              <div className="rbody">
                <a
                  className="rtitle"
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {r.title}
                </a>
                <div className="rmeta">
                  <span className={official ? 'official' : ''}>
                    {r.source_domain}
                  </span>
                  <span className="rsep">·</span>
                  <span>{r.date}</span>
                  <span className="rsep">·</span>
                  <span>
                    {r.tier_label ||
                      defaultTierLabel(r.source_tier || 'community')}
                  </span>
                </div>
                <a
                  className="rurl"
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {r.url}
                </a>
              </div>
              <a
                className="rgo"
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
                title="打开原文"
              >
                <Icon name="external" size={15} />
              </a>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/* ---- ReportHeader ---- */
export interface MetaItem {
  icon?: string;
  text: string;
}
export function ReportHeader({
  kicker,
  title,
  meta,
  actions,
}: {
  kicker: string;
  title: string;
  meta: MetaItem[];
  actions?: React.ReactNode;
}) {
  return (
    <header className="rhead">
      <div className="kicker">{kicker}</div>
      <h1>{title}</h1>
      <div className="rhead-meta">
        {meta.map((m, i) => (
          <span key={i} style={{ display: 'contents' }}>
            {i > 0 && <span className="sep">·</span>}
            <span className="m">
              {m.icon && <Icon name={m.icon} size={13} />}
              {m.text}
            </span>
          </span>
        ))}
        {actions && <div className="rhead-actions">{actions}</div>}
      </div>
    </header>
  );
}

/* ---- EmptyState (honest empty section) ---- */
export function EmptyState({ text }: { text: string }) {
  return (
    <div className="empty">
      <Icon name="check" size={20} />
      {text}
    </div>
  );
}
