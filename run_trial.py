"""Run one full trial: start capture, run the agent, stop capture, write manifest."""
import json
import os
import re
import subprocess
import sys
import time
import signal

from agent import run_trial
from logger import TrialLogger

AUDIT_KEYS = ["juiceshop_exec", "juiceshop_net", "juiceshop_docker"]
TS_PATTERN = re.compile(r"audit\((\d+)\.\d+:")


def main(task_path: str):
    with open(task_path) as f:
        task = json.load(f)

    trial_id = task["trial_id"]
    run_dir = f"runs/{trial_id}"
    os.makedirs(run_dir, exist_ok=True)

    pcap_path = f"{run_dir}/network.pcap"
    audit_path = f"{run_dir}/audit.log"
    trace_path = f"{run_dir}/agent_trace.jsonl"

    start_ts = time.time()
    tcpdump_proc = subprocess.Popen(
        ["sudo", "tcpdump", "-i", "any", "port", "3000", "-w", pcap_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    logger = TrialLogger(log_path=trace_path)
    run_trial(trial_id, task["instruction"], logger)

    end_ts = time.time()
    time.sleep(1)

    tcpdump_proc.send_signal(signal.SIGINT)
    try:
        tcpdump_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        tcpdump_proc.kill()

    # Let the kernel audit backlog flush before querying ausearch, so fast
    # trials don't miss events that haven't been written out yet.
    time.sleep(6)

    key_args = []
    for k in AUDIT_KEYS:
        key_args += ["-k", k]
    result = subprocess.run(
        ["sudo", "ausearch", *key_args, "--raw"],
        capture_output=True, text=True,
    )

    matched_lines = []
    current_ts = None
    margin = 2  # seconds of slack on each side
    for line in result.stdout.splitlines():
        m = TS_PATTERN.search(line)
        if m:
            current_ts = int(m.group(1))
        if current_ts is not None and (start_ts - margin) <= current_ts <= (end_ts + margin):
            matched_lines.append(line)

    with open(audit_path, "w") as f:
        f.write("\n".join(matched_lines))

    manifest = {
        "trial_id": trial_id,
        "label": task["label"],
        "start_ts": start_ts,
        "end_ts": end_ts,
        "agent_trace": trace_path,
        "pcap": pcap_path,
        "audit_log": audit_path,
        "audit_lines": len(matched_lines),
    }
    with open(f"{run_dir}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Trial {trial_id} complete. Manifest: {run_dir}/manifest.json ({len(matched_lines)} audit lines)")


if __name__ == "__main__":
    main(sys.argv[1])