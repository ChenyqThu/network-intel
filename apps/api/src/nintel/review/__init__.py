"""Human-review gate (PRD §3.2b).

A freshly built report is written to ``data/pending/<report_id>.json`` awaiting
human approval; :func:`approve` validates it, moves it to
``data/published/<report_id>.json`` and upserts it into the ``reports`` table so
the API serves it. The published dir is the source of truth the API reads from.

The cadence is config-driven via ``NINTEL_REVIEW_MODE``:

* ``manual`` (default) — :func:`submit` only writes to ``pending/``;
  a human must call :func:`approve`.
* ``auto`` — :func:`submit` publishes immediately.
"""

from .gate import (
    approve,
    list_pending,
    list_published,
    load_published,
    publish,
    reject,
    submit,
)

__all__ = [
    "submit",
    "approve",
    "reject",
    "publish",
    "list_pending",
    "list_published",
    "load_published",
]
