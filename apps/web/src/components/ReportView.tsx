/* ============================================================
   ReportView — renders a daily/weekly report from the contract.
   Lead + (weekly) StrategyBlock + section sheets + store table +
   analytics dashboard + References, with a sticky per-report TOC.
   ============================================================ */
import { useMemo, useState } from 'react';
import { Icon } from './Icon';
import { IntelEntry } from './IntelEntry';
import {
  Lead,
  SectionHead,
  References,
  ReportHeader,
  StrategyBlock,
  EmptyState,
  InsightEntry,
} from './ReportParts';
import { Donut, SourceBars, TrendLine, KpiCard, SOURCE_COLORS } from './Charts';
import type { ChartStyle } from './Charts';
import { categoryLabel, sourceDisplayLabel, fmtNum } from '../lib/intel';
import { jumpTo } from '../lib/jump';
import type {
  Report,
  Section,
  IntelItem,
  Insight,
  ArchiveEntry,
  Dashboard,
  SectionKey,
} from '../types';

/* sections that carry their own non-ledger rendering */
const SPECIAL_SECTIONS: SectionKey[] = ['store', 'dashboard'];

function useItemIndex(report: Report): Record<string, IntelItem> {
  return useMemo(
    () => Object.fromEntries(report.items.map((it) => [it.id, it])),
    [report],
  );
}

function pick(ids: string[], byId: Record<string, IntelItem>): IntelItem[] {
  return ids.map((id) => byId[id]).filter(Boolean) as IntelItem[];
}

/* ---- one section = header (with tone) + a sheet of ledger entries ---- */
function SectionSheet({
  section,
  num,
  byId,
}: {
  section: Section;
  num: string;
  byId: Record<string, IntelItem>;
}) {
  const items = pick(section.items, byId);
  return (
    <section className="sec" id={'sec-' + section.key}>
      <SectionHead
        icon={section.icon}
        num={num}
        title={section.title}
        count={items.length}
        desc={section.desc}
        tone={section.key}
      />
      {items.length ? (
        <div className="sheet">
          {items.map((it, i) => (
            <IntelEntry
              key={it.id}
              item={it}
              idx={it.cite_id}
              citeId={it.cite_id}
              delay={i * 45}
            />
          ))}
        </div>
      ) : (
        <div style={{ marginTop: 18 }}>
          <EmptyState text="本期该板块无硬信号——保持诚实，不凑数。" />
        </div>
      )}
    </section>
  );
}

/* ---- one synthesized section = header + multi-source insight cards ---- */
function InsightSection({
  section,
  num,
  insightsById,
  byCiteId,
}: {
  section: Section;
  num: string;
  insightsById: Record<string, Insight>;
  byCiteId: Record<number, IntelItem>;
}) {
  const insights = (section.insights || [])
    .map((id) => insightsById[id])
    .filter(Boolean) as Insight[];
  return (
    <section className="sec" id={'sec-' + section.key}>
      <SectionHead
        icon={section.icon}
        num={num}
        title={section.title}
        count={insights.length}
        desc={section.desc}
        tone={section.key}
      />
      {insights.length ? (
        <div className="insights">
          {insights.map((ins, i) => (
            <InsightEntry
              key={ins.id}
              insight={ins}
              byCiteId={byCiteId}
              num={`${Number(num)}.${i + 1}`}
            />
          ))}
        </div>
      ) : (
        <div style={{ marginTop: 18 }}>
          <EmptyState text="本期该板块无硬信号——保持诚实，不凑数。" />
        </div>
      )}
    </section>
  );
}

/* ---- store table (weekly) ---- */
function StoreSection({ report, num }: { report: Report; num: string }) {
  const rows = report.store || [];
  return (
    <section className="sec" id="sec-store">
      <SectionHead icon="store" num={num} title="Store 动向" desc="价格 / 库存 / 上架变化" />
      <div className="sheet" style={{ padding: '8px 8px' }}>
        {rows.length ? (
          <div className="tbl-scroll">
          <table className="tbl">
            <thead>
              <tr>
                <th>产品</th>
                <th>类别</th>
                <th>价格</th>
                <th>变化</th>
                <th>库存</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="prod">{r.product}</td>
                  <td style={{ color: 'var(--fg-tertiary)', fontSize: 12.5 }}>{r.cat}</td>
                  <td className="pricecell">
                    {r.from != null && <span className="old">${r.from}</span>}
                    <span style={{ fontWeight: 700 }}>{r.to != null ? `$${r.to}` : '—'}</span>
                  </td>
                  <td className={'chg ' + (r.dir === 'down' ? 'down' : r.dir === 'up' ? 'up' : '')}>{r.change}</td>
                  <td>
                    <span className={'stockpill ' + r.stock}>
                      {r.stock === 'in' ? '有货' : r.stock === 'low' ? '紧张' : '缺货'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : (
          <div style={{ padding: 14 }}>
            <EmptyState text="本周 Store 无价格 / 库存 / 上架变动。" />
          </div>
        )}
      </div>
    </section>
  );
}

/* ---- analytics dashboard (weekly) ---- */
function DashboardSection({
  report,
  db,
  num,
  chartStyle,
}: {
  report: Report;
  db: Dashboard;
  num: string;
  chartStyle: ChartStyle;
}) {
  const byId = useItemIndex(report);
  const sources = db.sources.map((s, i) => ({
    label: s.label,
    count: s.count,
    color: SOURCE_COLORS[i % SOURCE_COLORS.length],
  }));
  // Multi-week editorial series only render when the data is real and complete.
  // A single live report can't derive them yet, so guard each panel and show an
  // honest empty-state instead of NaN charts (see backend trend.normalize_dashboard).
  const trend = (db.sentimentTrend || []).filter(
    (d) => Number.isFinite(d?.omada) && Number.isFinite(d?.unifi),
  );
  const pains = (db.pains || []).filter(
    (p) => p && p.name && Number.isFinite(p.count) && Number.isFinite(p.of) && p.of > 0,
  );
  const vsOk = !!db.vs && ((db.vs.omada || 0) > 0 || (db.vs.unifi || 0) > 0);
  const delta = (v?: number) =>
    v == null || !Number.isFinite(v) ? undefined : `${v > 0 ? '+' : ''}${v} 环比`;
  const dir = (v?: number) =>
    v == null || !Number.isFinite(v) ? ('flat' as const) : v > 0 ? 'up' : v < 0 ? 'down' : 'flat';
  return (
    <>
      {/* sentiment / pains / vs panels */}
      <section className="sec" id="sec-sentiment-panels">
        <SectionHead icon="chat" num={num} title="口碑与痛点分析" desc="情感趋势 / 高频痛点 / Omada vs UniFi" tone="sentiment" />
        <div className="dash-grid">
          <div className="panel">
            <div className="panel-head">
              <h3>口碑指数趋势</h3>
              <span className="sub">近 8 周 · 情感加权</span>
            </div>
            {trend.length >= 2 ? (
              <TrendLine series={trend} style={chartStyle} />
            ) : (
              <EmptyState text="口碑指数趋势需多周历史数据，正在积累中" />
            )}
          </div>
          <div className="panel">
            <div className="panel-head">
              <h3>高频痛点 Top 5</h3>
              <span className="sub">UniFi 社区 · 本周</span>
            </div>
            {pains.length ? (
              <div className="pain">
                {pains.map((p, i) => (
                  <div className="pr" key={i}>
                    <div className="pt">
                      <span className="pn">{p.name}</span>
                      <span className="pc tnum">{p.count}</span>
                    </div>
                    <div className="track">
                      <div
                        className="fill"
                        style={{ width: (p.count / p.of) * 100 + '%', background: i < 2 ? 'var(--threat)' : 'var(--color-primary)' }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState text="高频痛点需更多样本统计，正在积累中" />
            )}
          </div>
        </div>
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="panel-head">
            <h3>Omada vs UniFi · 本周正面口碑</h3>
            <span className="sub">环比上周</span>
          </div>
          {vsOk ? (
            <div className="vs">
              <div className="vr">
                <div className="vl">
                  <span>Omada</span>
                  <span className="tnum" style={{ color: 'var(--opp)' }}>{db.vs.omada} ▲</span>
                </div>
                <div className="bar omada">
                  <i style={{ width: db.vs.omada + '%' }} />
                </div>
              </div>
              <div className="vr">
                <div className="vl">
                  <span>UniFi</span>
                  <span className="tnum" style={{ color: 'var(--threat)' }}>{db.vs.unifi} ▼</span>
                </div>
                <div className="bar unifi">
                  <i style={{ width: db.vs.unifi + '%' }} />
                </div>
              </div>
            </div>
          ) : (
            <EmptyState text="环比口碑对比需上周数据，正在积累中" />
          )}
        </div>
      </section>

      {/* KPI grid + source contribution + heat ranking */}
      <section className="sec" id="sec-dashboard">
        <SectionHead icon="barChart" num={String(Number(num) + 1)} title="数据看板" desc="信号量 / 各源贡献 / 热度 Top" tone="industry" />
        <div className="kpi-grid">
          <KpiCard label="本周信号量" icon="zap" value={db.signals} deltaText={delta(db.signalsDelta)} dir={dir(db.signalsDelta)} />
          <KpiCard label="威胁 / 机会" icon="swords" value={`${db.threats}/${db.opps}`} deltaText={`${db.neutral ?? 0} 中性`} dir="flat" />
          <KpiCard label="新竞品动作" icon="sparkle" value={db.newCompetitor ?? 0} deltaText={delta(db.newCompetitorDelta)} dir={dir(db.newCompetitorDelta)} />
          <KpiCard label="平均热度" icon="trendUp" value={db.avgHeat ?? '—'} deltaText={delta(db.avgHeatDelta)} dir={dir(db.avgHeatDelta)} />
        </div>
        <div className="dash-grid">
          <div className="panel">
            <div className="panel-head">
              <h3>各源贡献</h3>
              <span className="sub">本周 {db.signals} 条</span>
            </div>
            {chartStyle === 'filled' ? <SourceBars data={sources} /> : <Donut data={sources} total={db.signals} style="minimal" />}
          </div>
          <div className="panel">
            <div className="panel-head">
              <h3>热度 Top 5</h3>
              <span className="sub">赞 + 评论加权</span>
            </div>
            <div className="rank">
              {db.topHeat.map((h, i) => {
                const it = byId[h.id];
                return (
                  <div className={'rr' + (i < 1 ? ' top' : '')} key={i}>
                    <span className="ri">{String(i + 1).padStart(2, '0')}</span>
                    <div className="rl">
                      <div className="rt">{it ? it.title : h.id}</div>
                      <div className="rm">
                        {it ? `${sourceDisplayLabel(it.source, it.source_label)} · ${categoryLabel(it.category)}` : ''}
                      </div>
                    </div>
                    <span className="rv tnum">{h.fmt === 'views' ? fmtNum(h.v) + ' 播放' : fmtNum(h.v)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

/* ---- report body: render sections in contract order ---- */
function ReportBody({
  report,
  byId,
  chartStyle,
}: {
  report: Report;
  byId: Record<string, IntelItem>;
  chartStyle: ChartStyle;
}) {
  const insightsById = useMemo(
    () => Object.fromEntries((report.insights || []).map((i) => [i.id, i])),
    [report],
  );
  const byCiteId = useMemo(
    () => Object.fromEntries(report.items.map((it) => [it.cite_id, it])),
    [report],
  );
  let n = 0;
  return (
    <>
      {report.sections.map((s) => {
        n += 1;
        const num = String(n).padStart(2, '0');
        if (s.key === 'store') return <StoreSection key={s.key} report={report} num={num} />;
        if (s.key === 'dashboard') {
          if (!report.dashboard) return null;
          // dashboard section consumes two numbers (panels + board)
          n += 1;
          return (
            <DashboardSection
              key={s.key}
              report={report}
              db={report.dashboard}
              num={num}
              chartStyle={chartStyle}
            />
          );
        }
        // Synthesized mode: render insight cards instead of per-item entries.
        if (s.insights && s.insights.length) {
          return (
            <InsightSection
              key={s.key}
              section={s}
              num={num}
              insightsById={insightsById}
              byCiteId={byCiteId}
            />
          );
        }
        return <SectionSheet key={s.key} section={s} num={num} byId={byId} />;
      })}
    </>
  );
}

/* ---- per-report sticky sidebar TOC ---- */
function ReportAside({
  report,
  archive,
  onOpen,
}: {
  report: Report;
  archive: ArchiveEntry[];
  onOpen: (id: string) => void;
}) {
  const nav: [string, string, string][] = [];
  nav.push(['lead', '本期导语', '导语']);
  if (report.strategy) nav.push(['strategy', '市场策略洞察', '★']);
  let n = 0;
  for (const s of report.sections) {
    n += 1;
    if (s.key === 'dashboard') {
      nav.push(['sec-sentiment-panels', '口碑与痛点', String(n)]);
      n += 1;
      nav.push(['sec-dashboard', '数据看板', String(n)]);
    } else if (s.key === 'store') {
      nav.push(['sec-store', s.title, String(s.items.length || '—')]);
    } else {
      nav.push([
        'sec-' + s.key,
        s.title,
        String((s.insights && s.insights.length) || s.items.length),
      ]);
    }
  }
  nav.push(['refs', '参考来源', String(report.references.length)]);

  const [histFilter, setHistFilter] = useState<'all' | 'daily' | 'weekly'>('all');
  const recent = archive
    .filter(
      (a) =>
        a.id !== report.report_id &&
        (histFilter === 'all' || a.type === histFilter),
    )
    .slice(0, 5);
  const periodLabel = report.type === 'weekly' ? report.date_range : report.date;
  return (
    <aside className="aside">
      <div className="aside-sticky">
        <div className="aside-h">本期 · {periodLabel}</div>
        <nav className="toc">
          {nav.map(([id, label, n2], i) => (
            <a
              key={id}
              className={i === 0 ? 'active' : ''}
              role="link"
              tabIndex={0}
              onClick={() => jumpTo(id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') jumpTo(id);
              }}
            >
              {label}
              <span className="n tnum">{n2}</span>
            </a>
          ))}
        </nav>
        <div className="aside-div" />
        <div className="aside-note">
          数据融合 · 多源策展
          <br />
          <b>来源 A</b> 舆情流 Reddit / YouTube
          <br />
          <b>来源 B</b> UNIFI_CHANNELS（一手官方）
          <br />
          <b>来源 C</b> 行业 RSS
          <br />
          <b>来源 G</b> 深度研究（周报）
          <br />
          <br />
          <a
            href={`/api/reports/${report.report_id}/email`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--color-primary)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            <Icon name="mail" size={14} />
            邮件推送版本 ↗
          </a>
        </div>
        <div className="aside-div" />
        <div className="aside-h">近期报告</div>
        <div className="hist-filter seg">
          {(
            [
              ['all', '全部'],
              ['daily', '日报'],
              ['weekly', '周报'],
            ] as const
          ).map(([k, label]) => (
            <button
              key={k}
              className={histFilter === k ? 'on' : ''}
              onClick={() => setHistFilter(k)}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="hist">
          {recent.length ? (
            recent.map((a) => {
              const [, mm, dd] = a.date.split('-');
              return (
                <div className="hist-row" key={a.id} onClick={() => onOpen(a.id)} title={a.title}>
                  <span className={'ht ' + a.type}>{a.type === 'weekly' ? '周' : '日'}</span>
                  <span className="hd tnum">
                    {mm}-{dd}
                  </span>
                  <span className="hl">{a.title}</span>
                </div>
              );
            })
          ) : (
            <div className="hist-empty">
              近期暂无{histFilter === 'weekly' ? '周报' : '日报'}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

/* ---- FunnelBar (subtitle: 采集 per source -> 精炼 -> 策展 · time · byline) ---- */
function FunnelBar({ report }: { report: Report }) {
  const f = report.funnel;
  if (!f) return null;
  const collected = f.collected || [];
  const genTime = /T(\d{2}:\d{2})/.exec(report.generated_at)?.[1];
  const themes = report.insights?.length || 0;
  return (
    <div className="funnel" aria-label="数据漏斗">
      {collected.length > 0 && (
        <span className="fstage">
          {collected.map((c, i) => (
            <span className="fsrc" key={c.key}>
              {i > 0 && <span className="fdot">·</span>}
              <span className="flabel">{c.label}</span>
              <span className="fnum tnum">{c.count}</span>
            </span>
          ))}
        </span>
      )}
      {f.refined != null && (
        <>
          <span className="farrow">→</span>
          <span className="fstage">
            初筛 <span className="fnum tnum">{f.refined}</span>
          </span>
        </>
      )}
      {f.shortlisted != null && (
        <>
          <span className="farrow">→</span>
          <span className="fstage">
            精选 <span className="fnum tnum">{f.shortlisted}</span>
          </span>
        </>
      )}
      {f.curated != null && (
        <>
          <span className="farrow">→</span>
          <span className="fstage">
            策展 <span className="fnum tnum">{f.curated}</span> 条
            {themes ? ` · 综合 ${themes} 主题` : ''}
          </span>
        </>
      )}
      {(genTime || f.byline) && (
        <span className="fby">
          {genTime ? `${genTime} ${f.tz || 'PT'}` : ''}
          {f.byline ? ` · ${f.byline}` : ''}
        </span>
      )}
    </div>
  );
}

export interface ReportViewProps {
  report: Report;
  type: 'daily' | 'weekly';
  onSelectType?: (t: 'daily' | 'weekly') => void;
  showToggle?: boolean;
  twoCol: boolean;
  chartStyle: ChartStyle;
  archive: ArchiveEntry[];
  onOpen: (id: string) => void;
  offline?: boolean;
}

export function ReportView({
  report,
  type,
  onSelectType,
  showToggle = false,
  twoCol,
  chartStyle,
  archive,
  onOpen,
  offline,
}: ReportViewProps) {
  const byId = useItemIndex(report);
  const periodLabel = report.type === 'weekly' ? report.date_range : report.date;
  // Show the authored wall-clock time (its own offset), not a UTC-shifted one:
  // `new Date(...).toISOString()` would normalize to UTC and display the wrong hour.
  const genTime = /T(\d{2}:\d{2})/.exec(report.generated_at)?.[1];
  const genLabel = genTime ? `${genTime} 生成` : report.generated_at;
  const meta = [
    { icon: 'calendar', text: report.type === 'weekly' ? periodLabel : '覆盖 ' + report.date },
    { icon: 'clock', text: genLabel },
    { text: `report.json · ${report.type}` },
  ];

  const emailHref = `/api/reports/${report.report_id}/email`;

  return (
    <div className="wrap">
      {showToggle && (
        <div style={{ paddingTop: 24, display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          <div className="seg">
            <button className={type === 'daily' ? 'on' : ''} onClick={() => onSelectType?.('daily')}>
              <span className="dot" />日报
            </button>
            <button className={type === 'weekly' ? 'on' : ''} onClick={() => onSelectType?.('weekly')}>
              <span className="dot" />周报
            </button>
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--fg-tertiary)' }}>
            最新一期 · {periodLabel}
          </span>
          {offline && (
            <span className="offline-note">
              <Icon name="layers" size={13} />
              离线 · 内置 fixtures
            </span>
          )}
        </div>
      )}

      <ReportHeader
        kicker="Network Intel · 内部洞察情报"
        title={report.title || (report.type === 'weekly' ? periodLabel + ' · 周报' : report.date + ' · 日报')}
        meta={meta}
        actions={
          <>
            <a className="btn-ghost" href={emailHref} target="_blank" rel="noopener noreferrer">
              <Icon name="mail" size={15} />邮件版
            </a>
            <button className="btn-ghost" onClick={() => window.print()}>
              <Icon name="download" size={15} />导出
            </button>
          </>
        }
      />

      <FunnelBar report={report} />

      <Lead report={report} />

      <div className={'home-grid' + (twoCol ? ' two' : '')} style={{ marginTop: 8 }}>
        {twoCol && <ReportAside report={report} archive={archive} onOpen={onOpen} />}
        <div>
          {report.type === 'weekly' && report.strategy && <StrategyBlock strategy={report.strategy} />}
          <ReportBody report={report} byId={byId} chartStyle={chartStyle} />
          <References refs={report.references} />
        </div>
      </div>
    </div>
  );
}

export { SPECIAL_SECTIONS };
