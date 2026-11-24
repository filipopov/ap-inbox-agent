"""Step 5 - Measure accuracy against the human-labelled gold set (eval/gold_labels.csv).

Writes table `accuracy(metric, value, n, note)` into data/ap.db (copied into the app DB), so the agent can
quote measured numbers. Each value has a 95% Wilson confidence interval in `note`.
"""
import csv
import math
import sqlite3
from pathlib import Path

from pipeline.llm import DB

GOLD = Path(__file__).parent / "gold_labels.csv"


def wilson(k, n, z=1.96):
    if n == 0:
        return 0, 0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


def main():
    db = sqlite3.connect(DB)
    gold = list(csv.DictReader(GOLD.open()))
    pred = {(k, i): (lab, lvl, conf, by) for k, i, lab, lvl, conf, by in db.execute(
        "SELECT item_kind, item_id, label, dunning_level, confidence, decided_by FROM final_labels")}
    metrics = {}

    def add(name, hits):
        if hits:
            metrics[name] = (sum(hits), len(hits))

    pairs = [(g, pred.get((g["item_kind"], g["item_id"]))) for g in gold]
    pairs = [(g, p) for g, p in pairs if p]
    add("label accuracy (all items)", [g["label"] == p[0] for g, p in pairs])
    for kind in ("email", "document"):
        add(f"label accuracy ({kind}s)", [g["label"] == p[0] for g, p in pairs if g["item_kind"] == kind])
    for stage in ("rule", "classifier", "llm"):
        add(f"label accuracy (decided by {stage})", [g["label"] == p[0] for g, p in pairs if p[3] == stage])
    add("label accuracy (confidence >= 0.8)", [g["label"] == p[0] for g, p in pairs if (p[2] or 0) >= 0.8])
    add("label accuracy (confidence < 0.8)", [g["label"] == p[0] for g, p in pairs if (p[2] or 0) < 0.8])
    for lab in ("invoice", "payment_reminder"):
        add(f"{lab}: recall (found / truly {lab})", [p[0] == lab for g, p in pairs if g["label"] == lab])
        add(f"{lab}: precision (correct / predicted {lab})", [g["label"] == lab for g, p in pairs if p[0] == lab])
    add("dunning level accuracy", [g["dunning_level"] == p[1] for g, p in pairs
                                   if g["label"] == "payment_reminder" and p[0] == "payment_reminder"])
    add("invoice number correct", [g["invoice_number_ok"] == "yes" for g in gold if g["invoice_number_ok"] in ("yes", "no")])
    add("invoice total correct", [g["total_ok"] == "yes" for g in gold if g["total_ok"] in ("yes", "no")])

    db.execute("DROP TABLE IF EXISTS accuracy")
    db.execute("CREATE TABLE accuracy (metric TEXT, value REAL, n INTEGER, note TEXT)")
    for name, (k, n) in metrics.items():
        lo, hi = wilson(k, n)
        db.execute("INSERT INTO accuracy VALUES (?,?,?,?)",
                   (name, round(k / n, 3), n, f"{k}/{n} correct; 95% CI {lo:.0%}-{hi:.0%}"))
        print(f"{name:45s} {k / n:6.1%}  ({k}/{n}, 95% CI {lo:.0%}-{hi:.0%})")
    db.commit()
    print(f"\n{len(gold)} gold items, {len(gold) - len(pairs)} had no pipeline label")


if __name__ == "__main__":
    main()
