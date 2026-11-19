"""Consolidate all pilot trials into one dataset table."""
import csv
import glob
import json
import os
import re

RUNS_DIR = "runs"
OUT_CSV = "pilot_dataset.csv"

TS_PATTERN = re.compile(r"audit\((\d+)\.\d+:")


def load_agent_trace(path):
    steps = []
    if not os.path.exists(path):
        return steps
    with open(path) as f:
        for line in f:
            if line.strip():
                steps.append(json.loads(line))
    return steps


def summarize_agent_trace(steps):
    decides = [s for s in steps if s.get("kind") == "decide"]
    acts = [s for s in steps if s.get("kind") == "act"]
    tool_counts = {}
    status_counts = {"2xx": 0, "4xx": 0, "5xx": 0, "other": 0}
    for a in acts:
        tool = a.get("tool", "unknown")
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
        out = a.get("tool_output", "")
        m = re.match(r"status=(\d+)", out)
        if m:
            code = int(m.group(1))
            if 200 <= code < 300:
                status_counts["2xx"] += 1
            elif 400 <= code < 500:
                status_counts["4xx"] += 1
            elif 500 <= code < 600:
                status_counts["5xx"] += 1
            else:
                status_counts["other"] += 1
    return {
        "num_decide_steps": len(decides),
        "num_tool_calls": len(acts),
        "num_http_get": tool_counts.get("http_get", 0),
        "num_http_post": tool_counts.get("http_post", 0),
        "num_http_put": tool_counts.get("http_put", 0),
        "num_http_delete": tool_counts.get("http_delete", 0),
        "num_status_2xx": status_counts["2xx"],
        "num_status_4xx": status_counts["4xx"],
        "num_status_5xx": status_counts["5xx"],
    }


def summarize_audit(path):
    if not os.path.exists(path):
        return {"audit_lines": 0, "audit_execve": 0, "audit_net": 0, "audit_docker": 0}
    with open(path) as f:
        content = f.read()
    return {
        "audit_lines": len(content.splitlines()) if content.strip() else 0,
        "audit_execve": content.count('key="juiceshop_exec"'),
        "audit_net": content.count('key="juiceshop_net"'),
        "audit_docker": content.count('key="juiceshop_docker"'),
    }


def summarize_pcap(path):
    size = os.path.getsize(path) if os.path.exists(path) else 0
    return {"pcap_bytes": size}


def main():
    rows = []
    manifest_paths = sorted(glob.glob(os.path.join(RUNS_DIR, "*", "manifest.json")))
    for mpath in manifest_paths:
        with open(mpath) as f:
            manifest = json.load(f)

        trial_id = manifest["trial_id"]
        label = manifest["label"]
        duration = manifest["end_ts"] - manifest["start_ts"]

        steps = load_agent_trace(manifest["agent_trace"])
        agent_features = summarize_agent_trace(steps)
        audit_features = summarize_audit(manifest["audit_log"])
        pcap_features = summarize_pcap(manifest["pcap"])

        row = {
            "trial_id": trial_id,
            "label": label,
            "duration_sec": round(duration, 2),
            **agent_features,
            **audit_features,
            **pcap_features,
        }
        rows.append(row)

    if not rows:
        print("No trials found under runs/.")
        return

    fieldnames = list(rows[0].keys())
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_CSV}")
    for row in rows:
        print(row["trial_id"], row["label"], "dur=%.1fs" % row["duration_sec"],
              "tool_calls=%d" % row["num_tool_calls"], "audit_lines=%d" % row["audit_lines"])


if __name__ == "__main__":
    main()