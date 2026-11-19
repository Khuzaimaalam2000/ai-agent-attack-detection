#!/bin/bash
cd ~/Research/agent-harness
for f in tasks/benign/*.json tasks/attack/*.json; do
  trial_id=$(python3 -c "import json;print(json.load(open('$f'))['trial_id'])")
  if [ -f "runs/$trial_id/manifest.json" ]; then
    continue
  fi
  echo "=== Running $trial_id ==="
  docker restart juiceshop
  until curl -s -o /dev/null http://localhost:3000; do sleep 1; done
  sleep 2
  python3 run_trial.py "$f" && echo "OK: $trial_id" || echo "FAILED: $trial_id"
done
echo "All new trials attempted."