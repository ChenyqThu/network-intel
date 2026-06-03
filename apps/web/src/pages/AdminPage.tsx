/* ============================================================
   Admin review console (/admin) — password-gated.
   Review pending reports · edit directly OR via LLM chat with a
   live preview · publish / reject. Reuses the Dossier design
   tokens + the public ReportView for the preview.
   ============================================================ */
import { useEffect, useState } from 'react';
import { ReportView } from '../components/ReportView';
import { Icon } from '../components/Icon';
import type { Report, IntelItem, Subject, Impact } from '../types';
import {
  AdminAuthError,
  getToken,
  setToken,
  login,
  listPending,
  getPending,
  savePending,
  llmEdit,
  publishPending,
  rejectPending,
  type PendingEntry,
} from '../api/admin';

const SUBJECTS: Subject[] = ['omada_self', 'competitor', 'industry'];
const IMPACTS: Record<Subject, Impact[]> = {
  omada_self: ['needs_fix', 'feature_input', 'strength_confirm', 'unknown'],
  competitor: ['threat', 'opportunity', 'neutral', 'unknown'],
  industry: ['opportunity', 'neutral', 'unknown'],
};

type ChatMsg = { role: 'you' | 'ai'; text: string };

/* ---------- login ---------- */
function LoginGate({ onAuthed }: { onAuthed: () => void }) {
  const [pw, setPw] = useState('');
  const [err, setErr] = useState(false);
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(false);
    const ok = await login(pw).catch(() => false);
    setBusy(false);
    if (ok) onAuthed();
    else setErr(true);
  };
  return (
    <div className="admin-login">
      <form className="panel admin-login-card" onSubmit={submit}>
        <div className="admin-login-title">
          <Icon name="inbox" size={18} /> 审核台登录
        </div>
        <input
          className="admin-input"
          type="password"
          placeholder="密码"
          value={pw}
          autoFocus
          onChange={(e) => setPw(e.target.value)}
        />
        {err && <div className="admin-err">密码错误</div>}
        <button className="admin-btn admin-btn-primary" disabled={busy || !pw}>
          {busy ? '验证中…' : '进入'}
        </button>
      </form>
    </div>
  );
}

/* ---------- direct-edit: a single item row ---------- */
function ItemEditor({
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
  onChange: (patch: Partial<IntelItem>) => void;
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
          onChange={(e) => onChange({ title: e.target.value })}
        />
        <button className="admin-icon" title="上移" disabled={index === 0} onClick={() => onMove(-1)}>↑</button>
        <button className="admin-icon" title="下移" disabled={index === total - 1} onClick={() => onMove(1)}>↓</button>
        <button className="admin-icon admin-danger" title="删除" onClick={onDelete}>✕</button>
      </div>
      <div className="admin-item-row">
        <select className="admin-select" value={subj} onChange={(e) => onChange({ subject: e.target.value as Subject, omada_impact: IMPACTS[e.target.value as Subject][0] })}>
          {SUBJECTS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select className="admin-select" value={item.omada_impact ?? 'unknown'} onChange={(e) => onChange({ omada_impact: e.target.value as Impact })}>
          {IMPACTS[subj].map((i) => <option key={i} value={i}>{i}</option>)}
        </select>
        <a className="admin-item-url" href={item.url} target="_blank" rel="noopener noreferrer">源 ↗</a>
      </div>
      <textarea className="admin-textarea" rows={2} placeholder="摘要 summary" value={item.summary ?? ''} onChange={(e) => onChange({ summary: e.target.value })} />
      <textarea className="admin-textarea" rows={2} placeholder="研判 impact_note" value={item.impact_note ?? ''} onChange={(e) => onChange({ impact_note: e.target.value })} />
    </div>
  );
}

/* ---------- the editor rail ---------- */
function EditorRail({
  doc,
  setDoc,
  reportId,
  onSaved,
  onPublished,
  onRejected,
}: {
  doc: Report;
  setDoc: (d: Report) => void;
  reportId: string;
  onSaved: (d: Report) => void;
  onPublished: () => void;
  onRejected: () => void;
}) {
  const [tab, setTab] = useState<'ai' | 'edit'>('ai');
  const [chat, setChat] = useState<ChatMsg[]>([]);
  const [instr, setInstr] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const patchItem = (i: number, patch: Partial<IntelItem>) => {
    const items = doc.items.map((it, j) => (j === i ? { ...it, ...patch } : it));
    setDoc({ ...doc, items });
  };
  const deleteItem = (i: number) => setDoc({ ...doc, items: doc.items.filter((_, j) => j !== i) });
  const moveItem = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= doc.items.length) return;
    const items = [...doc.items];
    [items[i], items[j]] = [items[j], items[i]];
    setDoc({ ...doc, items });
  };

  const sendInstr = async () => {
    const text = instr.trim();
    if (!text) return;
    setChat((c) => [...c, { role: 'you', text }]);
    setInstr('');
    setBusy('ai');
    setStatus(null);
    try {
      const revised = await llmEdit(reportId, text);
      setDoc(revised);
      setChat((c) => [...c, { role: 'ai', text: '已按指令改稿，左侧为预览（未保存）。满意请点“保存草稿”。' }]);
    } catch (e) {
      setChat((c) => [...c, { role: 'ai', text: '改稿失败：' + (e as Error).message }]);
    } finally {
      setBusy(null);
    }
  };

  const doSave = async () => {
    setBusy('save');
    setStatus(null);
    try {
      const saved = await savePending(reportId, doc);
      onSaved(saved);
      setStatus('已保存草稿');
    } catch (e) {
      setStatus('保存失败：' + (e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const doPublish = async () => {
    if (!window.confirm('发布后将对外可见，确认发布？')) return;
    setBusy('publish');
    setStatus(null);
    try {
      await savePending(reportId, doc); // persist latest edits first
      await publishPending(reportId);
      onPublished();
    } catch (e) {
      setStatus('发布失败：' + (e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const doReject = async () => {
    if (!window.confirm('退回将丢弃这份待审报告，确认？')) return;
    setBusy('reject');
    try {
      await rejectPending(reportId);
      onRejected();
    } catch (e) {
      setStatus('退回失败：' + (e as Error).message);
      setBusy(null);
    }
  };

  return (
    <aside className="admin-rail panel">
      <div className="admin-tabs">
        <button className={'admin-tab' + (tab === 'ai' ? ' on' : '')} onClick={() => setTab('ai')}>AI 改稿</button>
        <button className={'admin-tab' + (tab === 'edit' ? ' on' : '')} onClick={() => setTab('edit')}>直接编辑</button>
      </div>

      {tab === 'ai' && (
        <div className="admin-chat">
          <div className="admin-chat-log">
            {chat.length === 0 && (
              <div className="admin-hint">
                用自然语言改稿，左侧实时预览。例如：<br />
                “把导语改犀利点”、“删掉第 3 条”、“强调安全角度”、“按重要性重排竞品”。
              </div>
            )}
            {chat.map((m, i) => (
              <div key={i} className={'admin-msg ' + m.role}>{m.text}</div>
            ))}
            {busy === 'ai' && <div className="admin-msg ai">改稿中…</div>}
          </div>
          <div className="admin-chat-input">
            <textarea
              className="admin-textarea"
              rows={2}
              placeholder="输入改稿指令…"
              value={instr}
              disabled={busy === 'ai'}
              onChange={(e) => setInstr(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) sendInstr(); }}
            />
            <button className="admin-btn admin-btn-primary" disabled={busy === 'ai' || !instr.trim()} onClick={sendInstr}>
              发送 ⌘↵
            </button>
          </div>
        </div>
      )}

      {tab === 'edit' && (
        <div className="admin-edit">
          <label className="admin-label">导语 lead</label>
          <textarea className="admin-textarea" rows={4} value={doc.lead?.text ?? ''} onChange={(e) => setDoc({ ...doc, lead: { ...doc.lead, text: e.target.value } })} />
          <input className="admin-input" placeholder="加粗结论 strong" value={doc.lead?.strong ?? ''} onChange={(e) => setDoc({ ...doc, lead: { ...doc.lead, strong: e.target.value } })} />
          {doc.strategy && (
            <>
              <label className="admin-label">策略标题 strategy.title</label>
              <input className="admin-input" value={doc.strategy.title ?? ''} onChange={(e) => setDoc({ ...doc, strategy: { ...doc.strategy!, title: e.target.value } })} />
            </>
          )}
          <label className="admin-label">条目（{doc.items.length}）· 可改写 / 删除 / 重排</label>
          {doc.items.map((it, i) => (
            <ItemEditor
              key={it.id ?? i}
              item={it}
              index={i}
              total={doc.items.length}
              onChange={(patch) => patchItem(i, patch)}
              onDelete={() => deleteItem(i)}
              onMove={(dir) => moveItem(i, dir)}
            />
          ))}
          <div className="admin-hint">新增条目需真实链接，请用 LLM 改稿或后续从源池添加（不凭空编造链接）。</div>
        </div>
      )}

      <div className="admin-actions">
        {status && <div className="admin-status">{status}</div>}
        <button className="admin-btn" disabled={!!busy} onClick={doSave}>{busy === 'save' ? '保存中…' : '保存草稿'}</button>
        <button className="admin-btn admin-btn-primary" disabled={!!busy} onClick={doPublish}>{busy === 'publish' ? '发布中…' : '发布'}</button>
        <button className="admin-btn admin-danger" disabled={!!busy} onClick={doReject}>退回</button>
      </div>
    </aside>
  );
}

/* ---------- page ---------- */
export function AdminPage() {
  const [authed, setAuthed] = useState(!!getToken());
  const [pending, setPending] = useState<PendingEntry[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [doc, setDoc] = useState<Report | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const list = await listPending();
      setPending(list);
      if (list.length && !list.some((p) => p.id === selected)) {
        setSelected(list[0].id);
      } else if (!list.length) {
        setSelected(null);
        setDoc(null);
      }
    } catch (e) {
      if (e instanceof AdminAuthError) setAuthed(false);
      else setErr((e as Error).message);
    }
  };

  useEffect(() => { if (authed) refresh(); /* eslint-disable-next-line */ }, [authed]);
  useEffect(() => {
    if (!selected) { setDoc(null); return; }
    getPending(selected).then(setDoc).catch((e) => {
      if (e instanceof AdminAuthError) setAuthed(false);
      else setErr((e as Error).message);
    });
  }, [selected]);

  if (!authed) return <LoginGate onAuthed={() => setAuthed(true)} />;

  return (
    <div className="admin-shell">
      <header className="admin-top">
        <div className="admin-brand"><Icon name="inbox" size={18} /> Network Intel · 审核台</div>
        <select className="admin-select" value={selected ?? ''} onChange={(e) => setSelected(e.target.value)}>
          {pending.length === 0 && <option value="">（无待审报告）</option>}
          {pending.map((p) => (
            <option key={p.id} value={p.id}>{p.id} · {p.item_count} 条</option>
          ))}
        </select>
        <span className="admin-spacer" />
        <button className="admin-icon" title="刷新" onClick={refresh}>↻</button>
        <button className="admin-btn" onClick={() => { setToken(null); setAuthed(false); }}>退出</button>
      </header>

      {err && <div className="admin-err">{err}</div>}

      {!doc && <div className="admin-empty">没有待审报告。周报会在每周定时生成后进入这里等待审核。</div>}

      {doc && (
        <div className="admin-body">
          <main className="admin-preview">
            <div className="admin-preview-tag">实时预览</div>
            <ReportView report={doc} type={doc.type} twoCol={false} chartStyle="minimal" archive={[]} onOpen={() => {}} />
          </main>
          <EditorRail
            doc={doc}
            setDoc={setDoc}
            reportId={selected!}
            onSaved={(d) => setDoc(d)}
            onPublished={() => { setDoc(null); refresh(); }}
            onRejected={() => { setDoc(null); refresh(); }}
          />
        </div>
      )}
    </div>
  );
}
