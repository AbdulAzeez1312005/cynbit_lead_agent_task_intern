# Cynbit Lead Qualifier (AI/ML assessment PoC)

An agent that turns a messy inbound inquiry into structured fields, matches it to Cynbit's services and products, scores it, and drafts a discovery brief.

**Deliverables**
1. [AI Opportunity Report](docs/01_AI_Opportunity_Report.md)
2. Proof of concept: this repo (`app.py` Streamlit demo + `src/leadagent` pipeline)
3. [Technical Approach Report](docs/02_Technical_Approach_Report.md)

## Setup

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Rules are the default for intent, service matching, budget, urgency, retrieval, and scoring. Optional Ollama mode only cleans the company/need summary and drafts the brief; it cannot set routing or score. Install [Ollama](https://ollama.com/download), run `ollama pull qwen3:1.7b`, and start its local server. Defaults are `OLLAMA_HOST=http://localhost:11434` and `LEAD_AGENT_MODEL=qwen3:1.7b`; override either with an environment variable. Requests time out after 60 seconds (`LEAD_AGENT_TIMEOUT` can override this). The app checks `/api/tags` and the selected model before enabling Ollama. If unavailable, it shows a warning and uses rules plus the template brief.

Optional Ollama environment defaults are also listed in [.env.example](.env.example); export the values in your shell before running the app.

## Evaluate

```bash
python eval/run_eval.py                 # rules-only baseline
python eval/run_eval.py --mode hybrid   # optional Ollama enrichment and brief; decisions stay rule-owned
python eval/run_eval.py --data eval/holdout_leads.jsonl  # separate synthetic holdout
python eval/tune_thresholds.py          # fit cutoffs on eval/leads.jsonl only
pytest -q
```

For local Ollama evaluation in PowerShell:

```powershell
ollama pull qwen3:1.7b
$env:OLLAMA_HOST = "http://localhost:11434"
$env:LEAD_AGENT_MODEL = "qwen3:1.7b"
python eval/run_eval.py --mode hybrid
```

Final rules results on the 30 synthetic tuning leads: intent 30/30 (100%), primary service 27/27 (100%), exact tier 28/30 (93%), and tier within one step 30/30 (100%). The 10-case synthetic holdout scored intent 10/10 (100%), primary service 8/9 (89%), exact tier 9/10 (90%), and within one tier 10/10 (100%). Labels were hand-written by the author; this small holdout is not independent validation.

The score cutoffs were grid-tuned on the 30-case tuning set to `HOT=61`, `WARM=39` (28/30 exact tier). Do not adjust them based on the holdout. Historical model-led extraction experiments on the prior pipeline: Ollama-only intent 22/30 (73%), service 11/27 (41%), tier exact 10/30 (33%), within one step 17/30 (57%); earlier hybrid intent 22/30 (73%), service 11/27 (41%), exact 20/30 (67%), within one step 28/30 (93%). The current system no longer uses model extraction for decisions.

The original 30 leads are the tuning set. Ten additional paraphrased, Hinglish, multi-need, no-budget and product inquiries are isolated in `eval/holdout_leads.jsonl`; do not adjust rules or cutoffs based on those results. Both sets are synthetic and hand-labelled by the author, so the holdout is a small internal check rather than independent validation.

## Layout
```
app.py                  Streamlit UI
src/leadagent/          schema, extract, retrieval, scoring, brief, llm, pipeline
data/cynbit_kb.json     knowledge base written from cynbit.in
eval/                   labelled leads and eval script
eval/holdout_leads.jsonl separate synthetic holdout (do not tune on it)
tests/                  unit tests
docs/                   the two reports
```

Company facts come from Cynbit's public website; figures Cynbit publishes about itself are treated as claims. Independent candidate work, not affiliated with or endorsed by Cynbit.

## AI assistance

AI tools, including Claude and Codex, assisted with implementation and documentation. The project author is responsible for reviewing the code, evaluation results, and claims before submission.

