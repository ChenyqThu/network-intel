/* AI revision tab: chat log + pending-revision diff card (accept / discard)
   + accepted-revision history with rollback. */
import { useEffect, useMemo, useRef, useState } from 'react';
import { diffWords, type FieldChange } from './diff';

export interface ChatMsg {
  role: 'you' | 'ai';
  text: string;
}

export interface PendingRev {
  instruction: string;
  changes: FieldChange[];
}

export interface AcceptedRev {
  instruction: string;
  at: string;
}

function DiffText({ before, after }: { before: string; after: string }) {
  const segs = useMemo(() => diffWords(before, after), [before, after]);
  return (
    <div className="admin-diff-text">
      {segs.map((s, i) =>
        s.kind === 'same' ? (
          <span key={i}>{s.text}</span>
        ) : s.kind === 'add' ? (
          <ins key={i}>{s.text}</ins>
        ) : (
          <del key={i}>{s.text}</del>
        ),
      )}
    </div>
  );
}

export function AiChatTab({
  chat,
  busy,
  pendingRev,
  revisions,
  onSend,
  onAccept,
  onDiscard,
  onRollback,
}: {
  chat: ChatMsg[];
  busy: boolean;
  pendingRev: PendingRev | null;
  revisions: AcceptedRev[];
  onSend: (text: string) => void;
  onAccept: () => void;
  onDiscard: () => void;
  onRollback: (idx: number) => void;
}) {
  const [instr, setInstr] = useState('');
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chat, busy, pendingRev]);

  const send = () => {
    const text = instr.trim();
    if (!text || busy) return;
    setInstr('');
    onSend(text);
  };

  return (
    <div className="admin-chat">
      <div className="admin-chat-log" ref={logRef}>
        {chat.length === 0 && (
          <div className="admin-hint">
            用自然语言改稿，AI 返回的修订会先以 diff 形式展示，采纳后才进入工作副本。例如：<br />
            “把导语改犀利点”、“删掉第 3 条”、“强调安全角度”、“按重要性重排竞品”。
          </div>
        )}
        {chat.map((m, i) => (
          <div key={i} className={'admin-msg ' + m.role}>{m.text}</div>
        ))}
        {busy && <div className="admin-msg ai">改稿中…（大报告可能要一两分钟）</div>}

        {pendingRev && (
          <div className="admin-rev">
            <div className="admin-rev-head">
              修订建议 · {pendingRev.changes.length} 处变更（未应用）
            </div>
            <div className="admin-rev-changes">
              {pendingRev.changes.length === 0 && (
                <div className="admin-hint">AI 没有改动任何字段。</div>
              )}
              {pendingRev.changes.map((c, i) => (
                <div key={i} className="admin-rev-change">
                  <div className="admin-rev-label">
                    {c.label}
                    {c.kind === 'added' && <span className="admin-rev-badge add">新增</span>}
                    {c.kind === 'removed' && <span className="admin-rev-badge del">删除</span>}
                  </div>
                  <DiffText before={c.before} after={c.after} />
                </div>
              ))}
            </div>
            <div className="admin-rev-actions">
              <button className="admin-btn admin-btn-primary" onClick={onAccept}>采纳全部</button>
              <button className="admin-btn" onClick={onDiscard}>放弃</button>
            </div>
          </div>
        )}

        {revisions.length > 0 && (
          <div className="admin-rev-history">
            <div className="admin-rev-head">已采纳的修订（{revisions.length} 轮）</div>
            {revisions.map((r, i) => (
              <div key={i} className="admin-rev-hist-row">
                <span className="admin-rev-hist-txt">#{i + 1} · {r.at} · {r.instruction}</span>
                <button className="admin-icon" title="回退到这轮之前" onClick={() => onRollback(i)}>↶</button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="admin-chat-input">
        <textarea
          className="admin-textarea"
          rows={2}
          placeholder="输入改稿指令…"
          value={instr}
          disabled={busy}
          onChange={(e) => setInstr(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) send();
          }}
        />
        <button className="admin-btn admin-btn-primary" disabled={busy || !instr.trim()} onClick={send}>
          发送 ⌘↵
        </button>
      </div>
    </div>
  );
}
