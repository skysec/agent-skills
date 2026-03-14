---
name: autoresearch
description: >
  Runs or resumes an autonomous experiment loop. Reads autoresearch.md and loops
  indefinitely: form hypothesis → edit files → run benchmark → log result → keep or revert.
  Use this skill whenever autoresearch.md exists in the project and the user wants to
  continue experimenting, or when a research loop was interrupted and needs to resume.
  Also use when the user says "keep going", "resume autoresearch", "continue the loop",
  "run more experiments", or "start the experiment loop" after setup is already done.
  Do NOT use this skill for initial setup — use autoresearch-create for that.
---

# Autoresearch — Experiment Loop

You run an autonomous experiment loop. The session is already configured — your job is to keep trying ideas until interrupted.

## Before Starting: Resume Check

Check whether a session exists:

1. Look for `autoresearch.md`. If it doesn't exist, tell the user to run `/autoresearch-create` first. Stop.
2. If it exists: read it fully.
3. Run `git log --oneline -20` to see what's been committed.
4. Run `tail -20 autoresearch.jsonl 2>/dev/null || echo "no log yet"` for recent results.
5. Note the current best metric and what's already been tried. Then begin the loop.

Resumption is designed to work — `autoresearch.md` contains everything needed. Don't re-ask setup questions.

---

## The Loop

Repeat this cycle indefinitely until interrupted:

### 1. Form Hypothesis

Based on `autoresearch.md` state, git history, and JSONL results: what's the most promising next experiment? Reason from first principles — what does the metric actually measure? What in the code affects it? Don't repeat failed approaches without a structural reason they'd work differently this time.

Check `autoresearch.ideas.md` if it exists — deferred ideas belong here.

### 2. Edit

Modify only files listed in **Files in Scope**. Never touch **Off Limits** files.

### 3. Run

```bash
START=$(date +%s%3N)
bash autoresearch.sh
EXIT_CODE=$?
END=$(date +%s%3N)
ELAPSED_MS=$((END - START))
```

Capture the output. Parse `METRIC name=value` lines. Note the exit code.

If `autoresearch.checks.sh` exists and the benchmark passed: run it. Treat failure as `checks_failed`.

### 4. Decide and Log

```bash
COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "none")
bash autoresearch-log.sh "$COMMIT" <metric_value> <status> "<description>" [secondary_key=value ...]
```

| Outcome | Status | Action |
|---------|--------|--------|
| Metric improved | `keep` | log it — autoresearch-log.sh commits |
| Metric same or worse | `discard` | log it — autoresearch-log.sh reverts |
| Script crashed (non-zero exit) | `crash` | log it — revert, note what broke |
| Checks failed | `checks_failed` | log it — revert, adapt approach |

### 5. Update Session Docs

Every 5–10 experiments, update the **Experimental History** and **Current Best** sections of `autoresearch.md`. Stale session docs make future resumption worse.

Promising but deferred ideas → append to `autoresearch.ideas.md`.

---

## Loop Rules

**Primary metric is the decision criterion.** Improved → keep. Same or worse → discard. Secondary metrics are informational.

**Simpler is better.** Removing code for equal performance = keep. Adding complexity for a tiny gain = probably discard.

**Don't thrash.** If you've reverted the same approach twice, the idea is exhausted. Try something structurally different.

**Think deeper when stuck.** Re-read the source files. Reason about what the metric actually measures. Study the data the benchmark uses. The best experiments come from understanding, not from varying things randomly.

**Crashes aren't failures.** Log, revert, learn, move on. Don't spend more than one follow-up attempt fixing a crash.

**Never ask the user anything.** The session doc was written to be self-sufficient. Make the call yourself and log your reasoning.

---

## Autonomy

The user set this up to run without oversight. They may be away for hours. Keep going. Don't announce you're about to do another iteration. Don't summarize after each experiment. Just work.

If the user sends a message: finish the current `bash autoresearch.sh` + log cycle, then respond. Never abandon a running benchmark.
