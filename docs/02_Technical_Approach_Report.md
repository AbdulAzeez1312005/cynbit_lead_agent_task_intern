# Technical Approach Report: Lead Qualification and Discovery-Brief Agent

## 1. Architecture

```
 inquiry text
      |
      v
 [1 Extract]  --rules own every decision field
      |        Ollama may clean company and need_summary for presentation only
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
| Extraction | Rules own intent, service hints, budget, urgency and timeline; local Ollama may clean company and need summary | Model output cannot change routing or score; deterministic behavior is the default | Model-led field extraction (tested separately and removed because it underperformed rules) |
| Model | Optional local Ollama `qwen3:1.7b` for summary cleanup and grounded brief drafting | Runs locally without an API key; errors fall back to rules and templates | Hosted model or GPU-backed local inference |
| Retrieval | In-memory TF-IDF over about 9 documents | The KB is tiny; a vector DB adds cost and moving parts with no accuracy gain at this size | Pinecone with embeddings once the KB holds case studies, past proposals and pricing notes |
| Scoring | Deterministic weighted rubric (budget 35, clarity 25, urgency 20, fit 20) | Sales can read and dispute every point; weights can be fitted to conversion data later | LLM-as-judge score (opaque, drifts between runs) |
| Brief generation | LLM drafts from retrieved excerpts; template fallback uses fixed service-specific and generic questions | LLM can tailor discovery questions to the lead's workflow and stack (for example, a voice receptionist's booking system and phone setup), while the fallback remains usable offline | Free generation without retrieval grounding (rejected) |
| Failure handling | Any LLM error returns to the rules path | A lead is never dropped because an API call failed | Hard fail |

## 3. Data pipeline

**Knowledge base** (`data/cynbit_kb.json`): 9 records (4 services, 3 products, BitElevate, engagement process) written from Cynbit's public pages, each with id, type, name, URL and text. Current KB is hand-curated for the PoC. Production version: scheduled crawl of cynbit.in, plus internal case studies and pricing guidance, chunked and embedded into Pinecone with source URL metadata.

**Evaluation data** (`eval/leads.jsonl`): 30 synthetic tuning inquiries I wrote to resemble real traffic, covering strong leads, vague one-liners, product inquiries (Revio, TenantEase, Studio), student inquiries, spam, and mixed INR/USD budgets. `eval/holdout_leads.jsonl` contains 10 additional cases, including paraphrase, Hinglish and multi-need examples. Several rules were changed after earlier inspection of overlapping holdout examples, including document/voice keywords, Hinglish handling, summary selection, and primary-service priority/fit; this is not an untouched holdout. Each case has hand-assigned labels, making the result a weak internal check rather than independent validation.

## 4. Prompt design

- **Optional enrichment prompt:** asks only for a stated company name and a concise need summary; pydantic validates the JSON. Extra intent, service, budget or urgency fields are ignored. Rule values remain authoritative.
- **Brief prompt:** fixed section list (Summary, Needs, Recommended offering, Risks, offering-specific discovery questions, Next step). It receives the inquiry, rule-owned fields and score, and retrieved KB excerpts. It is told not to invent prices, timelines, clients or capabilities; unsupported numeric claims cause a template fallback.
- **Injection defence:** the inquiry is delimited as untrusted data and the model is told to ignore instructions inside it. The pipeline has no tools that can send messages or change records, so the worst case is a poor draft that a human reviews.

## 5. Evaluation

Run `python eval/run_eval.py` for the final rules-only evaluation. `python eval/run_eval.py --mode hybrid` exercises the optional Ollama enrichment and brief while leaving evaluation decisions rule-owned.

Final rules-only results on the 30 hand-labelled synthetic leads:

| Mode | Intent | Primary service | Tier exact | Tier within one step |
|---|---:|---:|---:|---:|
| Final rules pipeline (30-case tuning set) | 30/30 = 100% | 26/27 = 96% | 24/30 = 80% | 30/30 = 100% |
| Ollama-only extraction experiment (removed) | 22/30 = 73% | 11/27 = 41% | 10/30 = 33% | 17/30 = 57% |
| Earlier hybrid extraction experiment (removed) | 22/30 = 73% | 11/27 = 41% | 20/30 = 67% | 28/30 = 93% |

The two model-led rows are historical experiments on the prior pipeline, when the model could decide intent and service hints. They explain why the final system makes those fields rules-only. In the final pipeline, Ollama (`qwen3:1.7b`) is restricted to optional company/summary wording and brief drafting; it cannot affect the rules-owned accuracy results.

The 30 original leads form the synthetic tuning set. The supplementary 10-lead set (`eval/holdout_leads.jsonl`) scored intent 10/10 (100%), primary service 8/9 (89%), exact tier 8/10 (80%), and tier within one step 10/10 (100%). These labels were also hand-written by the author. Several rules were changed after an earlier inspection of overlapping examples, so these results are a weak internal check rather than untouched validation. The primary-service miss was a local-search inquiry, which matched Revio rather than SEO/marketing; two tier labels differed by one tier.

How to read this honestly:
- **Not a held-out test.** I wrote the labels and the rules, then adjusted intent, urgency, clarity, and short-inquiry handling after inspecting examples. Treat these numbers as a smoke check, not an estimate of live accuracy.
- **Rules intent misses (0 on this version):** this synthetic set now includes product intent from the top product hint. This is likely optimistic because the labels and rules were authored together.
- **Threshold tuning:** a threshold search over the 30-case synthetic tuning set originally selected `HOT=61` and `WARM=39`, yielding 28/30 exact tiers at that time. The search script approximates the short-inquiry cap and does not exactly reproduce the scorer. After later extraction and primary-match changes, the current exact-tier result is 24/30. These cutoffs are fitted to synthetic labels, not real conversions.
- **Local model limits:** model-led extraction underperformed the rules baseline on these labels, and inference was slow on CPU (roughly four minutes per 30-lead run). The final pipeline does not use model predictions for decisions.
- **Scoring explanation:** clarity remains a simple proxy based on summary length and service hints, with a 5-point bonus when both a service hint and an 8-word summary are present. Scores of 15+ are described as clear, 10 to 14 as somewhat general, and below 10 as vague. This needs calibration with sales reviewers.
- **Discovery questions:** the rules template uses fixed service-specific questions plus generic questions. The LLM prompt asks for five questions tailored to the inquiry and offering. In a local clinic example it asked about call handling, appointment booking, existing tools, and data privacy, though some questions remained generic. This is a key quality difference to assess in a reviewed pilot; drafts still need human review.

## 6. Execution plan

| Phase | Work | Output |
|---|---|---|
| 0 (done) | KB, pipeline, rubric, Streamlit demo, 30-lead eval | This repo |
| 1 (week 1) | Collect a larger independent labeled set, calibrate thresholds with sales data, add embeddings, error and latency logging | Reliable evaluation and production readiness |
| 2 (weeks 2-3) | FastAPI service, contact-form webhook, CRM write-back (draft only), human accept/override buttons | Pilot on real inquiries |
| 3 (weeks 4-6) | Collect override data, refit scoring weights, proposal-outline generation, hot-lead Slack alert | Calibrated scoring |
| 4 | Package as a client offering, reuse for BitElevate applicants | Product/service |

**Team and cost:** one engineer for roughly 3 weeks to reach the pilot. LLM cost per lead is small at this prompt size, but I have not measured it; log token usage in phase 1.

**Success criteria for the pilot:** human override rate on tier under 25%, median time to first response under 1 hour in working hours, and sales team rating of brief usefulness of at least 4/5.

## 7. Limitations and next steps
- Synthetic test data and single labeller.
- Budget parser uses a fixed USD-INR rate and heuristics; it can misread unusual phrasing.
- Retrieval is lexical. Paraphrased needs ("my team re-types invoices") rely on the keyword lists and the LLM.
- Hinglish support is limited to common document terms (for example invoice, Tally, Excel, budget and lakh); Hindi urgency and broad conversational phrasing still need evaluation.
- No authentication, rate limiting or PII handling in the demo.
