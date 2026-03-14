# Autoresearch: [SECURITY RESEARCH GOAL]

## Research Type
[Optimization | Ablation | Verification | Comparison]

## Objective
[Describe the authorized research goal. e.g., "Improve detection rate of our LLM-based prompt injection classifier against adversarial inputs, evaluated on a held-out set of 500 adversarial prompts."]

## Authorization Context
[Document the authorization: CTF challenge name / pentest scope / research project / defensive use case]

## Hypothesis
[Fill in: e.g., "Adding a semantic similarity check against known injection patterns will improve detection_rate from 0.72 to ≥ 0.85 without increasing false_positive_rate above 0.05"]

## Metrics
- **Primary**: [detection_rate | success_rate | f1_score] (float [0–1], higher/lower is better)
- **Secondary**: false_positive_rate (float), latency_ms (ms), precision (float), recall (float)

## How to Run
`./autoresearch.sh` — outputs `METRIC name=number` lines.
Log with: `bash autoresearch-log.sh <commit> <metric_value> <status> "<description>"`

## Files in Scope
- [FILL IN: e.g., `classifier.py` — LLM-based classifier logic]
- [FILL IN: e.g., `prompts.json` — adversarial prompt templates]

## Off Limits
- `eval_set/` — held-out evaluation data. Never modify.
- Authorization scope — do not expand beyond declared targets.

## Constraints
- All experiments on isolated/authorized targets only.
- Minimum 30 trials per condition for statistical reliability.
- False positive rate must stay ≤ [THRESHOLD].
- Reproduce results with fixed random seed before committing.

## Domain Notes
- Change one variable at a time. Security metrics are noisy; multi-variable changes make attribution impossible.
- Tune on training set only; evaluate on held-out set.
- Base rate matters: detection_rate of 0.99 is meaningless if FPR is 0.50.

## Experimental History
[Updated periodically. Record: what was tried, metric values, why kept or discarded.]

## Current Best
Baseline: [metric] = [FILL IN], commit = [HASH]
