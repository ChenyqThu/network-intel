"""Offline tests for engine/subscription.py (per-section subscriber store)."""
from __future__ import annotations

import dataclasses
import json

import pytest

from nintel.config import get_settings
from nintel.engine import subscription


@pytest.fixture
def settings(tmp_path):
    return dataclasses.replace(get_settings(), data_dir=tmp_path)


# ---------------------------------------------------------------------------
# load / save
# ---------------------------------------------------------------------------

def test_load_returns_empty_when_file_missing(settings):
    assert subscription.load(settings) == []


def test_save_load_roundtrip(settings):
    entries = [
        {"email": "alice@tp-link.com", "name": "Alice", "sections": ["sentiment"], "active": True},
        {"email": "bob@tp-link.com",   "name": "Bob",   "sections": [], "active": True},
    ]
    saved = subscription.save(settings, entries)
    assert len(saved) == 2
    assert subscription.load(settings) == saved


def test_save_deduplicates_by_email_last_wins(settings):
    entries = [
        {"email": "alice@tp-link.com", "name": "Alice-old", "sections": []},
        {"email": "alice@tp-link.com", "name": "Alice-new", "sections": ["progress"]},
    ]
    saved = subscription.save(settings, entries)
    assert len(saved) == 1
    assert saved[0]["name"] == "Alice-new"


def test_save_rejects_bad_email(settings):
    with pytest.raises(ValueError, match="invalid email"):
        subscription.save(settings, [{"email": "not-an-email", "sections": []}])


def test_save_drops_unknown_section_keys(settings):
    saved = subscription.save(
        settings,
        [{"email": "x@tp-link.com", "sections": ["sentiment", "BOGUS_KEY", "progress"]}],
    )
    assert saved[0]["sections"] == ["sentiment", "progress"]


# ---------------------------------------------------------------------------
# upsert / remove / set_active
# ---------------------------------------------------------------------------

def test_upsert_adds_new(settings):
    subscription.upsert(settings, {"email": "a@x.com", "sections": ["industry"]})
    assert len(subscription.load(settings)) == 1


def test_upsert_updates_existing(settings):
    subscription.upsert(settings, {"email": "a@x.com", "sections": ["industry"]})
    subscription.upsert(settings, {"email": "a@x.com", "name": "Updated", "sections": ["progress"]})
    subs = subscription.load(settings)
    assert len(subs) == 1
    assert subs[0]["name"] == "Updated"
    assert subs[0]["sections"] == ["progress"]


def test_remove_existing_returns_true(settings):
    subscription.upsert(settings, {"email": "a@x.com", "sections": []})
    assert subscription.remove(settings, "a@x.com") is True
    assert subscription.load(settings) == []


def test_remove_missing_returns_false(settings):
    assert subscription.remove(settings, "nobody@x.com") is False


def test_set_active_toggles_flag(settings):
    subscription.upsert(settings, {"email": "a@x.com", "sections": [], "active": True})
    assert subscription.set_active(settings, "a@x.com", active=False) is True
    assert subscription.load(settings)[0]["active"] is False


# ---------------------------------------------------------------------------
# active_subscribers / sections_for
# ---------------------------------------------------------------------------

def test_active_subscribers_filters_inactive(settings):
    subscription.save(settings, [
        {"email": "a@x.com", "sections": [], "active": True},
        {"email": "b@x.com", "sections": [], "active": False},
    ])
    active = subscription.active_subscribers(settings)
    assert len(active) == 1
    assert active[0]["email"] == "a@x.com"


def test_sections_for_empty_means_all(settings):
    sub = {"email": "a@x.com", "sections": [], "active": True, "name": "", "subscribed_at": "2026-01-01"}
    assert subscription.sections_for(sub) == set()


def test_sections_for_specific(settings):
    sub = {"email": "a@x.com", "sections": ["sentiment", "progress"], "active": True,
           "name": "", "subscribed_at": "2026-01-01"}
    assert subscription.sections_for(sub) == {"sentiment", "progress"}


# ---------------------------------------------------------------------------
# contract: SectionKey includes new keys
# ---------------------------------------------------------------------------

def test_new_section_keys_in_valid_set():
    assert "progress" in subscription.VALID_SECTION_KEYS
    assert "picks" in subscription.VALID_SECTION_KEYS


def test_progress_section_accepted_in_save(settings):
    saved = subscription.save(
        settings,
        [{"email": "pm@tp-link.com", "sections": ["progress", "sentiment", "industry"]}],
    )
    assert "progress" in saved[0]["sections"]
