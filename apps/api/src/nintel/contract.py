"""Pydantic v2 models that EXACTLY mirror ``contract/report.schema.json``.

These models *are* the contract on the Python side: every field, enum and
optionality matches the JSON Schema (PRD v1.3 §7.9). Parsing is lossless —
``Report.model_validate(d).model_dump(...)`` round-trips back to ``d``.

Two validation layers are provided, intentionally:

* **Pydantic** — fast, typed, used everywhere internally.
* :func:`validate_against_schema` — authoritative ``jsonschema`` check against
  the on-disk schema file, used at the API/pipeline boundary and in tests so we
  catch any drift between the models and the canonical schema.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .config import get_settings

# ---------------------------------------------------------------------------
# Enums (kept as Literal aliases so they read like the schema)
# ---------------------------------------------------------------------------
ReportType = Literal["daily", "weekly"]
Subject = Literal["omada_self", "competitor", "industry"]
SourceTier = Literal["official", "community"]
SectionKey = Literal["omada_self", "competitor", "sentiment", "industry", "store", "dashboard"]
Source = Literal[
    "omada_community", "unifi_community", "unifi_product", "unifi_store",
    "unifi_release", "blog", "reddit", "youtube", "rss", "x",
]
Provenance = Literal["A", "B", "C", "D", "G", "H"]
Category = Literal[
    "bug", "feature_request", "praise", "pain_point", "new_product", "pricing",
    "firmware", "competitor", "sentiment", "industry", "industry_trend",
]
SignalStrength = Literal["high", "medium", "low"]
OmadaImpact = Literal[
    "threat", "opportunity", "neutral",
    "needs_fix", "feature_input", "strength_confirm", "unknown",
]
Sentiment = Optional[Literal["pos", "neg", "neu"]]
StoreDir = Literal["up", "down", "flat", "new"]
StoreStock = Literal["in", "low", "out"]


class _Strict(BaseModel):
    """Base config: forbid unknown keys (schema is additionalProperties:false)."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Leaf models
# ---------------------------------------------------------------------------
class Metrics(BaseModel):
    # Schema allows additionalProperties:true on metrics — keep extras.
    model_config = ConfigDict(extra="allow")

    likes: Optional[int] = None
    comments: Optional[int] = None
    views: Optional[int] = None
    score: Optional[int] = None
    note: Optional[str] = None


class IntelItem(_Strict):
    """A single normalized intelligence signal (schema ``$defs.intelItem``)."""

    id: str
    cite_id: int = Field(ge=1)
    subject: Subject
    source: Source
    source_domain: str
    source_tier: SourceTier
    source_label: Optional[str] = None
    tier_label: Optional[str] = None
    glyph: Optional[str] = None
    provenance: Optional[Provenance] = None
    title: str
    stage: Optional[str] = None
    badges: Optional[list[str]] = None
    summary: str
    category: Category
    signal_strength: Optional[SignalStrength] = None
    omada_impact: OmadaImpact
    impact_note: Optional[str] = None
    metrics: Optional[Metrics] = None
    sentiment: Sentiment = None
    relevance: Optional[float] = Field(default=None, ge=0, le=1)
    switch_intent: Optional[bool] = None
    date: str
    url: str


class Lead(_Strict):
    text: str
    strong: Optional[str] = None
    cite_refs: list[int] = Field(default_factory=list)


class StrategyPara(BaseModel):
    """Labeled paragraph ``[label, text-with-{{cite:N}}]`` (length-2 array)."""

    # Represented as a 2-tuple in JSON; we keep it as a plain list to round-trip.
    model_config = ConfigDict(extra="forbid")


class Strategy(_Strict):
    title: str
    period: Optional[str] = None
    paras: Optional[list[list[str]]] = None
    body: str
    cite_refs: list[int] = Field(default_factory=list)


class Tally(_Strict):
    signals: Optional[int] = None
    threat: Optional[int] = None
    opp: Optional[int] = None
    neutral: Optional[int] = None
    official: Optional[int] = None


class Section(_Strict):
    key: SectionKey
    title: str
    icon: Optional[str] = None
    desc: Optional[str] = None
    items: list[str] = Field(default_factory=list)
    # Optional insight.id refs (synthesized entries). When present the frontend
    # renders these instead of per-item entries.
    insights: Optional[list[str]] = None


class Reference(_Strict):
    cite_id: int = Field(ge=1)
    title: str
    source_domain: str
    source_tier: Optional[SourceTier] = None
    tier_label: Optional[str] = None
    date: str
    url: str


class StoreRow(_Strict):
    product: str
    cat: Optional[str] = None
    from_: Optional[float] = Field(default=None, alias="from")
    to: Optional[float] = None
    change: Optional[str] = None
    dir: Optional[StoreDir] = None
    stock: StoreStock

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class TopHot(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    title: Optional[str] = None
    score: Optional[float] = None


class Stats(BaseModel):
    # Schema: additionalProperties:true.
    model_config = ConfigDict(extra="allow")

    total_items: Optional[int] = None
    by_source: dict[str, int] = Field(default_factory=dict)
    by_impact: dict[str, int] = Field(default_factory=dict)
    top_hot: list[TopHot] = Field(default_factory=list)


class Insight(_Strict):
    """A synthesized thematic entry combining multiple real items (``$defs.insight``)."""

    id: str
    subject: Subject
    title: str
    body: str
    takeaway: Optional[str] = None
    omada_impact: Optional[OmadaImpact] = None
    cite_refs: list[int] = Field(default_factory=list)


class FunnelSource(_Strict):
    key: str
    label: str
    count: int


class Funnel(_Strict):
    """Pipeline provenance funnel for the subtitle (collected -> refined -> curated)."""

    collected: list[FunnelSource] = Field(default_factory=list)
    refined: Optional[int] = None       # 初筛: Python prefilter pool
    shortlisted: Optional[int] = None   # 精选: Sonnet value-selected
    curated: Optional[int] = None       # 策展: cited items
    byline: Optional[str] = None
    tz: Optional[str] = None


class Report(_Strict):
    """The top-level ``report.json`` document."""

    report_id: str
    type: ReportType
    date: str
    date_range: str
    generated_at: str
    title: Optional[str] = None
    lead: Lead
    strategy: Optional[Strategy] = None
    tally: Optional[Tally] = None
    sections: list[Section]
    items: list[IntelItem]
    # Synthesized thematic entries (v1.4); absent on legacy/offline reports.
    insights: Optional[list[Insight]] = None
    references: list[Reference]
    store: Optional[list[StoreRow]] = None
    stats: Stats
    # Pipeline provenance funnel for the subtitle (collected -> refined -> curated).
    funnel: Optional[Funnel] = None
    # Free-form charts payload (schema: object|null, additionalProperties:true).
    dashboard: Optional[dict[str, Any]] = None

    def dump(self) -> dict[str, Any]:
        """Serialize to a plain dict matching the JSON contract exactly.

        Round-trip is lossless: ``Report.model_validate(d).dump() == d`` for any
        schema-valid ``d``. We use ``exclude_unset=True`` so we emit *exactly*
        the keys that were present in the source — this preserves the seeds'
        mix of explicit nulls (``strategy: null``, ``sentiment: null``) and
        omitted-optional keys (e.g. a ``metrics`` block carrying only
        ``likes``/``comments``) without inventing ``null`` placeholders.
        ``by_alias=True`` restores ``from`` on store rows.
        """

        return self.model_dump(by_alias=True, exclude_unset=True)


# Forward-compat alias name used in some docs.
Dashboard = dict


# ---------------------------------------------------------------------------
# jsonschema bridge
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    path: Path = get_settings().schema_path
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator():
    from jsonschema import Draft202012Validator

    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_against_schema(doc: dict[str, Any]) -> None:
    """Validate ``doc`` against the on-disk JSON Schema.

    Raises ``jsonschema.ValidationError`` on the first failure (with a useful
    JSON-path), matching how the frontend's validator will behave.
    """

    _validator().validate(doc)


def iter_schema_errors(doc: dict[str, Any]):
    """Yield all schema validation errors (for diagnostics/tests)."""

    return sorted(_validator().iter_errors(doc), key=lambda e: list(e.path))


def load_report(doc: dict[str, Any], *, schema_check: bool = True) -> Report:
    """Parse a dict into a :class:`Report`, optionally schema-checking first."""

    if schema_check:
        validate_against_schema(doc)
    return Report.model_validate(doc)
