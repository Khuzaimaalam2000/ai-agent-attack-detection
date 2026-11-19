import json, glob
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support

df = pd.read_csv("stepwise_dataset.csv")

category_map = {}
for f in glob.glob("tasks/attack/*.json"):
    with open(f) as fh:
        t = json.load(fh)
    if "category" in t:
        category_map[t["trial_id"]] = t["category"]

fallback = {
    "attack_01": "sqli_admin_bypass",
    "attack_02": "basket_idor",
    "attack_03": "privilege_escalation",
    "attack_04": "xss_search",
    "attack_05": "basket_idor",
    "attack_06": "path_traversal",
    "attack_07": "coupon_forgery",
    "attack_08": "review_manipulation",
    "attack_09": "deluxe_bypass",
    "attack_10": "password_reset_flaw",
    "attack_11": "feedback_deletion",
    "attack_12": "file_upload_abuse",
    "attack_14": "basket_idor",
    "attack_15": "admin_bypass_direct",
}
for k, v in fallback.items():
    category_map.setdefault(k, v)

df["category"] = df["trial_id"].map(category_map)
df.loc[df["label"] == "benign", "category"] = "benign"

fused_cols = ["ts_offset", "num_get", "num_post", "num_put", "num_delete",
              "status_2xx", "status_4xx", "status_5xx",
              "path_len", "body_len", "special_char_count", "digit_count", "path_entropy",
              "audit_lines_so_far"]

attack_categories = sorted(df[df["label"] == "attack"]["category"].dropna().unique())
print(f"Attack categories found: {attack_categories}\n")

for held_out in attack_categories:
    train_mask = df["category"] != held_out
    test_mask = df["category"] == held_out
    if test_mask.sum() == 0:
        continue

    X_train = df.loc[train_mask, fused_cols].fillna(0).values
    y_train = df.loc[train_mask, "y"].values
    X_test = df.loc[test_mask, fused_cols].fillna(0).values
    y_test = df.loc[test_mask, "y"].values

    clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)

    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary", zero_division=0)
    n_trials = df.loc[test_mask, "trial_id"].nunique()
    n_steps = int(test_mask.sum())
    n_pos = int(y_test.sum())
    print(f"{held_out:22s} trials={n_trials:3d} steps={n_steps:4d} attack_steps={n_pos:4d}  recall={rec:.3f} precision={prec:.3f} f1={f1:.3f}")

print("\nDone. 'recall' is the key generalization metric: detection rate on an attack category the model never saw during training.")