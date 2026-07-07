/* ============================================================
   Small text helpers for compact list rendering.
   ============================================================ */

/**
 * Truncate `s` to at most `max` characters, placing the ellipsis in the
 * middle so both the head and tail survive (e.g. a report title's topic and
 * its punchline). Returns `s` unchanged when it already fits.
 */
export function middleEllipsis(s: string, max: number): string {
  if (s.length <= max) return s;
  if (max <= 1) return '…';
  const keep = max - 1; // one slot for the ellipsis
  const head = Math.ceil(keep / 2);
  const tail = keep - head;
  return (
    s.slice(0, head).trimEnd() +
    '…' +
    (tail ? s.slice(s.length - tail).trimStart() : '')
  );
}
