/* Console header: brand · pending/published selector with metadata · refresh · logout. */
import { Icon } from '../../components/Icon';
import type { PendingEntry } from '../../api/admin';

export type SelKind = 'pending' | 'published';
export interface Sel {
  kind: SelKind;
  id: string;
}

const fmtEntry = (p: PendingEntry) =>
  `${p.type === 'weekly' ? '周报' : '日报'} · ${p.date} · ${p.title ?? p.id}（${p.item_count} 条）`;

export function AdminHeader({
  pending,
  published,
  sel,
  onSelect,
  onRefresh,
  onLogout,
  onSettings,
}: {
  pending: PendingEntry[];
  published: PendingEntry[];
  sel: Sel | null;
  onSelect: (sel: Sel) => void;
  onRefresh: () => void;
  onLogout: () => void;
  onSettings: () => void;
}) {
  return (
    <header className="admin-top">
      <div className="admin-brand"><Icon name="inbox" size={18} /> Network Intel · 审核台</div>
      <select
        className="admin-select admin-report-select"
        value={sel ? `${sel.kind}:${sel.id}` : ''}
        onChange={(e) => {
          const v = e.target.value;
          if (!v) return;
          const i = v.indexOf(':');
          onSelect({ kind: v.slice(0, i) as SelKind, id: v.slice(i + 1) });
        }}
      >
        {pending.length === 0 && published.length === 0 && <option value="">（没有报告）</option>}
        {pending.length > 0 && (
          <optgroup label={`待审（${pending.length}）`}>
            {pending.map((p) => (
              <option key={p.id} value={`pending:${p.id}`}>{fmtEntry(p)}</option>
            ))}
          </optgroup>
        )}
        {published.length > 0 && (
          <optgroup label={`已发布（${published.length}）`}>
            {published.map((p) => (
              <option key={p.id} value={`published:${p.id}`}>{fmtEntry(p)}</option>
            ))}
          </optgroup>
        )}
      </select>
      <span className="admin-spacer" />
      <button className="admin-icon" title="刷新列表" onClick={onRefresh}>↻</button>
      <button className="admin-btn" onClick={onSettings}>邮件设置</button>
      <button className="admin-btn" onClick={onLogout}>退出</button>
    </header>
  );
}
