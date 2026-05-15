# Attack Chain Template

Use this exact structure for every attack chain document. All sections are required.
Omit a section only if it genuinely does not apply — state why it doesn't apply, don't
leave it blank or remove it.

---

```markdown
## Attack Chain: [VULN-NNN] — [Short Title]

**Vulnerability**: [one-sentence description] ([CWE-NNN — Name])
**Severity**: Critical | High | Medium | Low
**File**: `[path/to/file.c:line_start-line_end]`
**Function**: `[function_name]()`
**Evidence Level**: independently_verified | root_cause_explained
**Triage Confidence**: [N]% [[verdicts_str]→[arbiter_verdict]]

---

### 1. Entry Point

- **Primary entry function**: `[function()]` in `[file:line]`
- **Input vector**: [how attacker-controlled data enters — network packet, HTTP endpoint,
  file format field, environment variable, IPC message, CLI argument]
- **Protocol / format**: [TCP/UDP on port N, HTTP POST /api/upload, binary file format, etc.]
- **Authentication required**: [None / Bearer token (any user) / Admin role / Local process]
- **How to reach**:
  1. [Step 1: how to initiate the connection or trigger the input path]
  2. [Step 2: what to send to reach the vulnerable function]
  3. [Step 3: any state that must be established first]

**Call path** (source: trailmark graph / grep-based tracing — state which was used):
```
[entry_function() → intermediate() → vulnerable_function()]
[file:line]          [file:line]      [file:line]
```
If sourced from trailmark: `engine.entrypoint_paths_to(vulnerable_function)` result.
If sourced from grep: mark each hop as "grep-confirmed" or "inferred".

---

### 2. Vulnerability Mechanism

[2–4 sentences: what the code does wrong, which invariant is violated, what the attacker
controls, and what happens as a result of the violation.]

**Vulnerable code** (`[file:line_start-line_end]`):
```[language]
[relevant code snippet — the vulnerable lines ± 5 lines of context]
```

**Why existing defenses are insufficient**:
[If a guard exists: cite the specific check and show why it doesn't cover this case.
If no guard exists: confirm via grep.
Always cite actual numeric values — e.g., "header is declared as `char header[64]` (line 38),
len is attacker-controlled and not bounded before the memcpy at line 45".]

---

### 3. Exploitation Path

[Step-by-step from what the attacker sends to what security boundary is crossed.
Each step must be concrete — name the function, show the data, describe the state change.]

1. [Attacker connects to / opens / sends ...]
2. [The code parses / copies / evaluates the input, reaching `[function]` at `[file:line]`]
3. [The vulnerability manifests: buffer overflows / auth check returns true / query executes ...]
4. [The security boundary is crossed: stack corrupted / privilege granted / data returned ...]
5. [Post-exploitation (if applicable): attacker's position after the boundary is crossed]

---

### 4. Prerequisites & Constraints

| Prerequisite | Satisfied? | Notes |
|-------------|-----------|-------|
| Network access to port [N] | Yes / Maybe / No | [unauthenticated UDP, internal-only, etc.] |
| Authentication | None / User / Admin | [describe what credential or session is needed] |
| Target OS / architecture | [Linux x86_64, macOS ARM, any] | [ASLR / stack canary notes if memory corruption] |
| Race condition / timing | No / Yes | [if yes: describe the window and reliability] |
| Input format constraints | [describe] | [e.g., "must use binary protocol, not JSON API"] |
| Prior state required | No / Yes | [e.g., "session must be in authenticated state X"] |

**Exploitability summary:**
- **Attacker position**: Remote unauthenticated | Remote authenticated ([role]) | Local
- **Trigger reliability**: High (deterministic) | Medium (timing-dependent or partially guessed) |
  Low (requires specific target state or knowledge)
- **Trigger complexity**: Low (single malformed request) | Medium (multi-step setup) | High (race/chain)

---

### 5. Proof-of-Concept Skeleton

> Minimal reproduction skeleton for authorized security testing only.
> Not a complete exploit — demonstrates that the vulnerability is triggerable.
> Functions marked [VERIFY] must be confirmed against actual codebase before running.

```[python|bash|c|etc.]
# [Language] PoC skeleton for [VULN-NNN]
# Target: [function]() in [file]
# Authorization: [pentest engagement / CTF / security research — fill in]

[setup code: connection, auth if needed, file open, etc.]

# Craft the malformed input that triggers the bug
[input construction code — show exactly what makes it malicious]

# Send / trigger
[delivery code]

# Observe the result
# Expected when vulnerable: [crash / error message / auth granted / unexpected data returned]
# How to confirm it's fixed: [what changes in the output after the patch]
```

**If any function above is unresolvable from the codebase, mark it `# pseudocode` and
explain what it represents. A PoC with unresolved calls must be labeled "PSEUDOCODE ONLY"
in the heading.**

---

### 6. Severity Assessment

| Dimension | Assessment | Rationale |
|-----------|------------|-----------|
| Attacker position | Remote unauthenticated / Remote authenticated / Local | [specific reason] |
| Trigger complexity | Low / Medium / High | [e.g., "single malformed packet with no timing constraint"] |
| Impact class | RCE / Privilege escalation / Data exfiltration / Auth bypass / DoS / Info leak | [what specifically happens] |
| Preconditions | None / User account / Admin / Physical | [what the attacker needs] |

**Severity**: Critical | High | Medium | Low

**Rubric applied:**
- Critical: Remote unauthenticated + (RCE or full priv-esc or auth bypass) + low complexity
- High: Remote + high-impact + limited preconditions, OR remote unauth + medium impact
- Medium: Requires auth/local, OR limited impact even if remotely triggerable
- Low: Significant preconditions, minimal impact, primarily informational in isolation

[State which rule was applied and why. If between levels, state why you chose the lower/higher.]

**Calibration note**: [If hunter severity differs from this assessment: explain the discrepancy.
If they match: "Consistent with hunter-assigned severity."]

---

### 7. CWE Classification

- **Primary CWE**: CWE-[NNN] — [Name]
- **Related CWEs**: CWE-[NNN], CWE-[NNN]
- **OWASP Top 10**: A0[N]:202[X] — [Category]

---

### 8. Remediation

**Immediate fix** (minimal change to eliminate the bug):
```[language]
// Before
[vulnerable code]

// After
[patched code — show the specific check or bounds enforcement added]
```

**Defense in depth** (additional hardening):
- [Compiler flag / sanitizer / canary / ASLR / input validation layer]
- [Framework-level mitigation if applicable]

**Verification**: After applying the fix, the PoC skeleton above should produce:
`[expected safe output — e.g., "connection refused with error code X", "bounds check failure at line Y"]`

---

### 9. Related Findings

[List any variant findings or chained findings. If none, write "None identified."]

- [variant-XXXXXXXX — Potential variant in `other_file.c:L89` (suspicion level, unverified)]
- [VULN-002 — Related auth bypass that chains with this finding to enable RCE]
```
