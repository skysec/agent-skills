# Pipeline Stages — Deep Reference

## Stage 0 — Graph Build & Structural Analysis

### trailmark backend

Stage 0 is driven by `analyze.py` which calls trailmark:

```python
from trailmark import CodeGraph
engine = CodeGraph.from_directory(target_path, language="auto")
engine.preanalysis()
```

**Language coverage (20+):**
C, C++, Python, Go, Rust, JavaScript, TypeScript, Java, Ruby, PHP, Swift,
Solidity, Cairo, Circom, Haskell, Erlang, Kotlin, Dart, Objective-C, Miden Assembly.
`language="auto"` detects all supported languages in the target tree and merges their
graphs into a single queryable index.

**Node kinds:** function, method, class, struct, interface, trait, enum, module, namespace,
contract, library.

**Edge kinds and confidence:**
- `calls` — `certain` (direct static call), `inferred` (attribute access), `uncertain` (dynamic dispatch)
- `inherits`, `implements`, `contains`, `imports`

Only `certain` edges are used for blast-radius-rank normalization in Stage 1.
Both `certain` and `inferred` are used for entrypoint path tracing.

**Pre-analysis subgraphs** (computed by `engine.preanalysis()`):
- `tainted` — nodes reachable from untrusted external entry points via data flow
- `high_blast_radius` — functions called by many other nodes (wide downstream impact)
- `privilege_boundary` — nodes at trust-level transitions
- `entrypoint_reachable` — nodes reachable from the attack surface by any path

**Attack surface** (`engine.attack_surface()`):
Returns entry points with:
- `trust_level`: `untrusted_external` / `semi_trusted_external` / `trusted_internal`
- `asset_value`: `high` / `medium` / `low`

Entry point detection uses four-layer fallback:
1. Generic `main()` heuristic
2. Framework-aware scanning (Flask, FastAPI, Spring, NestJS, Solidity, etc.)
3. `pyproject.toml [project.scripts]` explicit targets
4. `.trailmark/entrypoints.toml` hand-curation override

**Fallback mode** (trailmark not installed):
`analyze.py` falls back to import-count heuristics for 8 languages.
`blast_radius_rank` is approximated from `import_count // 3`. `entrypoint_distance` defaults
to 3. `tainted`, `high_blast_radius`, `privilege_boundary` all default to False.
Downstream stages degrade gracefully — rankings are less accurate but the pipeline runs.

### SARIF augmentation (Stage 0b)

When `--sarif <path>` is passed to `analyze.py`:

```python
engine.augment_sarif(sarif_path)
```

External tool findings (Semgrep, CodeQL) are projected onto graph nodes by file/line overlap.
Matched findings become annotations on those nodes. Severity-stratified subgraphs are created
(`sarif:error`, `sarif:warning`).

**Effect on Stage 1:** Files with `sarif:error` annotations get their LLM-scored `surface`
boosted by +1 (capped at 5), ensuring they reach Tier A even if structural heuristics alone
would place them in Tier B.

### DFD generation (Stage 0c, depth=standard+)

After graph build, generate a Mermaid data-flow diagram from the attack surface:

```python
# Conceptual — use trailmark's diagramming-code skill
diagram = engine.diagramming("data-flow", depth=3, direction="LR")
```

This uses `attack_surface()` as roots and traces paths to sensitive functions (those in
the `tainted` or `privilege_boundary` subgraphs). Output: Mermaid `graph LR` diagram
written to `security-assessment/architecture-dfd.md`.

---

## Stage 1 — File Ranking

### Ranking axes

| Axis | Source | How computed |
|------|--------|-------------|
| `surface` | LLM | Semantic assessment per file (see scoring guide below) |
| `influence` | trailmark | `blast_radius_rank` from `ingest_graph.json` (1–5 normalized from certain_callers count) |
| `reachability` | trailmark | From `entrypoint_distance`: 0→5, 1→4, 2→3, 3→2 (normalized to 1–5) |

### Ranking LLM prompt inputs

For each file, provide the following to the ranker. Only ask for `surface` back:

```
File: net/parser.c
Language: C
LOC: 842
Cyclomatic complexity (max): 18
Tags: memory_unsafe, parser, network_entry
blast_radius_rank: 4       ← pre-computed, do NOT ask LLM to score
entrypoint_distance: 1     ← pre-computed, do NOT ask LLM to score
tainted: true              ← from pre-analysis
privilege_boundary: false  ← from pre-analysis
SARIF annotations: none    ← or list annotation severities if present
```

### Surface scoring guide (provide to ranker LLM)

**Score 5:**
- Parser for untrusted input with `memcpy` and unchecked length (C/C++)
- Authentication function with direct string/hash comparison of user-supplied credentials
- Crypto implementation with hardcoded key, IV, or salt
- Deserializer for network-supplied data (XML, YAML, pickle, msgpack)
- Any file tagged `memory_unsafe` AND `parser` AND `network_entry`

**Score 4:**
- Business logic processing external payments, transfer amounts, or access control decisions
- SQL query builder that accepts user-supplied filters
- File path handler that accepts user-supplied paths

**Score 3:**
- Internal API that processes data originating from external input (2+ hops removed)
- Template renderer for user-supplied content
- Session management code

**Score 2:**
- Internal utility with limited external exposure
- Logging/metrics code that receives sanitized data

**Score 1:**
- Constants file; pure configuration; auto-generated code; display-only code

### Priority formula and tiers

```
priority = surface × 0.5 + influence × 0.2 + reachability × 0.3
```

| Tier | Range | Budget share |
|------|-------|-------------|
| A | ≥ 3.5 | 65% |
| B | 2.0–3.5 | 30% |
| C | < 2.0 | 0% — skipped |

SARIF boost: files with `sarif:error` annotations get `surface += 1` (capped at 5) after
the LLM scoring step, before tier assignment.

---

## Stage 2 — Context Generation

### Graph data block (prepend to every briefing prompt)

```
[GRAPH DATA — from trailmark, do not re-derive these facts]

Taint status:       TAINTED
  Entrypoint path:  HTTP handler (net/server.c:recv_request) →
                    parse_header (net/parser.c:parse_header) →
                    parse_packet (net/parser.c:parse_packet)   ← THIS FILE
  Trust level:      untrusted_external (source: HTTP socket)

Blast radius:       HIGH
  Certain callers:  47 (transitively)
  Top callers:      process_request(), handle_connection(), main_loop()

Privilege boundary: NO

Cyclomatic complexity: 18 (branches: 14)

Entry point distance: 2 hops from attack surface
```

The taint entrypoint path is populated from `engine.entrypoint_paths_to(function_name)`.
This gives the hunter a verified, graph-derived call chain rather than an LLM-guessed one.

### Briefing LLM instructions

After the graph data block, ask for:

1. What this file does and its role in the project (2–3 sentences max)
2. Which specific variables inside the function carry attacker-controlled data
   (trailmark confirms taint reaches here; the LLM identifies the specific variable names
   and their flow within the function body)
3. Fixed-size buffers and numeric constants — use `GREP: #define MAX_BUF` to resolve values
4. Dangerous data flows: untrusted var → size arithmetic → allocation/copy → possible overflow
5. NULL/out-of-range parameters from malformed input
6. Tagged unions or variants accessed without type-tag validation
7. Top-3 most likely bug class(es) for this file given all the above

Cap briefing at 250 words. The graph data block is not counted against this limit.

---

## Stage 3 — Tiered Vulnerability Hunt

### Tier A specialist system prompts

Each specialist receives: (1) file content, (2) context briefing, (3) graph flags, (4) specialist focus.

**Graph flags block** (injected into every specialist system prompt):

```
[STRUCTURAL CONTEXT — from trailmark pre-analysis]
TAINTED: true — attacker-controlled data confirmed to reach this file
HIGH_BLAST_RADIUS: true — bugs here have wide downstream impact; escalate severity
PRIVILEGE_BOUNDARY: false — no trust level transition at this function
ENTRYPOINT_DISTANCE: 2 — reachable in 2 hops from the attack surface
```

These flags tell each specialist what to prioritize before reading a line of code:
- `TAINTED: true` + `injection` specialist → prioritize data-flow analysis immediately
- `PRIVILEGE_BOUNDARY: true` + `auth_logic` specialist → focus on the trust transition
- `HIGH_BLAST_RADIUS: true` → any finding here gets impact raised by one severity level

#### memory_safety specialist

**System prompt emphasis:**
Focus on spatial memory safety (buffer overflow, heap corruption, integer overflow → allocator
tricks), temporal safety (UAF, double-free), null dereference, type confusion, format string,
uninitialized memory.

Key checks:
- Every `memcpy`, `strcpy`, `sprintf`, `gets` call: is destination bound checked before the copy?
- Every size computation before allocation: can it wrap (integer overflow)?
- Every pointer cast: is the underlying allocation large enough for the target type?
- Every `free()`: is the pointer used afterward?
- Every `malloc()` return: is NULL checked before dereference?

#### auth_logic specialist

**System prompt emphasis:**
Authentication bypass, broken access control, IDOR, privilege escalation, session
fixation/hijacking, insecure deserialization leading to object injection.

Key checks:
- Every authentication check: can it be short-circuited by parameter manipulation?
- Every authorization gate: is it applied consistently on ALL paths to the protected resource?
- Every object reference (ID, path, key): is the caller authorized for that specific object?
- Every role/permission check: can a lower-privileged role reach the same action with different params?
- Every deserialization point: are type constraints enforced?

When `PRIVILEGE_BOUNDARY: true`: focus here first — this is where trust transitions happen.

#### injection specialist

**System prompt emphasis:**
Command injection (shell=True, exec, eval), SQLi (string concatenation), SSRF (unvalidated URL),
path traversal, SSTI, XSS, XXE, LDAP injection.

Key checks:
- Every `subprocess.run` / `os.system` / `exec`: does attacker data flow into the command?
- Every database query: is user input parameterized or concatenated?
- Every HTTP request with user-supplied URL: is the host validated against an allowlist?
- Every file open with user-supplied path: is `../` stripped? Is the path canonicalized?
- Every template render: does attacker content reach the template engine as code?

When `TAINTED: true`: trace the specific tainted variable from the graph data block through
every operation until it reaches a dangerous sink. Do not stop at the first use.

#### crypto_logic specialist

**System prompt emphasis:**
Algorithm weakness (MD5/SHA1 for integrity, DES/RC4 for encryption), hardcoded keys/IVs/salts,
ECB mode, predictable randomness, missing integrity checks (unauthenticated encryption), key
reuse across sessions, timing side-channels in comparison.

Key checks:
- Every crypto primitive: is the algorithm appropriate for the security goal?
- Every key/IV: hardcoded? Reused across operations or sessions?
- Every encryption call: is it authenticated (AEAD)?
- Every secret comparison: constant-time?
- Every random value for security: CSPRNG (`secrets` / `crypto/rand` / not `math/rand`)?

### Hunter severity rubric

All four specialists must use this rubric when assigning `"severity"` to a finding.
The attack chain skill uses the same rubric — if a hunter's label and the attack chain
label differ by more than one level, Stage 7 takes the lower (conservative).

| Severity | Attacker position | Impact class | Complexity |
|----------|------------------|--------------|-----------|
| **Critical** | Remote, unauthenticated | RCE, full priv-esc, or auth bypass | Low — single malformed input |
| **High** | Remote, unauthenticated | Significant data exfil, partial priv-esc, DoS | Any |
| **High** | Remote, authenticated (any role) | RCE, full priv-esc, or auth bypass | Any |
| **Medium** | Remote, authenticated | Significant data exfil, partial priv-esc | Any |
| **Medium** | Local | RCE or full priv-esc | Any |
| **Low** | Local | Limited impact, info leak, or DoS | High preconditions |
| **Info** | Any | No direct security boundary crossed in isolation | — |

**Bias rule:** when in doubt, go one level higher — undersizing risk is more dangerous than oversizing.
**Chaining rule:** if this finding chains with another (e.g., info-leak enables memory corruption),
state the dependency and rate the *combined* impact, not the isolated one.

---

### Tier B — single-pass guided hunt

One LLM call with full context briefing + graph flags + file content. Ask for a JSON array
of findings. Model may emit `GREP: pattern` — execute and follow up.

### Cross-file subsystem hunt (depth=deep)

Use trailmark connectivity data for subsystem identification rather than directory prefix alone:

```python
# Files where >30% of their calls cross into each other
# Use engine.subgraph() cross-reference counts
```

For each identified subsystem (max file priority ≥ 3.5), run the subsystem hunter with access
to all files in the subsystem. Focus on bugs that span file boundaries:
- **TOCTOU**: check in function A, use in function B (different call stacks, shared state)
- **Confused deputy**: function A calls B with A's broad credentials for C's narrow operation
- **Inconsistent validation**: X validates input, passes to Y which validates differently (gaps)
- **Split-phase**: authorization check in phase 1, privileged action in phase 2, state modified
  between phases
- **Data races**: two functions accessing shared mutable state without synchronization

Subsystem hunter has access to all standard tools plus `engine.paths_between(src, dst)` to
confirm cross-file call paths.

---

## Stage 8 — Report Generation

### Recommendations priority matrix

The `recommendations` section of the YAML report is a ranked list ordered by a composite
score. Compute the score for each finding after Stage 7 calibration:

```
priority_score = (severity_score × 0.50)
              + (confidence_score × 0.25)
              + (attacker_position_score × 0.25)
```

**Severity score** (use `final_severity` after Stage 7 calibration):

| Label | Score |
|-------|-------|
| critical | 4 |
| high | 3 |
| medium | 2 |
| low | 1 |

**Confidence score** — use `triage.confidence_score` (float 0.0–1.0) scaled to 0–4:
`confidence_score × 4`

**Attacker position score** — derived from the attack chain entry point trust level:

| Position | Score |
|----------|-------|
| Remote, unauthenticated | 4 |
| Remote, authenticated (low-privilege role) | 3 |
| Remote, authenticated (elevated role) | 2 |
| Local | 1 |

If no attack chain was generated (finding did not reach `root_cause_explained`), use
`attacker_position_score = 2` as a conservative default.

**Tie-breaking:** when two findings have identical `priority_score`, rank by:
1. `severity_score` descending
2. `confidence_score` descending
3. Alphabetical by `id`

**Chained findings:** a finding pair confirmed as exploitable in Stage 7 (e.g.,
info-leak + memory corruption) receives the combined severity's score for both entries.
List the pair consecutively and note the dependency in the recommendation text.

**Output:** the `recommendations` list in `vuln-research-report.yaml` must be sorted by
`priority_score` descending before the report is rendered.
