"""End-to-end pipeline: extract -> retrieve -> score -> brief."""
from __future__ import annotations

from . import llm
from .brief import template_brief
from .extract import extract_rules
from .retrieval import Retriever
from .schema import LeadReport
from .scoring import score_lead

_retriever: Retriever | None = None


def _get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def process_lead(text: str, use_llm: bool = False, hybrid: bool = True) -> LeadReport:
    r = _get_retriever()
    rules_lead = extract_rules(text)
    enrichment = llm.extract_llm(text) if use_llm and hybrid else None
    # Routing and scoring fields remain rule-owned; the model supplies only
    # optional presentation fields for the discovery brief.
    lead = rules_lead
    if enrichment:
        lead = rules_lead.model_copy(update={
            "company": enrichment.company or rules_lead.company,
            "need_summary": enrichment.need_summary.strip() or rules_lead.need_summary,
        })

    # Use the cleaned need summary so introductions do not dominate retrieval.
    all_matches = r.search(rules_lead.need_summary or text, k=len(r.docs))

    # Prefer an explicit service hint when present, otherwise the top retrieval hit.
    primary = None
    if lead.intent in {"client_project", "product_interest", "student_program"}:
        if lead.intent == "student_program":
            primary = "prog-bitelevate"
        elif lead.service_hints:
            primary = lead.service_hints[0]
        elif all_matches:
            primary = all_matches[0].id

    # Keep the rule-selected offering first even when a product description has
    # stronger incidental vocabulary overlap (for example, “clinics”).
    primary_match = next((m for m in all_matches if m.id == primary), None)
    if primary and primary_match is None:
        doc = next((d for d in r.docs if d["id"] == primary), None)
        if doc:
            from .schema import KBMatch
            primary_match = KBMatch(id=doc["id"], name=doc["name"], type=doc["type"], url=doc["url"], score=0.0)
    matches = ([primary_match] if primary_match else []) + [m for m in all_matches if m.id != primary][:2]

    score = score_lead(rules_lead, matches, primary)
    kb_docs = {d["id"]: d["text"] for d in r.docs}
    llm_brief = llm.brief_llm(text, lead, matches, kb_docs, score, primary) if use_llm and hybrid else None
    brief = llm_brief or template_brief(text, lead, matches, score, primary)
    mode = "hybrid" if enrichment or llm_brief else "rules"
    return LeadReport(extracted=lead, matches=matches, primary_service=primary,
                      score=score, brief=brief, mode=mode)
