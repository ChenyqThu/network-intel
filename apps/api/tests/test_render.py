"""Email + markdown render tests."""

from __future__ import annotations

import pytest

from nintel.engine.render import render_email, render_markdown
from nintel.pipeline import build


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
    assert "数据看板" in html                  # dashboard section
    assert "舆情对比" in html                  # dashboard vs widget


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
