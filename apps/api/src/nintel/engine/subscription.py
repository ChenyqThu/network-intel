"""Per-subscriber section preferences, persisted as JSON in the data dir.

Each subscriber chooses which *sections* they want to receive; the delivery
layer renders a personalised email containing only those sections.

Schema (``data/subscribers.json``)::

    [
      {
        "email": "alice@tp-link.com",
        "name": "Alice",
        "sections": ["progress", "sentiment", "industry"],
        "active": true,
        "subscribed_at": "2026-06-26"
      },
      ...
    ]

Rules
-----
* The file is read fresh on every delivery (no caching) so changes from the
  admin console take effect immediately without a restart.
* ``sections`` is a list of ``SectionKey`` strings.  An **empty list means all
  sections** (convenient default for "subscribe to everything").
* ``active: false`` silently opts the subscriber out without deleting the record
  — useful for vacations or temporary pauses.
* The env var ``NINTEL_MAIL_TO`` still seeds the *global* recipient list
  (``mail_config.py``); ``subscribers.json`` is a separate, finer-grained
  mechanism.  Both can co-exist: global recipients get the full report,
  subscriber-specific entries get their filtered slice.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from ..config import Settings

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# All currently valid section keys (mirrors contract.py SectionKey).
VALID_SECTION_KEYS: frozenset[str] = frozenset({
    "omada_self", "competitor", "sentiment", "industry",
    "store", "dashboard", "progress", "picks",
})


# ---------------------------------------------------------------------------
# Data-access helpers
# ---------------------------------------------------------------------------

def _path(settings: Settings) -> Path:
    return settings.data_dir / "subscribers.json"


def _clean_sections(raw: Any) -> list[str]:
    """Strip + validate section keys; silently drop unknowns."""
    out: list[str] = []
    for k in raw or []:
        k = str(k).strip()
        if k in VALID_SECTION_KEYS and k not in out:
            out.append(k)
    return out


def _validate_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalise + validate one subscriber entry.  Raises ``ValueError``."""
    email = str(entry.get("email") or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise ValueError(f"invalid email: {email!r}")
    sections = _clean_sections(entry.get("sections", []))
    return {
        "email": email,
        "name": str(entry.get("name") or "").strip(),
        "sections": sections,
        "active": bool(entry.get("active", True)),
        "subscribed_at": str(entry.get("subscribed_at") or date.today()),
    }


# ---------------------------------------------------------------------------
# Public CRUD
# ---------------------------------------------------------------------------

def load(settings: Settings) -> list[dict[str, Any]]:
    """Return all subscriber records (empty list when file is absent)."""
    p = _path(settings)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return [_validate_entry(e) for e in (data if isinstance(data, list) else [])]
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def save(settings: Settings, subscribers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate + persist the full subscriber list.  Raises ``ValueError`` on bad data."""
    cleaned = [_validate_entry(e) for e in subscribers]
    # Enforce email uniqueness (last entry wins).
    seen: dict[str, dict[str, Any]] = {}
    for e in cleaned:
        seen[e["email"]] = e
    deduped = list(seen.values())
    p = _path(settings)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
    return deduped


def upsert(settings: Settings, entry: dict[str, Any]) -> dict[str, Any]:
    """Add or update a single subscriber.  Returns the saved entry."""
    validated = _validate_entry(entry)
    current = load(settings)
    updated = [e for e in current if e["email"] != validated["email"]]
    updated.append(validated)
    save(settings, updated)
    return validated


def remove(settings: Settings, email: str) -> bool:
    """Remove a subscriber by email.  Returns True if the record existed."""
    target = (email or "").strip().lower()
    current = load(settings)
    before = len(current)
    remaining = [e for e in current if e["email"] != target]
    if len(remaining) < before:
        save(settings, remaining)
        return True
    return False


def set_active(settings: Settings, email: str, *, active: bool) -> bool:
    """Toggle ``active`` flag for a subscriber.  Returns True on success."""
    target = (email or "").strip().lower()
    current = load(settings)
    found = False
    for e in current:
        if e["email"] == target:
            e["active"] = active
            found = True
    if found:
        save(settings, current)
    return found


# ---------------------------------------------------------------------------
# Delivery helper
# ---------------------------------------------------------------------------

def active_subscribers(settings: Settings) -> list[dict[str, Any]]:
    """Return only ``active: true`` subscribers."""
    return [e for e in load(settings) if e.get("active", True)]


def sections_for(subscriber: dict[str, Any]) -> set[str]:
    """Section keys for one subscriber.  Empty set = all sections."""
    return set(subscriber.get("sections") or [])
