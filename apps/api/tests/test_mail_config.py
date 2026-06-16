"""Offline tests for engine/mail_config.py (editable recipient store)."""
from __future__ import annotations

import dataclasses

import pytest

from nintel.config import get_settings
from nintel.engine import mail_config


@pytest.fixture
def settings(tmp_path):
    return dataclasses.replace(get_settings(), data_dir=tmp_path)


def test_save_load_roundtrip_trims_and_dedupes(settings):
    saved = mail_config.save(settings, to=["a@b.com", " a@b.com ", "c@d.com"], cc=["e@f.com"])
    assert saved == {"to": ["a@b.com", "c@d.com"], "cc": ["e@f.com"]}
    assert mail_config.load(settings) == saved


def test_save_rejects_invalid_email(settings):
    with pytest.raises(ValueError):
        mail_config.save(settings, to=["a@b.com", "not-an-email"], cc=[])


def test_load_missing_file_is_empty(settings):
    assert mail_config.load(settings) == {"to": [], "cc": []}


def test_resolve_falls_back_to_env_when_unset(settings):
    s = dataclasses.replace(settings, mail_to=("env@x.com",), mail_cc=())
    assert mail_config.resolve_recipients(s) == (["env@x.com"], [])


def test_resolve_prefers_saved_over_env(settings):
    s = dataclasses.replace(settings, mail_to=("env@x.com",))
    mail_config.save(s, to=["saved@y.com"], cc=[])
    assert mail_config.resolve_recipients(s) == (["saved@y.com"], [])


def test_unsubscribe_removes_case_insensitive(settings):
    mail_config.save(settings, to=["a@b.com", "c@d.com"], cc=["e@f.com"])
    res = mail_config.unsubscribe(settings, "A@B.com")
    assert res["removed"] is True
    assert mail_config.load(settings) == {"to": ["c@d.com"], "cc": ["e@f.com"]}


def test_unsubscribe_absent_is_noop(settings):
    mail_config.save(settings, to=["a@b.com"], cc=[])
    res = mail_config.unsubscribe(settings, "x@y.com")
    assert res["removed"] is False
    assert mail_config.load(settings)["to"] == ["a@b.com"]


def test_unsubscribe_materializes_env_fallback(settings):
    # recipients only in env -> unsubscribe writes the filtered list to the file
    s = dataclasses.replace(settings, mail_to=("keep@x.com", "drop@x.com"))
    res = mail_config.unsubscribe(s, "drop@x.com")
    assert res["removed"] is True
    assert mail_config.load(s)["to"] == ["keep@x.com"]
