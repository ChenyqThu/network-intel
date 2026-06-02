/* ============================================================
   Tweaks panel + useTweaks (TS port of project/tweaks-panel.jsx).
   Persists to localStorage('nintel.tweaks') so the no-FOUC script
   in index.html can resolve theme/density/primary before paint.
   Keeps the host edit-mode protocol for parity.
   ============================================================ */
import { useCallback, useEffect, useRef, useState } from 'react';

export interface Tweaks {
  primaryColor: string;
  density: 'compact' | 'regular' | 'comfy';
  homeLayout: 'two' | 'single';
  chartStyle: 'minimal' | 'filled';
  theme: 'system' | 'light' | 'dark';
}

const STORAGE_KEY = 'nintel.tweaks';

function loadPersisted(defaults: Tweaks): Tweaks {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...defaults, ...(JSON.parse(raw) as Partial<Tweaks>) };
  } catch {
    /* ignore */
  }
  return defaults;
}

export function useTweaks(
  defaults: Tweaks,
): [Tweaks, (key: keyof Tweaks, val: Tweaks[keyof Tweaks]) => void] {
  const [values, setValues] = useState<Tweaks>(() => loadPersisted(defaults));

  const setTweak = useCallback(
    (key: keyof Tweaks, val: Tweaks[keyof Tweaks]) => {
      setValues((prev) => {
        const next = { ...prev, [key]: val };
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch {
          /* ignore */
        }
        return next;
      });
      try {
        window.parent.postMessage(
          { type: '__edit_mode_set_keys', edits: { [key]: val } },
          '*',
        );
      } catch {
        /* ignore */
      }
    },
    [],
  );

  return [values, setTweak];
}

const TWEAKS_STYLE = `
  .twk-panel{position:fixed;right:16px;bottom:16px;z-index:2147483646;width:280px;
    max-height:calc(100vh - 32px);display:flex;flex-direction:column;
    background:rgba(250,249,247,.86);color:#29261b;
    -webkit-backdrop-filter:blur(24px) saturate(160%);backdrop-filter:blur(24px) saturate(160%);
    border:.5px solid rgba(255,255,255,.6);border-radius:14px;
    box-shadow:0 1px 0 rgba(255,255,255,.5) inset,0 12px 40px rgba(0,0,0,.18);
    font:11.5px/1.4 ui-sans-serif,system-ui,-apple-system,sans-serif;overflow:hidden}
  .twk-hd{display:flex;align-items:center;justify-content:space-between;
    padding:10px 8px 10px 14px;cursor:move;user-select:none}
  .twk-hd b{font-size:12px;font-weight:600;letter-spacing:.01em}
  .twk-x{appearance:none;border:0;background:transparent;color:rgba(41,38,27,.55);
    width:22px;height:22px;border-radius:6px;cursor:pointer;font-size:13px;line-height:1}
  .twk-x:hover{background:rgba(0,0,0,.06);color:#29261b}
  .twk-body{padding:2px 14px 14px;display:flex;flex-direction:column;gap:10px;
    overflow-y:auto;overflow-x:hidden;min-height:0}
  .twk-row{display:flex;flex-direction:column;gap:5px}
  .twk-row-h{flex-direction:row;align-items:center;justify-content:space-between;gap:10px}
  .twk-lbl{display:flex;justify-content:space-between;align-items:baseline;color:rgba(41,38,27,.72)}
  .twk-lbl>span:first-child{font-weight:500}
  .twk-sect{font-size:10px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
    color:rgba(41,38,27,.45);padding:10px 0 0}
  .twk-sect:first-child{padding-top:0}
  .twk-seg{position:relative;display:flex;padding:2px;border-radius:8px;background:rgba(0,0,0,.06)}
  .twk-seg button{appearance:none;position:relative;z-index:1;flex:1;border:0;background:transparent;
    color:inherit;font:inherit;font-weight:500;min-height:22px;border-radius:6px;cursor:pointer;padding:4px 6px}
  .twk-seg button[data-on="1"]{background:rgba(255,255,255,.9);box-shadow:0 1px 2px rgba(0,0,0,.12)}
  .twk-chips{display:flex;gap:6px}
  .twk-chip{position:relative;appearance:none;flex:1;min-width:0;height:30px;padding:0;border:0;border-radius:6px;
    overflow:hidden;cursor:pointer;box-shadow:0 0 0 .5px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.06);transition:box-shadow .12s}
  .twk-chip[data-on="1"]{box-shadow:0 0 0 1.5px rgba(0,0,0,.85),0 2px 6px rgba(0,0,0,.15)}
`;

function TweakSection({ label }: { label: string }) {
  return <div className="twk-sect">{label}</div>;
}

function TweakRadio<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: readonly T[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="twk-row">
      <div className="twk-lbl">
        <span>{label}</span>
      </div>
      <div className="twk-seg" role="radiogroup">
        {options.map((o) => (
          <button
            key={o}
            type="button"
            role="radio"
            aria-checked={o === value}
            data-on={o === value ? '1' : '0'}
            onClick={() => onChange(o)}
          >
            {o}
          </button>
        ))}
      </div>
    </div>
  );
}

function TweakColor({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="twk-row">
      <div className="twk-lbl">
        <span>{label}</span>
      </div>
      <div className="twk-chips" role="radiogroup">
        {options.map((c) => (
          <button
            key={c}
            type="button"
            role="radio"
            aria-checked={c.toLowerCase() === value.toLowerCase()}
            data-on={c.toLowerCase() === value.toLowerCase() ? '1' : '0'}
            className="twk-chip"
            title={c}
            style={{ background: c }}
            onClick={() => onChange(c)}
          />
        ))}
      </div>
    </div>
  );
}

export function TweaksPanel({
  title = 'Tweaks',
  tweaks,
  setTweak,
}: {
  title?: string;
  tweaks: Tweaks;
  setTweak: (key: keyof Tweaks, val: Tweaks[keyof Tweaks]) => void;
}) {
  const [open, setOpen] = useState(false);
  const dragRef = useRef<HTMLDivElement>(null);
  const offsetRef = useRef({ x: 16, y: 16 });

  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      const t = (e?.data as { type?: string })?.type;
      if (t === '__activate_edit_mode') setOpen(true);
      else if (t === '__deactivate_edit_mode') setOpen(false);
    };
    window.addEventListener('message', onMsg);
    try {
      window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    } catch {
      /* ignore */
    }
    return () => window.removeEventListener('message', onMsg);
  }, []);

  const onDragStart = (e: React.MouseEvent) => {
    const panel = dragRef.current;
    if (!panel) return;
    const r = panel.getBoundingClientRect();
    const sx = e.clientX,
      sy = e.clientY;
    const startRight = window.innerWidth - r.right;
    const startBottom = window.innerHeight - r.bottom;
    const move = (ev: MouseEvent) => {
      offsetRef.current = {
        x: Math.max(8, startRight - (ev.clientX - sx)),
        y: Math.max(8, startBottom - (ev.clientY - sy)),
      };
      panel.style.right = offsetRef.current.x + 'px';
      panel.style.bottom = offsetRef.current.y + 'px';
    };
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

  if (!open) return null;
  return (
    <>
      <style>{TWEAKS_STYLE}</style>
      <div
        ref={dragRef}
        className="twk-panel"
        data-omelette-chrome=""
        style={{ right: offsetRef.current.x, bottom: offsetRef.current.y }}
      >
        <div className="twk-hd" onMouseDown={onDragStart}>
          <b>{title}</b>
          <button
            className="twk-x"
            aria-label="Close tweaks"
            onMouseDown={(e) => e.stopPropagation()}
            onClick={() => {
              setOpen(false);
              try {
                window.parent.postMessage({ type: '__edit_mode_dismissed' }, '*');
              } catch {
                /* ignore */
              }
            }}
          >
            ✕
          </button>
        </div>
        <div className="twk-body">
          <TweakSection label="外观" />
          <TweakColor
            label="主色"
            value={tweaks.primaryColor}
            options={['#0C6151', '#0A5A5A', '#15503B', '#1F4E79', '#2C2F36']}
            onChange={(v) => setTweak('primaryColor', v)}
          />
          <TweakRadio
            label="主题"
            value={tweaks.theme}
            options={['system', 'light', 'dark'] as const}
            onChange={(v) => setTweak('theme', v)}
          />
          <TweakRadio
            label="密度"
            value={tweaks.density}
            options={['compact', 'regular', 'comfy'] as const}
            onChange={(v) => setTweak('density', v)}
          />
          <TweakSection label="布局 & 图表" />
          <TweakRadio
            label="首页布局"
            value={tweaks.homeLayout}
            options={['two', 'single'] as const}
            onChange={(v) => setTweak('homeLayout', v)}
          />
          <TweakRadio
            label="图表风格"
            value={tweaks.chartStyle}
            options={['minimal', 'filled'] as const}
            onChange={(v) => setTweak('chartStyle', v)}
          />
        </div>
      </div>
    </>
  );
}
