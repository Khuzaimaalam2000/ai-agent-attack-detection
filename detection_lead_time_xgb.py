import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedGroupKFold

df = pd.read_csv("stepwise_dataset.csv")

fused_cols = ["ts_offset", "num_get", "num_post", "num_put", "num_delete",
              "status_2xx", "status_4xx", "status_5xx",
              "path_len", "body_len", "special_char_count", "digit_count", "path_entropy",
              "audit_lines_so_far"]

y = df["y"].values
groups = df["trial_id"].values
X = df[fused_cols].fillna(0).values

n_pos = y.sum()
n_neg = len(y) - n_pos
scale_pos_weight = n_neg / n_pos

sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
y_pred = np.zeros_like(y)
for train_idx, test_idx in sgkf.split(X, y, groups):
    clf = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.1,
        scale_pos_weight=scale_pos_weight, eval_metric="logloss",
        random_state=42,
    )
    clf.fit(X[train_idx], y[train_idx])
    y_pred[test_idx] = clf.predict(X[test_idx])

df["y_pred"] = y_pred

attack_trial_ids = df[df["label"] == "attack"]["trial_id"].unique()

delays = []
never_detected = 0
for tid in attack_trial_ids:
    g = df[df["trial_id"] == tid].sort_values("act_index")
    true_rows = g[g["y"] == 1]
    if true_rows.empty:
        continue
    true_start = true_rows["act_index"].min()
    detected_rows = g[g["y_pred"] == 1]
    if detected_rows.empty:
        never_detected += 1
        continue
    first_detected = detected_rows["act_index"].min()
    delays.append(first_detected - true_start)

delays = np.array(delays)
total = len(delays) + never_detected
print(f"Attack trials evaluated: {total}")
print(f"Never detected (no positive prediction anywhere): {never_detected} ({never_detected/total:.1%})")
print(f"Detected: {len(delays)} ({len(delays)/total:.1%})")
if len(delays):
    print(f"Mean delay (steps): {delays.mean():.2f}")
    print(f"Median delay (steps): {np.median(delays):.2f}")
    print(f"Detected at or before the true issuing step: {(delays <= 0).sum()} / {len(delays)} ({(delays<=0).mean():.1%})")