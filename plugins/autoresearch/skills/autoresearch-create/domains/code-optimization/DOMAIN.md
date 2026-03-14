# Domain: Code Optimization

## What This Domain Covers

Making existing code faster, more memory-efficient, or higher-throughput. This includes algorithmic improvements, data structure choices, parallelism, caching strategies, compiler/interpreter-friendly patterns, and I/O optimization. The correctness of the output must be preserved.

## Typical Goals

- Reduce wall-clock time for a workload (e.g., "make the test suite 30% faster")
- Increase throughput (requests/second, items/second)
- Reduce peak memory usage
- Reduce cold-start latency

## Standard Metrics

- **wall_time_ms**: integer (milliseconds), lower is better. Most reliable for single-threaded work.
- **wall_time_s**: float (seconds), lower is better. For longer-running workloads.
- **throughput_rps**: float (requests/sec), higher is better. For server/batch workloads.
- **peak_memory_mb**: float (megabytes), lower is better. Track to avoid regressions.

## Common Secondary Metrics

- `p50_ms`, `p95_ms`, `p99_ms` — percentile latencies; p99 matters for user-facing systems
- `peak_memory_mb` — even if not primary, track it to catch accidental regressions
- `cpu_percent` — utilization; near 100% = CPU-bound, near 0% = I/O-bound (different optimization paths)

## Proven Experimental Approaches (Try These First)

1. **Profile before optimizing** — run a profiler (cProfile, py-spy, perf) to find the actual hot path. Most gains come from the top 3 functions.
2. **Algorithm complexity** — O(n²) → O(n log n) can dominate all constant-factor wins.
3. **Data structures** — wrong structure (list vs dict, sorted vs unsorted) is often the culprit.
4. **Caching / memoization** — recomputing expensive pure functions is common.
5. **Batch operations** — vectorized ops (NumPy, Pandas) vs Python loops: 10–100× speedup.
6. **Avoid unnecessary allocations** — object creation inside hot loops is expensive.
7. **Parallelism** — CPU-bound → multiprocessing; I/O-bound → async or threading.

## Known Dead Ends

- **Micro-optimizations before profiling**: almost always wrong path, wastes time.
- **Premature parallelism**: adds complexity, often slower for small workloads due to overhead.
- **Rewriting in a "faster" language** without algorithmic improvement: rarely worth the complexity cost.
- **Changing output format or semantics** to game the benchmark: invalidates results.

## Critical Constraints

- **Output must be identical**: correctness is non-negotiable. Benchmark must verify correctness.
- **Benchmark must be representative**: the workload timed must reflect real usage patterns.
- **Warm-up runs**: for JIT-compiled code (PyPy, JVM), exclude cold-start from timing.
- **Stable environment**: don't run benchmarks while other heavy processes are running.

## Common Pitfalls

- Benchmarking I/O vs CPU: if the bottleneck is reading from disk, CPU optimization won't help.
- Testing on unrepresentative input sizes: gains at n=100 may disappear at n=10,000.
- Forgetting that `time` measures wall clock, not CPU time — background processes skew results.
- Caching between benchmark runs (check for state leakage in your benchmark script).

## Benchmark Design Notes

- Run 3–5 iterations and take the median, not the minimum — minimum is misleadingly optimistic.
- Use `hyperfine` for CLI commands if available; it handles warm-up and statistics automatically.
- For Python: use `timeit` with `number=10` for sub-second operations; plain `time` for longer ones.
- Correctness check: add a diff/assert after the main command to catch silent regressions.
