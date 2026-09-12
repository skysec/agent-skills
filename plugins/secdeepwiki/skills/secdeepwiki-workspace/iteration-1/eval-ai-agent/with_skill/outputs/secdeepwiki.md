# SecDeepWiki — code-assistant-agent

> **Branch**: — | **Commit**: `—` | **Date**: —
> **Mode**: full | **Generated**: 2026-05-26T12:10:00Z | **Confidence**: 85%

---

## Repository Overview

| Field | Value |
|---|---|
| URL | /Users/hecbercordova/.claude/skills/ai-security-assess-workspace/evals/files/ai-agent |
| Author | — |
| Commit message | — |
| Monorepo | False |
| Languages | Python |
| Component types | ai_agent, cli_tool |

---

## Top Security Observations

| Severity | Component | Observation | Recommendation |
|---|---|---|---|
| **CRITICAL** | code-assistant-agent | HARDCODED API KEY: OpenAI API key hardcoded at agent.py:10 — CWE-798. Must be rotated immediately. | Rotate key. Move to os.environ['OPENAI_API_KEY']. Scan git history. |
| **CRITICAL** | code-assistant-agent | PROMPT INJECTION → RCE: user_context interpolated into system prompt via str.format() at agent.py:26. Attacker controls system prompt → model generates exec()/RUN: payload → code execution. | Static system prompt only. Never use str.format() with user input on the system prompt. |
| **CRITICAL** | code-assistant-agent | AUTO EXEC: LLM response auto-executed via exec() at agent.py:45 with full builtins — any prompt injection or model output manipulation leads to arbitrary code execution. | Remove exec() on LLM output. Use a sandboxed execution environment with human confirmation. |
| **CRITICAL** | code-assistant-agent | AUTO SHELL: LLM 'RUN: ' lines executed via subprocess.run(shell=True) at agent.py:53 — OS command injection from LLM output. | Remove subprocess execution of LLM output. If needed, use an allowlist and require explicit confirmation. |
| **HIGH** | code-assistant-agent | NO AUTH BEFORE CONTRACTOR ROLLOUT: Agent has no authentication. All future contractors get full code/shell execution as the process OS user. | Add authentication and per-identity authorization before any multi-user deployment. |
| **HIGH** | code-assistant-agent | API KEY LEAKAGE VIA EXCEPTIONS: agent.py:76 prints raw OpenAI exceptions which may contain API key fragments or request context. | Catch specific exception types. Log stripped error codes only, never raw exception strings. |

---

## Attack Surface Summary

| Metric | Count |
|---|---|
| External entry points | 1 |
| Internal entry points | 0 |
| Unauthenticated endpoints | 1 |
| File upload endpoints | 0 |
| Admin interfaces | 0 |
| Debug endpoints | 0 |

### ⚠️ Unauthenticated Endpoints

| Component | Path / Name |
|---|---|
| code-assistant-agent | `main (CLI)` |



---

## Component Inventory

| ID | Name | Path | Types | Entry Points | Overall Confidence |
|---|---|---|---|---|---|
| `code-assistant-agent` | Code Assistant Agent | `.` | ai_agent, cli_tool | 1 | 85% |

---

## Component: Code Assistant Agent

> Single-file Python AI agent (82 lines) wrapping the OpenAI GPT-4o API. Automatically executes Python code blocks and shell commands extracted from raw LLM output with no human confirmation. Contains a hardcoded API key and is described in comments as being extended to external contractors in a forthcoming sprint.


**Owner**: — | **Path**: `.`


### Classification

**Types detected**: ai_agent, cli_tool


**AI agent**: framework=`custom`
Models referenced:
- `openai/gpt-4o` — API key from: **hardcoded** 🚨 HARDCODED
Tools defined:
- **python_exec** (code_exec): Executes any Python code block from LLM response via exec() with full builtins. No sandbox, no allowlist, no confirmation.
- **shell_exec** (code_exec): Executes any 'RUN: ' prefixed line from LLM response via subprocess.run(shell=True). Full shell access.
RAG: False | Memory: none | Guardrails: False


### Tech Stack

**Languages**: Python

**Frameworks**:
- openai  (ai_ml)

**Runtime**: Python 

### Entry Points

| ID | Type | Path / Name | Method | Auth Required | Input Validation | File Upload |
|---|---|---|---|---|---|---|
| EP-001 | `cli_command` | `main` | — | — | False | False |

> ⚠️ **CRITICAL** `main`: user_context collected via input() and interpolated unescaped into system prompt via str.format() at agent.py:26. Attacker-controlled string reaches the system prompt directly — prompt injection leading to code execution.> Recommendation: Use a static system prompt. Place user context in the user role with explicit delimiters. Never use str.format() with user input on the system prompt.

> ⚠️ **CRITICAL** `main`: Every user_input turn passed to OpenAI as user message with no filtering. LLM response auto-executed via exec() (agent.py:45) and subprocess.run(shell=True) (agent.py:53). Indirect prompt injection from any content the agent is asked to review leads directly to code execution. (CWE-78)> Recommendation: Remove exec() and subprocess.run() on LLM output. Use a sandboxed code-execution API if execution capability is required. Add human confirmation before any execution.

> ⚠️ **HIGH** `main`: No authentication before contractor rollout (noted in comment). Any operator of the script will have full code/shell execution as the OS user running the process. (CWE-306)> Recommendation: Add identity verification and per-user authorization before any multi-user rollout.


### Authentication

| Type | Provider | Config Source | Token Storage | MFA Enforced |
|---|---|---|---|---|
| `none` | — | — | none | False |

**Session management**: none (store: unknown)


**Service-to-service auth**: api_key

### Authorization

**Model**: none | **Framework**: — | **Policy**: —

**Enforcement points**:
- `none` — coverage: **some_routes** — ⚠️ bypass risks: No authorization at any layer — all operators get full code/shell execution

### Cryptography

*No cryptographic operations detected.*

### Observability

- **Sensitive data in logs**: True
  - `agent.py:76 — print(f'Error: {e}') — raw OpenAI SDK exceptions may include API key fragments or request headers`
  - `agent.py:10 — OPENAI_API_KEY = 'sk-proj-4aB8...kL8' (redacted) — key present in source at module level`
- **Stack traces in HTTP responses**: True ⚠️
- **Audit trail present**: False

### Data Stores

*No data stores detected.*

---

## Data Flow Diagrams

### Context DFD

```mermaid
graph LR
  Operator([CLI Operator\nunauthenticated]) -->|stdin: user_context → system prompt\nuser_input → user message| Agent[Code Assistant Agent\nPython]
  Agent -->|HTTPS + hardcoded API key| OpenAI([OpenAI API\ngpt-4o])
  OpenAI -->|LLM response| Agent
  Agent -->|exec() / subprocess shell=True| OS[Host OS]

```

---

## Open Questions

These are Tier 2 controls that could not be confirmed from source code alone.
The team should answer these to complete the security picture.

| ID | Component | Impact if Absent | Question | Answer |
|---|---|---|---|---|
| Q-001 | code-assistant-agent | **CRITICAL** | What OS user runs this agent, and what filesystem/network privileges does it have? | *(unanswered)* |
| Q-002 | code-assistant-agent | **CRITICAL** | Has the hardcoded OpenAI API key (agent.py:10) been rotated? Is it present in git history? | *(unanswered)* |
| Q-003 | code-assistant-agent | **HIGH** | Is there rate limiting or quota enforcement on OpenAI API calls before the contractor rollout? | *(unanswered)* |
| Q-004 | code-assistant-agent | **HIGH** | Are there outbound network restrictions on the host that would limit data exfiltration via exec() or subprocess? | *(unanswered)* |
| Q-005 | code-assistant-agent | **CRITICAL** | What security hardening is planned before the 'next sprint' contractor rollout described in the code comments? | *(unanswered)* |

---

## Tester Handoff

### Pen Test Scope

**In scope:**

| Component | Entry Points | Technology |
|---|---|---|
| code-assistant-agent | 1 | Python CLI / OpenAI GPT-4o |


**SARIF export**: `exports/sarif-observations.json`

---

## CI/CD Security Gates

**Platform**: none

| Gate | Enabled |
|---|---|
| SAST | False |
| DAST | False |
| Secret scan | False |
| Code review required | False |

---

## Component Relationships

*Cross-component relationships not analyzed.*

---

*Generated by SecDeepWiki v3.0.0 | [snapshot.yaml](snapshot.yaml)*
