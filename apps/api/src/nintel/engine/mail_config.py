"""Operator-editable email recipient config, persisted as JSON in the data dir.

Read fresh on every send (no caching) so edits from the admin console take effect
immediately, no restart — matching how reports are served per-request. Falls back
to the ``NINTEL_MAIL_TO`` / ``NINTEL_MAIL_CC`` env vars when the file is absent or
has no entries, so the env-only path keeps working.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..config import Settings

# Pragmatic email check (not RFC-complete): non-space local@domain.tld.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _path(settings: Settings) -> Path:
    return settings.data_dir / "mail_config.json"


def _clean(addrs: Any) -> list[str]:
    """Strip, drop empties, de-dupe (order-preserving)."""
    out: list[str] = []
    for a in addrs or []:
        a = str(a or "").strip()
        if a and a not in out:
            out.append(a)
    return out


def invalid(addrs: list[str]) -> list[str]:
    """Return the malformed entries (empty list => all valid)."""
    return [a for a in addrs if not _EMAIL.match(a)]


def load(settings: Settings) -> dict[str, list[str]]:
    """Read the saved config (``{"to": [...], "cc": [...]}``); {} when absent."""
    p = _path(settings)
    data: dict[str, Any] = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    return {"to": _clean(data.get("to")), "cc": _clean(data.get("cc"))}


def save(settings: Settings, *, to: list[str], cc: list[str]) -> dict[str, list[str]]:
    """Validate + persist the recipient config. Raises ``ValueError`` on bad email."""
    cfg = {"to": _clean(to), "cc": _clean(cc)}
    bad = invalid(cfg["to"]) + invalid(cfg["cc"])
    if bad:
        raise ValueError(f"invalid email address(es): {', '.join(bad[:5])}")
    p = _path(settings)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


def resolve_recipients(settings: Settings) -> tuple[list[str], list[str]]:
    """(to, cc) for delivery: the saved config, falling back to env when empty."""
    cfg = load(settings)
    to = cfg["to"] or list(settings.mail_to)
    cc = cfg["cc"] or list(settings.mail_cc)
    return to, cc
