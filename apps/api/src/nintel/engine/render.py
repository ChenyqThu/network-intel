"""Render stage: contract → email HTML (Jinja2) + Markdown (Feishu).

The email templates are driven *entirely* by the contract — they port
``project/email-daily.html`` to a contract-driven, table-based, fully
inline-styled, JS-free, 620px-wide layout (preheader + mso fallback), and add a
weekly template (strategy block + store table + compact dashboard summary).
Both use the Dossier deep-evergreen ``#0C6151`` accent on a light theme.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from ..config import get_settings
from ..contract import Report

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Impact -> (label, dot/accent color, tint bg, border, text color) for badges
# and research notes. Matches the Dossier palette from email-daily.html.
IMPACT_STYLE: dict[str, dict[str, str]] = {
    "threat": {"label": "威胁", "accent": "#B23B4B", "bg": "#F7ECEE", "border": "#ECCBD1", "text": "#6E2630", "judge": "威胁研判"},
    "opportunity": {"label": "机会", "accent": "#2E8259", "bg": "#E9F2EC", "border": "#C9E0D1", "text": "#1F5C3E", "judge": "机会研判"},
    "neutral": {"label": "中性", "accent": "#7C8079", "bg": "#F0F1ED", "border": "#E3E3DD", "text": "#4A4E47", "judge": "中性研判"},
    "needs_fix": {"label": "待修复", "accent": "#B23B4B", "bg": "#F7ECEE", "border": "#ECCBD1", "text": "#6E2630", "judge": "修复建议"},
    "feature_input": {"label": "功能需求", "accent": "#0C6151", "bg": "#E9F2EC", "border": "#C9E0D1", "text": "#1F5C3E", "judge": "需求信号"},
    "strength_confirm": {"label": "优势确认", "accent": "#2E8259", "bg": "#E9F2EC", "border": "#C9E0D1", "text": "#1F5C3E", "judge": "优势确认"},
    "unknown": {"label": "待研判", "accent": "#7C8079", "bg": "#F0F1ED", "border": "#E3E3DD", "text": "#4A4E47", "judge": "研判"},
}

SECTION_TONE: dict[str, str] = {
    "omada_self": "#0C6151",
    "competitor": "#B23B4B",
    "sentiment": "#2E8259",
    "store": "#8A6D1F",
    "industry": "#7C8079",
    "dashboard": "#0C6151",
    "progress": "#1D6FA4",   # project-blue
    "picks": "#6B4FA4",     # editorial-purple
}

# Tier label fallbacks by source_tier.
TIER_LABEL = {"official": "一手官方", "community": "社区来源"}

_CITE_RE = re.compile(r"\{\{cite:(\d+)\}\}")

# Inline markdown the curator occasionally emits in prose (in practice: **bold**).
# Mirrors the web reader (web/src/lib/intel.ts parseInlineMd): bold before italic,
# `_` is never emphasis (avoids snake_case false positives), \S flanking guards
# stop "a * b" / lone asterisks from becoming emphasis.
_MD_BOLD = re.compile(r"\*\*(\S(?:[^*]*?\S)?)\*\*")
_MD_CODE = re.compile(r"`([^`]+?)`")
_MD_ITALIC = re.compile(r"\*(\S(?:[^*\n]*?\S)?)\*")
_MD_CODE_STYLE = (
    "font-family:'SF Mono',ui-monospace,Menlo,Consolas,monospace;"
    "background:#EEF2EE;padding:1px 5px;border-radius:3px;"
)


def _inline_md(escaped: str) -> str:
    """Render inline markdown (**bold** / `code` / *italic*) on already-escaped
    text. Only ``*`` and backticks are touched, so it is safe on escaped HTML."""
    s = _MD_BOLD.sub(r"<strong>\1</strong>", escaped)
    s = _MD_CODE.sub(rf'<code style="{_MD_CODE_STYLE}">\1</code>', s)
    s = _MD_ITALIC.sub(r"<em>\1</em>", s)
    return s


@lru_cache(maxsize=1)
def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["cite_links"] = _cite_links_filter
    env.filters["metrics_line"] = _metrics_line
    env.globals["IMPACT_STYLE"] = IMPACT_STYLE
    env.globals["SECTION_TONE"] = SECTION_TONE
    env.globals["TIER_LABEL"] = TIER_LABEL
    return env


def _ref_index(report: Report) -> dict[int, Any]:
    return {ref.cite_id: ref for ref in report.references}


def _cite_links_filter(text: str, ref_index: dict[int, Any]) -> Markup:
    """Replace ``{{cite:N}}`` with a superscript anchor linking to the ref URL."""

    def repl(m: re.Match[str]) -> str:
        n = int(m.group(1))
        ref = ref_index.get(n)
        url = escape(ref.url) if ref else "#"
        return (
            f'<a href="{url}" style="color:#0C6151;'
            f"font-family:'SF Mono',ui-monospace,Menlo,Consolas,monospace;"
            f'font-size:11px;font-weight:700;vertical-align:5px;">{n}</a>'
        )

    # Cites split first (citation logic stays the sole first pass), then inline
    # markdown renders on each escaped text run between them — mirrors the web
    # reader so **bold** etc. don't show up raw in the email.
    parts: list[str] = []
    last = 0
    for m in _CITE_RE.finditer(text):
        parts.append(_inline_md(str(escape(text[last : m.start()]))))
        parts.append(repl(m))
        last = m.end()
    parts.append(_inline_md(str(escape(text[last:]))))
    return Markup("".join(parts))


def _metrics_line(item_metrics: Any) -> str:
    """Human metrics footer line (likes/comments/views/note).

    Accepts either a plain dict or the Pydantic ``Metrics`` model.
    """

    if not item_metrics:
        return ""
    m = item_metrics if isinstance(item_metrics, dict) else item_metrics.model_dump()
    bits: list[str] = []
    if m.get("likes") is not None:
        bits.append(f"↑ {m['likes']:,} 赞")
    if m.get("comments") is not None:
        bits.append(f"{m['comments']:,} 评论")
    if m.get("views") is not None:
        bits.append(f"{m['views']:,} 浏览")
    if m.get("note"):
        bits.append(str(m["note"]))
    return "  ·  ".join(bits)


def _ctx(report: Report) -> dict[str, Any]:
    item_by_id = {it.id: it for it in report.items}
    ref_index = _ref_index(report)
    insights_by_id = {ins.id: ins for ins in (report.insights or [])}
    # Pre-resolve each section -> ordered item objects + its synthesized insights
    # (each with its cite_refs resolved to References). When a section carries
    # insight refs (v1.4 synthesis) the templates render those cards; otherwise
    # they render per-item cards — same branch the web ReportView uses.
    sections = []
    for sec in report.sections:
        sec_items = [item_by_id[i] for i in sec.items if i in item_by_id]
        sec_insights = []
        for iid in sec.insights or []:
            ins = insights_by_id.get(iid)
            if ins is None:
                continue
            sources = [ref_index[n] for n in ins.cite_refs if n in ref_index]
            sec_insights.append({"ins": ins, "sources": sources})
        sections.append({"meta": sec, "entries": sec_items, "insights": sec_insights})
    return {
        "report": report,
        "sections": sections,
        "ref_index": ref_index,
        "references": report.references,
        "accent": "#0C6151",
        "site_url": get_settings().site_url,
    }


def render_email(report: Report) -> str:
    """Render the cadence-appropriate email HTML for ``report``."""

    template_name = "weekly_email.html.j2" if report.type == "weekly" else "daily_email.html.j2"
    template = _env().get_template(template_name)
    return template.render(**_ctx(report))


def render_email_filtered(report: Report, sections: set[str]) -> str:
    """Render a personalised email containing only the requested *sections*.

    The lead / header / footer are always included.  Section-level filtering is
    done by building a lightweight shim report whose ``.sections`` list only
    contains the subscriber’s chosen keys; items that belong exclusively to
    excluded sections are also stripped so the References block stays clean.

    Args:
        report:   The full, published report (not mutated).
        sections: Set of ``SectionKey`` strings the subscriber wants.
                  An empty set → full report (no filtering).
    """
    if not sections:
        return render_email(report)

    # Build filtered section list; preserve original ordering.
    filtered_sections = [s for s in report.sections if s.key in sections]

    # Collect item ids referenced by the surviving sections.
    kept_item_ids: set[str] = set()
    kept_insight_ids: set[str] = set()
    for sec in filtered_sections:
        kept_item_ids.update(sec.items)
        kept_insight_ids.update(sec.insights or [])

    filtered_items = [it for it in report.items if it.id in kept_item_ids]
    filtered_insights = [ins for ins in (report.insights or []) if ins.id in kept_insight_ids]

    # Also keep references cited by kept items / insights.
    cited_nums: set[int] = set()
    _CITE_RE_LOCAL = re.compile(r"\{\{cite:(\d+)\}\}")
    for it in filtered_items:
        for field in (it.summary, it.analysis or ""):
            cited_nums.update(int(m) for m in _CITE_RE_LOCAL.findall(field))
    for ins in filtered_insights:
        cited_nums.update(int(m) for m in _CITE_RE_LOCAL.findall(ins.body))
    # Lead always included — keep its refs too.
    cited_nums.update(report.lead.cite_refs)

    filtered_refs = [r for r in (report.references or []) if r.n in cited_nums]

    # Construct a shallow copy using model_copy (Pydantic v2); avoids re-validation.
    slim = report.model_copy(update={
        "sections": filtered_sections,
        "items": filtered_items,
        "insights": filtered_insights,
        "references": filtered_refs,
    })

    return render_email(slim)


def render_markdown(report: Report) -> str:
    """Render a Feishu-friendly Markdown digest of ``report``.

    Lighter than the email: lead (with [n] cites), each section's items as
    bullet lines with the citation line, and the references list. Used for the
    Feishu push path (SOLUTION §8 render → markdown).
    """

    ref_index = _ref_index(report)
    item_by_id = {it.id: it for it in report.items}

    def cites_to_md(text: str) -> str:
        return _CITE_RE.sub(lambda m: f"[{m.group(1)}]", text or "")

    lines: list[str] = []
    lines.append(f"# {report.title or report.report_id}")
    lines.append("")
    lines.append(f"> {cites_to_md(report.lead.text)}")
    if report.lead.strong:
        lines.append(">")
        lines.append(f"> **{report.lead.strong}**")
    lines.append("")

    if report.strategy:
        s = report.strategy
        lines.append(f"## 🎯 {s.title}")
        if s.paras:
            for label, body in s.paras:
                lines.append(f"- **{label}** — {cites_to_md(body)}")
        else:
            lines.append(cites_to_md(s.body))
        lines.append("")

    for sec in report.sections:
        sec_items = [item_by_id[i] for i in sec.items if i in item_by_id]
        if not sec_items and sec.key in {"store", "dashboard"}:
            continue
        lines.append(f"## {sec.title}")
        for it in sec_items:
            style = IMPACT_STYLE.get(it.omada_impact, IMPACT_STYLE["unknown"])
            lines.append(f"- **[{style['label']}]** {it.title}")
            lines.append(f"  - {it.summary}")
            if it.impact_note:
                lines.append(f"  - _{style['judge']}_: {it.impact_note}")
            lines.append(
                f"  - 来源: {it.source_domain} · {it.date} · "
                f"[查看原文 ↗]({it.url}) `[{it.cite_id}]`"
            )
        lines.append("")

    if report.store:
        lines.append("## Store 动向")
        lines.append("| 产品 | 类别 | 变化 | 库存 |")
        lines.append("|---|---|---|---|")
        for row in report.store:
            cat = row.cat or ""
            change = row.change or ""
            lines.append(f"| {row.product} | {cat} | {change} | {row.stock} |")
        lines.append("")

    lines.append("## 参考来源")
    for ref in report.references:
        lines.append(f"{ref.cite_id}. [{ref.title}]({ref.url}) — {ref.source_domain} · {ref.date}")
    lines.append("")
    return "\n".join(lines)
