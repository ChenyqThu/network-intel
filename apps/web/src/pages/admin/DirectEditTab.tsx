/* Structured direct editing: lead · strategy (incl. body/paras) · insights ·
   items, plus the entry point to add real items from the intel pool. */
import type { Insight, IntelItem, Report } from '../../types';
import { SUBJECT_LABEL, SUBJECTS } from './constants';
import { InsightEditor } from './InsightEditor';
import { ItemEditor } from './ItemEditor';

export function DirectEditTab({
  doc,
  onPatch,
  onOpenPool,
}: {
  doc: Report;
  onPatch: (next: Report, coalesce?: boolean) => void;
  onOpenPool: () => void;
}) {
  const patchItem = (i: number, patch: Partial<IntelItem>, coalesce?: boolean) => {
    const items = doc.items.map((it, j) => (j === i ? { ...it, ...patch } : it));
    onPatch({ ...doc, items }, coalesce);
  };
  const deleteItem = (i: number) =>
    onPatch({ ...doc, items: doc.items.filter((_, j) => j !== i) });
  const moveItem = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= doc.items.length) return;
    const items = [...doc.items];
    [items[i], items[j]] = [items[j], items[i]];
    onPatch({ ...doc, items });
  };

  const insights = doc.insights ?? [];
  const patchInsight = (id: string, patch: Partial<Insight>, coalesce?: boolean) =>
    onPatch(
      { ...doc, insights: insights.map((ins) => (ins.id === id ? { ...ins, ...patch } : ins)) },
      coalesce,
    );
  const deleteInsight = (id: string) =>
    onPatch({ ...doc, insights: insights.filter((ins) => ins.id !== id) });

  const patchStrategyPara = (k: number, slot: 0 | 1, value: string) => {
    if (!doc.strategy) return;
    const paras = (doc.strategy.paras ?? []).map((p, i) => {
      if (i !== k) return p;
      const next: [string, string] = [p[0], p[1]];
      next[slot] = value;
      return next;
    });
    onPatch({ ...doc, strategy: { ...doc.strategy, paras } }, true);
  };

  return (
    <div className="admin-edit">
      <label className="admin-label">导语 lead</label>
      <textarea
        className="admin-textarea"
        rows={4}
        value={doc.lead?.text ?? ''}
        onChange={(e) => onPatch({ ...doc, lead: { ...doc.lead, text: e.target.value } }, true)}
      />
      <input
        className="admin-input"
        placeholder="加粗结论 strong"
        value={doc.lead?.strong ?? ''}
        onChange={(e) => onPatch({ ...doc, lead: { ...doc.lead, strong: e.target.value } }, true)}
      />

      {doc.strategy && (
        <>
          <label className="admin-label">策略 strategy</label>
          <input
            className="admin-input"
            placeholder="标题 title"
            value={doc.strategy.title ?? ''}
            onChange={(e) => onPatch({ ...doc, strategy: { ...doc.strategy!, title: e.target.value } }, true)}
          />
          {(doc.strategy.paras ?? []).map((p, k) => (
            <div key={k} className="admin-para">
              <input
                className="admin-input admin-para-head"
                placeholder={`段落${k + 1} 小标题`}
                value={p[0] ?? ''}
                onChange={(e) => patchStrategyPara(k, 0, e.target.value)}
              />
              <textarea
                className="admin-textarea"
                rows={3}
                placeholder={`段落${k + 1} 正文`}
                value={p[1] ?? ''}
                onChange={(e) => patchStrategyPara(k, 1, e.target.value)}
              />
            </div>
          ))}
          {doc.strategy.body != null && doc.strategy.body !== '' && (
            <textarea
              className="admin-textarea"
              rows={4}
              placeholder="正文 body"
              value={doc.strategy.body}
              onChange={(e) => onPatch({ ...doc, strategy: { ...doc.strategy!, body: e.target.value } }, true)}
            />
          )}
        </>
      )}

      {insights.length > 0 && (
        <>
          <label className="admin-label">洞察 insights（{insights.length}）· 报告主体</label>
          <div className="admin-hint">
            删除洞察后，仅被它引用的条目会在保存时被引擎一并剔除（可用左下「撤销」恢复）。
          </div>
          {SUBJECTS.map((subj) => {
            const group = insights.filter((ins) => ins.subject === subj);
            if (!group.length) return null;
            return (
              <div key={subj}>
                <div className="admin-group-head">{SUBJECT_LABEL[subj]}</div>
                {group.map((ins) => (
                  <InsightEditor
                    key={ins.id}
                    insight={ins}
                    index={insights.indexOf(ins)}
                    onChange={(patch, c) => patchInsight(ins.id, patch, c)}
                    onDelete={() => deleteInsight(ins.id)}
                  />
                ))}
              </div>
            );
          })}
        </>
      )}

      <label className="admin-label">条目（{doc.items.length}）· 可改写 / 删除 / 重排</label>
      {doc.items.map((it, i) => (
        <ItemEditor
          key={it.id ?? i}
          item={it}
          index={i}
          total={doc.items.length}
          onChange={(patch, c) => patchItem(i, patch, c)}
          onDelete={() => deleteItem(i)}
          onMove={(dir) => moveItem(i, dir)}
        />
      ))}
      <button className="admin-btn" onClick={onOpenPool}>＋ 从素材池添加条目</button>
      <div className="admin-hint">素材池里都是真实采集的信号——新增条目永远来自这里，不凭空编造链接。</div>
    </div>
  );
}
