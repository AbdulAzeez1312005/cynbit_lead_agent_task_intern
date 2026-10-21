# AI Opportunity Report: Cynbit Technologies

**Prepared for:** Cynbit Technologies technical assessment
**Scope:** Where AI/ML creates the most value for Cynbit, and which single opportunity to prototype.

> **Evidence note.** Company facts come from cynbit.in (home, services, products and BitElevate pages). Figures Cynbit publishes about itself (for example 98% retention, "1000+ certified architects", 25k+ newsletter readers, client uptime and growth testimonials) are marketing claims and are treated as *claimed*, not verified. Third-party directories describe Cynbit as a Jaipur company founded in 2024 with roughly 10-49 staff; I have not independently verified this. Case-study and blog pages are not cited in this report.

## 1. Company snapshot

Cynbit positions itself as an "AI-first" software and automation company in Jaipur with three revenue lines:

| Line | What the site says |
|---|---|
| **Services** | AI automation (autonomous agents, LLM document/data-entry automation, voice agents, AI inside client SaaS), software development (web, mobile, backend, legacy migration), cloud (AWS, Azure), technical SEO and marketing |
| **Products** | Cynbit Studio (career/edtech: adaptive tests, AI code evaluation, mock interviews, resume engine), Revio (AI review replies, sentiment, crisis detection), TenantEase (rent tracking, reminders, dashboard) |
| **BitElevate** | Training and internship program with AI/ML/NLP/data tracks and college partnerships |

Stated stack: Python, FastAPI, OpenAI, LangChain, PyTorch, Pinecone, Postgres, Supabase. The site describes a six-step engagement process that begins with "discovery and audit", entered through a single "Start discovery" contact funnel.

**Implication:** Cynbit is small and product-minded. It already ships AI inside two products, so the best new opportunity should (a) use the existing stack, (b) strengthen revenue rather than duplicate a product, and (c) be buildable by a small team in weeks.

## 2. Market context

- **Enterprise demand in India is real and speed-sensitive.** EY India's 2025 C-suite survey of 200+ Indian enterprise leaders (published Nov 2025) reports 76% expect significant business impact from GenAI, 47% have multiple GenAI use cases live in production, and 91% rank deployment speed as the top factor when deciding whether to buy or build. For a small agency this favours narrow, fast-to-deploy automations over large platform builds.
- **Responsiveness to inbound leads is a recurring sales lever.** Vendor-compiled sales research (summarised by Teamgate, Dec 2025, citing InsideSales and Velocify) claims that leads contacted within minutes convert far better than leads contacted after a day, and that the average response time across industries is about 42 hours. These figures come from a vendor blog without a stated methodology or sample size and some of its numbers are internally inconsistent, so I use them only directionally: *faster, better-prioritised follow-up helps; magnitude is unproven.*

## 3. Opportunity long-list

Scored 1 (low) to 5 (high). "Revenue link" is how directly the use case touches new business or retention. "Build risk" is inverse (5 = easy to build well).

| # | Opportunity | Revenue link | Differentiation vs. existing products | Data availability | Build risk | Total /20 |
|---|---|---|---|---|---|---|
| 1 | **Lead qualification and discovery-brief agent** (internal, then sellable as a service) | 5 | 5 | 4 | 4 | **18** |
| 2 | BitElevate applicant triage and track recommender | 3 | 4 | 4 | 5 | 16 |
| 3 | TenantEase tenant assistant (chat, maintenance triage) | 3 | 3 | 3 | 3 | 12 |
| 4 | SEO and content audit agent | 4 | 3 | 4 | 3 | 14 |
| 5 | Cynbit Studio code-evaluation calibration | 3 | 2 | 3 | 2 | 10 |
| 6 | Project estimation assistant from past engagements | 4 | 4 | 2 | 3 | 13 |

Scores are my judgement from public information, not measured values.

## 4. Selected opportunity: Lead qualification and discovery-brief agent

### Problem
Every Cynbit engagement starts as a free-text inquiry through the contact page, calls or demo requests. Those inquiries vary widely: a founder with a budget and a deadline, a student asking about internships, a vendor pitching backlinks. In a small team, someone reads each one, decides whether it is worth a call, works out which service or product fits, and prepares for discovery. This is slow, inconsistent and depends on who happens to read it.

### Proposed solution
An agent that, for each inquiry:
1. Extracts structured fields (company, intent, budget in INR, urgency, services implied).
2. Retrieves the best-matching Cynbit offerings from a knowledge base built from Cynbit's own pages.
3. Scores the lead with an auditable rubric and assigns hot/warm/cold.
4. Drafts a one-page discovery brief with tailored questions and a next step.
5. Routes non-buyers (students to BitElevate, spam to a discard queue).

### Why this one
- **Revenue-adjacent:** it sits at the top of the funnel for the services line that Cynbit sells hardest (AI automation, software).
- **Dogfooding:** the agency's own "autonomous agents that manage leads" pitch becomes a live proof point and a reusable template that can be sold to clients.
- **Fits the stack:** Python, FastAPI, OpenAI, LangChain and Pinecone are all already in use.
- **Low risk:** a human stays in the loop; the agent drafts and ranks, it does not email prospects.
- **Does not cannibalise** Revio or Studio.

### Expected value (hypothesis, to be measured)
| Metric | How to measure | Target to test |
|---|---|---|
| Time from inquiry to first response | CRM timestamps | Under 1 hour in working hours |
| Share of inquiries triaged without manual reading | Agent output vs. human override rate | Over 70% |
| Discovery-call prep time | Sales team time log | Down by half |
| Qualified-lead to call conversion | CRM | Track before/after, no target claimed |

No ROI number is claimed here: Cynbit's real inquiry volume and conversion data are needed first.

### PoC evaluation snapshot

The current rules-first prototype scored 30/30 (100%) on intent, 27/27 (100%) on primary service, 28/30 (93%) on exact tier, and 30/30 (100%) within one tier on its 30-case synthetic tuning set. On 10 separately held-out synthetic inquiries it scored 10/10 (100%) on intent, 8/9 (89%) on primary service, 9/10 (90%) on exact tier, and 10/10 (100%) within one tier. The cutoffs (`HOT=61`, `WARM=39`) were selected on the tuning set only. These author-labelled cases are an internal check, not a forecast of live performance.

### Risks
| Risk | Mitigation |
|---|---|
| LLM invents capabilities or prices in a brief | Briefs use only retrieved KB excerpts; prompt forbids inventing prices, timelines or clients; human review |
| Prompt injection from inquiry text | Inquiry is wrapped as untrusted data; structured outputs; agent has no send-email tool |
| Scoring bias or wrong thresholds | Transparent rubric, override tracking, recalibrate on real conversion data |
| Personal data in inquiries | Store minimal fields, retention policy, avoid logging raw text to third parties without consent |
| Small KB goes stale | Re-crawl on a schedule; version the KB |

## 5. Follow-on roadmap
1. **Now (PoC, this repo):** extraction, retrieval, scoring, brief, evaluation on 30 labelled synthetic leads.
2. **Weeks 1-3:** connect to the real contact form and CRM, add human-override feedback capture, evaluate on real (anonymised) inquiries.
3. **Weeks 4-8:** proposal-outline generation, scheduled re-crawl of the KB, Slack/WhatsApp notifications for hot leads.
4. **Later:** package as a client offering ("AI lead desk"), and reuse the same pipeline for BitElevate applicant triage (runner-up opportunity).

## 6. Sources
- Cynbit Technologies website, cynbit.in (home, services, products, BitElevate pages), read October 2026.
- EY India, "The AIdea of India: Outlook 2026", Chapter 2 survey findings (16 Nov 2025): https://www.ey.com/en_in/insights/ai/agentic-ai-india/aidea-survey-findings
- Teamgate, lead response time study blog post (Dec 2025; vendor-compiled, methodology not stated): https://teamgate.com/blog/lead-response-time-study
