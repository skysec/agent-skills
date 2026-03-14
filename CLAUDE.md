# AGENT Profile

## Quick Obligations

* Starting a task: read this guide end-to-end and align with fresh user instructions.
* Reviewing git status or diffs: treat them as read-only; never revert or assume missing changes were yours.
* Adding a dependency: research well-maintained options and confirm fit with the user before adding.

## Core Principles

- Think a lot before acting.
- If you delete or move code, do not leave a comment in the old place. No "// moved to X", no "relocated". Just remove it.
- **Think hard, do not lose the plot**.
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
- **Find root causes**: Fix things from first principles, find the source and fix it versus applying a cheap bandaid on top.
- When taking on new work, follow this order:
  1. Think about the architecture.
  1. Research official docs, blogs, or papers on the best architecture.
  1. Review the existing codebase.
  1. Compare the research with the codebase to choose the best fit.
  1. Implement the fix or ask about the tradeoffs the user is willing to make.
- Write idiomatic, simple, maintainable code. Always ask yourself if this is the most simple intuitive solution to the problem.
- Clean up unused code ruthlessly. If a function no longer needs a parameter or a helper is dead, delete it and update the callers instead of letting the junk linger.
- **Search before pivoting**. If you are stuck or uncertain, do a quick web search for official docs or specs, then continue with the current approach. Do not change direction unless asked.
- If code is very confusing or hard to understand:
  1. Try to simplify it.
  1. Add an ASCII art diagram in a code comment if it would help.

## Task Management

1. **Plan First**: Write plan to `.tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `.tasks/todo.md`
6. **Capture Lessons**: Update `.tasks/lessons.md` after corrections

## Workflow Orchestration

### 1. Plan Node Default
- Enter Plan mmode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Self-Improvement Loop
- After ANY correction from the user: update `.tasks/lessonsmd` with the pattern
- Write rules from yourself that precvent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant projects

### 3. Verification Before Done
- never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Run tests, check logs, demonstrate correctness

### 4. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 5. Autonmoous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Language Guidance

### TypeScript

- Do not use `any`; we are better than that.
- Using `as` is bad, use the types given everywhere and model the real shapes.
- If the app is for a browser, assume we use all modern browsers unless otherwise specified, we don't need most polyfills.

### Python

- **Python repos standard**. We use `uv` and `pyproject.toml` in all Python repos. Prefer `uv sync` for env and dependency resolution. Do not introduce `pip` venvs, Poetry, or `requirements.txt` unless asked. If you add a Nix shell, include `uv`.
- Use strong types, prefer type hints everywhere, keep models explicit instead of loose dicts or strings.

## Final Handoff

Before finishing a task:

1. Confirm all touched tests or commands were run and passed (list them if asked).
1. Summarize changes with file and line references.
1. Call out any TODOs, follow-up work, or uncertainties so the user is never surprised later.

## Dependencies & External APIs

- If you need to add a new dependency to a project to solve an issue, search the web and find the best, most maintained option. Something most other folks use with the best exposed API. We don't want to be in a situation where we are using an unmaintained dependency, that no one else relies on.

# SKILLs

## Technical Reference

### Plugin Structure

```
plugins/
  <plugin-name>/
    .claude-plugin/
      plugin.json         # Plugin metadata (name, version, description, author)
    commands/             # Optional: slash commands
    agents/               # Optional: autonomous agents
    skills/               # Optional: knowledge/guidance
      <skill-name>/
        SKILL.md          # Entry point with frontmatter
        references/       # Optional: detailed docs
        workflows/        # Optional: step-by-step guides
        scripts/          # Optional: utility scripts
    hooks/                # Optional: event hooks
    README.md             # Plugin documentation
```
**Important**: Component directories (`skills/`, `commands/`, `agents/`, `hooks/`) must be at the plugin root, NOT inside `.claude-plugin/`. Only `plugin.json` belongs in `.claude-plugin/`.

### Frontmatter

```yaml
---
name: skill-name              # kebab-case, max 64 chars
description: "Third-person description of what it does and when to use it"
allowed-tools:                # Optional: restrict to needed tools only
  - Read
  - Grep
---
```

### Naming Conventions

- **kebab-case**: `constant-time-analysis`, not `constantTimeAnalysis`
- **Gerund form preferred**: `analyzing-contracts`, `processing-pdfs` (not `contract-analyzer`, `pdf-processor`)
- **Avoid vague names**: `helper`, `utils`, `tools`, `misc`
- **Avoid reserved words**: `anthropic`, `claude`

### Path Handling

- Use `{baseDir}` for paths, **never hardcode** absolute paths
- Use forward slashes (`/`) even on Windows

### Python Scripts

When skills include Python scripts with dependencies:

1. **Use PEP 723 inline metadata** - Declare dependencies in the script header:
   ```python
   # /// script
   # requires-python = ">=3.11"
   # dependencies = ["requests>=2.28", "pydantic>=2.0"]
   # ///
   ```

2. **Use `uv run`** - Enables automatic dependency resolution:
   ```bash
   uv run {baseDir}/scripts/process.py input.pdf
   ```

3. **Include `pyproject.toml`** - Keep in `scripts/` for development tooling (ruff, etc.)

4. **Document system dependencies** - List non-Python deps (poppler, tesseract) in workflows with platform-specific install commands

### Hooks

PreToolUse hooks run on every Bash command—performance is critical:

- **Prefer shell + jq** over Python—interpreter startup (Python + tree-sitter) adds noticeable latency
- **Fast-fail early** - exit 0 immediately for non-matching commands so most invocations are instant
- **Favor regex over AST parsing** - accept rare false positives if performance gain is significant and Claude can rephrase
- **Anticipate false positive patterns** - diagnostic commands (`which python`), search tools (`grep python`), and filenames (`cat python.txt`) shouldn't trigger interception
- **Document tradeoffs** in PR descriptions so reviewers understand deliberate design choices

## Quality Standards

These are Trail of Bits house standards on top of Anthropic's requirements.

### Description Quality

Your skill competes with 100+ others. The description must trigger correctly.

- **Third-person voice**: "Analyzes X" not "I help with X"
- **Include triggers**: "Use when auditing Solidity" not just "Smart contract tool"
- **Be specific**: "Detects reentrancy vulnerabilities" not "Helps with security"

### Value-Add

Skills should provide guidance Claude doesn't already have, not duplicate reference material.

- **Behavioral guidance over reference dumps** - Don't paste entire specs; teach when and how to look things up
- **Explain WHY, not just WHAT** - Include trade-offs, decision criteria, judgment calls
- **Document anti-patterns WITH explanations** - Say why something is wrong, not just that it's wrong

**Example**: The DWARF skill doesn't include the full DWARF spec. It teaches Claude how to use `dwarfdump`, `readelf`, and `pyelftools` to look up what it needs, plus judgment about when each tool is appropriate.

### Scope Boundaries

Prescriptiveness should match task risk:
- **Strict for fragile tasks** - Security audits, crypto implementations, compliance checks need rigid step-by-step enforcement
- **Flexible for variable tasks** - Code exploration, documentation, refactoring can offer options and judgment calls

### Required Sections

Every SKILL.md must include:

```markdown
## When to Use
[Specific scenarios where this skill applies]

## When NOT to Use
[Scenarios where another approach is better]
```

### Security Skills

For audit/security skills, also include:

```markdown
## Rationalizations to Reject
[Common shortcuts or rationalizations that lead to missed findings]
```

### Content Organization

- Keep SKILL.md **under 500 lines** - split into `references/`, `workflows/`
- Use **progressive disclosure** - quick start first, details in linked files
- **One level deep** - SKILL.md links to files, files don't chain to more files

Note: Directory depth is fine (`references/guides/topic.md`). Reference *chains* are not (`SKILL.md → file1.md → file2.md` where file1 references file2). The problem is chained references, not nested folders.

### Progressive Disclosure Pattern

```markdown
## Quick Start
[Core instructions here]

## Advanced Usage
See [ADVANCED.md](references/ADVANCED.md) for detailed patterns.

## API Reference
See [API.md](references/API.md) for complete method documentation.
```

