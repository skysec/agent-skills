# Autoresearch: Optimize [WORKLOAD]

## Research Type
Optimization

## Objective
Minimize wall-clock time for [WORKLOAD DESCRIPTION]. The workload runs [COMMAND]. Output correctness must be preserved — any optimization that changes output is invalid.

## Hypothesis
[Fill in: e.g., "The hot path is in the nested loop at line 42 of processor.py; vectorizing it with NumPy should give 5–10× speedup"]

## Metrics
- **Primary**: wall_time_ms (milliseconds, lower is better)
- **Secondary**: peak_memory_mb (MB), p95_ms (ms)

## How to Run
`./autoresearch.sh` — outputs `METRIC name=number` lines.
Log with: `bash autoresearch-log.sh <commit> <metric_value> <status> "<description>"`

## Files in Scope
- [FILL IN: file paths and brief description of what each does]

## Off Limits
- Benchmark script (`autoresearch.sh`) — modifying this could game results.
- Test fixtures and expected outputs — changing them hides regressions.
- External API contracts / function signatures.

## Constraints
- Output must be byte-for-byte identical to baseline (checked automatically).
- No new dependencies without approval.
- Benchmark must complete in < [X] seconds per run to keep the loop fast.

## Domain Notes
- Profile the hot path before optimizing blindly. Use `python -m cProfile -s cumulative`.
- Algorithm complexity wins beat constant-factor wins at scale.
- NumPy vectorization of Python loops: common 10–100× win.
- Avoid allocating objects in hot loops.
- For I/O-bound workloads: async/threading. For CPU-bound: multiprocessing.
- Median of 5 runs is more reliable than a single run.

## Experimental History
[Updated periodically. Record: what was tried, the metric value, why kept or discarded.]

## Current Best
Baseline: wall_time_ms = [FILL IN], commit = [HASH]
