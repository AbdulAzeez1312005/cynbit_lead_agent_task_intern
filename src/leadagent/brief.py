"""Template-based discovery brief, used when no LLM is available."""
from __future__ import annotations

from .schema import ExtractedLead, KBMatch, ScoreResult

_QUESTIONS = {
    "svc-ai-automation": [
        "Which manual process costs the most time today, and how many hours a week?",
        "Where does the data live (CRM, email, spreadsheets, PDFs) and who owns it?",
        "What does a correct output look like, and who reviews mistakes?",
        "How many invoices or other documents arrive each day, and which formats do they use?",
        "Which fields should be extracted, and where should the verified data be entered?",
        "For voice agents, which calls should be handled and how should transfers or failures work?",
    ],
    "svc-software": [
        "Who are the users and what are the top three workflows?",
        "Is there an existing system or design to integrate with or migrate from?",
        "What is the launch date and what must be in version one?",
    ],
    "svc-cloud": [
        "What is the current hosting setup and monthly cost?",
        "What are the uptime, compliance or data-residency requirements?",
    ],
    "svc-seo-marketing": [
        "What are the current traffic and lead numbers per month?",
        "Which markets and keywords matter most?",
    ],
    "prod-revio": ["How many locations and review platforms do you manage?"],
    "prod-tenantease": ["How many properties and tenants do you manage?"],
    "prod-studio": ["How many students per batch, and which assessments do you run today?"],
}
_GENERIC = ["What is the budget range and decision timeline?", "Who else is involved in the decision?"]


def service_discovery_questions(primary: str | None, inquiry: str = "") -> list[str]:
    """Return offering-specific question prompts for the brief drafter."""
    text = inquiry.lower()
    if primary == "svc-ai-automation" and any(word in text for word in ("invoice", "pdf", "tally", "scan", "ocr")):
        return [
            "How many invoices or other documents arrive each day, and which formats do they use?",
            "Which fields should be extracted, and where should verified data be entered?",
            "How should low-confidence or mismatched fields be reviewed?",
        ]
    if primary == "svc-ai-automation" and any(word in text for word in ("voice", "call", "phone", "receptionist")):
        return [
            "Which calls should the voice agent handle, and when should it transfer to a person?",
            "Which phone system and booking tools should it integrate with?",
            "How should it handle unclear requests, cancellations, and after-hours calls?",
        ]
    return list(_QUESTIONS.get(primary or "", []))[:3]


def template_brief(text: str, lead: ExtractedLead, matches: list[KBMatch],
                   score: ScoreResult, primary: str | None) -> str:
    top = matches[0] if matches else None
    qs = service_discovery_questions(primary, text)
    if lead.budget_inr is None:
        qs.append(_GENERIC[0])
    if not lead.has_timeline:
        qs.append(_GENERIC[1])
    bud = f"about INR {lead.budget_inr:,}" if lead.budget_inr else "not stated"
    lines = [
        f"# Discovery brief: {lead.company or 'Unnamed lead'}",
        f"**Score:** {score.total}/100 ({score.tier.upper()})  |  **Intent:** {lead.intent}",
        "",
        "## Summary",
        lead.need_summary or text[:200],
        "",
        f"## Facts extracted\n- Budget: {bud}\n- Urgency: {lead.urgency}",
        "",
        "## Recommended Cynbit offering",
        (f"**{top.name}** ({top.url}). Matched on the wording of the inquiry."
         if top else "No clear match; qualify manually."),
        "",
        "## Why this score",
        *[f"- {r}" for r in score.reasons],
        "",
        "## Discovery questions",
        *[f"{i}. {q}" for i, q in enumerate(qs[:5], 1)],
        "",
        "## Suggested next step",
        {
            "hot": "Book a discovery call within 24 hours.",
            "warm": "Send a short qualification email and a case study, then follow up in 3 days.",
            "cold": "Add to nurture list or route to the right team.",
        }[score.tier],
    ]
    return "\n".join(lines)
