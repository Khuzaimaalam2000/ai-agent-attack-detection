#!/bin/bash
for f in tasks/benign/*.json tasks/attack/*.json; do
    trial_id=$(python3 -c "import json; print(json.load(open('$f'))['trial_id'])")
    echo "=== Running $trial_id ==="
    docker restart juiceshop > /dev/null

    # wait up to 30s for Juice Shop to actually respond
    for i in $(seq 1 15); do
        code=$(curl -s -o /dev/null -w "%{http_code}" localhost:3000)
        if [ "$code" = "200" ]; then
            break
        fi
        sleep 2
    done

    rm -rf "runs/$trial_id"
    if python run_trial.py "$f"; then
        echo "OK: $trial_id"
    else
        echo "FAILED: $trial_id"
    fi
done
echo "All trials attempted."
