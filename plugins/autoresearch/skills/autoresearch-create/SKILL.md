---
name: autoresearch-create
description: >
  Sets up and launches an autonomous experiment loop for any optimization or research target.
  Use this skill whenever the user wants to: "run autoresearch", "optimize X in a loop",
  "set up experiments for Y", "start autoresearch on Z", "autonomously research X",
  "run experiments overnight", "keep trying ideas until the metric improves", or
  "set up a benchmark loop". Also trigger when the user asks to improve a metric continuously
  or wants an agent to experiment autonomously without human approval at each step.
  This skill is the setup phase — it gathers context, writes session documents, and launches the loop.
---

# Autoresearch — Session Setup

Autonomous experiment loop: form hypotheses, try them, keep what improves the metric, discard the rest, run until interrupted. This skill creates the session and launches it.

## Behavioral Contract

You are **conversational during setup** and **autonomous after baseline**. Ask the minimum needed to proceed. Infer what you can from the codebase. Once the baseline is committed, enter the loop without asking for permission.

---

## Step 1 — Gather Context

Ask or infer the following. If you can read the codebase and answer confidently, do it without asking. Batch all questions into one message if you do need to ask.

| Field | What to determine |
|-------|------------------|
| **Goal** | What are we researching? e.g. "minimize val loss", "find fastest sorting config", "verify hypothesis H" |
| **Research type** | Optimization / Discovery / Verification / Ablation / Comparison |
| **Command** | Shell command that runs one experiment |
| **Primary metric** | Single number that decides success. Direction: lower or higher is better? |
| **Secondary metrics** | Other numbers to track (informational, not decision criteria) |
| **Files in scope** | What the agent may modify |
| **Off limits** | What must never change (eval harness, data, deps, etc.) |
| **Constraints** | Hard rules: tests must pass, no new deps, time budget per run, etc. |
| **Hypothesis** | Optional: what you expect to find |

Fail fast: if you genuinely can't infer goal or command from the codebase, ask — don't guess.

---

## Step 2 — Check Domain Templates

Look for `domains/` in the skill's directory (sibling to this SKILL.md). List subdirectory names, then read the `DOMAIN.md` in the best match. If a domain matches (confidence ≥ 60%), use its `autoresearch-template.md` and `benchmark-template.sh` as starting points.

If no domain matches or confidence is low, proceed without a template and note "no domain match" in the session doc.

See `references/domains-guide.md` for the domain folder structure and how to pick the best match.

---

## Step 3 — Branch and Read

```bash
git checkout -b autoresearch/<goal-slug>-$(date +%Y-%m-%d)
```

`<goal-slug>` = goal compressed to kebab-case, max 30 chars.

Read **all files in scope** before writing anything. Understand what the code does, how the command works, and what the metric measures. Surface-level understanding makes bad benchmarks.

---

## Step 4 — Write Session Documents

### `autoresearch.md` — The rules document

A fresh agent with no conversation history must be able to read this and run the loop effectively. Invest time making it excellent.

```markdown
# Autoresearch: <goal>

## Research Type
<Optimization | Discovery | Verification | Ablation | Comparison>

## Objective
<What are we researching and why? What question does this answer?>

## Hypothesis
<Initial expectation and what confirming/refuting it looks like. Delete if N/A.>

## Metrics
- **Primary**: <name> (<unit>, lower/higher is better)
- **Secondary**: <name> (<unit>), ...

## How to Run
`./autoresearch.sh` — outputs `METRIC name=number` lines.
Log with: `bash autoresearch-log.sh <commit> <metric_value> <status> "<description>"`

## Files in Scope
<Every file the agent may modify, with a note on what it does.>

## Off Limits
<What must never be touched.>

## Constraints
<Hard rules.>

## Domain Notes
<Domain-specific guidance from the template. Leave blank if no match.>

## Experimental History
<Updated every 5–10 runs. Key wins with why they worked. Dead ends with why they failed.
Directions exhausted. Do not let this grow stale.>

## Current Best
<Best result: metric value, commit hash, what changed.>
```

### `autoresearch.sh` — The experiment runner

```bash
#!/bin/bash
set -euo pipefail

# Pre-checks (should finish in < 1 second)
# <syntax check, fast validation, etc.>

# Run the experiment
<main command here>

# Output metrics — required format
echo "METRIC <primary_metric>=<value>"
echo "METRIC <secondary_metric>=<value>"   # repeat for each secondary
```

Rules:
- Keep it fast. Every extra second × hundreds of runs = real time lost.
- Exit 0 = success. Non-zero = crash (agent reverts and tries next idea).
- Must output at least one `METRIC name=value` line.
- Can be modified mid-loop to fix issues or add metrics.

### `autoresearch.checks.sh` — Correctness gate (optional)

**Only create this if the user's constraints require correctness validation** (e.g., "tests must pass", "types must check"). When this file exists, it runs automatically after every passing benchmark. Failure means `checks_failed` — revert, no commit. Execution time does NOT count toward primary metric.

```bash
#!/bin/bash
set -euo pipefail
# Suppress success output. Only let errors through.
pnpm test --run --reporter=dot 2>&1 | tail -50
```

### `autoresearch-log.sh` — Logging helper

Write this file to the project root:

```bash
#!/bin/bash
# Usage: bash autoresearch-log.sh <commit> <metric> <status> "<description>" [key=val ...]
# status: keep | discard | crash | checks_failed
set -euo pipefail
COMMIT="$1"; METRIC="$2"; STATUS="$3"; DESC="$4"
TIMESTAMP=$(date +%s%3N)
shift 4
EXTRAS=""
for kv in "$@"; do
  K="${kv%%=*}"; V="${kv#*=}"
  EXTRAS="$EXTRAS, \"$K\": $V"
done
echo "{\"commit\":\"$COMMIT\",\"metric\":$METRIC,\"status\":\"$STATUS\",\"description\":\"$DESC\",\"timestamp\":$TIMESTAMP$EXTRAS}" >> autoresearch.jsonl
if [ "$STATUS" = "keep" ]; then
  git add -A && git commit -m "autoresearch: $DESC (metric=$METRIC)"
else
  git checkout -- .
fi
```

---

## Step 5 — Commit Session Documents

```bash
git add autoresearch.md autoresearch.sh autoresearch-log.sh
git add autoresearch.checks.sh  # only if created
git commit -m "autoresearch: initialize session"
```

---

## Step 6 — Establish Baseline

Run the experiment once to get the starting metric:

```bash
bash autoresearch.sh
```

Parse the `METRIC name=value` output. Then log it:

```bash
COMMIT=$(git rev-parse HEAD)
bash autoresearch-log.sh "$COMMIT" <baseline_value> keep "baseline"
```

This commits the baseline. The loop starts from here.

---

## Step 7 — Enter the Loop

Now begin the experiment loop. Do **not** ask the user for permission to start. Follow the loop rules below until interrupted.

### Loop Rules

**LOOP FOREVER.** The user is likely away. Keep going until manually interrupted.

- **Primary metric is king.** Improved → `keep` (commit). Worse/equal → `discard` (revert). No exceptions.
- **Simpler is better.** Deleting code for equal performance = keep. Ugly complexity for tiny gain = discard.
- **Don't thrash.** Reverting the same idea repeatedly? Switch to a structurally different approach.
- **Think deeper when stuck.** Re-read source files. Reason from first principles. The best experiments come from deep understanding, not random variation.
- **Crashes:** Fix if trivial. Otherwise log, revert, move on. Don't over-invest.
- **Checks failed:** Log as `checks_failed`, revert, adapt the approach.
- **Never ask the user anything.** Make a reasonable choice and log your reasoning.

### Per-experiment cycle

1. Form hypothesis based on `autoresearch.md` state and prior results.
2. Edit files within declared scope only.
3. `bash autoresearch.sh` — capture stdout, exit code, timing.
4. If `autoresearch.checks.sh` exists and benchmark passed: run checks.
5. Decide: `keep` / `discard` / `crash` / `checks_failed`.
6. `bash autoresearch-log.sh <commit> <metric> <status> "<description>"` (+ secondary metrics as `key=value` args).
7. Every 5–10 experiments: update `autoresearch.md` "Experimental History" section.
8. Deferred ideas → append to `autoresearch.ideas.md`.

### Resuming after context reset

If `autoresearch.md` already exists when you're invoked:
1. Read `autoresearch.md`.
2. `git log --oneline -20` to see committed experiments.
3. `tail -20 autoresearch.jsonl` to see recent results.
4. Resume looping. No re-asking setup questions.
