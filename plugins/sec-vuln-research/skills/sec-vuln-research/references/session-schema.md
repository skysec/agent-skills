# Session Directory Schema

All three skills (`sec-vuln-research`, `sec-vuln-triage`, `sec-attack-chain`) read and write
the same session directory structure. This is the coordination contract between them.

## Output Model

**`vuln-research-report.yaml` is the single source of truth.**

The session directory holds two representations of the report:
- `vuln-research-report.yaml` — the authoritative data store, filled progressively as each stage completes
- `vuln-research-report.md` — a rendered Markdown view, generated on demand from the YAML

Never edit the Markdown directly. Render at any time with:
```
uv run {baseDir}/scripts/render_report.py <session_dir>/vuln-research-report.yaml
```

At session start, copy the blank template into the session directory:
```
cp {baseDir}/templates/vuln-research-report.yaml <session_dir>/vuln-research-report.yaml
```

The full YAML schema (with field documentation and allowed values) is in:
`{baseDir}/templates/vuln-research-report.yaml`

## Directory Layout

```
<session_dir>/                              # e.g., vuln-research/2026-05-15T14:05:00Z/
├── vuln-research-report.yaml              # SINGLE SOURCE OF TRUTH — fill during pipeline
├── vuln-research-report.md                # rendered from YAML (do not edit directly)
├── session-state.json                     # checkpoints + budget — session_state.py owns this
├── ingest_graph.json                      # Stage 0: graph + per-file data + coverage ledger
├── semgrep.sarif                          # Stage 0b bundled pre-filter output (if semgrep ran)
├── rejected.jsonl                         # Demoted findings (one JSON object per line)
├── findings.sarif                         # SARIF v2.1.0 (+ taint codeFlows) — emitted by
│                                          #   render_report.py from the validated pass
├── validation-plan.json                   # testable plan per attack-chained finding; a
│                                          #   validator writes results back to close the loop
├── architecture-dfd.md                    # Stage 0c Mermaid DFD (depth=standard+)
├── attack-chains/
│   ├── VULN-001_parser_c_stack_overflow.md
│   └── ...
├── triage/
│   ├── rounds/                            # TALLY INPUTS — written by lens subagents, read
│   │   └── VULN-001/                      # by triage_tally.py and render_report.py. Never
│   │       ├── 01_reachability.json       # hand-edit: the report's verification stamp is
│   │       ├── 02_defenses.json           # recomputed from these files.
│   │       ├── 03_impact.json
│   │       └── 04_arbiter.json
│   ├── T0001_parser_c_stack_overflow.md   # human-readable narratives
│   └── ...
└── context/
    ├── net_parser_c.context.md
    └── ...
```

> `findings.json` and `pipeline-status.json` from the previous design are superseded
> by `vuln-research-report.yaml`, which carries both in its `findings` and `pipeline` sections.

## Ownership: which tool writes what

| Artifact | Written by | Model may edit? |
|----------|-----------|-----------------|
| `session-state.json` | `session_state.py` (init/checkpoint/cost) | Never directly |
| `triage/rounds/**/*.json` | lens + arbiter subagents (once each) | Never after writing |
| YAML `findings[].triage` block | `triage_tally.py` | Never |
| YAML `verification`, `risk_counts`, recommendation scores/order | `render_report.py` | Never |
| YAML everything else | the orchestrating model, per stage | Yes |
| `vuln-research-report.md` | `render_report.py` | Never |
| `findings.sarif` | `render_report.py` (same validated pass as the report) | Never |
| `validation-plan.json` | `render_report.py` (from `attack_chain.validation` blocks) | Never |
| `attack_chain.validation.result` | the downstream validator (DAST/fuzzer/agent) | Only the validator writes it |

`render_report.py` recomputes triage tallies from `triage/rounds/` at render time and refuses
any finding whose YAML claims don't match — so hand-editing computed fields doesn't change the
report, it just gets the finding refused.

## Round record schema (`triage/rounds/<FINDING_ID>/<seq>_<lens>.json`)

```json
{
  "finding_id": "VULN-001",
  "lens": "reachability | defenses | impact | combined | arbiter | redteam",
  "verdict": "VALID | INVALID | UNCERTAIN",
  "reasoning": "cites the decisive code",
  "evidence": [{"file": "net/parser.c", "line": 42, "note": "unchecked memcpy"}],
  "crux": "arbiter records only — one sentence",
  "recorded_at": "ISO-8601"
}
```

---

## session-state.json

Owned entirely by `session_state.py` — created by `init`, advanced by `checkpoint`, charged
by `cost record`. The `resume` subcommand reads it to print the first incomplete stage and
its pending units.

```json
{
  "created_at": "2026-05-05T14:05:00Z",
  "updated_at": "2026-05-05T14:22:10Z",
  "config": {"mode": "full", "depth": "standard", "budget_usd": 25.0},
  "budget": {
    "limit_usd": 25.0,
    "spent_usd": 12.4,
    "by_stage": {"ranking": 0.4, "context_generation": 2.1, "hunting": 9.9}
  },
  "stages": {
    "graph_build": {"status": "completed", "units": {}},
    "hunting": {
      "status": "started",
      "units": {"net/parser.c": "done", "db/queries.py": "pending"}
    }
  }
}
```

`cost record` exits with code 3 when the total crosses `limit_usd` — the resumable-stop
signal (0 = unlimited).

---

## ingest_graph.json

Produced by `analyze.py` (trailmark backend). Its fields populate `report.graph_analysis`
and `report.file_ranking` in the YAML report during Stages 0–1.

Schema is identical whether trailmark is
installed or the fallback heuristic ran — trailmark-specific fields default to conservative
values in fallback mode.

```json
{
  "target": "/path/to/repo",
  "generated_at": "2026-05-05T14:05:10Z",
  "elapsed_seconds": 12.4,
  "backend": "trailmark",
  "graph_backend": "trailmark",
  "warning": null,
  "sarif_source": "/path/to/session/semgrep.sarif",
  "sarif_annotated_files": 7,
  "coverage": {
    "total_files": 214,
    "analyzed_files": 187,
    "not_analyzed_files": 27,
    "by_top_level_dir": {"net": {"total": 40, "analyzed": 38}},
    "skipped_dirs": {"vendor": {"reason": "vendored dependencies", "file_count": 12}}
  },
  "summary": {
    "node_count": 1847,
    "edge_count": 4312,
    "language_count": 3
  },
  "attack_surface": [
    {
      "id": "net/server.c:recv_request",
      "name": "recv_request",
      "file": "net/server.c",
      "line": 88,
      "trust_level": "untrusted_external",
      "asset_value": "high"
    }
  ],
  "complexity_hotspots": [
    {
      "id": "net/parser.c:parse_packet",
      "name": "parse_packet",
      "cyclomatic_complexity": 18
    }
  ],
  "files": [
    {
      "path": "net/parser.c",
      "language": "C",
      "loc": 842,
      "function_count": 34,
      "max_cyclomatic_complexity": 18,
      "total_branches": 42,
      "tainted": true,
      "high_blast_radius": true,
      "privilege_boundary": false,
      "entrypoint_reachable": true,
      "entrypoint_distance": 2,
      "certain_callers": 47,
      "inferred_callers": 6,
      "blast_radius_rank": 4,
      "sarif_errors": 1,
      "sarif_warnings": 0,
      "surface": null,
      "influence": null,
      "reachability": null,
      "priority": null,
      "tier": null
    }
  ]
}
```

**Fallback indicator:** `"backend": "fallback-heuristic"` — blast_radius_rank is approximated,
taint/blast_radius/privilege_boundary flags are False (conservative).

**Stage 1 populates:** `surface`, `influence`, `reachability`, `priority`, `tier` per file.

---

## findings.json

Array of finding objects. Fields are added progressively as findings move through stages.

```json
[
  {
    "id": "VULN-001",
    "hunt_id": "hunt-abc12345",
    "specialist": "memory_safety",
    "file": "net/parser.c",
    "line_start": 42,
    "line_end": 67,
    "function": "parse_packet",
    "finding_type": "stack_buffer_overflow",
    "cwe": "CWE-122",
    "severity": "critical",
    "confidence": "high",
    "description": "memcpy copies attacker-controlled len into 64-byte stack buffer",
    "code_snippet": "char header[64]; memcpy(header, data, len);",
    "taint_source": "recv_request() → parse_header() → parse_packet() [from trailmark]",
    "taint_sink": "memcpy(header, data, len)",
    "precondition": "Attacker controls the `len` field of the incoming packet",
    "evidence_level": "independently_verified",
    "graph_context": {
      "tainted": true,
      "high_blast_radius": true,
      "privilege_boundary": false,
      "entrypoint_distance": 2,
      "entrypoint_path": "recv_request → parse_header → parse_packet"
    },
    "triage": {
      "rounds": 4,
      "verdicts": "VVI",
      "lenses": "R:V D:V I:I",
      "arbiter_verdict": "VALID",
      "confidence_score": 0.75,
      "low_confidence": false,
      "crux": "len is attacker-controlled, no bounds check before memcpy",
      "triage_file": "triage/T0001_parser_c_stack_overflow.md",
      "computed_by": "triage_tally.py"
    },
    "attack_chain_file": "attack-chains/VULN-001_parser_c_stack_overflow.md",
    "variants": ["variant-def67890"],
    "chained_with": null,
    "final_severity": "critical",
    "severity_calibration_note": null
  }
]
```

**`graph_context`** — added by Stage 3 hunters, sourced from `ingest_graph.json`. Provides
verifiable structural context for triage (the `TRIGGERABLE` axis can reference `entrypoint_path`
rather than relying on grep-based caller tracing alone).

---

## pipeline-status.json

```json
{
  "stages": {
    "graph_build": {
      "status": "completed",
      "duration_ms": 12400,
      "backend": "trailmark",
      "files": 187,
      "node_count": 1847,
      "edge_count": 4312
    },
    "dfd_generation": {"status": "completed", "duration_ms": 800},
    "ranking": {
      "status": "completed",
      "duration_ms": 8200,
      "cost_usd": 0.07,
      "note": "LLM scored surface only; influence and reachability from trailmark graph",
      "tier_a": 22, "tier_b": 61, "tier_c": 104
    },
    "context_generation": {"status": "completed", "duration_ms": 38000, "cost_usd": 0.81, "files_briefed": 83},
    "hunting": {"status": "completed", "duration_ms": 184000, "cost_usd": 3.12, "findings_raw": 47},
    "triage": {"status": "completed", "duration_ms": 96000, "cost_usd": 1.87, "valid": 14, "invalid": 28, "uncertain": 5},
    "variant_analysis": {"status": "completed", "duration_ms": 12000, "cost_usd": 0.22, "variants": 8},
    "attack_chains": {"status": "completed", "duration_ms": 78000, "cost_usd": 1.44, "chains_generated": 9},
    "report": {"status": "completed", "duration_ms": 5200}
  },
  "totals": {
    "duration_ms": 434000,
    "cost_usd": 7.53,
    "ranking_savings_note": "~60% fewer ranking tokens vs 3-axis LLM scoring",
    "findings_critical": 3,
    "findings_high": 6,
    "findings_medium": 5,
    "findings_uncertain": 5,
    "variants_surfaced": 8
  }
}
```

---

## executive-summary.md Structure

```markdown
# Security Vulnerability Research — Executive Summary

**Session**: 2026-05-05T14:05:00Z
**Target**: /path/to/repo
**Date**: 2026-05-05
**Duration**: 7m 14s
**LLM Cost**: $7.53
**Graph backend**: trailmark (1847 nodes, 4312 edges)

## Critical Findings

| ID | Title | File | Severity | Confidence |
|----|-------|------|----------|-----------|
| VULN-001 | Stack buffer overflow in parse_packet | net/parser.c:42 | Critical | 83% [VVIVV→V] |

## High Findings

| ID | Title | File | Severity | Confidence |
|----|-------|------|----------|-----------|
| VULN-004 | SQL injection in user_search | db/queries.py:118 | High | 80% [VVIVV→V] |

## Findings Requiring Human Review

| ID | Title | Reason |
|----|-------|--------|
| UNC-001 | Potential TOCTOU in file handler | Uncertain after 5 rounds |

## Attack Surface (from trailmark)

| Entry Point | File | Trust Level | Asset Value |
|------------|------|------------|------------|
| recv_request | net/server.c:88 | untrusted_external | high |

## Statistics

- Files analyzed: 187 (Tier A: 22, Tier B: 61, Tier C: 104 skipped)
- Findings from hunters: 47
- After triage: 14 (Critical: 3, High: 6, Medium: 5)
- Rejected by triage: 28
- Uncertain (human review): 5
- Variants surfaced: 8
- Attack chains generated: 9

## Pipeline Health

| Stage | Status | Notes |
|-------|--------|-------|
| Graph build | OK | trailmark, 187 files, 1847 nodes |
| DFD generation | OK | architecture-dfd.md written |
| Ranking | OK | 22 Tier A (surface-only LLM scoring) |
| Context generation | OK | 83 files briefed with graph context |
| Hunting | OK | 47 raw findings (graph flags injected) |
| Triage | OK | 14 valid, 28 rejected, 5 uncertain |
| Attack chains | OK | 9 generated |
```

---

## Standalone Invocation Contract

When `sec-vuln-triage` or `sec-attack-chain` are invoked standalone (not via the orchestrator):

- **`sec-vuln-triage`** standalone: user provides `finding_id` or raw finding JSON + `session_dir`
  path (or repo path without session). If `session_dir` exists, triage can read `ingest_graph.json`
  to use `entrypoint_path` from `graph_context` for the `TRIGGERABLE` axis.

- **`sec-attack-chain`** standalone: user provides `finding_id` + `session_dir` + `repo_path`.
  If `session_dir` contains `ingest_graph.json`, the skill uses `engine.entrypoint_paths_to()`
  for entry point tracing. Falls back to grep-based `trace_callers` if graph is unavailable.

If no session directory exists (ad-hoc invocation), both skills create a minimal `session.json`
and `findings.json` in `vuln-research/standalone-<timestamp>/`.
