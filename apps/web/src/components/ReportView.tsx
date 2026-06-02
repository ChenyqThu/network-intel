/* ============================================================
   ReportView — renders a daily/weekly report from the contract.
   Lead + (weekly) StrategyBlock + section sheets + store table +
   analytics dashboard + References, with a sticky per-report TOC.
   ============================================================ */
import { useMemo } from 'react';
import { Icon } from './Icon';
import { IntelEntry } from './IntelEntry';
import {
  Lead,
  SectionHead,
  References,
  ReportHeader,
  StrategyBlock,
  EmptyState,
} from './ReportParts';
import { Donut, SourceBars, TrendLine, KpiCard, SOURCE_COLORS } from './Charts';
import type { ChartStyle } from './Charts';
import { categoryLabel, sourceDisplayLabel, fmtNum } from '../lib/intel';
import { jumpTo } from '../lib/jump';
import type {
  Report,
  Section,
  IntelItem,
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

/* ---- store table (weekly) ---- */
function StoreSection({ report, num }: { report: Report; num: string }) {
  const rows = report.store || [];
  return (
    <section className="sec" id="sec-store">
      <SectionHead icon="store" num={num} title="Store 动向" desc="价格 / 库存 / 上架变化" />
      <div className="sheet" style={{ padding: '8px 8px' }}>
        {rows.length ? (
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
            <TrendLine series={db.sentimentTrend} style={chartStyle} />
          </div>
          <div className="panel">
            <div className="panel-head">
              <h3>高频痛点 Top 5</h3>
              <span className="sub">UniFi 社区 · 本周</span>
            </div>
            <div className="pain">
              {db.pains.map((p, i) => (
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
          </div>
        </div>
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="panel-head">
            <h3>Omada vs UniFi · 本周正面口碑</h3>
            <span className="sub">环比上周</span>
          </div>
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
        </div>
      </section>

      {/* KPI grid + source contribution + heat ranking */}
      <section className="sec" id="sec-dashboard">
        <SectionHead icon="barChart" num={String(Number(num) + 1)} title="数据看板" desc="信号量 / 各源贡献 / 热度 Top" tone="industry" />
        <div className="kpi-grid">
          <KpiCard label="本周信号量" icon="zap" value={db.signals} deltaText={`${db.signalsDelta > 0 ? '+' : ''}${db.signalsDelta} 环比`} dir={db.signalsDelta > 0 ? 'up' : db.signalsDelta < 0 ? 'down' : 'flat'} />
          <KpiCard label="威胁 / 机会" icon="swords" value={`${db.threats}/${db.opps}`} deltaText={`${db.neutral} 中性`} dir="flat" />
          <KpiCard label="新竞品动作" icon="sparkle" value={db.newCompetitor} deltaText={`${db.newCompetitorDelta > 0 ? '+' : ''}${db.newCompetitorDelta} 环比`} dir={db.newCompetitorDelta > 0 ? 'up' : db.newCompetitorDelta < 0 ? 'down' : 'flat'} />
          <KpiCard label="平均热度" icon="trendUp" value={db.avgHeat} deltaText={`${db.avgHeatDelta > 0 ? '+' : ''}${db.avgHeatDelta} 环比`} dir={db.avgHeatDelta > 0 ? 'up' : db.avgHeatDelta < 0 ? 'down' : 'flat'} />
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
      nav.push(['sec-' + s.key, s.title, String(s.items.length)]);
    }
  }
  nav.push(['refs', '参考来源', String(report.references.length)]);

  const recent = archive.filter((a) => a.id !== report.report_id).slice(0, 5);
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
          数据融合 · 双路
          <br />
          <b>来源 B</b> UNIFI_CHANNELS Supabase（一手官方）
          <br />
          <b>来源 A</b> 个人情报流 Reddit / YouTube
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
        <div className="hist">
          {recent.map((a) => (
            <div className="hist-row" key={a.id} onClick={() => onOpen(a.id)}>
              <span className="hl">{a.title.length > 15 ? a.title.slice(0, 15) + '…' : a.title}</span>
              <span className="ht">{a.type === 'weekly' ? '周' : '日'}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
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
        kicker="Network Intel · 内部竞品情报"
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
