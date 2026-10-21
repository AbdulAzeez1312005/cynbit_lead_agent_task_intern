"""End-to-end pipeline: extract -> retrieve -> score -> brief."""
from __future__ import annotations

from . import llm
from .brief import template_brief
from .extract import extract_rules, SERVICE_KEYWORDS
from .retrieval import Retriever
from .schema import LeadReport
from .scoring import score_lead

_retriever: Retriever | None = None


def _get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def process_lead(text: str, use_llm: bool = True, hybrid: bool = True) -> LeadReport:
    r = _get_retriever()
    rules_lead = extract_rules(text)
    lead = llm.extract_llm(text) if use_llm else None
    mode = "llm" if lead else "rules"
    if lead is None:
        lead = rules_lead
    elif hybrid:
        allowed_hints = set(SERVICE_KEYWORDS)
        hints = [hint for hint in lead.service_hints if hint in allowed_hints]
        lead = lead.model_copy(update={
            "budget_inr": rules_lead.budget_inr,
            "urgency": rules_lead.urgency,
            "has_timeline": rules_lead.has_timeline,
            "service_hints": hints or rules_lead.service_hints,
        })

    # Retrieve with the raw text plus the extracted summary so short inquiries still match.
    matches = r.search(text + " " + lead.need_summary, k=3)

    # Prefer an explicit service hint when present, otherwise the top retrieval hit.
    primary = None
    if lead.intent in {"client_project", "product_interest", "student_program"}:
        if lead.intent == "student_program":
            primary = "prog-bitelevate"
        elif lead.service_hints:
            primary = lead.service_hints[0]
        elif matches:
            primary = matches[0].id
        if primary and matches and primary not in {m.id for m in matches}:
            pass  # keep retrieval list as supporting evidence

    score = score_lead(lead, matches)
    kb_docs = {d["id"]: d["text"] for d in r.docs}
    brief = (llm.brief_llm(text, lead, matches, kb_docs, score, primary) if use_llm else None) \
        or template_brief(text, lead, matches, score, primary)
    return LeadReport(extracted=lead, matches=matches, primary_service=primary,
                      score=score, brief=brief, mode=mode)
