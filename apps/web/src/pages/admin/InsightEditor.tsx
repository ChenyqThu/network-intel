/* Direct-edit card for one synthesized insight (the report's main body).
   Cite handling ({{cite:N}} markers / cite_refs) stays server-side — the
   engine renumbers and prunes on save. */
import type { Insight } from '../../types';

export function InsightEditor({
  insight,
  index,
  onChange,
  onDelete,
}: {
  insight: Insight;
  index: number;
  onChange: (patch: Partial<Insight>, coalesce?: boolean) => void;
  onDelete: () => void;
}) {
  return (
    <div className="admin-item admin-insight-edit">
      <div className="admin-item-top">
        <span className="chip">{index + 1}</span>
        <input
          className="admin-input admin-item-title"
          value={insight.title ?? ''}
          onChange={(e) => onChange({ title: e.target.value }, true)}
        />
        <button className="admin-icon admin-danger" title="删除整条洞察" onClick={onDelete}>✕</button>
      </div>
      <textarea
        className="admin-textarea"
        rows={5}
        placeholder="洞察正文（请保留 {{cite:N}} 引用标记，引擎会自动重排编号）"
        value={insight.body ?? ''}
        onChange={(e) => onChange({ body: e.target.value }, true)}
      />
      <textarea
        className="admin-textarea"
        rows={2}
        placeholder="💡 takeaway（可留空）"
        value={insight.takeaway ?? ''}
        onChange={(e) => onChange({ takeaway: e.target.value }, true)}
      />
    </div>
  );
}
