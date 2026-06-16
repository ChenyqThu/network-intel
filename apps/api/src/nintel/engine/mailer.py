"""Email transport via local davmail (SMTP send + IMAP draft).

davmail bridges a local SMTP (1025) / IMAP (1143) server to Exchange/O365 over
OAuth. Authentication here is plain SMTP/IMAP where the *password is the davmail
cipher key* (not the O365 password); the real OAuth token lives in davmail's
token.dat and refreshes itself. See ``apps/api/infra/davmail/README.md``.

Pure standard library — no third-party deps. Connection/auth failures raise
(fail loud) so a scheduled job surfaces "davmail down / token expired" instead of
silently not delivering.
"""
from __future__ import annotations

import imaplib
import re
import smtplib
import time
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

# RFC 6154 SPECIAL-USE \Drafts flag, e.g. b'(\\HasNoChildren \\Drafts) "/" "Drafts"'
_DRAFTS_FLAG = re.compile(rb"\\Drafts", re.IGNORECASE)


def build_report_message(
    *,
    from_email: str,
    from_name: str,
    to: list[str],
    cc: list[str] | None,
    subject: str,
    html: str,
    text: str | None = None,
) -> EmailMessage:
    """Build a multipart/alternative message (plain-text fallback + HTML body)."""
    msg = EmailMessage()
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=from_email.split("@")[-1])
    # set_content first (text/plain), then add_alternative (text/html): order makes
    # HTML the preferred rendering, with plain text as the fallback part.
    msg.set_content(text or "This report is best viewed in an HTML-capable mail client.")
    msg.add_alternative(html, subtype="html")
    return msg


def send_via_davmail(
    msg: EmailMessage,
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    recipients: list[str],
    timeout: int = 120,
) -> str:
    """Send ``msg`` over davmail's SMTP. ``recipients`` is the envelope set
    (to + cc + bcc). Returns the Message-ID. Raises on connection/auth failure."""
    with smtplib.SMTP(host, port, timeout=timeout) as s:
        s.ehlo()
        # davmail.smtpStartTls=false -> plaintext on the loopback leg; no starttls().
        s.login(user, password)
        s.send_message(msg, from_addr=user, to_addrs=recipients)
    return msg["Message-ID"]


def discover_drafts_folder(imap: imaplib.IMAP4, default: str = "Drafts") -> str:
    """Return the Drafts folder name via the RFC 6154 SPECIAL-USE ``\\Drafts``
    flag (handles localized names); fall back to ``default``."""
    typ, data = imap.list()
    if typ == "OK" and data:
        for entry in data:
            if entry and _DRAFTS_FLAG.search(entry):
                # entry: b'(\\HasNoChildren \\Drafts) "/" "Drafts"'
                return entry.decode("utf-8", "replace").rsplit(" ", 1)[-1].strip('"')
    return default


def append_draft_via_davmail(
    msg: EmailMessage,
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    drafts_folder: str | None = None,
    timeout: int = 60,
) -> str:
    """APPEND ``msg`` to the Exchange Drafts folder (review-then-send). Returns the
    folder it landed in. Raises on connection/auth/APPEND failure.

    Marks ``\\Draft \\Seen`` so Outlook treats it as a self-authored draft (no
    unread badge). ``drafts_folder`` defaults to SPECIAL-USE discovery.
    """
    raw = msg.as_bytes()
    imap = imaplib.IMAP4(host, port, timeout=timeout)  # imapStartTls=false -> plaintext
    try:
        imap.login(user, password)
        folder = drafts_folder or discover_drafts_folder(imap)
        typ, data = imap.append(
            folder, "(\\Draft \\Seen)", imaplib.Time2Internaldate(time.time()), raw
        )
        if typ != "OK":
            raise RuntimeError(f"IMAP APPEND to {folder!r} failed: {data!r}")
        return folder
    finally:
        try:
            imap.logout()
        except Exception:
            pass
