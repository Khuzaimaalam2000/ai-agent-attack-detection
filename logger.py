"""Per-trial JSONL logger for the agent harness."""
import json
import os
import time


class TrialLogger:
    def __init__(self, log_path: str):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def log_step(self, **fields):
        record = {"ts": time.time(), **fields}
        with open(self.log_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
