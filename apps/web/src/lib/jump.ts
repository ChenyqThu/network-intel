/* ============================================================
   jumpTo — offset scroll + flash (ported from project/components.jsx)
   No scrollIntoView: respects the sticky nav height and
   prefers-reduced-motion, and flashes the target.
   ============================================================ */

export function jumpTo(id: string): void {
  let el = document.getElementById(id);
  // Synthesized reports have no per-item cards (id="item-N"); fall back to the
  // numbered reference row (id="ref-N") so citation superscripts still scroll.
  if (!el && id.startsWith('item-')) el = document.getElementById('ref-' + id.slice(5));
  if (!el) return;
  const navH =
    parseInt(
      getComputedStyle(document.documentElement).getPropertyValue('--nav-h'),
    ) || 62;
  const reduce =
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const y = el.getBoundingClientRect().top + window.pageYOffset - navH - 16;
  window.scrollTo({ top: y, behavior: reduce ? 'auto' : 'smooth' });
  el.classList.remove('flash');
  void el.offsetWidth; // reflow to restart the animation
  el.classList.add('flash');
  window.setTimeout(() => el.classList.remove('flash'), 1600);
}
