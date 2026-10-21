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

Optional LLM mode with OpenAI: set `OPENAI_API_KEY` (and optionally `LEAD_AGENT_MODEL`, default `gpt-4o-mini`). Or install [Ollama](https://ollama.com/download), pull a model with `ollama pull qwen3:1.7b`, then set `LEAD_AGENT_PROVIDER=ollama` and optionally `LEAD_AGENT_MODEL=qwen3:1.7b` before launching. The default model for Ollama is `qwen3:1.7b`; the local Ollama server must be running. Without a configured LLM provider the app runs the offline rules pipeline, so it always works.

## Evaluate

```bash
python eval/run_eval.py --verbose        # rules baseline
python eval/run_eval.py --llm            # OpenAI key, or LEAD_AGENT_PROVIDER=ollama with a local model
pytest -q
```

For local Ollama evaluation in PowerShell:

```powershell
ollama pull qwen3:1.7b
$env:LEAD_AGENT_PROVIDER = "ollama"
$env:LEAD_AGENT_MODEL = "qwen3:1.7b"
python eval/run_eval.py --llm
```

Current rules-baseline results on 30 hand-labelled synthetic leads: intent 90%, primary service 100%, tier 80% exact and 100% within one step. On the same synthetic leads, local Ollama `qwen3:1.7b` achieved intent 73%, primary service 37%, tier 40% exact and 77% within one step; 29 of 30 rows used LLM extraction. These are not held-out results; see the technical report for caveats. The evaluator reports how many rows were actually extracted with an LLM, since unavailable models fall back to rules.

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

