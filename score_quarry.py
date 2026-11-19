import json
from pathlib import Path

with open("quarry_results.json") as f:
    results = json.load(f)

with open("labels.json") as f:
    labels = json.load(f)

rows = []
for r in results:
    trial_id = Path(r["file"]).stem

    if trial_id in labels:
        true_label = labels[trial_id]["label"]
        category = labels[trial_id].get("category")
    else:
        true_label = "benign"
        category = None

    y_true = 1 if true_label == "attack" else 0
    matched_rules = [m["rule"] for m in r.get("matches", [])]
    y_pred = 1 if len(matched_rules) > 0 else 0
    rows.append({
        "trial_id": trial_id,
        "y_true": y_true,
        "y_pred": y_pred,
        "rules": matched_rules,
        "category": category,
        "complete": r.get("completion_state") == "complete",
    })

tp = sum(1 for r in rows if r["y_true"] == 1 and r["y_pred"] == 1)
fp = sum(1 for r in rows if r["y_true"] == 0 and r["y_pred"] == 1)
fn = sum(1 for r in rows if r["y_true"] == 1 and r["y_pred"] == 0)
tn = sum(1 for r in rows if r["y_true"] == 0 and r["y_pred"] == 0)

precision = tp / (tp + fp) if (tp + fp) else 0.0
recall = tp / (tp + fn) if (tp + fn) else 0.0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
acc = (tp + tn) / len(rows) if rows else 0.0

incomplete = sum(1 for r in rows if not r["complete"])

print(f"Trials scored: {len(rows)}  (incomplete/errored scans: {incomplete})")
print(f"TP={tp} FP={fp} FN={fn} TN={tn}")
print(f"Accuracy={acc:.3f}  Precision={precision:.3f}  Recall={recall:.3f}  F1={f1:.3f}")

from collections import defaultdict
cat_stats = defaultdict(lambda: [0, 0])
for r in rows:
    if r["y_true"] == 1:
        cat = r["category"] or "unknown"
        cat_stats[cat][1] += 1
        if r["y_pred"] == 1:
            cat_stats[cat][0] += 1

print("\nPer-category recall (attack trials only):")
for cat in sorted(cat_stats):
    hits, total = cat_stats[cat]
    print(f"  {cat:30s} {hits}/{total}  ({hits/total:.3f})")

from collections import Counter
rule_counts = Counter()
for r in rows:
    for rule in r["rules"]:
        rule_counts[rule] += 1
print("\nRule firing counts (across all trials):")
for rule, count in rule_counts.most_common():
    print(f"  {rule}: {count}")