/* ============================================================
   Icon registry + SourceGlyph (ported from project components +
   ds-foundations; merged superset incl. v2/v3 additions:
   activity, target, wrench, bulb, star).
   ============================================================ */
import type { CSSProperties } from 'react';

export const ICONS: Record<string, string> = {
  activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
  swords:
    'M14.5 17.5 3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2M14.5 6.5 18 3h3v3l-3.5 3.5',
  chat:
    'M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z',
  factory:
    'M2 20a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1V8l-7 5V8l-7 5V4a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1zM7 21v-4M11 21v-4M15 21v-4',
  target:
    'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  external: 'M7 17 17 7M9 7h8v8',
  link: 'M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1',
  arrowUp: 'M12 19V5M5 12l7-7 7 7',
  arrowDown: 'M12 5v14M5 12l7 7 7 7',
  trendUp: 'M22 7 13.5 15.5l-5-5L2 17M16 7h6v6',
  thumb:
    'M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88z',
  eye: 'M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  up: 'M12 19V5M6 11l6-6 6 6',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
  calendar:
    'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2',
  share: 'M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13',
  download: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
  sun: 'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  moon: 'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z',
  layers: 'M12 2 2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  check: 'M20 6 9 17l-5-5',
  x: 'M18 6 6 18M6 6l12 12',
  inbox:
    'M22 12h-6l-2 3h-4l-2-3H2M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z',
  filter: 'M22 3H2l8 9.46V19l4 2v-8.54z',
  store: 'M2 7l1.5-4h17L22 7M2 7h20M2 7v12a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1V7M6 11v5M18 11v5',
  barChart: 'M3 3v18h18M8 17V9M13 17V5M18 17v-6',
  zap: 'M13 2 3 14h9l-1 8 10-12h-9z',
  sparkle: 'M12 3l1.9 5.8L20 10l-6.1 1.2L12 17l-1.9-5.8L4 10l6.1-1.2z',
  doc: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8',
  mail: 'M3 5h18a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM3 7l9 6 9-6',
  // v2/v3 additions:
  wrench:
    'M14.7 6.3a4 4 0 0 0-5.2 5L3 17.8 6.2 21l6.5-6.5a4 4 0 0 0 5-5.2l-2.6 2.6-2.1-.4-.4-2.1z',
  bulb: 'M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.2 1 2V18h6v-1.3c0-.8.4-1.5 1-2A7 7 0 0 0 12 2z',
  star: 'M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.9 6.1 20.5l1.2-6.5L2.5 9.4l6.6-.9z',
};

export interface IconProps {
  name: string;
  size?: number;
  style?: CSSProperties;
  cls?: string;
}

export function Icon({ name, size = 18, style, cls }: IconProps) {
  const d = ICONS[name];
  if (!d) return null;
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cls}
      style={style}
      aria-hidden="true"
    >
      {d
        .split('M')
        .filter(Boolean)
        .map((seg, i) => (
          <path key={i} d={'M' + seg} />
        ))}
    </svg>
  );
}

/* ---- source glyphs (brand identity marks) ---- */
export function SourceGlyph({ kind }: { kind?: string }) {
  switch (kind) {
    case 'unifi':
      return (
        <svg viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.2" />
          <path
            d="M12 7v5a3 3 0 0 0 6 0"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
          />
        </svg>
      );
    case 'reddit':
      return (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12.5" r="8.5" />
          <circle cx="8.7" cy="12.5" r="1.1" fill="currentColor" stroke="none" />
          <circle cx="15.3" cy="12.5" r="1.1" fill="currentColor" stroke="none" />
          <path d="M8.7 15.5c1.8 1.2 4.8 1.2 6.6 0" />
          <circle cx="17.5" cy="6.5" r="1.4" />
        </svg>
      );
    case 'youtube':
      return (
        <svg viewBox="0 0 24 24" fill="none">
          <rect
            x="2.5"
            y="5.5"
            width="19"
            height="13"
            rx="3.5"
            stroke="currentColor"
            strokeWidth="1.9"
          />
          <path d="M10.3 9.3 15 12l-4.7 2.7z" fill="currentColor" />
        </svg>
      );
    case 'rss':
      return (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.9"
          strokeLinecap="round"
        >
          <circle cx="6" cy="18" r="1.4" fill="currentColor" stroke="none" />
          <path d="M5 11a8 8 0 0 1 8 8M5 5a14 14 0 0 1 14 14" />
        </svg>
      );
    case 'x':
      return (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.1"
          strokeLinecap="round"
        >
          <path d="M5 5l14 14M19 5 5 19" />
        </svg>
      );
    default:
      return null;
  }
}

/* ---- brand mark (Network Intel logo) ---- */
export function BrandMark() {
  return <img className="brand-mark" src="/logo.png" alt="Network Intel" />;
}
