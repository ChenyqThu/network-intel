/* Direct-edit form row for a single intel item. */
import type { Impact, IntelItem, Subject } from '../../types';
import { IMPACTS, SUBJECTS } from './constants';

export function ItemEditor({
  item,
  index,
  total,
  onChange,
  onDelete,
  onMove,
}: {
  item: IntelItem;
  index: number;
  total: number;
  onChange: (patch: Partial<IntelItem>, coalesce?: boolean) => void;
  onDelete: () => void;
  onMove: (dir: -1 | 1) => void;
}) {
  const subj = (item.subject ?? 'competitor') as Subject;
  return (
    <div className="admin-item">
      <div className="admin-item-top">
        <span className="chip">{index + 1}</span>
        <input
          className="admin-input admin-item-title"
          value={item.title ?? ''}
          onChange={(e) => onChange({ title: e.target.value }, true)}
        />
        <button className="admin-icon" title="上移" disabled={index === 0} onClick={() => onMove(-1)}>↑</button>
        <button className="admin-icon" title="下移" disabled={index === total - 1} onClick={() => onMove(1)}>↓</button>
        <button className="admin-icon admin-danger" title="删除" onClick={onDelete}>✕</button>
      </div>
      <div className="admin-item-row">
        <select
          className="admin-select"
          value={subj}
          onChange={(e) =>
            onChange({
              subject: e.target.value as Subject,
              omada_impact: IMPACTS[e.target.value as Subject][0],
            })
          }
        >
          {SUBJECTS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          className="admin-select"
          value={item.omada_impact ?? 'unknown'}
          onChange={(e) => onChange({ omada_impact: e.target.value as Impact })}
        >
          {IMPACTS[subj].map((i) => <option key={i} value={i}>{i}</option>)}
        </select>
        <a className="admin-item-url" href={item.url} target="_blank" rel="noopener noreferrer">源 ↗</a>
      </div>
      <textarea
        className="admin-textarea"
        rows={2}
        placeholder="摘要 summary"
        value={item.summary ?? ''}
        onChange={(e) => onChange({ summary: e.target.value }, true)}
      />
      <textarea
        className="admin-textarea"
        rows={2}
        placeholder="研判 impact_note"
        value={item.impact_note ?? ''}
        onChange={(e) => onChange({ impact_note: e.target.value }, true)}
      />
    </div>
  );
}
