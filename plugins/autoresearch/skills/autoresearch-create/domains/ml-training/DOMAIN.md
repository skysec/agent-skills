# Domain: ML Training

## What This Domain Covers

Training neural networks from scratch or fine-tuning. Optimizing model architecture, hyperparameters, optimizers, data pipelines, and training dynamics to achieve better generalization (lower validation loss/perplexity) within a fixed compute budget.

## Typical Goals

- Minimize validation loss / bits-per-byte (val_bpb) within a fixed training time
- Find the optimal learning rate schedule for a given architecture
- Determine which architectural components contribute most to performance
- Ablate regularization strategies (dropout, weight decay, etc.)

## Standard Metrics

- **val_loss**: float, lower is better. Measures generalization. Primary metric for most tasks.
- **val_bpb**: float (bits per byte), lower is better. Vocabulary-size-independent; preferred for language models.
- **val_ppl**: float (perplexity), lower is better. Exponential of val_loss; human-readable.
- **train_loss**: float, lower is better. Tracks if model is learning; large gap with val_loss = overfitting.

## Common Secondary Metrics

- `train_loss` — gap between train and val signals overfitting
- `tokens_per_second` — training throughput; drops signal architectural regressions
- `peak_gpu_mb` — memory usage; higher usage often enables bigger batches
- `grad_norm` — gradient norm; instability signal

## Proven Experimental Approaches (Try These First)

1. **Adjust learning rate** — most impactful single hyperparameter. Try cosine decay with warmup.
2. **Batch size** — larger batches enable higher LR (linear scaling rule). Start with what fits in memory.
3. **Architecture width vs. depth** — wider is often more compute-efficient than deeper at small scale.
4. **Optimizer** — AdamW is the default; try Muon for 2D matrices if available.
5. **Normalization** — RMSNorm > LayerNorm at small scale. Pre-norm > post-norm for stability.
6. **Attention** — Flash Attention for memory efficiency; GQA reduces KV cache.
7. **Embedding tying** — tying input/output embeddings reduces params with minimal loss in quality.

## Known Dead Ends

- **Dropout > 0.1** for language models: hurts more than it helps at small scale.
- **Very small batch sizes** (< 8): training instability without meaningful gain.
- **Complex LR schedules** without warmup: almost always worse than cosine with warmup.
- **Architecture changes that grow param count without matching data**: just overfits faster.

## Critical Constraints

- **Eval harness is off-limits**: never modify the evaluation code or data loading — this invalidates comparisons.
- **Fixed compute budget**: all experiments must respect the same time/step budget for fair comparison.
- **Reproducibility**: set seeds when possible; if training is stochastic, take the average of 2 runs before deciding.
- **val_loss must improve, not just train_loss**: generalization is the goal.

## Common Pitfalls

- Overfitting to training loss: a model that memorizes training data shows worse val_bpb.
- Benchmarking on different sequence lengths or batch sizes across experiments.
- Forgetting to reset the optimizer state when changing architecture.
- Modifying the dataset processing code (bugs can make any metric look better).

## Benchmark Design Notes

- Use a fixed subset of val data for fast experiments; run full eval only before committing a promising result.
- 5-minute training runs enable ~12 experiments/hour. Aim for this as the default time budget.
- Log `tokens_per_second` as secondary metric to catch accidental regressions in throughput.
