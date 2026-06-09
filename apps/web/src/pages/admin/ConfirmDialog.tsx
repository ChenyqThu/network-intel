/* Promise-based styled confirm dialog (replaces window.confirm). */
import { createContext, useCallback, useContext, useState } from 'react';

interface ConfirmOpts {
  danger?: boolean;
  confirmLabel?: string;
}
type ConfirmFn = (msg: string, opts?: ConfirmOpts) => Promise<boolean>;

const ConfirmCtx = createContext<ConfirmFn>(() => Promise.resolve(false));

export const useConfirm = () => useContext(ConfirmCtx);

interface Req {
  msg: string;
  opts?: ConfirmOpts;
  resolve: (v: boolean) => void;
}

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [req, setReq] = useState<Req | null>(null);

  const confirm = useCallback<ConfirmFn>(
    (msg, opts) => new Promise<boolean>((resolve) => setReq({ msg, opts, resolve })),
    [],
  );

  const answer = (v: boolean) => {
    req?.resolve(v);
    setReq(null);
  };

  return (
    <ConfirmCtx.Provider value={confirm}>
      {children}
      {req && (
        <div className="admin-dialog-mask" onClick={() => answer(false)}>
          <div className="admin-dialog panel" onClick={(e) => e.stopPropagation()}>
            <div className="admin-dialog-msg">{req.msg}</div>
            <div className="admin-dialog-actions">
              <button className="admin-btn" onClick={() => answer(false)}>
                取消
              </button>
              <button
                className={'admin-btn ' + (req.opts?.danger ? 'admin-btn-danger' : 'admin-btn-primary')}
                autoFocus
                onClick={() => answer(true)}
              >
                {req.opts?.confirmLabel ?? '确认'}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmCtx.Provider>
  );
}
