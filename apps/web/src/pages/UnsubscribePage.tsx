/* Standalone unsubscribe landing page (linked from the report email footer).
   Recipient enters their email -> POST /api/unsubscribe -> removed from the list. */
import { useState, type CSSProperties, type FormEvent } from 'react';
import { API_BASE } from '../api/client';

type State = 'idle' | 'busy' | 'done' | 'notfound' | 'error';

export function UnsubscribePage() {
  const [email, setEmail] = useState('');
  const [state, setState] = useState<State>('idle');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const v = email.trim();
    if (!v) return;
    setState('busy');
    try {
      const res = await fetch(`${API_BASE}/unsubscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: v }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const data = (await res.json()) as { removed: boolean };
      setState(data.removed ? 'done' : 'notfound');
    } catch {
      setState('error');
    }
  };

  return (
    <div style={wrap}>
      <div style={card}>
        <div style={{ fontSize: 18, fontWeight: 800, color: '#191B18', letterSpacing: '-.3px' }}>
          Network <span style={{ color: '#0C6151' }}>Intel</span>
        </div>

        {state === 'done' ? (
          <p style={msg}>
            ✅ 已退订 <strong>{email.trim()}</strong>，不会再收到报告邮件。如需重新订阅，请联系报告维护者。
          </p>
        ) : state === 'notfound' ? (
          <>
            <p style={msg}>该邮箱不在订阅列表中（可能已退订，或拼写有误）。</p>
            <button onClick={() => setState('idle')} style={btnGhost}>
              重新输入
            </button>
          </>
        ) : (
          <form onSubmit={submit}>
            <p style={{ ...msg, color: '#54584F', fontSize: 14 }}>
              输入你的邮箱以退订 Network Intel 日报 / 周报。
            </p>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@omadanetworks.com"
              required
              autoFocus
              style={input}
            />
            {state === 'error' && (
              <div style={{ marginTop: 8, fontSize: 13, color: '#B23B4B' }}>退订失败，请稍后重试。</div>
            )}
            <button type="submit" disabled={state === 'busy'} style={btnPrimary}>
              {state === 'busy' ? '处理中…' : '退订'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

const wrap: CSSProperties = {
  minHeight: '100vh',
  background: '#F4F3EE',
  display: 'grid',
  placeItems: 'center',
  padding: 24,
  fontFamily: "-apple-system,'Segoe UI','PingFang SC','Microsoft YaHei',Arial,sans-serif",
};
const card: CSSProperties = {
  width: 'min(440px, 100%)',
  background: '#fff',
  border: '1px solid #E6E3DA',
  borderRadius: 14,
  padding: '30px 28px',
  boxSizing: 'border-box',
};
const msg: CSSProperties = { marginTop: 16, fontSize: 15, lineHeight: 1.7, color: '#34372F' };
const input: CSSProperties = {
  width: '100%',
  marginTop: 12,
  padding: '10px 12px',
  fontSize: 14,
  border: '1px solid #D4D0C4',
  borderRadius: 8,
  boxSizing: 'border-box',
  fontFamily: 'inherit',
};
const btnPrimary: CSSProperties = {
  marginTop: 14,
  width: '100%',
  padding: '10px 14px',
  fontSize: 14,
  fontWeight: 700,
  color: '#fff',
  background: '#0C6151',
  border: 'none',
  borderRadius: 8,
  cursor: 'pointer',
};
const btnGhost: CSSProperties = {
  marginTop: 14,
  padding: '8px 14px',
  fontSize: 13,
  fontWeight: 600,
  color: '#0C6151',
  background: '#fff',
  border: '1px solid #0C6151',
  borderRadius: 8,
  cursor: 'pointer',
};
