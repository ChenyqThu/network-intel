/* Mail delivery settings — edit the recipient list (To/Cc). Reuses the
   admin-dialog modal shell. Saved to the server (data/mail_config.json) and
   read fresh on every send, so changes take effect with no restart. */
import { useEffect, useState } from 'react';
import { getMailConfig, saveMailConfig, type MailConfig } from '../../api/admin';
import { useToast } from './Toast';

// split on newlines, commas (ASCII + fullwidth), semicolons, whitespace.
const parseAddrs = (s: string): string[] =>
  s
    .split(/[\n,，;；\s]+/)
    .map((x) => x.trim())
    .filter(Boolean);

export function MailSettings({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved?: () => void;
}) {
  const toast = useToast();
  const [cfg, setCfg] = useState<MailConfig | null>(null);
  const [toText, setToText] = useState('');
  const [ccText, setCcText] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const c = await getMailConfig();
        setCfg(c);
        // seed from saved config, falling back to the env values.
        setToText((c.to.length ? c.to : c.env_to).join('\n'));
        setCcText((c.cc.length ? c.cc : c.env_cc).join('\n'));
      } catch (e) {
        toast('err', (e as Error).message);
      }
    })();
  }, [toast]);

  const save = async () => {
    setBusy(true);
    try {
      const to = parseAddrs(toText);
      const cc = parseAddrs(ccText);
      await saveMailConfig(to, cc);
      toast('ok', `已保存收件人（${to.length} 人${cc.length ? ` · 抄送 ${cc.length}` : ''}）`);
      onSaved?.();
      onClose();
    } catch (e) {
      toast('err', (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-dialog-mask" onClick={onClose}>
      <div className="admin-dialog panel" onClick={(e) => e.stopPropagation()}>
        <div className="admin-dialog-msg">邮件投递设置 · 收件人</div>

        {cfg && !cfg.configured && (
          <div className="admin-hint">
            ⚠ davmail 凭据未配置（NINTEL_DAVMAIL_USER / NINTEL_DAVMAIL_CIPHER_KEY），发送会失败。
          </div>
        )}
        <div className="admin-hint">
          发件人：{cfg?.from ?? '（未配置）'}。每行或用逗号分隔一个邮箱地址。「发送」会寄给下面的收件人；「存草稿」不受影响。
        </div>

        <label className="admin-label">收件人 To</label>
        <textarea
          className="admin-textarea"
          rows={4}
          value={toText}
          onChange={(e) => setToText(e.target.value)}
          placeholder="someone@omadanetworks.com"
        />

        <label className="admin-label">抄送 Cc（可选）</label>
        <textarea
          className="admin-textarea"
          rows={2}
          value={ccText}
          onChange={(e) => setCcText(e.target.value)}
        />

        <div className="admin-dialog-actions">
          <button className="admin-btn" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button className="admin-btn admin-btn-primary" onClick={save} disabled={busy}>
            {busy ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
