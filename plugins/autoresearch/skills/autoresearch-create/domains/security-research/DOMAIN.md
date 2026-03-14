# Domain: Security Research

## What This Domain Covers

Empirical security research: testing attack success rates, defense mechanisms, detection systems, adversarial examples, evasion techniques, and security property verification. This domain is for authorized research contexts (CTF competitions, pentesting engagements, academic research, red team exercises, and defensive tooling development).

## Typical Goals

- Improve attack success rate against a target system (authorized testing only)
- Maximize defense/detection system robustness
- Minimize false positive rate while maintaining detection coverage
- Ablate which defensive features contribute most to security
- Benchmark security tools against known attack patterns

## Standard Metrics

- **success_rate**: float [0.0–1.0], higher is better for attack research, lower is better for defense
- **detection_rate**: float [0.0–1.0], higher is better for defenders
- **false_positive_rate**: float [0.0–1.0], lower is better
- **evasion_rate**: float [0.0–1.0], higher is better for adversarial research (authorized)
- **f1_score**: float [0.0–1.0], higher is better for balanced precision/recall

## Common Secondary Metrics

- `latency_ms` — detection/response time; critical for real-time systems
- `precision`, `recall` — complement f1_score for nuanced analysis
- `coverage_pct` — percentage of attack surface evaluated
- `payload_size_bytes` — smaller payloads are harder to detect (for authorized evasion research)

## Proven Experimental Approaches

1. **Baseline first** — establish a clear baseline before any modification.
2. **Single variable changes** — change one thing at a time to attribute metric changes correctly.
3. **Adversarial evaluation** — test against both known and novel attack patterns.
4. **Held-out test set** — never tune on the same examples you evaluate on.
5. **Statistical significance** — run enough trials (≥ 30) to distinguish signal from noise.
6. **Ablation study** — systematically remove/add defensive components to find what matters.

## Known Dead Ends

- **Tuning on the evaluation set** — overfitting to known attacks makes results meaningless.
- **Single-point measurements** — security metrics are stochastic; always aggregate over many trials.
- **Ignoring base rates** — a 99% detection rate sounds good until you learn FPR is 50%.
- **Closed-world evaluation** — systems tuned only on known attacks fail on novel ones.

## Critical Constraints

- **Authorization**: All experiments must be against systems you are authorized to test.
- **Isolation**: Run experiments in isolated environments to prevent accidental real-world impact.
- **Reproducibility**: Set random seeds; security research requires reproducible results.
- **Documentation**: Log all experiments — security research must be auditable.
- **Responsible disclosure**: If real vulnerabilities are found, follow responsible disclosure norms.

## Common Pitfalls

- Conflating detection on training data with detection on real attacks.
- Testing with unrealistically noisy or clean signals (benchmark must match deployment).
- Missing the actual threat model: optimizing for the wrong adversary.
- Not controlling for confounders (e.g., payload size affecting detection independent of content).

## Benchmark Design Notes

- Use a fixed, held-out evaluation set. Never tune against it.
- Run ≥ 30 trials per condition to get reliable statistics.
- Log both successes and failures — failures are often more informative.
- Version your attack/defense configurations in git so experiments are reproducible.
