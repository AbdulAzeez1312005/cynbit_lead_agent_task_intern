"""Choose hot/warm score cutoffs on the tuning dataset only.

Usage: python eval/tune_thresholds.py [eval/leads.jsonl]
The separately held-out file must not be passed to this script.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("eval/leads.jsonl")
if not data.is_absolute():
    data = ROOT / data
rows = [json.loads(line) for line in data.read_text(encoding="utf-8").splitlines() if line.strip()]
preds = json.loads((ROOT / "eval" / ("results.json" if data.name == "leads.jsonl" else f"results_{data.stem}.json")).read_text(encoding="utf-8"))
if len(rows) != len(preds):
    raise SystemExit("Run eval/run_eval.py on the same tuning file first")

best = []
for hot in range(45, 91, 1):
    for warm in range(25, hot):
        correct = 0
        for row, pred in zip(rows, preds):
            if row["intent"] in {"student_program", "not_a_fit"}:
                tier = "cold"
            else:
                score = sum(pred["breakdown"].values())
                if len(row["text"].split()) < 5 and pred["breakdown"].get("budget") == 8:
                    score = min(score, warm - 5)
                tier = "hot" if score >= hot else "warm" if score >= warm else "cold"
            correct += tier == row["tier"]
        best.append((correct, -abs(hot - 65) - abs(warm - 40), hot, warm))

correct, _, hot, warm = max(best)
print(f"tuning_file={data.name} n={len(rows)}")
print(f"selected HOT={hot}, WARM={warm}; exact tier={correct}/{len(rows)} ({correct / len(rows):.0%})")
print("Thresholds are fitted to synthetic tuning labels only; evaluate a separate holdout once, without further tuning.")
