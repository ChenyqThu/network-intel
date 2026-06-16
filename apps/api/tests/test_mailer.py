"""Offline tests for the davmail email transport (engine/mailer.py).

No network: these exercise MIME construction and the SPECIAL-USE Drafts folder
parsing only. The live SMTP/IMAP send paths are covered by the manual smoke test
in docs/EMAIL-SENDING.md.
"""
from __future__ import annotations

from email.message import EmailMessage

from nintel.engine import mailer


def _build() -> EmailMessage:
    return mailer.build_report_message(
        from_email="lucien.chen@omadanetworks.com",
        from_name="Network Intel",
        to=["a@omadanetworks.com", "b@omadanetworks.com"],
        cc=["c@omadanetworks.com"],
        subject="Network Intel · 2026-06-01 · 日报",
        html="<h1>hello</h1><p>body</p>",
        text="hello\nbody",
    )


def test_build_report_message_headers():
    msg = _build()
    assert isinstance(msg, EmailMessage)
    assert msg["Subject"] == "Network Intel · 2026-06-01 · 日报"
    assert msg["From"] == "Network Intel <lucien.chen@omadanetworks.com>"
    assert msg["To"] == "a@omadanetworks.com, b@omadanetworks.com"
    assert msg["Cc"] == "c@omadanetworks.com"
    assert msg["Message-ID"] and msg["Message-ID"].endswith("@omadanetworks.com>")
    assert msg["Date"]


def test_build_report_message_multipart_alternative():
    msg = _build()
    assert msg.get_content_type() == "multipart/alternative"
    # plain first, html second -> HTML is the preferred rendering, plain the fallback.
    types = [p.get_content_type() for p in msg.iter_parts()]
    assert types == ["text/plain", "text/html"]
    html_part = next(p for p in msg.iter_parts() if p.get_content_type() == "text/html")
    assert "<h1>hello</h1>" in html_part.get_content()
    plain_part = next(p for p in msg.iter_parts() if p.get_content_type() == "text/plain")
    assert "hello" in plain_part.get_content()


def test_build_report_message_no_cc_and_default_plain():
    msg = mailer.build_report_message(
        from_email="x@y.com", from_name="X", to=["z@y.com"], cc=None,
        subject="s", html="<p>hi</p>",
    )
    assert "Cc" not in msg
    plain_part = next(p for p in msg.iter_parts() if p.get_content_type() == "text/plain")
    assert "HTML-capable" in plain_part.get_content()  # default fallback text


class _FakeIMAP:
    def __init__(self, entries: list[bytes]):
        self._entries = entries

    def list(self):  # noqa: A003 - mirrors imaplib.IMAP4.list
        return "OK", self._entries


def test_discover_drafts_folder_special_use():
    imap = _FakeIMAP([
        b'(\\HasNoChildren) "/" "INBOX"',
        b'(\\Sent \\HasNoChildren) "/" "Sent"',
        b'(\\Drafts \\HasNoChildren) "/" "Drafts"',
    ])
    assert mailer.discover_drafts_folder(imap) == "Drafts"


def test_discover_drafts_folder_localized_name():
    imap = _FakeIMAP([
        b'(\\HasNoChildren) "/" "INBOX"',
        '(\\Drafts \\HasNoChildren) "/" "草稿"'.encode("utf-8"),
    ])
    assert mailer.discover_drafts_folder(imap) == "草稿"


def test_discover_drafts_folder_fallback_default():
    imap = _FakeIMAP([b'(\\HasNoChildren) "/" "INBOX"'])
    assert mailer.discover_drafts_folder(imap) == "Drafts"
