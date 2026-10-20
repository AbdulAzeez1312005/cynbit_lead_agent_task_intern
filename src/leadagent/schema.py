"""Data models shared by every stage of the pipeline."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Intent = Literal["client_project", "product_interest", "student_program", "not_a_fit"]
Urgency = Literal["high", "medium", "low", "unspecified"]
Tier = Literal["hot", "warm", "cold"]


class ExtractedLead(BaseModel):
    """Structured fields pulled out of a free-text inquiry."""

    company: Optional[str] = None
    intent: Intent = "client_project"
    need_summary: str = ""
    budget_inr: Optional[int] = Field(
        default=None, description="Stated budget converted to INR, if any"
    )
    urgency: Urgency = "unspecified"
    has_timeline: bool = False
    service_hints: list[str] = Field(default_factory=list)


class KBMatch(BaseModel):
    id: str
    name: str
    type: str
    url: str
    score: float


class ScoreResult(BaseModel):
    total: int
    tier: Tier
    breakdown: dict[str, int]
    reasons: list[str]


class LeadReport(BaseModel):
    extracted: ExtractedLead
    matches: list[KBMatch]
    primary_service: Optional[str]
    score: ScoreResult
    brief: str
    mode: Literal["rules", "llm"]
