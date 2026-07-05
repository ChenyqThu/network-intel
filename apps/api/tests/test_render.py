"""Email + markdown render tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nintel.engine.render import _cite_links_filter, render_email, render_markdown
from nintel.pipeline import build


def test_cite_links_renders_inline_markdown_without_breaking_cites():
    """Email prose: **bold** renders to <strong>, the {{cite:N}} stays a
    clickable anchor, raw ** never leaks, and escaping/snake_case are safe."""
    ref_index = {3: SimpleNamespace(url="https://example.com/x")}
    out = str(_cite_links_filter("风险在于**确认在野利用**{{cite:3}}，需警惕", ref_index))
    assert "<strong>确认在野利用</strong>" in out
    assert 'href="https://example.com/x"' in out and ">3</a>" in out
    assert "**" not in out
    # escaping preserved; lone/flanked asterisks + snake_case are not emphasis.
    assert str(_cite_links_filter("&<x> 与 store_recent_items 与 a * b", {})) == (
        "&amp;&lt;x&gt; 与 store_recent_items 与 a * b"
    )


@pytest.mark.parametrize("rtype", ["daily", "weekly"])
def test_email_renders(rtype):
    html = render_email(build(rtype, persist_items=False))
    assert html.startswith("<!doctype html>") or html.lstrip().startswith("<!doctype")
    # Dossier accent + 620px frame + preheader-driven content.
    assert "#0C6151" in html
    assert "620" in html
    # References section + per-item citation footer.
    assert "参考来源" in html
    assert "查看原文" in html
    # A real citation domain is present.
    assert "community.ui.com" in html or "reddit.com" in html


def test_daily_includes_omada_self_and_impact_labels():
    html = render_email(build("daily", persist_items=False))
    assert "Omada 自身舆情" in html
    # subject-aware impact labels for omada_self (canonical handoff v2 §修改2 /
    # web vocabulary): needs_fix→待修复, feature_input→功能需求.
    assert "待修复" in html      # needs_fix badge
    assert "功能需求" in html      # feature_input badge (NOT 功能输入)
    assert "功能输入" not in html  # guard against label drift
    # research-note vocabulary: needs_fix→修复建议, feature_input→需求信号.
    assert "需求信号" in html
    assert "修复建议" in html


def test_weekly_includes_strategy_store_dashboard_and_strength():
    html = render_email(build("weekly", persist_items=False))
    assert "市场策略洞察" in html              # strategy block
    assert "优势确认" in html                  # strength_confirm label (omada_self)
    assert "store.ui.com" in html              # store table content
    # dashboard is split into two sections, mirroring the web ReportView:
    # 「口碑与痛点分析」(sentiment panels) + 「数据看板」(KPI / sources / heat).
    assert "口碑与痛点分析" in html            # sentiment-panels section
    assert "口碑指数 · 本周" in html           # 口碑 vs panel (current week + 环比)
    assert "高频痛点 Top 5" in html            # pains panel
    assert "数据看板" in html                  # dashboard section
    assert "本周信号量" in html                # KPI: signals
    assert "平均热度" in html                  # KPI: avgHeat (full KPI set, not just 3 tiles)
    assert "各源贡献" in html                  # source-contribution bars
    assert "热度 Top 5" in html                # topHeat ranking
    assert "舆情对比" not in html              # old compressed vs widget is gone


@pytest.mark.parametrize("rtype", ["daily", "weekly"])
def test_markdown_renders(rtype):
    md = render_markdown(build(rtype, persist_items=False))
    assert "## 参考来源" in md
    assert "查看原文" in md
    # cite superscripts are converted to [n] markers.
    assert "[1]" in md


def test_weekly_markdown_has_strategy_and_store():
    md = render_markdown(build("weekly", persist_items=False))
    assert "🎯" in md
    assert "Store 动向" in md
