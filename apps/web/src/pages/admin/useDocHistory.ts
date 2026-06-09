/* Working-copy state for the admin editor: undo stack + dirty flag.
   Text-field keystrokes pass coalesce so continuous typing costs one
   undo entry instead of one per character. */
import { useRef, useState } from 'react';
import type { Report } from '../../types';

const LIMIT = 50;
const COALESCE_MS = 1500;

export interface DocHistory {
  doc: Report | null;
  dirty: boolean;
  canUndo: boolean;
  /** Replace the working copy, pushing the previous one onto the undo stack. */
  update: (next: Report, opts?: { coalesce?: boolean }) => void;
  /** Load a fresh doc (report switch / after save): clears history. */
  reset: (next: Report | null, opts?: { dirty?: boolean }) => void;
  undo: () => void;
}

export function useDocHistory(): DocHistory {
  const [doc, setDoc] = useState<Report | null>(null);
  const [past, setPast] = useState<Report[]>([]);
  const [dirty, setDirty] = useState(false);
  const lastPush = useRef(0);

  const update: DocHistory['update'] = (next, opts) => {
    const now = Date.now();
    const skip =
      opts?.coalesce && past.length > 0 && now - lastPush.current < COALESCE_MS;
    if (!skip && doc) {
      setPast((p) => [...p.slice(-(LIMIT - 1)), doc]);
      lastPush.current = now;
    }
    setDoc(next);
    setDirty(true);
  };

  const reset: DocHistory['reset'] = (next, opts) => {
    setDoc(next);
    setPast([]);
    setDirty(opts?.dirty ?? false);
    lastPush.current = 0;
  };

  const undo = () => {
    if (!past.length) return;
    setDoc(past[past.length - 1]);
    setPast(past.slice(0, -1));
    setDirty(true);
  };

  return { doc, dirty, canUndo: past.length > 0, update, reset, undo };
}
