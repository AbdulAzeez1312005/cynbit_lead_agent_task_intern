# Technical Approach Report: Lead Qualification and Discovery-Brief Agent

## 1. Architecture

```
 inquiry text
      |
      v
 [1 Extract]  --LLM structured output (OpenAI or local Ollama, JSON schema) --or-- rules fallback
      |        company, intent, budget_inr, urgency, service_hints
      v
 [2 Retrieve] TF-IDF over Cynbit knowledge base (services, products, BitElevate, process)
      |        top-3 offerings + similarity
      v
 [3 Score]    auditable rubric, 0-100 -> hot / warm / cold  (no LLM)
      |
      v
 [4 Brief]    LLM drafts brief from retrieved KB only  --or-- template fallback
      |
      v
 LeadReport (pydantic)  ->  Streamlit UI today, FastAPI + CRM webhook next
```

Code layout: `src/leadagent/{schema,extract,retrieval,scoring,brief,llm,pipeline}.py`, UI in `app.py`, evaluation in `eval/`.

## 2. Key design decisions

| Decision | Choice | Reason | Alternative considered |
|---|---|---|---|
| Extraction | Local Ollama with pydantic JSON schema, deterministic budget/timeline parsers, rule fallback | Structured output plus explicit deterministic fields; fallback keeps the demo working offline | Pure rules (brittle on paraphrases), unguarded LLM |
| Model | OpenAI `gpt-4o-mini` by default; optional local Ollama model set with `LEAD_AGENT_PROVIDER=ollama` and `LEAD_AGENT_MODEL` (tested with `qwen3:1.7b`) | OpenAI matches Cynbit's stated stack; Ollama allows local inference without an API key | Larger hosted model for brief quality; GPU-backed local inference |
| Retrieval | In-memory TF-IDF over about 9 documents | The KB is tiny; a vector DB adds cost and moving parts with no accuracy gain at this size | Pinecone with embeddings once the KB holds case studies, past proposals and pricing notes |
| Scoring | Deterministic weighted rubric (budget 35, clarity 25, urgency 20, fit 20) | Sales can read and dispute every point; weights can be fitted to conversion data later | LLM-as-judge score (opaque, drifts between runs) |
| Brief generation | LLM drafts from retrieved excerpts; template fallback uses fixed service-specific and generic questions | LLM can tailor discovery questions to the lead's workflow and stack (for example, a voice receptionist's booking system and phone setup), while the fallback remains usable offline | Free generation without retrieval grounding (rejected) |
| Failure handling | Any LLM error returns to the rules path | A lead is never dropped because an API call failed | Hard fail |

## 3. Data pipeline

**Knowledge base** (`data/cynbit_kb.json`): 9 records (4 services, 3 products, BitElevate, engagement process) written from Cynbit's public pages, each with id, type, name, URL and text. Current KB is hand-curated for the PoC. Production version: scheduled crawl of cynbit.in, plus internal case studies and pricing guidance, chunked and embedded into Pinecone with source URL metadata.

**Evaluation data** (`eval/leads.jsonl`): 30 synthetic inquiries I wrote to resemble real traffic, covering strong leads, vague one-liners, product inquiries (Revio, TenantEase, Studio), student inquiries, spam, and mixed INR/USD budgets. Each has a hand-assigned intent, expected primary service and expected tier. These are synthetic, so results show the pipeline behaves sensibly, not how it performs on Cynbit's real inbox.

## 4. Prompt design

- **Extraction prompt:** fixed system message defining the schema fields, INR conversion rules (1 lakh = 100000, 1 crore = 10000000, 1 USD = 85 INR) and the allowed KB ids. Output is validated by pydantic, so malformed output is rejected rather than trusted.
- **Brief prompt:** fixed section list (Summary, Needs, Recommended offering, Risks, 5 discovery questions, Next step). It receives only the inquiry, the extracted JSON, the score with reasons and the retrieved KB excerpts. It is told not to invent prices, timelines, clients or capabilities.
- **Injection defence:** the inquiry is delimited as untrusted data and the model is told to ignore instructions inside it. The pipeline has no tools that can send messages or change records, so the worst case is a poor draft that a human reviews.

## 5. Evaluation

Run `python eval/run_eval.py --mode rules`, `--mode ollama` and `--mode hybrid` after pulling the local model. Ollama-only uses raw extraction; hybrid keeps budget and urgency from deterministic parsers.

Results of the **rules pipeline** on the 30 synthetic leads:

| Metric | Result |
|---|---|
| Intent accuracy | 30/30 = 100% |
| Primary service accuracy (27 leads with a service) | 27/27 = 100% |
| Tier accuracy, exact | 25/30 = 83% |
| Tier within one step (hot/warm/cold are ordinal) | 30/30 = 100% |

Ollama-only and hybrid results on the current prompt/code were **not measured**: no Ollama executable or local API was available in this environment. This comparison is incomplete until both modes are run with `qwen3:1.7b` available:

| Metric | Result |
|---|---|
| Mode | Intent | Primary service | Tier exact | Tier within one step |
|---|---:|---:|---:|---:|
| Rules | 30/30 = 100% | 27/27 = 100% | 25/30 = 83% | 30/30 = 100% |
| Ollama only | Not measured | Not measured | Not measured | Not measured |
| Hybrid | Not measured | Not measured | Not measured | Not measured |

A previous run with an earlier prompt and pipeline measured Ollama `qwen3:1.7b` at 73% intent, 37% primary service, 40% exact tier, and 77% within one step. It is not directly comparable to the current implementation and is historical context only. All leads are synthetic, and labels were assigned by the project author; this is not a held-out test.

How to read this honestly:
- **Not a held-out test.** I wrote the labels and the rules, then adjusted intent, urgency, clarity, and short-inquiry handling after inspecting examples. Treat these numbers as a smoke check, not an estimate of live accuracy.
- **Rules intent misses (0 on this version):** this synthetic set now includes product intent from the top product hint. This is likely optimistic because the labels and rules were authored together.
- **Rules tier misses (5):** remaining misses cluster around the 65/40 thresholds, which are still hand-selected rather than calibrated on independent data.
- **Local model limits:** the tested 1.7B model underperformed the rules baseline on this dataset, and inference was slow on CPU. A larger model or GPU might change speed or accuracy, but this has not been measured.
- **Scoring explanation:** clarity remains a simple proxy based on summary length and service hints, with a 5-point bonus when both a service hint and an 8-word summary are present. Scores of 15+ are described as clear, 10–14 as somewhat general, and below 10 as vague. This needs calibration with sales reviewers.
- **Discovery questions:** the rules template uses fixed service-specific questions plus generic questions. The LLM prompt asks for five questions tailored to the inquiry and offering. In a local clinic example it asked about call handling, appointment booking, existing tools, and data privacy, though some questions remained generic. This is a key quality difference to assess in a reviewed pilot; drafts still need human review.

## 6. Execution plan

| Phase | Work | Output |
|---|---|---|
| 0 (done) | KB, pipeline, rubric, Streamlit demo, 30-lead eval | This repo |
| 1 (week 1) | Run `--llm` eval, tune thresholds, add embeddings for retrieval, error and latency logging | Measured LLM vs. rules comparison |
| 2 (weeks 2-3) | FastAPI service, contact-form webhook, CRM write-back (draft only), human accept/override buttons | Pilot on real inquiries |
| 3 (weeks 4-6) | Collect override data, refit scoring weights, proposal-outline generation, hot-lead Slack alert | Calibrated scoring |
| 4 | Package as a client offering, reuse for BitElevate applicants | Product/service |

**Team and cost:** one engineer for roughly 3 weeks to reach the pilot. LLM cost per lead is small at this prompt size, but I have not measured it; log token usage in phase 1.

**Success criteria for the pilot:** human override rate on tier under 25%, median time to first response under 1 hour in working hours, and sales team rating of brief usefulness of at least 4/5.

## 7. Limitations and next steps
- Synthetic test data and single labeller.
- Budget parser uses a fixed USD-INR rate and heuristics; it can misread unusual phrasing.
- Retrieval is lexical. Paraphrased needs ("my team re-types invoices") rely on the keyword lists and the LLM.
- English only. Hinglish and Hindi inquiries are likely in Jaipur and should be added to the eval.
- No authentication, rate limiting or PII handling in the demo.
