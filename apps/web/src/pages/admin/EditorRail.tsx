/* Right rail: AI-revision tab + direct-edit tab + the action bar.
   Owns chat / revision / pool-drawer state so tab switches keep context. */
import { useEffect, useState } from 'react';
import { llmEdit, publishPending, rejectPending, savePending } from '../../api/admin';
import type { IntelItem, Report } from '../../types';
import { AiChatTab, type AcceptedRev, type ChatMsg, type PendingRev } from './AiChatTab';
import { useConfirm } from './ConfirmDialog';
import { diffReport } from './diff';
import { DirectEditTab } from './DirectEditTab';
import { ItemPoolDrawer } from './ItemPoolDrawer';
import { useToast } from './Toast';
import type { DocHistory } from './useDocHistory';

interface PendingRevState extends PendingRev {
  base: Report;
  revised: Report;
}

interface AcceptedRevState extends AcceptedRev {
  before: Report;
}

export function EditorRail({
  hist,
  reportId,
  onSaved,
  onPublished,
  onRejected,
}: {
  hist: DocHistory;
  reportId: string;
  onSaved: (saved: Report) => void;
  onPublished: () => void;
  onRejected: () => void;
}) {
  const toast = useToast();
  const confirm = useConfirm();
  const doc = hist.doc!;
  const [tab, setTab] = useState<'ai' | 'edit'>('ai');
  const [chat, setChat] = useState<ChatMsg[]>([]);
  const [busy, setBusy] = useState<'ai' | 'save' | 'publish' | 'reject' | null>(null);
  const [pendingRev, setPendingRev] = useState<PendingRevState | null>(null);
  const [revisions, setRevisions] = useState<AcceptedRevState[]>([]);
  const [poolOpen, setPoolOpen] = useState(false);

  // fresh report -> fresh conversation/revision context
  useEffect(() => {
    setChat([]);
    setPendingRev(null);
    setRevisions([]);
    setPoolOpen(false);
  }, [reportId]);

  const sendInstr = async (text: string) => {
    setChat((c) => [...c, { role: 'you', text }]);
    setBusy('ai');
    try {
      const revised = await llmEdit(reportId, text, doc);
      const changes = diffReport(doc, revised);
      setPendingRev({ instruction: text, base: doc, revised, changes });
      setChat((c) => [
        ...c,
        { role: 'ai', text: `已生成修订建议（${changes.length} 处变更），请查看 diff 后采纳或放弃。` },
      ]);
    } catch (e) {
      setChat((c) => [...c, { role: 'ai', text: '改稿失败：' + (e as Error).message }]);
      toast('err', '改稿失败：' + (e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const acceptRev = () => {
    if (!pendingRev) return;
    hist.update(pendingRev.revised);
    setRevisions((r) => [
      ...r,
      {
        instruction: pendingRev.instruction,
        at: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
        before: pendingRev.base,
      },
    ]);
    setPendingRev(null);
    toast('ok', '已采纳修订（左下「撤销」或修订历史可回退）');
  };

  const rollback = (idx: number) => {
    hist.update(revisions[idx].before);
    setRevisions((r) => r.slice(0, idx));
    setPendingRev(null);
    toast('ok', `已回退到第 ${idx + 1} 轮修订之前`);
  };

  const addPoolItem = (draft: IntelItem, insightId: string | null) => {
    const cite = Math.max(0, ...doc.items.map((i) => i.cite_id ?? 0)) + 1;
    const item: IntelItem = { ...draft, id: draft.id || `pool-${cite}`, cite_id: cite };
    let next: Report = { ...doc, items: [...doc.items, item] };
    if (insightId) {
      next = {
        ...next,
        insights: (next.insights ?? []).map((ins) =>
          ins.id === insightId
            ? { ...ins, cite_refs: [...(ins.cite_refs ?? []), cite] }
            : ins,
        ),
      };
    }
    hist.update(next);
    toast('ok', `已添加「${item.title}」${insightId ? '，并引用到所选洞察' : ''}`);
  };

  const doSave = async () => {
    if (busy) return;
    setBusy('save');
    try {
      const saved = await savePending(reportId, doc);
      onSaved(saved);
      toast('ok', '已保存草稿');
    } catch (e) {
      toast('err', '保存失败：' + (e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const doPublish = async () => {
    if (!(await confirm('发布后将对外可见，确认发布？', { confirmLabel: '发布' }))) return;
    setBusy('publish');
    try {
      await savePending(reportId, doc); // persist latest edits first
      await publishPending(reportId);
      toast('ok', '已发布');
      onPublished();
    } catch (e) {
      toast('err', '发布失败：' + (e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const doReject = async () => {
    if (!(await confirm('退回将丢弃这份待审报告，确认？', { danger: true, confirmLabel: '退回' }))) return;
    setBusy('reject');
    try {
      await rejectPending(reportId);
      toast('ok', '已退回');
      onRejected();
    } catch (e) {
      toast('err', '退回失败：' + (e as Error).message);
      setBusy(null);
    }
  };

  // ⌘S / Ctrl+S saves the draft
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        doSave();
      }
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc, busy, reportId]);

  return (
    <aside className="admin-rail panel">
      <div className="admin-tabs">
        <button className={'admin-tab' + (tab === 'ai' ? ' on' : '')} onClick={() => setTab('ai')}>
          AI 改稿{pendingRev ? ' ●' : ''}
        </button>
        <button className={'admin-tab' + (tab === 'edit' ? ' on' : '')} onClick={() => setTab('edit')}>
          直接编辑
        </button>
      </div>

      {tab === 'ai' && (
        <AiChatTab
          chat={chat}
          busy={busy === 'ai'}
          pendingRev={pendingRev}
          revisions={revisions}
          onSend={sendInstr}
          onAccept={acceptRev}
          onDiscard={() => setPendingRev(null)}
          onRollback={rollback}
        />
      )}
      {tab === 'edit' && (
        <DirectEditTab
          doc={doc}
          onPatch={(next, coalesce) => hist.update(next, { coalesce })}
          onOpenPool={() => setPoolOpen(true)}
        />
      )}

      <div className="admin-actions">
        {hist.dirty && <span className="admin-dirty" title="有未保存的修改">未保存</span>}
        <span className="admin-spacer" />
        <button className="admin-icon" title="撤销上一步（结构操作）" disabled={!hist.canUndo || !!busy} onClick={hist.undo}>↶</button>
        <button className="admin-btn" disabled={!!busy} onClick={doSave}>
          {busy === 'save' ? '保存中…' : '保存草稿 ⌘S'}
        </button>
        <button className="admin-btn admin-btn-primary" disabled={!!busy} onClick={doPublish}>
          {busy === 'publish' ? '发布中…' : '发布'}
        </button>
        <button className="admin-btn admin-danger" disabled={!!busy} onClick={doReject}>退回</button>
      </div>

      <ItemPoolDrawer open={poolOpen} doc={doc} onClose={() => setPoolOpen(false)} onAdd={addPoolItem} />
    </aside>
  );
}
