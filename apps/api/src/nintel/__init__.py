"""Network Intel (``nintel``) backend package.

Competitive & sentiment intelligence engine for the TP-Link network products team.
The whole system is wired around a single contract — ``report.json`` (see
``contract/report.schema.json``). The engine produces it; every frontend
(web / email / Feishu) only renders it.

See ``ARCHITECTURE.md`` (§3) and SOLUTION §8 for the design.
"""

__version__ = "1.3.0"
