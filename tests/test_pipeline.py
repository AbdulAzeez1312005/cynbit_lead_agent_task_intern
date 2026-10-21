import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from leadagent import process_lead  # noqa: E402
from leadagent.extract import classify_intent, parse_budget_inr, parse_urgency  # noqa: E402
from leadagent.schema import ExtractedLead  # noqa: E402
from leadagent.scoring import score_lead  # noqa: E402


def test_budget_parsing():
    assert parse_budget_inr("Budget is around 4 lakh") == 400_000
    assert parse_budget_inr("budget 1.5 lakh over 3 months") == 150_000
    assert parse_budget_inr("about $4000") == 340_000
    assert parse_budget_inr("40k per month") == 40_000
    assert parse_budget_inr("we need it in 3 weeks") is None


def test_urgency():
    assert parse_urgency("need this ASAP")[0] == "high"
    assert parse_urgency("start this month") == ("high", True)
    assert parse_urgency("this month") == ("high", True)
    assert parse_urgency("no rush, just exploring")[0] == "low"


def test_unnamed_tenantease_inquiry_is_product_interest():
    assert classify_intent("I own 20 flats and want rent reminders") == "product_interest"


def test_unnamed_product_intent_from_top_hint():
    assert classify_intent("Please help manage Google reviews for my restaurant") == "product_interest"


def test_ollama_strips_think_block(monkeypatch):
    import json
    from leadagent import llm

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"message": {"content": '<think>hidden reasoning</think>{"intent":"client_project"}'}}).encode()

    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    assert llm._ollama_chat([], 0) == '{"intent":"client_project"}'


def test_spam_is_cold():
    rep = process_lead("We offer guest post and backlinks for sale on high DA sites.", use_llm=False)
    assert rep.extracted.intent == "not_a_fit"
    assert rep.score.tier == "cold"


def test_student_routes_to_bitelevate():
    rep = process_lead("I am a B.Tech student, want to join the AI internship.", use_llm=False)
    assert rep.primary_service == "prog-bitelevate"


def test_strong_lead_is_not_cold():
    rep = process_lead(
        "We need an AI agent to automate WhatsApp orders into Excel. Budget 4 lakh, start this month.",
        use_llm=False,
    )
    assert rep.primary_service == "svc-ai-automation"
    assert rep.score.tier in {"warm", "hot"}
    assert "Discovery questions" in rep.brief


def test_vague_is_cold():
    assert process_lead("Need a website.", use_llm=False).score.tier == "cold"


def test_reason_for_midrange_clarity_is_not_too_blunt():
    lead = ExtractedLead(
        need_summary="We need an AI voice receptionist for appointment booking.",
        service_hints=["svc-ai-automation"],
    )
    score = score_lead(lead, [])
    assert score.breakdown["clarity"] == 20
    assert "Clear need" in " ".join(score.reasons)


def test_clarity_reason_bands():
    for clarity, expected in [(5, "vague"), (10, "somewhat general"), (15, "Clear")]:
        lead = ExtractedLead(need_summary="short", service_hints=[])
        if clarity == 10:
            lead.service_hints = ["svc-ai-automation"]
        elif clarity == 15:
            lead.service_hints = ["svc-ai-automation", "svc-cloud"]
        score = score_lead(lead, [])
        assert score.breakdown["clarity"] == clarity
        assert expected.lower() in " ".join(score.reasons).lower()
