# autoresearch plugin

Autonomous experiment loop for any optimization or research target. An agent continuously proposes experiments, runs them, measures outcomes, and keeps what improves the metric — looping until manually interrupted.

## Skills

### `autoresearch-create`

**Interactive session bootstrapper.** Gathers context about the research goal, matches a domain template, creates session documents (`autoresearch.md`, `autoresearch.sh`, `autoresearch-log.sh`), establishes a baseline, and launches the loop.

Trigger: "run autoresearch", "optimize X in a loop", "set up experiments for Y", "start autoresearch on Z"

### `autoresearch`

**Domain-agnostic autonomous loop.** Reads existing session documents and runs the experiment cycle indefinitely: form hypothesis → edit files → run benchmark → log result → keep or revert.

Trigger: "resume autoresearch", "keep going", "continue the loop", or when `autoresearch.md` already exists and the loop needs to continue.

## Domain Templates

Pre-encoded knowledge for common research domains lives in `skills/autoresearch-create/domains/`. Each domain provides:

- `DOMAIN.md` — proven approaches, known dead ends, metrics, constraints
- `autoresearch-template.md` — pre-filled `autoresearch.md` starter
- `benchmark-template.sh` — ready-to-adapt benchmark script

| Domain | Primary Metric | Best for |
|--------|---------------|---------|
| `ml-training` | val_bpb / val_loss | Neural network training optimization |
| `code-optimization` | wall_time_ms | Making code faster or more memory-efficient |
| `security-research` | detection_rate / f1_score | Authorized security testing and defense research |

To add a new domain: create `skills/autoresearch-create/domains/<name>/` with the three required files.

## Session Artifacts

Created in the project being researched (not in this plugin):

```
autoresearch.md        # Rules document — read by every resuming agent
autoresearch.sh        # Experiment runner — outputs METRIC name=value lines
autoresearch-log.sh    # Logging helper — appends to JSONL, commits or reverts
autoresearch.jsonl     # Append-only result log — survives context resets
autoresearch.checks.sh # Optional correctness gate
autoresearch.ideas.md  # Optional deferred ideas backlog
```

## Design

See [../../.tasks/SKILL_DESIGN.md](../../.tasks/SKILL_DESIGN.md) for the full architecture decision record.
