import json, re, os, glob, math
import pandas as pd

RUNS_DIR = "runs"
AUDIT_TS_RE = re.compile(r"audit\((\d+\.\d+):")
SPECIAL_CHARS = set("'\"%<>=;()-.")

def parse_audit_timestamps(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", errors="ignore") as f:
        text = f.read()
    return [float(m) for m in AUDIT_TS_RE.findall(text)]

def status_bucket(tool_output):
    if not isinstance(tool_output, str):
        return None
    m = re.match(r"status=(\d+)", tool_output)
    if not m:
        return None
    code = int(m.group(1))
    if 200 <= code < 300:
        return "2xx"
    if 400 <= code < 500:
        return "4xx"
    if 500 <= code < 600:
        return "5xx"
    return "other"

def shannon_entropy(s):
    if not s:
        return 0.0
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())

def content_features(tool_input):
    path = tool_input.get("path", "") if isinstance(tool_input, dict) else ""
    body = tool_input.get("json_body", "") if isinstance(tool_input, dict) else ""
    body_str = json.dumps(body) if not isinstance(body, str) else body
    combined = path + body_str
    return {
        "path_len": len(path),
        "body_len": len(body_str),
        "special_char_count": sum(1 for c in combined if c in SPECIAL_CHARS),
        "digit_count": sum(1 for c in path if c.isdigit()),
        "path_entropy": shannon_entropy(path),
    }

with open("labels.json") as f:
    labels = json.load(f)

rows = []

for trial_dir in sorted(glob.glob(f"{RUNS_DIR}/*")):
    trial_id = os.path.basename(trial_dir)
    manifest_path = os.path.join(trial_dir, "manifest.json")
    trace_path = os.path.join(trial_dir, "agent_trace.jsonl")
    audit_path = os.path.join(trial_dir, "audit.log")
    if not (os.path.exists(manifest_path) and os.path.exists(trace_path)):
        continue

    with open(manifest_path) as f:
        manifest = json.load(f)
    label = manifest.get("label")
    start_ts = manifest.get("start_ts")

    audit_ts_list = sorted(parse_audit_timestamps(audit_path))

    act_records = []
    with open(trace_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("kind") == "act":
                act_records.append(rec)

    lbl = labels.get(trial_id, {})
    attack_start_step = lbl.get("attack_start_step")

    counts = {"http_get": 0, "http_post": 0, "http_put": 0, "http_delete": 0}
    status_counts = {"2xx": 0, "4xx": 0, "5xx": 0, "other": 0}

    for idx, rec in enumerate(act_records):
        tool = rec.get("tool", "unknown")
        counts[tool] = counts.get(tool, 0) + 1
        bucket = status_bucket(rec.get("tool_output"))
        if bucket:
            status_counts[bucket] = status_counts.get(bucket, 0) + 1

        ts = rec.get("ts", start_ts)
        audit_count_so_far = sum(1 for a in audit_ts_list if a <= ts)

        cf = content_features(rec.get("tool_input", {}))

        if label == "attack" and attack_start_step is not None and idx >= attack_start_step:
            y = 1
        else:
            y = 0

        row = {
            "trial_id": trial_id,
            "act_index": idx,
            "ts_offset": (ts - start_ts) if start_ts else None,
            "num_get": counts.get("http_get", 0),
            "num_post": counts.get("http_post", 0),
            "num_put": counts.get("http_put", 0),
            "num_delete": counts.get("http_delete", 0),
            "status_2xx": status_counts["2xx"],
            "status_4xx": status_counts["4xx"],
            "status_5xx": status_counts["5xx"],
            "audit_lines_so_far": audit_count_so_far,
            "label": label,
            "y": y,
        }
        row.update(cf)
        rows.append(row)

df = pd.DataFrame(rows)
df.to_csv("stepwise_dataset.csv", index=False)
print(f"Wrote {len(df)} rows from {df['trial_id'].nunique()} trials to stepwise_dataset.csv")
print(df["y"].value_counts())