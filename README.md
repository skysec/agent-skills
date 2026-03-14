# agent-skills

Reusable Claude Code assets shared across projects: skills, hooks, sub-agents, and CLAUDE.md configuration.

## What's Here

| Component | Path | Purpose |
|-----------|------|---------|
| Agent config | `CLAUDE.md` | Shared agent profile — drop into any project |
| Skills plugin | `plugins/autoresearch/` | Autonomous experiment loop skills |

## CLAUDE.md — Shared Agent Profile

`CLAUDE.md` defines the agent's behavior contract for this workspace and any project that copies it. It covers:

- **Core principles** — simplicity-first, minimal impact, root-cause fixes
- **Task management** — plan → verify → implement → document workflow
- **Workflow orchestration** — plan mode, self-improvement loop, autonomous bug fixing
- **Language standards** — TypeScript (no `any`, no `as`), Python (`uv` + `pyproject.toml`)
- **Skill authoring standards** — plugin structure, naming conventions, quality requirements

To use it in another project, copy `CLAUDE.md` to the project root.

## Plugins

### `autoresearch`

Autonomous experiment loop for any optimization or research target. An agent continuously proposes experiments, runs them, measures outcomes, and keeps what improves the metric — looping until manually interrupted.

```
plugins/autoresearch/
  skills/
    autoresearch-create/    # Setup: gather context, write session docs, establish baseline
    autoresearch/           # Loop: form hypothesis → edit → benchmark → log → keep/discard
      domains/
        ml-training/        # Neural network training optimization
        code-optimization/  # Runtime and memory performance
        security-research/  # Authorized security testing and defense
```

**Skills:**

- **`autoresearch-create`** — Interactive bootstrapper. Gathers the research goal, matches a domain template, creates session documents (`autoresearch.md`, `autoresearch.sh`, `autoresearch-log.sh`), establishes a baseline, and enters the loop.

  Triggers: "run autoresearch", "optimize X in a loop", "set up experiments for Y", "start autoresearch on Z"

- **`autoresearch`** — Domain-agnostic loop executor. Reads the existing session and runs the experiment cycle indefinitely.

  Triggers: "resume autoresearch", "keep going", "continue the loop", or when `autoresearch.md` exists in a project

**Session artifacts** (created in the project, not here):

```
autoresearch.md        # Rules document — survives context resets
autoresearch.sh        # Experiment runner — outputs METRIC name=value lines
autoresearch-log.sh    # Logging helper — appends to JSONL, commits or reverts
autoresearch.jsonl     # Append-only result log
autoresearch.checks.sh # Optional correctness gate
autoresearch.ideas.md  # Optional deferred ideas backlog
```

See [plugins/autoresearch/README.md](plugins/autoresearch/README.md) for full documentation and [.tasks/SKILL_DESIGN.md](.tasks/SKILL_DESIGN.md) for the architecture decision record.

## Skill Authoring Standards

New skills must follow the conventions in `CLAUDE.md` (`# SKILLs` section). Key rules:

- **Plugin structure**: `plugins/<name>/.claude-plugin/plugin.json` + component dirs at plugin root
- **Frontmatter**: `name` (kebab-case), `description` (third-person, trigger-inclusive), optional `allowed-tools`
- **Required sections**: `## When to Use` and `## When NOT to Use` in every `SKILL.md`
- **Size limit**: `SKILL.md` under 500 lines — overflow into `references/` or `workflows/`
- **No hardcoded paths**: use `{baseDir}` in scripts

