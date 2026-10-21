import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from leadagent import process_lead  # noqa: E402
from leadagent.extract import classify_intent, extract_company, parse_budget_inr, parse_urgency  # noqa: E402
from leadagent.schema import ExtractedLead  # noqa: E402
from leadagent.scoring import score_lead  # noqa: E402


def test_budget_parsing():
    assert parse_budget_inr("Budget is around 4 lakh") == 400_000
    assert parse_budget_inr("budget 1.5 lakh over 3 months") == 150_000
    assert parse_budget_inr("about $4000") == 340_000
    assert parse_budget_inr("40k per month") == 40_000
    assert parse_budget_inr("we need it in 3 weeks") is None


def test_company_extraction_rejects_product_names():
    assert extract_company("Interested in a demo of Revio") is None
    assert extract_company("We need integration with WhatsApp") is None
    assert extract_company("We are from PDF into Tally") is None


def test_company_stops_at_sentence_end():
    assert extract_company("I'm Priya from Green Leaf Hotels. We manage 5 hotels.") == "Green Leaf Hotels"
    assert extract_company("I'm the owner of Sharma Dental Care. We have three clinics.") == "Sharma Dental Care"


def test_urgency():
    assert parse_urgency("need this ASAP")[0] == "high"
    assert parse_urgency("start this month") == ("high", True)
    assert parse_urgency("this month") == ("high", True)
    assert parse_urgency("start next month") == ("high", True)
    assert parse_urgency("no rush, just exploring")[0] == "low"


def test_unnamed_tenantease_inquiry_is_product_interest():
    assert classify_intent("I own 20 flats and want rent reminders") == "product_interest"


def test_unnamed_product_intent_from_top_hint():
    assert classify_intent("Please help manage Google reviews for my restaurant") == "product_interest"


def test_ollama_think_block_is_stripped_before_validation(monkeypatch):
    import json
    from leadagent import llm

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"message": {"content": '<think>hidden reasoning</think>{"company":null,"need_summary":"Need rent reminders"}'}}).encode()

    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(
        llm.urllib.request, "urlopen",
        lambda *args, **kwargs: Response(),
    )
    result = llm.extract_llm("Need rent reminders for flats")
    assert result is not None
    assert result.need_summary == "Need rent reminders"


def test_ollama_brief_grounding_allows_known_budget_and_score(monkeypatch):
    from leadagent import llm
    from leadagent.schema import KBMatch, ScoreResult

    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(
        llm, "_ollama_chat",
        lambda *args, **kwargs: "Budget: INR 300,000. Score: 81/100.",
    )
    lead = ExtractedLead(need_summary="Automate document extraction", budget_inr=300_000)
    match = KBMatch(
        id="svc-ai-automation", name="AI Automation", type="service",
        url="https://example.test", score=0.4,
    )
    score = ScoreResult(total=81, tier="hot", breakdown={"budget": 35}, reasons=[])
    result = llm.brief_llm(
        "Automate document extraction", lead, [match],
        {"svc-ai-automation": "Document extraction automation"}, score,
        "svc-ai-automation",
    )
    assert result == "Budget: INR 300,000. Score: 81/100."


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


def test_pipeline_defaults_to_rules():
    assert process_lead("Need a website.").mode == "rules"


def test_service_discovery_question_bank_is_specific():
    from leadagent.brief import service_discovery_questions
    assert "How many properties and tenants do you manage?" in service_discovery_questions("prod-tenantease")
    invoice_questions = service_discovery_questions(
        "svc-ai-automation", "We process invoices in PDF into Tally"
    )
    assert any("invoices" in question and "formats" in question for question in invoice_questions)
    voice_questions = service_discovery_questions(
        "svc-ai-automation", "Need a voice receptionist for phone calls"
    )
    assert any("calls" in question and "transfer" in question for question in voice_questions)


def test_invoice_automation_is_hot_and_matched():
    inquiry = (
        "Our invoices arrive as PDFs and scans and we type them into Tally. "
        "Want an LLM based document extraction automation. Budget 2.5 lakh, start next month."
    )
    from leadagent.extract import extract_rules
    rules = extract_rules(inquiry)
    report = process_lead(inquiry, use_llm=False)
    assert "svc-ai-automation" in rules.service_hints
    assert rules.urgency == "high"
    assert report.primary_service == "svc-ai-automation"
    assert report.score.tier == "hot"


def test_hinglish_invoice_terms_match_automation():
    from leadagent.extract import extract_rules
    lead = extract_rules("Invoices scan karke Tally mein entry chahiye, budget 2 lakh.")
    assert lead.budget_inr == 200_000
    assert "svc-ai-automation" in lead.service_hints


def test_invalid_model_intent_and_service_cannot_override_rules(monkeypatch):
    import json
    from leadagent import llm

    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "_ollama_chat", lambda *args, **kwargs: json.dumps({
        "company": "Acme",
        "need_summary": "Manage Google reviews for a restaurant.",
        "intent": "not_a_real_intent",
        "service_hints": ["bad-service-id"],
    }))
    monkeypatch.setattr(llm, "brief_llm", lambda *args, **kwargs: None)
    report = process_lead("Please help manage Google reviews for my restaurant", use_llm=True)
    assert report.extracted.intent == "product_interest"
    assert report.extracted.service_hints[0] == "prod-revio"


def test_invalid_model_json_falls_back_to_rule_extraction(monkeypatch):
    from leadagent import llm
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "_ollama_chat", lambda *args, **kwargs: "not valid JSON")
    monkeypatch.setattr(llm, "brief_llm", lambda *args, **kwargs: None)
    report = process_lead("Need a website.", use_llm=True)
    assert report.mode == "rules"
    assert report.extracted.intent == "client_project"
    assert report.primary_service == "svc-software"


def test_rules_keep_two_sentence_need_summary_under_300_chars():
    from leadagent.extract import extract_rules
    text = "First sentence gives the concrete workflow. Second sentence adds an important integration detail. Third sentence is extra context."
    summary = extract_rules(text).need_summary
    assert summary.startswith("First sentence")
    assert "Second sentence" in summary
    assert "Third sentence" not in summary
    assert len(summary) <= 300


def test_summary_skips_clinic_introduction_and_keeps_voice_agent_request():
    from leadagent.extract import extract_rules
    inquiry = (
        "Hi, I'm the owner of Sharma Dental Care, we have 3 clinics in Jaipur. "
        "We need an AI voice receptionist that answers calls and books appointments. "
        "It should confirm available slots."
    )
    lead = extract_rules(inquiry)
    assert lead.need_summary.startswith("We need an AI voice receptionist")
    assert "Sharma Dental Care" not in lead.need_summary
    assert len(lead.need_summary) <= 300
    assert "svc-ai-automation" in lead.service_hints


def test_primary_service_controls_recommendation_and_fit():
    inquiry = (
        "Hi, I'm the owner of Sharma Dental Care, we have 3 clinics in Jaipur. "
        "We need an AI voice receptionist that answers calls and books appointments."
    )
    report = process_lead(inquiry, use_llm=False)
    assert report.primary_service == "svc-ai-automation"
    assert report.matches[0].id == "svc-ai-automation"
    assert "## Recommended Cynbit offering\n**AI Automation**" in report.brief
    assert any("Best KB match: AI Automation" in reason for reason in report.score.reasons)


def test_voice_discovery_questions_cover_clinic_setup():
    from leadagent.brief import service_discovery_questions
    questions = service_discovery_questions(
        "svc-ai-automation", "Need a voice receptionist for clinic calls and WhatsApp"
    )
    all_questions = " ".join(questions).lower()
    for term in ("calls", "whatsapp business api", "clinic booking", "hindi", "cannot answer"):
        assert term in all_questions


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
