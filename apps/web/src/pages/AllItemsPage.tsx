/* ============================================================
   All Items — flat, time-grouped stream of every intel item with
   filters: subject, source tier, impact, and search.
   ============================================================ */
import { Fragment, useState } from 'react';
import { Icon } from '../components/Icon';
import { IntelEntry } from '../components/IntelEntry';
import { ReportHeader } from '../components/ReportParts';
import { useAsync } from '../lib/useAsync';
import { fetchAllItems } from '../api/client';
import { impactClass } from '../lib/intel';
import type { ImpactClass } from '../lib/intel';
import type { Subject, Impact } from '../types';

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

const SUBJECTS: [Subject, string][] = [
  ['omada_self', '自家'],
  ['competitor', '竞品'],
  ['industry', '行业'],
];

const IMPACTS: [ImpactClass, string][] = [
  ['threat', '威胁'],
  ['opportunity', '机会'],
  ['neutral', '中性'],
  ['fix', '待修复'],
  ['feat', '功能需求'],
  ['strength', '优势确认'],
];

export function AllItemsPage() {
  const { data, loading } = useAsync(() => fetchAllItems(), []);
  const [q, setQ] = useState('');
  const [subject, setSubject] = useState<Subject | 'all'>('all');
  const [src, setSrc] = useState<'all' | 'official' | 'community'>('all');
  const [impact, setImpact] = useState<ImpactClass | 'all'>('all');

  const items = data || [];
  let list = items.filter((it) => {
    if (subject !== 'all' && it.subject !== subject) return false;
    if (src === 'official' && it.source_tier !== 'official') return false;
    if (src === 'community' && it.source_tier !== 'community') return false;
    if (impact !== 'all' && impactClass(it.omada_impact as Impact) !== impact) return false;
    if (q && !(it.title + it.summary).toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });
  list = [...list].sort(
    (a, b) => b.date.localeCompare(a.date) || a.id.localeCompare(b.id),
  );

  const groups: Record<string, typeof list> = {};
  for (const it of list) (groups[it.date] = groups[it.date] || []).push(it);
  const dayLabel = (d: string) => {
    const [, m, da] = d.split('-');
    return `${+m} 月 ${+da} 日`;
  };

  let n = 0;
  return (
    <div className="wrap">
      <ReportHeader
        kicker="Network Intel · 全部条目"
        title="情报条目流"
        meta={[
          { icon: 'inbox', text: `${items.length} 条条目` },
          { icon: 'filter', text: `${list.length} 条匹配` },
        ]}
      />
      <div className="filters">
        <label className="search">
          <Icon name="search" size={16} />
          <input placeholder="搜索标题、摘要…" value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        <div className="chipset">
          {SUBJECTS.map(([k, l]) => (
            <Chip key={k} on={subject === k} onClick={() => setSubject(subject === k ? 'all' : k)}>
              {l}
            </Chip>
          ))}
          <span className="chip-div" />
          <Chip on={src === 'official'} onClick={() => setSrc(src === 'official' ? 'all' : 'official')}>
            官方源
          </Chip>
          <Chip on={src === 'community'} onClick={() => setSrc(src === 'community' ? 'all' : 'community')}>
            社区源
          </Chip>
          <span className="chip-div" />
          {IMPACTS.map(([k, l]) => (
            <Chip key={k} on={impact === k} onClick={() => setImpact(impact === k ? 'all' : k)}>
              {l}
            </Chip>
          ))}
        </div>
      </div>
      <div style={{ marginTop: 8 }}>
        {loading && (
          <div className="state-msg">
            <span className="spinner" />
            加载条目…
          </div>
        )}
        {!loading &&
          Object.keys(groups)
            .sort((a, b) => b.localeCompare(a))
            .map((date) => (
              <Fragment key={date}>
                <div className="stream-day">{dayLabel(date)}</div>
                <div className="sheet">
                  {groups[date].map((it, i) => (
                    <IntelEntry key={it.id} item={it} idx={++n} delay={i * 35} />
                  ))}
                </div>
              </Fragment>
            ))}
        {!loading && !list.length && (
          <div style={{ padding: '50px 0', textAlign: 'center', color: 'var(--fg-tertiary)' }}>
            没有匹配的条目。
          </div>
        )}
      </div>
    </div>
  );
}
