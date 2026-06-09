/* Hand-rolled diff for the AI-revision view (no runtime deps).
   diffWords: word-level LCS (CJK chars as single tokens, latin runs whole).
   diffReport: walks the editable report fields and lists what changed. */
import type { Report } from '../../types';

export type SegKind = 'same' | 'add' | 'del';
export interface Seg {
  kind: SegKind;
  text: string;
}

/** Above this token count the DP table gets heavy; fall back to whole-text. */
const MAX_TOKENS = 1500;

export function tokenize(s: string): string[] {
  return s.match(/[A-Za-z0-9_]+|\s+|[^\sA-Za-z0-9_]/g) ?? [];
}

export function diffWords(a: string, b: string): Seg[] {
  if (a === b) return a ? [{ kind: 'same', text: a }] : [];
  const ta = tokenize(a);
  const tb = tokenize(b);
  if (ta.length > MAX_TOKENS || tb.length > MAX_TOKENS) {
    const out: Seg[] = [];
    if (a) out.push({ kind: 'del', text: a });
    if (b) out.push({ kind: 'add', text: b });
    return out;
  }
  const n = ta.length;
  const m = tb.length;
  const w = m + 1;
  // dp[i*w+j] = LCS length of ta[i:] vs tb[j:]
  const dp = new Uint16Array((n + 1) * w);
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i * w + j] =
        ta[i] === tb[j]
          ? dp[(i + 1) * w + j + 1] + 1
          : Math.max(dp[(i + 1) * w + j], dp[i * w + j + 1]);
    }
  }
  const segs: Seg[] = [];
  const push = (kind: SegKind, text: string) => {
    const last = segs[segs.length - 1];
    if (last && last.kind === kind) last.text += text;
    else segs.push({ kind, text });
  };
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (ta[i] === tb[j]) {
      push('same', ta[i]);
      i++;
      j++;
    } else if (dp[(i + 1) * w + j] >= dp[i * w + j + 1]) {
      push('del', ta[i]);
      i++;
    } else {
      push('add', tb[j]);
      j++;
    }
  }
  while (i < n) push('del', ta[i++]);
  while (j < m) push('add', tb[j++]);
  return segs;
}

export interface FieldChange {
  label: string;
  kind: 'text' | 'added' | 'removed';
  before: string;
  after: string;
}

export function diffReport(a: Report, b: Report): FieldChange[] {
  const out: FieldChange[] = [];
  const cmp = (label: string, x?: string | null, y?: string | null) => {
    const xs = x ?? '';
    const ys = y ?? '';
    if (xs !== ys) out.push({ label, kind: 'text', before: xs, after: ys });
  };

  cmp('导语', a.lead?.text, b.lead?.text);
  cmp('导语 · 加粗结论', a.lead?.strong, b.lead?.strong);
  cmp('策略 · 标题', a.strategy?.title, b.strategy?.title);
  cmp('策略 · 正文', a.strategy?.body, b.strategy?.body);
  const pa = a.strategy?.paras ?? [];
  const pb = b.strategy?.paras ?? [];
  for (let k = 0; k < Math.max(pa.length, pb.length); k++) {
    cmp(`策略 · 段落${k + 1}小标题`, pa[k]?.[0], pb[k]?.[0]);
    cmp(`策略 · 段落${k + 1}`, pa[k]?.[1], pb[k]?.[1]);
  }

  const ia = new Map((a.insights ?? []).map((x) => [x.id, x]));
  const ib = new Map((b.insights ?? []).map((x) => [x.id, x]));
  for (const [id, x] of ia) {
    const y = ib.get(id);
    if (!y) {
      out.push({ label: `洞察「${x.title}」已删除`, kind: 'removed', before: x.body, after: '' });
      continue;
    }
    cmp(`洞察「${y.title}」标题`, x.title, y.title);
    cmp(`洞察「${y.title}」正文`, x.body, y.body);
    cmp(`洞察「${y.title}」💡 takeaway`, x.takeaway, y.takeaway);
  }
  for (const [id, y] of ib) {
    if (!ia.has(id)) {
      out.push({ label: `洞察「${y.title}」新增`, kind: 'added', before: '', after: y.body });
    }
  }

  const ma = new Map(a.items.map((x) => [x.id, x]));
  const mb = new Map(b.items.map((x) => [x.id, x]));
  for (const [id, x] of ma) {
    const y = mb.get(id);
    if (!y) {
      out.push({
        label: `条目「${x.title}」已删除`,
        kind: 'removed',
        before: x.summary ?? '',
        after: '',
      });
      continue;
    }
    cmp(`条目「${y.title}」标题`, x.title, y.title);
    cmp(`条目「${y.title}」摘要`, x.summary, y.summary);
    cmp(`条目「${y.title}」研判`, x.impact_note, y.impact_note);
    if (x.subject !== y.subject) {
      out.push({ label: `条目「${y.title}」板块`, kind: 'text', before: x.subject, after: y.subject });
    }
    if (x.omada_impact !== y.omada_impact) {
      out.push({
        label: `条目「${y.title}」影响`,
        kind: 'text',
        before: x.omada_impact ?? '',
        after: y.omada_impact ?? '',
      });
    }
  }
  for (const [id, y] of mb) {
    if (!ma.has(id)) {
      out.push({
        label: `条目「${y.title}」新增`,
        kind: 'added',
        before: '',
        after: y.summary ?? '',
      });
    }
  }
  return out;
}
