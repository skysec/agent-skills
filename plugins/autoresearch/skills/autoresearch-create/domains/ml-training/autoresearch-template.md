# Autoresearch: Minimize Validation Loss

## Research Type
Optimization

## Objective
Minimize validation bits-per-byte (val_bpb) on the held-out validation set within a 5-minute training budget per experiment. The training setup is a GPT-style language model trained on [DATASET]. We want the best generalization possible per unit compute.

## Hypothesis
[Fill in: e.g., "Increasing embedding dimension from 256 to 512 will improve val_bpb by ~0.05 given that the current model appears under-parameterized"]

## Metrics
- **Primary**: val_bpb (bits per byte, lower is better)
- **Secondary**: train_loss (float), tokens_per_second (tok/s), peak_gpu_mb (MB)

## How to Run
`./autoresearch.sh` — outputs `METRIC name=number` lines.
Log with: `bash autoresearch-log.sh <commit> <metric_value> <status> "<description>"`

## Files in Scope
- `train.py` — model architecture, optimizer, training loop, hyperparameters. PRIMARY modification target.

## Off Limits
- `prepare.py` — data preprocessing and evaluation harness. Modifying this invalidates all comparisons.
- `data/` — raw dataset files.
- `autoresearch.sh`, `autoresearch.jsonl` — session infrastructure.

## Constraints
- Each experiment must run in ≤ 5 minutes.
- No new Python packages without explicit user approval.
- val_bpb must improve (not just train_loss).
- Keep changes to `train.py` only — single-file diffs are reviewable; multi-file changes are not.

## Domain Notes
- Try learning rate first — it's the highest-leverage hyperparameter.
- Larger batch sizes + higher LR often outperform small batch sizes + low LR.
- RMSNorm outperforms LayerNorm at small scale.
- Flash Attention reduces memory, enabling larger batches.
- Dropout > 0.1 usually hurts language model generalization.
- Embedding tying (share input/output weights) reduces params cheaply.

## Experimental History
[Updated periodically. Record: what was tried, what the metric was, why kept or discarded.]

## Current Best
Baseline: val_bpb = [FILL IN], commit = [HASH]
