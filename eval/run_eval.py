"""Evaluate the pipeline against hand-labelled synthetic leads.

Usage:
    python eval/run_eval.py            # rules baseline (offline)
    python eval/run_eval.py --mode rules|hybrid

Metrics: intent accuracy, primary-service accuracy (on leads that have a service),
tier accuracy, and tier within-one-step accuracy (hot/warm/cold are ordinal).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leadagent import process_lead  # noqa: E402

ORDER = {"cold": 0, "warm": 1, "hot": 2}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="deprecated alias for --mode hybrid")
    ap.add_argument("--mode", choices=("rules", "hybrid"), default=None)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--data", default="eval/leads.jsonl", help="JSONL file to evaluate")
    args = ap.parse_args()
    mode = args.mode or ("hybrid" if args.llm else "rules")
    if mode == "hybrid":
        import os
        os.environ.setdefault("LEAD_AGENT_MODEL", "qwen3:1.7b")
        from leadagent import llm
        llm.MODEL = os.environ["LEAD_AGENT_MODEL"]
        if not llm.available():
            print(f"mode={mode} not run: Ollama or required model {llm.MODEL} is unavailable")
            return

    data_path = Path(args.data)
    if not data_path.is_absolute():
        data_path = ROOT / data_path
    rows = [json.loads(l) for l in data_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    n = len(rows)
    intent_ok = tier_ok = tier_near = svc_ok = svc_n = 0
    llm_rows = 0
    results = []
    for row in rows:
        if args.verbose:
            print(f"processing lead #{row['id']}", flush=True)
        rep = process_lead(row["text"], use_llm=mode == "hybrid")
        llm_rows += rep.mode == "hybrid"
        i_ok = rep.extracted.intent == row["intent"]
        t_ok = rep.score.tier == row["tier"]
        near = abs(ORDER[rep.score.tier] - ORDER[row["tier"]]) <= 1
        s_ok = None
        if row["service"]:
            svc_n += 1
            s_ok = rep.primary_service == row["service"]
            svc_ok += bool(s_ok)
        intent_ok += i_ok
        tier_ok += t_ok
        tier_near += near
        results.append({"id": row["id"], "mode": rep.mode,
                        "intent_ok": i_ok, "tier_ok": t_ok, "service_ok": s_ok,
                        "pred_tier": rep.score.tier, "pred_score": rep.score.total,
                        "breakdown": rep.score.breakdown,
                        "pred_service": rep.primary_service, "pred_intent": rep.extracted.intent})
        if args.verbose and not (i_ok and t_ok and s_ok in (True, None)):
            print(f"#{row['id']:>2} intent {rep.extracted.intent}/{row['intent']} "
                  f"svc {rep.primary_service}/{row['service']} "
                  f"tier {rep.score.tier}({rep.score.total})/{row['tier']}")

    print(f"mode={mode}  n={n}")
    if mode != "rules":
        print(f"Hybrid enrichment used:  {llm_rows}/{n}")
    print(f"intent accuracy:          {intent_ok}/{n} = {intent_ok / n:.0%}")
    print(f"primary service accuracy: {svc_ok}/{svc_n} = {svc_ok / svc_n:.0%}")
    print(f"tier accuracy (exact):    {tier_ok}/{n} = {tier_ok / n:.0%}")
    print(f"tier within one step:     {tier_near}/{n} = {tier_near / n:.0%}")
    result_name = "results.json" if data_path.name == "leads.jsonl" else f"results_{data_path.stem}.json"
    (ROOT / "eval" / result_name).write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
