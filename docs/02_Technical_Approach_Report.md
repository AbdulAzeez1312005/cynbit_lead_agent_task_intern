# Technical Approach Report: Lead Qualification and Discovery-Brief Agent

## 1. Architecture

```
 inquiry text
      |
      v
 [1 Extract]  --LLM structured output (OpenAI, JSON schema) --or-- rules fallback
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
| Model | `gpt-4o-mini` by default, set via `LEAD_AGENT_MODEL` | Cheap and fast for short extraction and drafting; OpenAI is already in Cynbit's stated stack. Any model with structured outputs can replace it | Larger model for brief quality, to be tested |
| Retrieval | In-memory TF-IDF over about 9 documents | The KB is tiny; a vector DB adds cost and moving parts with no accuracy gain at this size | Pinecone with embeddings once the KB holds case studies, past proposals and pricing notes |
| Scoring | Deterministic weighted rubric (budget 35, clarity 25, urgency 20, fit 20) | Sales can read and dispute every point; weights can be fitted to conversion data later | LLM-as-judge score (opaque, drifts between runs) |
| Brief generation | LLM constrained to retrieved excerpts | Reduces fabricated claims | Free generation (rejected) |
| Failure handling | Any LLM error returns to the rules path | A lead is never dropped because an API call failed | Hard fail |

## 3. Data pipeline

**Knowledge base** (`data/cynbit_kb.json`): 9 records (4 services, 3 products, BitElevate, engagement process) written from Cynbit's public pages, each with id, type, name, URL and text. Current KB is hand-curated for the PoC. Production version: scheduled crawl of cynbit.in, plus internal case studies and pricing guidance, chunked and embedded into Pinecone with source URL metadata.

**Evaluation data** (`eval/leads.jsonl`): 30 synthetic inquiries I wrote to resemble real traffic, covering strong leads, vague one-liners, product inquiries (Revio, TenantEase, Studio), student inquiries, spam, and mixed INR/USD budgets. Each has a hand-assigned intent, expected primary service and expected tier. These are synthetic, so results show the pipeline behaves sensibly, not how it performs on Cynbit's real inbox.

## 4. Prompt design

- **Extraction prompt:** fixed system message defining the schema fields, INR conversion rules (1 lakh = 100000, 1 crore = 10000000, 1 USD = 85 INR) and the allowed KB ids. Output is validated by pydantic, so malformed output is rejected rather than trusted.
- **Brief prompt:** fixed section list (Summary, Needs, Recommended offering, Risks, 5 discovery questions, Next step). It receives only the inquiry, the extracted JSON, the score with reasons and the retrieved KB excerpts. It is told not to invent prices, timelines, clients or capabilities.
- **Injection defence:** the inquiry is delimited as untrusted data and the model is told to ignore instructions inside it. The pipeline has no tools that can send messages or change records, so the worst case is a poor draft that a human reviews.

## 5. Evaluation

Run: `python eval/run_eval.py --verbose` (add `--llm` with an API key).

Results of the **rules pipeline** on the 30 synthetic leads:

| Metric | Result |
|---|---|
| Intent accuracy | 27/30 = 90% |
| Primary service accuracy (27 leads with a service) | 27/27 = 100% |
| Tier accuracy, exact | 23/30 = 77% |
| Tier within one step (hot/warm/cold are ordinal) | 30/30 = 100% |

How to read this honestly:
- **Not a held-out test.** I wrote the labels and the rules, and made two changes after seeing the first run (recognise Cynbit product names as product interest; cap very short inquiries at cold). Exact tier accuracy moved from 22/30 to 23/30 and intent stayed at 27/30 across those changes. Real accuracy on unseen inquiries will likely be lower.
- **Remaining intent misses (3):** product inquiries that describe the need without naming the product (for example "adaptive coding test platform with mock interviews"). An LLM extractor should handle these better; this is the main reason the LLM path exists.
- **Tier misses (7):** mostly lead-like inquiries scoring one tier off, usually at the 65/40 thresholds, which are untuned guesses.
- **LLM mode has not been evaluated.** The environment this was built in had no API key or package access, so only the rules path was run. The LLM code path is written but untested end to end; run the eval with `--llm` before relying on it.

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
