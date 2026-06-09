/* Drawer for adding real ingested items (intel_items pool) to the report.
   For synthesized reports the new item must be cited by an insight, or the
   engine prunes it on save — so the target insight is chosen up front. */
import { useEffect, useState } from 'react';
import { itemDraft, itemsPool, type PoolItem } from '../../api/admin';
import type { IntelItem, Report, Subject } from '../../types';
import { SUBJECT_LABEL, SUBJECTS } from './constants';
import { useToast } from './Toast';

export function ItemPoolDrawer({
  open,
  doc,
  onClose,
  onAdd,
}: {
  open: boolean;
  doc: Report;
  onClose: () => void;
  onAdd: (item: IntelItem, insightId: string | null) => void;
}) {
  const toast = useToast();
  const [q, setQ] = useState('');
  const [days, setDays] = useState(14);
  const [subject, setSubject] = useState<Subject | ''>('');
  const [rows, setRows] = useState<PoolItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyHash, setBusyHash] = useState<string | null>(null);
  const insights = doc.insights ?? [];
  const [insightId, setInsightId] = useState<string>(insights[0]?.id ?? '');

  useEffect(() => {
    if (!open) return;
    setInsightId((cur) => (insights.some((i) => i.id === cur) ? cur : insights[0]?.id ?? ''));
    const t = window.setTimeout(() => {
      setLoading(true);
      itemsPool({ q: q.trim() || undefined, days, subject })
        .then(setRows)
        .catch((e) => toast('err', '素材池加载失败：' + (e as Error).message))
        .finally(() => setLoading(false));
    }, 300);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, q, days, subject]);

  if (!open) return null;
  const inDoc = new Set(doc.items.map((it) => it.url));

  const add = async (row: PoolItem) => {
    setBusyHash(row.content_hash);
    try {
      const draft = await itemDraft(row.content_hash);
      onAdd(draft, insights.length ? insightId || null : null);
    } catch (e) {
      toast('err', '添加失败：' + (e as Error).message);
    } finally {
      setBusyHash(null);
    }
  };

  return (
    <div className="admin-drawer-mask" onClick={onClose}>
      <div className="admin-drawer panel" onClick={(e) => e.stopPropagation()}>
        <div className="admin-drawer-head">
          <span>素材池 · 真实采集信号</span>
          <button className="admin-icon" title="关闭" onClick={onClose}>✕</button>
        </div>

        <div className="admin-drawer-filters">
          <input
            className="admin-input"
            placeholder="搜索标题…"
            value={q}
            autoFocus
            onChange={(e) => setQ(e.target.value)}
          />
          <select className="admin-select" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>近 7 天</option>
            <option value={14}>近 14 天</option>
            <option value={30}>近 30 天</option>
          </select>
          <select className="admin-select" value={subject} onChange={(e) => setSubject(e.target.value as Subject | '')}>
            <option value="">全部主体</option>
            {SUBJECTS.map((s) => <option key={s} value={s}>{SUBJECT_LABEL[s]}</option>)}
          </select>
        </div>

        {insights.length > 0 && (
          <div className="admin-drawer-target">
            <span className="admin-label">引用到洞察</span>
            <select className="admin-select" value={insightId} onChange={(e) => setInsightId(e.target.value)}>
              {insights.map((ins) => <option key={ins.id} value={ins.id}>{ins.title}</option>)}
            </select>
            <div className="admin-hint">合成报告里未被洞察引用的条目会在保存时被剔除，所以新条目会自动挂到所选洞察的引用上。</div>
          </div>
        )}

        <div className="admin-drawer-list">
          {loading && <div className="admin-hint">加载中…</div>}
          {!loading && rows.length === 0 && <div className="admin-hint">没有匹配的素材。</div>}
          {rows.map((row) => {
            const exists = inDoc.has(row.url);
            return (
              <div key={row.content_hash} className={'admin-pool-row' + (exists ? ' exists' : '')}>
                <div className="admin-pool-main">
                  <a href={row.url} target="_blank" rel="noopener noreferrer" className="admin-pool-title">
                    {row.title}
                  </a>
                  <div className="admin-pool-meta">
                    {row.source} · {row.date} · {SUBJECT_LABEL[row.subject] ?? row.subject}
                    {row.last_heat > 0 && <> · 热度 {Math.round(row.last_heat)}</>}
                    {row.report_count > 0 && <> · 已报 {row.report_count} 次</>}
                  </div>
                </div>
                <button
                  className="admin-btn"
                  disabled={exists || busyHash === row.content_hash}
                  onClick={() => add(row)}
                >
                  {exists ? '已在报告' : busyHash === row.content_hash ? '添加中…' : '添加'}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
