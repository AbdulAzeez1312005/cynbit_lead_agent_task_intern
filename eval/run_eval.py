"""Evaluate the pipeline against hand-labelled synthetic leads.

Usage:
    python eval/run_eval.py            # rules baseline (offline)
    python eval/run_eval.py --llm      # LLM extraction + brief (needs OPENAI_API_KEY)

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
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    rows = [json.loads(l) for l in (ROOT / "eval" / "leads.jsonl").read_text().splitlines() if l.strip()]
    n = len(rows)
    intent_ok = tier_ok = tier_near = svc_ok = svc_n = 0
    llm_rows = 0
    results = []
    for row in rows:
        if args.verbose:
            print(f"processing lead #{row['id']}", flush=True)
        rep = process_lead(row["text"], use_llm=args.llm)
        llm_rows += rep.mode == "llm"
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
                        "pred_service": rep.primary_service, "pred_intent": rep.extracted.intent})
        if args.verbose and not (i_ok and t_ok and s_ok in (True, None)):
            print(f"#{row['id']:>2} intent {rep.extracted.intent}/{row['intent']} "
                  f"svc {rep.primary_service}/{row['service']} "
                  f"tier {rep.score.tier}({rep.score.total})/{row['tier']}")

    mode = "llm" if args.llm else "rules"
    print(f"mode={mode}  n={n}")
    if args.llm:
        print(f"LLM extraction used:     {llm_rows}/{n}")
    print(f"intent accuracy:          {intent_ok}/{n} = {intent_ok / n:.0%}")
    print(f"primary service accuracy: {svc_ok}/{svc_n} = {svc_ok / svc_n:.0%}")
    print(f"tier accuracy (exact):    {tier_ok}/{n} = {tier_ok / n:.0%}")
    print(f"tier within one step:     {tier_near}/{n} = {tier_near / n:.0%}")
    (ROOT / "eval" / "results.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
