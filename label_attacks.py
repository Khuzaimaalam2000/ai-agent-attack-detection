"""Interactive labeling: mark the step where each attack trial's malicious
action was actually issued (not when it succeeded), to avoid hindsight
leakage in later detection-lead-time evaluation."""
import glob
import json
import os
import re

RUNS_DIR = "runs"
OUT_PATH = "labels.json"

SUSPICIOUS_PATTERNS = [
    r"'--", r"' OR ", r"OR 1=1", r"<script", r"../", r"/admin",
]


def load_acts(trace_path):
    acts = []
    if not os.path.exists(trace_path):
        return acts
    with open(trace_path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("kind") == "act":
                acts.append(r)
    return acts


def flag_suspicious(act):
    text = json.dumps(act.get("tool_input", {}))
    for pat in SUSPICIOUS_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def main():
    labels = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH) as f:
            labels = json.load(f)

    manifest_paths = sorted(glob.glob(os.path.join(RUNS_DIR, "*", "manifest.json")))
    for mpath in manifest_paths:
        with open(mpath) as f:
            manifest = json.load(f)
        trial_id = manifest["trial_id"]
        label = manifest["label"]

        if label == "benign":
            labels[trial_id] = {"label": "benign", "attack_start_step": None, "attack_start_ts": None}
            continue

        if trial_id in labels and labels[trial_id].get("attack_start_step") is not None:
            print(f"{trial_id}: already labeled (step {labels[trial_id]['attack_start_step']}), skipping.")
            continue

        acts = load_acts(manifest["agent_trace"])
        print(f"\n=== {trial_id} (attack) — {len(acts)} tool calls ===")
        for i, a in enumerate(acts):
            flag = " <-- SUSPICIOUS" if flag_suspicious(a) else ""
            tool = a.get("tool")
            tool_input = a.get("tool_input")
            status_line = a.get("tool_output", "")[:60].replace("\n", " ")
            print(f"[{i}] ts={a['ts']:.2f} {tool} {tool_input}{flag}")
            print(f"     -> {status_line}")

        while True:
            choice = input(f"Which step index issued the attack action? (0-{len(acts)-1}, or 's' to skip): ").strip()
            if choice.lower() == "s":
                labels[trial_id] = {"label": "attack", "attack_start_step": None, "attack_start_ts": None}
                break
            if choice.isdigit() and 0 <= int(choice) < len(acts):
                idx = int(choice)
                labels[trial_id] = {
                    "label": "attack",
                    "attack_start_step": idx,
                    "attack_start_ts": acts[idx]["ts"],
                }
                break
            print("Invalid input, try again.")

    with open(OUT_PATH, "w") as f:
        json.dump(labels, f, indent=2)
    print(f"\nSaved labels for {len(labels)} trials to {OUT_PATH}")


if __name__ == "__main__":
    main()