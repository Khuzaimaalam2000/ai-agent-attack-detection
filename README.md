# Detecting External AI-Agent-Driven Cyberattacks

Research harness for the project *"Detecting External AI-Agent-Driven
Cyberattacks Through the Fusion of AI Agent Execution Traces and
System-Level Telemetry."* An autonomous LLM agent plays the attacker
against OWASP Juice Shop; every trial captures the agent's own
decide/act trace alongside host (`auditd`) and network (`tcpdump`)
telemetry, time-aligned. Step-level classifiers (Random Forest,
XGBoost) are trained to detect the attack as early as possible, and
compared against a rule-based baseline built on Cisco's open-source
[Project Quarry](https://github.com/cisco-ai-defense/project-quarry).

This repo contains every script needed to regenerate the full
pipeline from scratch: task generation → trial execution → labeling →
feature extraction → training → evaluation → the Quarry baseline.
Raw trial output (`runs/`) is **not** checked in — re-running the
harness regenerates it.

## Research design

Three evidence streams are captured per trial and compared in three
conditions:

- **agent-only** — the attacking agent's own decide/tool-call trace
- **system-only** — host syscalls (`auditd`) around the target container
- **fused** — both, time-aligned

Ground truth is labeled at the step where the attack action was
*issued*, never where it succeeded — this keeps detection-lead-time
measurement honest (a model trained on "the step that happened to
work" would already know the outcome).

## Repo structure
agent.py # LangGraph decide/act loop, the attacking agent
tools.py # HTTP tool definitions the agent can call
logger.py # per-step trace + telemetry logging
run_trial.py # runs one trial end-to-end (start capture, run agent, stop capture)
run_new_trials.sh # resumable batch runner (skips trials with existing manifest.json)

tasks/benign/.json # benign task definitions
tasks/attack/.json # attack task definitions (13 categories)
generate_tasks.py # original task generator
generate_tasks_large.py # round 1 scale-up generator
generate_tasks_round2.py # round 2 scale-up generator

label_attacks.py # manual labeling CLI (original 30 trials)
auto_label_attacks.py # category-based heuristic auto-labeler (validate/label modes)
labels.json # per-trial ground truth: label, attack_start_step, category

build_dataset.py # original trial-level feature extraction (superseded)
build_stepwise_dataset.py # causal, step-level feature extraction -> stepwise_dataset.csv
diagnose_stepwise.py # feature-importance / overfitting diagnostics

train_baseline.py # original trial-level baseline (superseded)
train_stepwise.py # Random Forest, 3 conditions, grouped 5-fold CV
train_xgboost.py # XGBoost, same conditions and CV
detection_lead_time.py # RF: first-detection vs. true issuance step, per attack trial
detection_lead_time_xgb.py # same, XGBoost
generalization_loco.py # RF: leave-one-category-out generalization test
generalization_loco_xgb.py # same, XGBoost

convert_to_quarry.py # converts agent_trace.jsonl -> Quarry’s OpenAI-chat JSON schema
quarry_rules/*.rule # 10 hand-written Quarry DSL rules covering the attack surface
quarry_rules/config.yaml # Quarry scan config referencing the rule set
score_quarry.py # scores Quarry’s scan output against labels.json


## Prerequisites

- An Ubuntu VM (tested on 22.04) with Docker installed
- Python 3.10+ for the main harness
- Python 3.11+ for Project Quarry (kept in a **separate venv** — see
  "Project Quarry setup" below; Ubuntu 22.04's `python3.11` package
  from the default `universe` pocket is a broken pre-release snapshot,
  so install from the [deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa) instead)
- An Anthropic API key (used as the attacking agent's reasoning model)
- `sudo` access with NOPASSWD rules for `tcpdump` and `ausearch` (needed
  so the harness can start/stop packet and syscall capture per trial
  without interactive prompts)

## Setup

### 1. Target application

```bash
docker run -d -p 3000:3000 --name juiceshop bkimminich/juice-shop
```

### 2. Main harness environment

```bash
git clone <this-repo-url> agent-harness
cd agent-harness
python3 -m venv harness-venv
source harness-venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=<your-key>
```

### 3. Project Quarry setup (separate venv — Python 3.11 required)

```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

cd ~/Research   # or wherever you keep this alongside agent-harness
git clone --depth 1 https://github.com/cisco-ai-defense/project-quarry.git
python3.11 -m venv quarry-venv
source quarry-venv/bin/activate
cd project-quarry
pip install -e .
```

## Reproducing the full pipeline

All commands below run inside `agent-harness/` with `harness-venv`
active, unless noted otherwise.

```bash
# 1. Generate task definitions (or use the ones already checked in)
python3 generate_tasks_round2.py

# 2. Run all trials (resumable — safe to interrupt and re-run)
./run_new_trials.sh

# 3. Auto-label attack trials from their traces
python3 auto_label_attacks.py validate   # sanity-check against hand-labeled trials first
python3 auto_label_attacks.py label      # label the rest

# 4. Build the step-level feature dataset
python3 build_stepwise_dataset.py

# 5. Train and evaluate both classifiers
python3 train_stepwise.py          # Random Forest: agent-only / system-only / fused
python3 train_xgboost.py           # XGBoost: same three conditions

# 6. Detection lead time
python3 detection_lead_time.py
python3 detection_lead_time_xgb.py

# 7. Leave-one-category-out generalization
python3 generalization_loco.py
python3 generalization_loco_xgb.py

# 8. Project Quarry baseline (switch to quarry-venv for the scan step)
python3 convert_to_quarry.py       # harness-venv: build quarry_input/ from runs/
source ../quarry-venv/bin/activate  # or wherever quarry-venv lives
quarry scan -c quarry_rules/config.yaml -t quarry_input/ --recursive -o json --output quarry_results.json
deactivate && source harness-venv/bin/activate
python3 score_quarry.py
```

## Key methodological notes

- **Labeling convention**: `attack_start_step` marks where the attack
  action was *issued*, not where it succeeded. This matters for honest
  lead-time measurement.
- **Causal features only**: every feature in `build_stepwise_dataset.py`
  uses only information available up to and including the current
  step — never future information.
- **Grouped CV**: all cross-validation is grouped by `trial_id`
  (`StratifiedGroupKFold`), so a trial's own steps never split across
  train and test.
- **Project Quarry is a rule-authoring DSL, not a pretrained
  classifier.** It ships no production detection rule pack — only
  DSL-feature-demo fixtures explicitly marked "not for production."
  The rules in `quarry_rules/` were hand-written for this project's
  attack surface, the way a security engineer would use the tool on
  day one.

## Headline results (510 trials: 235 benign, 275 attack, 13 attack categories)

| Condition | Model | Precision | Recall | F1 |
|---|---|---|---|---|
| Agent-only | Random Forest | 0.909 | 0.821 | 0.863 |
| Agent-only | XGBoost | 0.835 | 0.870 | 0.852 |
| System-only | Random Forest | 0.545 | 0.789 | 0.645 |
| **Fused** | **Random Forest** | **0.935** | **0.831** | **0.880** |
| Fused | XGBoost | 0.833 | 0.885 | 0.858 |
| Agent-only | Project Quarry (rules) | 0.910 | 0.585 | 0.712 |

- Detection lead time: both models detect ~98–99% of attacks with a
  median delay of 0 steps.
- Leave-one-category-out generalization: Random Forest mean recall
  21.1%, XGBoost 28.6% — XGBoost transfers meaningfully better to
  unseen attack categories, though both (and Quarry's rules) fail
  almost completely on IDOR / ownership-dependent categories
  (`basket_idor`, `order_idor`, `admin_bypass_direct`), which require
  resource-ownership context that surface-level features don't
  capture — the clearest open problem for future work.

## License

<choose a license, e.g. MIT>