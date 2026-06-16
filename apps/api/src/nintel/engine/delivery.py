"""Deliver a published report by email via davmail.

Shared orchestration for the CLI (`pipeline send`) and the admin console
(`POST /api/admin/published/{id}/email`): render the report, build the MIME, and
either stage a draft or send. Keeps `engine/mailer.py` pure transport — this is
the layer that knows about Settings + rendering.
"""
from __future__ import annotations

from typing import Any

from ..config import Settings
from ..contract import Report
from . import mail_config, mailer, render


class MailConfigError(ValueError):
    """davmail credentials or recipients are not configured (operator error)."""


def deliver_report(report: Report, *, mode: str, settings: Settings) -> dict[str, Any]:
    """Render ``report`` and deliver it. ``mode`` is ``"draft"`` or ``"send"``.

    Returns a small result dict (mode, report_id, + folder | message_id/to).
    Raises ``MailConfigError`` for missing config; transport errors propagate.
    """
    if mode not in ("draft", "send"):
        raise MailConfigError(f"mode must be 'draft' or 'send', got {mode!r}")

    user = settings.davmail_user or settings.mail_from
    from_email = settings.mail_from or settings.davmail_user
    if not user or not settings.davmail_cipher_key:
        raise MailConfigError(
            "set NINTEL_DAVMAIL_USER and NINTEL_DAVMAIL_CIPHER_KEY "
            "(see apps/api/infra/davmail/README.md)"
        )
    to, cc = mail_config.resolve_recipients(settings)
    if mode == "send" and not to:
        raise MailConfigError("no recipients — add them in 邮件设置 (or set NINTEL_MAIL_TO)")

    cadence = "周报" if report.type == "weekly" else "日报"
    msg = mailer.build_report_message(
        from_email=from_email,
        from_name=settings.mail_from_name,
        to=to or [from_email],
        cc=cc or None,
        subject=f"Network Intel · {report.date} · {cadence}",
        html=render.render_email(report),
        text=render.render_markdown(report),
    )

    if mode == "draft":
        folder = mailer.append_draft_via_davmail(
            msg,
            host=settings.davmail_host,
            port=settings.davmail_imap_port,
            user=user,
            password=settings.davmail_cipher_key,
            drafts_folder=settings.drafts_folder,
        )
        return {"mode": "draft", "report_id": report.report_id, "folder": folder}

    mid = mailer.send_via_davmail(
        msg,
        host=settings.davmail_host,
        port=settings.davmail_smtp_port,
        user=user,
        password=settings.davmail_cipher_key,
        recipients=[*to, *cc],
    )
    return {"mode": "send", "report_id": report.report_id, "message_id": mid, "to": to}
