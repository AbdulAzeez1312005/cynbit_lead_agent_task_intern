import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from leadagent import process_lead  # noqa: E402
from leadagent.extract import parse_budget_inr, parse_urgency  # noqa: E402


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
