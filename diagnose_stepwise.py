import pandas as pd
from sklearn.ensemble import RandomForestClassifier

df = pd.read_csv("stepwise_dataset.csv")

feature_sets = {
    "agent_only": ["ts_offset", "num_get", "num_post", "num_put", "num_delete",
                   "status_2xx", "status_4xx", "status_5xx",
                   "path_len", "body_len", "special_char_count", "digit_count", "path_entropy"],
    "system_only": ["audit_lines_so_far"],
}

y = df["y"].values

for name, cols in feature_sets.items():
    X = df[cols].fillna(0).values
    clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
    clf.fit(X, y)
    importances = sorted(zip(cols, clf.feature_importances_), key=lambda x: -x[1])
    print(f"\n=== {name} feature importances ===")
    for feat, imp in importances:
        print(f"  {feat}: {imp:.3f}")

fused_cols = ["ts_offset", "num_get", "num_post", "num_put", "num_delete",
              "status_2xx", "status_4xx", "status_5xx",
              "path_len", "body_len", "special_char_count", "digit_count", "path_entropy",
              "audit_lines_so_far"]
X = df[fused_cols].fillna(0).values
clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
clf.fit(X, y)
df["pred_in_sample"] = clf.predict(X)

summary = df.groupby("trial_id").apply(lambda g: pd.Series({
    "label": g["label"].iloc[0],
    "n_steps": len(g),
    "n_attack_steps": int(g["y"].sum()),
    "n_correct": int((g["y"] == g["pred_in_sample"]).sum()),
}))
print("\nPer-trial in-sample fit summary (diagnostic only, not a held-out result):")
print(summary.to_string())
