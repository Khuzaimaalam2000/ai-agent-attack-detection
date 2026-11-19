import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
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

sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)

for name, cols in feature_sets.items():
    X = df[cols].fillna(0).values
    y_pred = np.zeros_like(y)
    for train_idx, test_idx in sgkf.split(X, y, groups):
        clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
        clf.fit(X[train_idx], y[train_idx])
        y_pred[test_idx] = clf.predict(X[test_idx])
    acc = accuracy_score(y, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y, y_pred, average="binary", zero_division=0)
    cm = confusion_matrix(y, y_pred)
    print(f"\n=== {name} ===")
    print(f"features: {cols}")
    print(f"accuracy={acc:.3f} precision={prec:.3f} recall={rec:.3f} f1={f1:.3f}")
    print(f"confusion matrix [[TN,FP],[FN,TP]]:\n{cm}")

print("\nDone. Grouped by trial_id so no trial's steps appear in both train and test within a fold.")