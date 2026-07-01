"""regen_synth CLI date resolution.

The script itself is live-only (loads .env, hits the LLM), but its job-date
resolution is pure and worth pinning so a prod "current week" run targets the
right dates. Loaded by path since ``scripts/`` isn't an importable package; the
module top-level is side-effect-free (all .env/build work lives in ``main()``).
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "regen_synth.py"


def _load():
    spec = importlib.util.spec_from_file_location("regen_synth", _PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


regen = _load()
TODAY = date(2026, 7, 1)


def test_no_date_flag_uses_pinned_seed_dates():
    jobs = regen.resolve_jobs(["weekly", "daily"], current=False, as_of=None, today=TODAY)
    assert jobs == [("weekly", date(2026, 5, 31)), ("daily", date(2026, 6, 2))]


def test_current_targets_today_for_each_kind():
    assert regen.resolve_jobs(["weekly"], current=True, as_of=None, today=TODAY) == [("weekly", TODAY)]


def test_as_of_overrides_for_each_kind():
    d = date(2026, 6, 15)
    jobs = regen.resolve_jobs(["weekly", "daily"], current=False, as_of=d, today=TODAY)
    assert jobs == [("weekly", d), ("daily", d)]


def test_current_and_as_of_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        regen.resolve_jobs(["weekly"], current=True, as_of=date(2026, 6, 15), today=TODAY)


def test_parse_args_defaults_and_type_filter():
    assert regen._parse_args([]).type == "both"
    ns = regen._parse_args(["--type", "weekly", "--current"])
    assert ns.type == "weekly" and ns.current is True
