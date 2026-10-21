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
| Extraction | LLM with a pydantic JSON schema, rule-based fallback | Structured output gives validated fields; fallback keeps the demo working offline and gives a baseline to beat | Pure rules (brittle on messy text), pure LLM (no offline path) |
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

Run: `python eval/run_eval.py --verbose` for rules. For LLM mode, set `OPENAI_API_KEY` or set `LEAD_AGENT_PROVIDER=ollama` and pull a local model, then run `python eval/run_eval.py --llm`.

Results of the **rules pipeline** on the 30 synthetic leads:

| Metric | Result |
|---|---|
| Intent accuracy | 27/30 = 90% |
| Primary service accuracy (27 leads with a service) | 27/27 = 100% |
| Tier accuracy, exact | 24/30 = 80% |
| Tier within one step (hot/warm/cold are ordinal) | 30/30 = 100% |

Results of the **local LLM pipeline** on the same 30 leads, using Ollama `qwen3:1.7b` (Q4_K_M) on this CPU-only machine:

| Metric | Result |
|---|---|
| Intent accuracy | 22/30 = 73% |
| Primary service accuracy (27 leads with a service) | 10/27 = 37% |
| Tier accuracy, exact | 12/30 = 40% |
| Tier within one step | 23/30 = 77% |
| LLM extraction used | 29/30; one lead fell back to rules |

Across the 29 rows that used LLM extraction, intent accuracy was 21/29 = 72%, primary service accuracy was 9/26 = 35%, exact tier accuracy was 11/29 = 38%, and tier within one step was 22/29 = 76%. The all-row figures above include the single rules fallback. The local model scored below the rules baseline on these labels, so this run does not support replacing the rules path. It is also not a fair held-out comparison: all leads are synthetic and the labels were hand assigned by the project author.

How to read this honestly:
- **Not a held-out test.** I wrote the labels and the rules, and changed them after inspecting results: recognise Cynbit product names as product interest, cap very short inquiries at cold, and recognise "this month" / "start this month" as high urgency after a manual app run exposed the miss. Rules tier accuracy moved from 22/30 to 24/30; intent stayed at 27/30. Real accuracy on unseen inquiries will likely be lower.
- **Remaining intent misses (3):** product inquiries that describe the need without naming the product (for example "adaptive coding test platform with mock interviews"). This is a useful case to watch in the LLM comparison.
- **Rules tier misses (7):** mostly lead-like inquiries scoring one tier off, usually at the 65/40 thresholds, which are untuned guesses.
- **Local model limits:** the tested 1.7B model underperformed the rules baseline on this dataset, and inference was slow on CPU. A larger model or GPU might change speed or accuracy, but this has not been measured.
- **Scoring explanation:** clarity remains a simple proxy based on summary length and service hints. A 15/25 score is described as reasonably clear, 10–14 as partly specified, and below 10 as vague. A future rubric could reward concrete action-object details; the current score still needs calibration with sales reviewers.
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
