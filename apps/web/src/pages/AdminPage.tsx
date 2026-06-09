/* ============================================================
   Admin review console (/admin) — password-gated.
   Review pending reports · edit directly OR via LLM diff-revisions
   with a live preview · add real items from the intel pool ·
   publish / reject · pull published reports back for re-review.
   Components live in ./admin/; reuses Dossier tokens + ReportView.
   ============================================================ */
import { useEffect, useRef, useState } from 'react';
import { ReportView } from '../components/ReportView';
import type { Report } from '../types';
import {
  AdminAuthError,
  getPending,
  getPublishedReport,
  getToken,
  listPending,
  listPublished,
  setToken,
  unpublishReport,
  type PendingEntry,
} from '../api/admin';
import { AdminHeader, type Sel } from './admin/AdminHeader';
import { ConfirmProvider, useConfirm } from './admin/ConfirmDialog';
import { EditorRail } from './admin/EditorRail';
import { LoginGate } from './admin/LoginGate';
import { ToastProvider, useToast } from './admin/Toast';
import { useDocHistory } from './admin/useDocHistory';

const draftKey = (id: string) => `nintel_admin_draft_${id}`;

function AdminShell() {
  const toast = useToast();
  const confirm = useConfirm();
  const [authed, setAuthed] = useState(!!getToken());
  const [pending, setPending] = useState<PendingEntry[]>([]);
  const [published, setPublished] = useState<PendingEntry[]>([]);
  const [sel, setSel] = useState<Sel | null>(null);
  const [loadingDoc, setLoadingDoc] = useState(false);
  const [pubDoc, setPubDoc] = useState<Report | null>(null);
  const [busyUnpub, setBusyUnpub] = useState(false);
  const hist = useDocHistory();
  const loadSeq = useRef(0);

  const onApiError = (e: unknown) => {
    if (e instanceof AdminAuthError) setAuthed(false);
    else toast('err', (e as Error).message);
  };

  const refresh = async (keep?: Sel | null) => {
    try {
      const [p, pub] = await Promise.all([listPending(), listPublished()]);
      setPending(p);
      setPublished(pub);
      const want = keep === undefined ? sel : keep;
      const stillThere =
        want &&
        (want.kind === 'pending'
          ? p.some((x) => x.id === want.id)
          : pub.some((x) => x.id === want.id));
      if (stillThere) setSel(want);
      else if (p.length) setSel({ kind: 'pending', id: p[0].id });
      else if (pub.length) setSel({ kind: 'published', id: pub[0].id });
      else setSel(null);
    } catch (e) {
      onApiError(e);
    }
  };

  useEffect(() => {
    if (authed) refresh(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed]);

  // load the selected report (pending → editable working copy, with local-draft
  // recovery; published → read-only view)
  useEffect(() => {
    const seq = ++loadSeq.current;
    setPubDoc(null);
    if (!sel) {
      hist.reset(null);
      return;
    }
    setLoadingDoc(true);
    (async () => {
      try {
        if (sel.kind === 'pending') {
          const serverDoc = await getPending(sel.id);
          if (seq !== loadSeq.current) return;
          const raw = localStorage.getItem(draftKey(sel.id));
          if (raw) {
            try {
              const { at, doc } = JSON.parse(raw) as { at: number; doc: Report };
              const ok = await confirm(
                `检测到 ${new Date(at).toLocaleString('zh-CN', { hour12: false })} 的未保存本地草稿，恢复它吗？（取消则丢弃草稿）`,
                { confirmLabel: '恢复草稿' },
              );
              if (seq !== loadSeq.current) return;
              if (ok) {
                hist.reset(doc, { dirty: true });
                return;
              }
            } catch {
              /* corrupt draft — fall through to the server copy */
            }
            localStorage.removeItem(draftKey(sel.id));
          }
          hist.reset(serverDoc);
        } else {
          const doc = await getPublishedReport(sel.id);
          if (seq !== loadSeq.current) return;
          hist.reset(null);
          setPubDoc(doc);
        }
      } catch (e) {
        if (seq === loadSeq.current) onApiError(e);
      } finally {
        if (seq === loadSeq.current) setLoadingDoc(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sel?.kind, sel?.id]);

  // debounced local-draft autosave while dirty
  useEffect(() => {
    if (!hist.doc || !hist.dirty || sel?.kind !== 'pending') return;
    const id = sel.id;
    const t = window.setTimeout(() => {
      try {
        localStorage.setItem(draftKey(id), JSON.stringify({ at: Date.now(), doc: hist.doc }));
      } catch {
        /* storage full — autosave is best-effort */
      }
    }, 2000);
    return () => window.clearTimeout(t);
  }, [hist.doc, hist.dirty, sel]);

  // warn before closing the tab with unsaved edits
  useEffect(() => {
    if (!hist.dirty) return;
    const h = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener('beforeunload', h);
    return () => window.removeEventListener('beforeunload', h);
  }, [hist.dirty]);

  const selectEntry = async (next: Sel) => {
    if (sel && next.kind === sel.kind && next.id === sel.id) return;
    if (hist.dirty) {
      const ok = await confirm('当前报告有未保存的修改，切换会丢弃它们（本地草稿仍保留）。继续？', {
        danger: true,
        confirmLabel: '切换',
      });
      if (!ok) return;
    }
    setSel(next);
  };

  const doUnpublish = async () => {
    if (!sel || sel.kind !== 'published') return;
    const ok = await confirm(
      '「撤回重审」会复制一份回待审队列；公开站继续显示当前版本，重新发布后才会覆盖。继续？',
      { confirmLabel: '撤回重审' },
    );
    if (!ok) return;
    setBusyUnpub(true);
    try {
      await unpublishReport(sel.id);
      toast('ok', '已撤回到待审队列');
      await refresh({ kind: 'pending', id: sel.id });
    } catch (e) {
      onApiError(e);
    } finally {
      setBusyUnpub(false);
    }
  };

  if (!authed) return <LoginGate onAuthed={() => setAuthed(true)} />;

  const doc = hist.doc;
  const viewDoc = sel?.kind === 'published' ? pubDoc : doc;

  return (
    <div className="admin-shell">
      <AdminHeader
        pending={pending}
        published={published}
        sel={sel}
        onSelect={selectEntry}
        onRefresh={() => refresh()}
        onLogout={() => {
          setToken(null);
          setAuthed(false);
        }}
      />

      {loadingDoc && <div className="admin-empty">加载报告中…</div>}
      {!loadingDoc && !viewDoc && (
        <div className="admin-empty">没有报告。周报会在每周定时生成后进入待审队列。</div>
      )}

      {!loadingDoc && viewDoc && (
        <div className="admin-body">
          <main className="admin-preview">
            <div className="admin-preview-tag">
              {sel?.kind === 'published' ? '已发布 · 只读' : '实时预览'}
            </div>
            <ReportView
              report={viewDoc}
              type={viewDoc.type}
              twoCol={false}
              chartStyle="minimal"
              archive={[]}
              onOpen={() => {}}
            />
          </main>

          {sel?.kind === 'pending' && doc && (
            <EditorRail
              hist={hist}
              reportId={sel.id}
              onSaved={(saved) => {
                hist.reset(saved);
                localStorage.removeItem(draftKey(sel.id));
              }}
              onPublished={() => {
                localStorage.removeItem(draftKey(sel.id));
                hist.reset(null);
                refresh(null);
              }}
              onRejected={() => {
                localStorage.removeItem(draftKey(sel.id));
                hist.reset(null);
                refresh(null);
              }}
            />
          )}

          {sel?.kind === 'published' && (
            <aside className="admin-rail panel admin-pub-rail">
              <div className="admin-hint">
                已发布报告为只读。「撤回重审」会复制一份回待审队列进入正常编辑流；公开站继续显示当前版本，重新发布后覆盖。
              </div>
              <button className="admin-btn admin-btn-primary" disabled={busyUnpub} onClick={doUnpublish}>
                {busyUnpub ? '撤回中…' : '撤回重审'}
              </button>
            </aside>
          )}
        </div>
      )}
    </div>
  );
}

export function AdminPage() {
  return (
    <ToastProvider>
      <ConfirmProvider>
        <AdminShell />
      </ConfirmProvider>
    </ToastProvider>
  );
}
