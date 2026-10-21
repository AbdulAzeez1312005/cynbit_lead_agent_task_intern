"""Streamlit demo: paste an inbound inquiry, get a scored lead and a discovery brief.

Run:  streamlit run app.py
Install Ollama and pull qwen3:1.7b for optional enrichment and brief drafting; decisions stay rule-based.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from leadagent import process_lead  # noqa: E402
from leadagent import llm  # noqa: E402

st.set_page_config(page_title="Cynbit Lead Qualifier (PoC)", page_icon="🎯", layout="wide")

SAMPLES = {
    "WhatsApp order automation (hot)": (
        "Hi, I'm the founder of Kiran Foods. We get 300+ WhatsApp orders a day and our team copies "
        "them into Excel by hand. We want an AI agent to read the messages and fill our order sheet. "
        "Budget is around 4 lakh and we want to start this month."
    ),
    "Restaurant reviews / Revio": (
        "We run 12 restaurants in Jaipur and manage Google reviews manually. Interested in a demo "
        "of Revio. ASAP please."
    ),
    "Vague one-liner (cold)": "Need a website.",
    "Student internship (route to BitElevate)": (
        "Hello, I am a B.Tech 3rd year student, want to join the AI internship at BitElevate."
    ),
    "Invoice document automation (hot)": (
        "Our invoices arrive as PDFs and scans and we type them into Tally. Want an LLM based "
        "document extraction automation. Budget 2.5 lakh, start next month."
    ),
    "Vendor spam": "We offer guest post and backlinks for sale on high DA sites. Reply for rate card.",
}

st.title("Cynbit Lead Qualifier")
st.caption("Proof of concept: extract, retrieve, score, brief. Built from Cynbit's public website content.")

with st.sidebar:
    st.header("Settings")
    llm_ready = llm.available()
    use_llm = st.toggle("Use Ollama enrichment and brief", value=False, disabled=not llm_ready)
    if not llm_ready:
        st.info("Ollama is unavailable or qwen3:1.7b is not pulled. Using rules and the template brief.")
    st.markdown("**Sample inquiries**")
    choice = st.selectbox("Load a sample", ["(none)"] + list(SAMPLES))

default = SAMPLES.get(choice, "")
text = st.text_area("Paste an inbound inquiry", value=default, height=160, key=f"inq-{choice}")

if st.button("Qualify lead", type="primary", disabled=not text.strip()):
    rep = process_lead(text, use_llm=use_llm)
    if use_llm and rep.mode == "rules":
        st.warning("Ollama did not return usable enrichment or a brief. Showing the rules-based result and template brief.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{rep.score.total}/100")
    c2.metric("Tier", rep.score.tier.upper())
    c3.metric("Intent", rep.extracted.intent.replace("_", " "))
    st.caption(f"Pipeline mode: {rep.mode}")

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Extracted fields")
        st.json(rep.extracted.model_dump())
        st.subheader("Score breakdown")
        st.bar_chart(rep.score.breakdown)
        for r in rep.score.reasons:
            st.write("-", r)
    with right:
        st.subheader("Retrieved Cynbit offerings")
        for m in rep.matches:
            st.write(f"**{m.name}** ({m.type}), similarity {m.score}  \n{m.url}")
        st.subheader("Discovery brief")
        st.markdown(rep.brief)
