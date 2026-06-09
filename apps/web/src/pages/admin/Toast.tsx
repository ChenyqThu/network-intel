/* Minimal toast system for the admin console (no deps, Dossier tokens). */
import { createContext, useCallback, useContext, useRef, useState } from 'react';

export type ToastKind = 'ok' | 'err' | 'info';
interface ToastMsg {
  id: number;
  kind: ToastKind;
  text: string;
}

const ToastCtx = createContext<(kind: ToastKind, text: string) => void>(() => {});

export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMsg[]>([]);
  const seq = useRef(0);

  const push = useCallback((kind: ToastKind, text: string) => {
    const id = ++seq.current;
    setToasts((t) => [...t, { id, kind, text }]);
    window.setTimeout(
      () => setToasts((t) => t.filter((m) => m.id !== id)),
      kind === 'err' ? 6000 : 3200,
    );
  }, []);

  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="admin-toasts">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`admin-toast ${t.kind}`}
            onClick={() => setToasts((x) => x.filter((m) => m.id !== t.id))}
          >
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
