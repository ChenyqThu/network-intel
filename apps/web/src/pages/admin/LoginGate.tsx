/* Password gate for the review console. */
import { useState } from 'react';
import { Icon } from '../../components/Icon';
import { login } from '../../api/admin';

export function LoginGate({ onAuthed }: { onAuthed: () => void }) {
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
