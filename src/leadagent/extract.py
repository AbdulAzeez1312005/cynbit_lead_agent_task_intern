"""Stage 1: turn a messy inquiry into structured fields.

Two implementations share one output schema:
  * rules: deterministic regex/keyword extractor. Works offline, used as the fallback and
    as the baseline in the eval.
  * llm:   OpenAI structured-output extraction (see llm.py).
"""
from __future__ import annotations

import re
from typing import Optional

from .schema import ExtractedLead

_LAKH = 100_000
_CRORE = 10_000_000
_USD_INR = 85  # fixed rate for the PoC; make configurable for production

SERVICE_KEYWORDS = {
    "svc-ai-automation": [
        "ai", "llm", "agent", "agents", "chatbot", "automation", "automate", "gpt", "voice",
        "rag", "machine learning", "ml", "openai", "workflow", "ocr", "data entry",
    ],
    "svc-software": [
        "website", "web app", "mobile app", "app", "dashboard", "portal", "crm", "erp", "mvp",
        "backend", "api", "platform", "software", "migration", "legacy", "saas", "ecommerce",
    ],
    "svc-cloud": ["aws", "azure", "cloud", "devops", "hosting", "kubernetes", "uptime", "deploy"],
    "svc-seo-marketing": [
        "seo", "ranking", "organic", "ads", "marketing", "traffic", "funnel", "google ads", "leads",
    ],
    "prod-revio": ["reviews", "review", "google reviews", "reputation", "ratings", "zomato"],
    "prod-tenantease": ["tenant", "tenants", "rent", "landlord", "property", "pg ", "flats"],
    "prod-studio": ["placement", "placement cell", "mock interview", "resume", "coding test", "campus"],
    "prog-bitelevate": ["internship", "intern", "training", "course", "bootcamp", "student", "btech", "b.tech"],
}

_STUDENT = re.compile(r"\b(i am a student|btech|b\.tech|bca|mca|fresher|internship for me|"
                      r"want to (join|learn)|apply for (the )?(internship|training|program))", re.I)
_NOT_FIT = re.compile(r"\b(guest post|backlinks? for sale|buy followers|crypto giveaway|"
                      r"we offer (seo|leads)|sell(ing)? (you )?(a )?(database|email list)|"
                      r"partnership proposal for our services|job opening at our)\b", re.I)
_PRODUCT = re.compile(r"\b(demo of|pricing for|trial of|subscribe to|sign up for)\b", re.I)

_MONEY = re.compile(
    r"(?P<cur>₹|rs\.?|inr|\$|usd)?\s*(?P<num>\d+(?:[.,]\d+)*)\s*(?P<unit>lakhs?|lacs?|l\b|crores?|cr\b|k\b|m\b)?\s*(?P<cur2>inr|rupees|usd|dollars)?",
    re.I,
)


def parse_budget_inr(text: str) -> Optional[int]:
    """Best-effort budget extraction. Only trusts numbers that carry a currency or a
    lakh/crore/k unit, or that sit next to the word budget, so '3 weeks' is not a budget."""
    best = None
    low = text.lower()
    for m in _MONEY.finditer(text):
        cur = (m.group("cur") or m.group("cur2") or "").lower()
        unit = (m.group("unit") or "").lower()
        window = low[max(0, m.start() - 25): m.end() + 25]
        if not (cur or unit in {"lakh", "lakhs", "lac", "lacs", "l", "crore", "crores", "cr", "k", "m"}
                or "budget" in window):
            continue
        # ignore years and plain small counts without any money signal
        raw = m.group("num").replace(",", "")
        try:
            val = float(raw)
        except ValueError:
            continue
        if not cur and not unit and val < 1000:
            continue
        mult = 1
        if unit.startswith(("lakh", "lac")) or unit == "l":
            mult = _LAKH
        elif unit.startswith("cr"):
            mult = _CRORE
        elif unit == "k":
            mult = 1000
        elif unit == "m":
            mult = 1_000_000
        inr = val * mult
        if cur in {"$", "usd"} or m.group("cur2") in {"usd", "dollars"}:
            inr *= _USD_INR
        inr = int(inr)
        if best is None or inr > best:
            best = inr
    return best


def parse_urgency(text: str) -> tuple[str, bool]:
    t = text.lower()
    if re.search(r"\b(asap|urgent|immediately|this (week|month)|next (week|month)|start(ing)? (now|today|this month|next month)|within (a |\d+ )?(week|weeks|days?)|by (end of )?(this )?month)\b", t):
        return "high", True
    if re.search(r"\b(within|in|by|over) (the next )?(\d+|a|two|three|four|six) (month|months|quarter)\b|\bq[1-4]\b|\bnext quarter\b", t):
        return "medium", True
    if re.search(r"\b(exploring|just looking|no rush|someday|in the future|research(ing)?)\b", t):
        return "low", False
    return "unspecified", False


def classify_intent(text: str) -> str:
    if _NOT_FIT.search(text):
        return "not_a_fit"
    if _STUDENT.search(text):
        return "student_program"
    if _PRODUCT.search(text):
        return "product_interest"
    t = text.lower()
    # Naming one of Cynbit's own products is a strong signal the lead wants the product,
    # not a bespoke build.
    if re.search(r"\b(revio|tenantease|cynbit studio)\b", t):
        return "product_interest"
    return "client_project"


def service_hints(text: str) -> list[str]:
    t = " " + text.lower() + " "
    scores = {}
    for sid, kws in SERVICE_KEYWORDS.items():
        n = sum(1 for kw in kws if re.search(r"(?<![a-z])" + re.escape(kw.strip()) + r"(?![a-z])", t))
        if n:
            scores[sid] = n
    return [s for s, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]


def extract_company(text: str) -> Optional[str]:
    m = re.search(r"(?:from|at|with|of|represent(?:ing)?|founder of|ceo of|cto of)\s+([A-Z][\w&.\-]+(?:\s+[A-Z][\w&.\-]+){0,3})", text)
    if m:
        name = m.group(1).strip(" .,")
        if name.lower() not in {"india", "jaipur", "the", "our"}:
            return name
    return None


def extract_rules(text: str) -> ExtractedLead:
    urgency, has_tl = parse_urgency(text)
    first = re.split(r"(?<=[.!?])\s+", text.strip())[0][:220]
    return ExtractedLead(
        company=extract_company(text),
        intent=classify_intent(text),
        need_summary=first,
        budget_inr=parse_budget_inr(text),
        urgency=urgency,
        has_timeline=has_tl,
        service_hints=service_hints(text),
    )
