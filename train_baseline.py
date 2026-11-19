import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

df = pd.read_csv("pilot_dataset.csv")
df["y"] = (df["label"] == "attack").astype(int)

feature_sets = {
    "agent_only": [
        "duration_sec", "num_decide_steps", "num_tool_calls",
        "num_http_get", "num_http_post", "num_http_put", "num_http_delete",
        "num_status_2xx", "num_status_4xx", "num_status_5xx",
    ],
    "system_only": [
        "audit_lines", "audit_execve", "audit_net", "audit_docker",
    ],
    "fused": [
        "duration_sec", "num_decide_steps", "num_tool_calls",
        "num_http_get", "num_http_post", "num_http_put", "num_http_delete",
        "num_status_2xx", "num_status_4xx", "num_status_5xx",
        "audit_lines", "audit_execve", "audit_net", "audit_docker",
        "pcap_bytes",
    ],
}

y = df["y"].values
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

for name, cols in feature_sets.items():
    X = df[cols].fillna(0).values
    clf = RandomForestClassifier(n_estimators=200, random_state=42)
    y_pred = cross_val_predict(clf, X, y, cv=skf)
    acc = accuracy_score(y, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y, y_pred, average="binary", zero_division=0)
    cm = confusion_matrix(y, y_pred)
    print(f"\n=== {name} ===")
    print(f"features: {cols}")
    print(f"accuracy={acc:.3f} precision={prec:.3f} recall={rec:.3f} f1={f1:.3f}")
    print(f"confusion matrix [[TN,FP],[FN,TP]]:\n{cm}")

print("\nDone. n=30 is a small-sample pilot result, not a final claim.")