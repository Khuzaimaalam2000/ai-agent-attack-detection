import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

df = pd.read_csv("stepwise_dataset.csv")

feature_sets = {
    "agent_only": ["ts_offset", "num_get", "num_post", "num_put", "num_delete",
                   "status_2xx", "status_4xx", "status_5xx",
                   "path_len", "body_len", "special_char_count", "digit_count", "path_entropy"],
    "system_only": ["audit_lines_so_far"],
    "fused": ["ts_offset", "num_get", "num_post", "num_put", "num_delete",
              "status_2xx", "status_4xx", "status_5xx",
              "path_len", "body_len", "special_char_count", "digit_count", "path_entropy",
              "audit_lines_so_far"],
}

y = df["y"].values
groups = df["trial_id"].values

n_pos = y.sum()
n_neg = len(y) - n_pos
scale_pos_weight = n_neg / n_pos

sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)

for name, cols in feature_sets.items():
    X = df[cols].fillna(0).values
    y_pred = np.zeros_like(y)
    for train_idx, test_idx in sgkf.split(X, y, groups):
        clf = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            scale_pos_weight=scale_pos_weight, eval_metric="logloss",
            random_state=42,
        )
        clf.fit(X[train_idx], y[train_idx])
        y_pred[test_idx] = clf.predict(X[test_idx])
    acc = accuracy_score(y, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y, y_pred, average="binary", zero_division=0)
    cm = confusion_matrix(y, y_pred)
    print(f"\n=== {name} (XGBoost) ===")
    print(f"features: {cols}")
    print(f"accuracy={acc:.3f} precision={prec:.3f} recall={rec:.3f} f1={f1:.3f}")
    print(f"confusion matrix [[TN,FP],[FN,TP]]:\n{cm}")

print("\nDone. Same grouped CV as train_stepwise.py (Random Forest) — directly comparable.")