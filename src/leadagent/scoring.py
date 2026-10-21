"""Stage 3: transparent, auditable lead score (0-100).

Deliberately rule-based rather than an LLM judgement: sales teams need to see *why* a lead
is hot, and the weights can be tuned against real conversion data later.
"""
from __future__ import annotations

from .schema import ExtractedLead, KBMatch, ScoreResult

HOT, WARM = 65, 40


def score_lead(lead: ExtractedLead, matches: list[KBMatch]) -> ScoreResult:
    b: dict[str, int] = {}
    reasons: list[str] = []

    if lead.intent == "not_a_fit":
        return ScoreResult(
            total=3, tier="cold", breakdown={"fit": 0},
            reasons=["Looks like spam or a vendor pitch, not a buying inquiry."],
        )
    if lead.intent == "student_program":
        return ScoreResult(
            total=20, tier="cold", breakdown={"fit": 20},
            reasons=["Student/internship inquiry: route to BitElevate, not the sales pipeline."],
        )

    # Budget (0-35). Thresholds reflect a small agency's typical project sizes.
    bud = lead.budget_inr
    if bud is None:
        b["budget"] = 8
        reasons.append("No budget stated (ask in discovery).")
    elif bud >= 500_000:
        b["budget"] = 35
        reasons.append(f"Budget of about INR {bud:,} supports a full project.")
    elif bud >= 150_000:
        b["budget"] = 28
        reasons.append(f"Budget of about INR {bud:,} fits an MVP or automation build.")
    elif bud >= 50_000:
        b["budget"] = 18
        reasons.append(f"Budget of about INR {bud:,} suits a narrow scope.")
    else:
        b["budget"] = 6
        reasons.append(f"Budget of about INR {bud:,} is below typical project size.")

    # Need clarity (0-25)
    words = len(lead.need_summary.split())
    clarity = 5 + min(len(lead.service_hints), 3) * 5 + (5 if words >= 8 else 0)
    b["clarity"] = min(clarity, 25)
    if b["clarity"] >= 15:
        reasons.append("Need is reasonably clear; confirm implementation details.")
    elif b["clarity"] >= 12:
        reasons.append("Need is partially specified; confirm scope details.")
    else:
        reasons.append("Need is vague; clarify scope first.")

    # Urgency (0-20)
    b["urgency"] = {"high": 20, "medium": 14, "unspecified": 6, "low": 2}[lead.urgency]
    if lead.has_timeline:
        reasons.append("Has a concrete timeline.")

    # Service fit (0-20), from retrieval similarity to the KB
    top = matches[0].score if matches else 0.0
    b["fit"] = int(min(top / 0.35, 1.0) * 20)
    if matches:
        reasons.append(f"Best KB match: {matches[0].name} (similarity {matches[0].score}).")

    if lead.intent == "product_interest":
        b["fit"] = min(20, b["fit"] + 4)

    total = sum(b.values())
    # A one-line inquiry with no budget gives sales nothing to act on; never rank it above cold.
    if words < 5 and lead.budget_inr is None:
        total = min(total, WARM - 5)
        reasons.append("Inquiry is too short to qualify; capped at cold.")
    tier = "hot" if total >= HOT else "warm" if total >= WARM else "cold"
    return ScoreResult(total=total, tier=tier, breakdown=b, reasons=reasons)
