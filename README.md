# Cynbit Lead Qualifier (AI/ML assessment PoC)

An agent that turns a messy inbound inquiry into structured fields, matches it to Cynbit's services and products, scores it, and drafts a discovery brief.

**Deliverables**
1. [AI Opportunity Report](docs/01_AI_Opportunity_Report.md)
2. Proof of concept: this repo (`app.py` Streamlit demo + `src/leadagent` pipeline)
3. [Technical Approach Report](docs/02_Technical_Approach_Report.md)

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Optional LLM mode: `export OPENAI_API_KEY=...` (and optionally `LEAD_AGENT_MODEL`, default `gpt-4o-mini`). Without a key the app runs the offline rules pipeline, so it always works.

## Evaluate

```bash
python eval/run_eval.py --verbose        # rules baseline
python eval/run_eval.py --llm            # needs OPENAI_API_KEY
pytest -q
```

Current rules-baseline results on 30 hand-labelled synthetic leads: intent 90%, primary service 100%, tier 77% exact and 100% within one step. These are not held-out results; see the technical report for caveats. LLM mode has not yet been evaluated.

## Layout
```
app.py                  Streamlit UI
src/leadagent/          schema, extract, retrieval, scoring, brief, llm, pipeline
data/cynbit_kb.json     knowledge base written from cynbit.in
eval/                   labelled leads and eval script
tests/                  unit tests
docs/                   the two reports
```

Company facts come from Cynbit's public website; figures Cynbit publishes about itself are treated as claims. Independent candidate work, not affiliated with or endorsed by Cynbit.

## AI assistance

AI tools, including Claude and Codex, assisted with implementation and documentation. The project author is responsible for reviewing the code, evaluation results, and claims before submission.

