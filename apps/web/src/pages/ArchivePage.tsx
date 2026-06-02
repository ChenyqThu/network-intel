/* ============================================================
   Archive — history list with search + type chips (日报/周报) +
   theme chips (omada_self/competitor/sentiment/industry/pricing).
   Click a row -> opens the matching report cadence.
   ============================================================ */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../components/Icon';
import { ReportHeader } from '../components/ReportParts';
import { useAsync } from '../lib/useAsync';
import { fetchArchive } from '../api/client';
import type { ReportType, ArchiveTheme } from '../types';

function Chip({
  on,
  onClick,
  children,
}: {
  on: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button className={'chip' + (on ? ' on' : '')} onClick={onClick}>
      {children}
      {on && <Icon name="x" size={12} />}
    </button>
  );
}

const THEMES: [ArchiveTheme, string][] = [
  ['omada_self', '自家'],
  ['competitor', '竞品'],
  ['sentiment', '舆情'],
  ['industry', '行业'],
  ['pricing', '定价'],
  ['new_product', '新品'],
];

export function ArchivePage() {
  const navigate = useNavigate();
  const { data, loading } = useAsync(() => fetchArchive(), []);
  const [q, setQ] = useState('');
  const [type, setType] = useState<ReportType | 'all'>('all');
  const [theme, setTheme] = useState<ArchiveTheme | 'all'>('all');

  const all = data || [];
  const list = all.filter((a) => {
    if (type !== 'all' && a.type !== type) return false;
    if (theme !== 'all' && !a.themes.includes(theme)) return false;
    if (q && !(a.title + a.excerpt).toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });

  const fmtD = (d: string) => {
    const [y, m, da] = d.split('-');
    return { top: `${m}/${da}`, yr: y };
  };

  const open = (t: ReportType) => navigate(t === 'weekly' ? '/weekly' : '/daily');

  return (
    <div className="wrap">
      <ReportHeader
        kicker="Network Intel · 归档"
        title="历史报告检索"
        meta={[
          { icon: 'doc', text: `${all.length} 期报告` },
          { icon: 'calendar', text: '2026-05-17 至今' },
        ]}
      />
      <div className="filters">
        <label className="search">
          <Icon name="search" size={16} />
          <input
            placeholder="搜索报告标题、摘要…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </label>
        <div className="chipset">
          <Chip on={type === 'daily'} onClick={() => setType(type === 'daily' ? 'all' : 'daily')}>
            日报
          </Chip>
          <Chip on={type === 'weekly'} onClick={() => setType(type === 'weekly' ? 'all' : 'weekly')}>
            周报
          </Chip>
          <span className="chip-div" />
          {THEMES.map(([k, l]) => (
            <Chip key={k} on={theme === k} onClick={() => setTheme(theme === k ? 'all' : k)}>
              {l}
            </Chip>
          ))}
        </div>
      </div>
      <div className="arch-list">
        {loading && (
          <div className="state-msg">
            <span className="spinner" />
            加载归档…
          </div>
        )}
        {!loading &&
          list.map((a) => {
            const d = fmtD(a.date);
            return (
              <div className="arch-row" key={a.id} onClick={() => open(a.type)}>
                <div className="arch-date tnum">
                  {d.top}
                  <span className="yr">{d.yr}</span>
                </div>
                <div className="arch-main">
                  <h3>
                    <span className={'type-badge ' + a.type}>
                      {a.type === 'weekly' ? '周报' : '日报'}
                    </span>
                    <span className="axt">{a.title}</span>
                  </h3>
                  <p className="ax">{a.excerpt}</p>
                </div>
                <div className="arch-stats">
                  <div className="arch-stat">
                    <div className="v tnum">{a.signals}</div>
                    <div className="l">信号</div>
                  </div>
                  <div className="arch-stat">
                    <div className="v tnum" style={{ color: a.threats ? 'var(--threat)' : 'var(--fg-faint)' }}>
                      {a.threats}
                    </div>
                    <div className="l">威胁</div>
                  </div>
                  <div className="arch-stat">
                    <div className="v tnum" style={{ color: a.opps ? 'var(--opp)' : 'var(--fg-faint)' }}>
                      {a.opps}
                    </div>
                    <div className="l">机会</div>
                  </div>
                </div>
              </div>
            );
          })}
        {!loading && !list.length && (
          <div style={{ padding: '50px 0', textAlign: 'center', color: 'var(--fg-tertiary)' }}>
            没有匹配的报告，试试调整筛选条件。
          </div>
        )}
      </div>
    </div>
  );
}
