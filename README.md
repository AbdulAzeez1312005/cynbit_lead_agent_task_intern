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

Optional local LLM mode: install [Ollama](https://ollama.com/download), pull `qwen3:1.7b`, start its server, and set `LEAD_AGENT_PROVIDER=ollama` (optionally `OLLAMA_HOST` and `LEAD_AGENT_MODEL`; defaults are `http://localhost:11434` and `qwen3:1.7b`). Requests time out after 60 seconds (`LEAD_AGENT_TIMEOUT` can override this). The app checks the local tags endpoint and required model before enabling LLM mode. Without an available model, it uses the offline rules pipeline.

## Evaluate

```bash
python eval/run_eval.py --mode rules --verbose
python eval/run_eval.py --mode ollama    # raw local model extraction
python eval/run_eval.py --mode hybrid    # local model plus deterministic budget/timeline safeguards
pytest -q
```

For local Ollama evaluation in PowerShell:

```powershell
ollama pull qwen3:1.7b
$env:LEAD_AGENT_PROVIDER = "ollama"
$env:LEAD_AGENT_MODEL = "qwen3:1.7b"
python eval/run_eval.py --mode ollama
python eval/run_eval.py --mode hybrid
```

Results on the same 30 hand-labelled synthetic leads: rules — intent 100%, primary service 100%, tier 83% exact / 100% within one step; Ollama-only (`qwen3:1.7b`) — 73%, 41%, 33% / 57%; hybrid — 73%, 41%, 67% / 93%. These are not held-out results; see the technical report for limitations. The evaluator reports how many rows actually used LLM extraction and refuses to run model metrics if the selected Ollama model is unavailable.

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

