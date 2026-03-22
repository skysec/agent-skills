# MCP Security Requirements

> **Convention:** Obligation levels follow RFC 2119. **MUST** = mandatory. **SHOULD** = strongly recommended. **MAY** = optional.  
> **Priority:** `HIGH` = foundational control, `LOW` = baseline hygiene, `INFO` = defence-in-depth / best practice.

---

## Table of Contents

1. [AD — Prompt Injection & Agent Defense](#ad--prompt-injection--agent-defense)
2. [AA — Authentication & Authorization](#aa--authentication--authorization)
3. [IV — Input Validation](#iv--input-validation)
4. [SM — Secrets Management](#sm--secrets-management)
5. [RI — Runtime Isolation](#ri--runtime-isolation)
6. [SS — Supply Chain Security](#ss--supply-chain-security)
7. [TD — Tool Definitions](#td--tool-definitions)
8. [LM — Logging & Monitoring](#lm--logging--monitoring)
9. [CH — Consent & Human Controls](#ch--consent--human-controls)
10. [TN — Transport & Network Security](#tn--transport--network-security)
11. [DP — Data Provenance](#dp--data-provenance)
12. [ST — Security Testing](#st--security-testing)

---

## AD — Prompt Injection & Agent Defense

### MCP-REQ-001 · AD-1 · `MUST` · Priority: HIGH

**Control/Data Flow Separation**

Separate control flow (trusted instructions) from data flow (untrusted tool descriptions, user inputs, tool outputs). Malicious instructions embedded in data MUST NOT influence program execution.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | High |
| Mitigated Tactics | SAFE-T1001 (Initial Access – ATK-TA0001), SAFE-T1102 (Initial Access – ATK-TA0001) |
| SAFE-MCP-ID | SAFE-M-1 |
| CoSAI Control | Prompt Injection & Content Security (T4) |

---

### MCP-REQ-002 · AD-2 · `MUST` · Priority: HIGH

**Output Context Isolation**

Implement output context isolation — responses from one tool MUST NOT inject instructions affecting other tools or the host agent's control flow. Use structured formatting to delimit tool outputs from system instructions.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Medium |
| Mitigated Tactics | SAFE-T1701 (Lateral Movement – ATK-TA0008) |
| SAFE-MCP-ID | SAFE-M-21 |
| CoSAI Control | Prompt Injection & Content Security (T4) |

---

### MCP-REQ-003 · AD-3 · `MUST` · Priority: LOW

**Single-Purpose Tool Design**

Each tool MUST have a single, clearly defined purpose with explicit input/output boundaries. Do not create overly permissive "do-everything" tools.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1104 (Privilege Escalation – ATK-TA0004) |
| CoSAI Control | Least Privilege & Isolation (T2), Trust Boundary Enforcement (T9) |

---

### MCP-REQ-004 · AD-4 · `MUST` · Priority: LOW

**Security Logic in Server Code**

Security-critical decisions (authz checks, input validation, scope enforcement) MUST be implemented in server/tool code. Never rely on the LLM to perform security enforcement.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1309 (Execution – ATK-TA0002) |
| CoSAI Control | Trust Boundary Enforcement (T9) |

---

### MCP-REQ-005 · AD-5 · `MUST` · Priority: LOW

**No Token Passthrough**

MCP servers MUST NOT accept tokens that were not explicitly issued for the MCP server (no token passthrough).

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Authentication & Authorization (T1) |

---

### MCP-REQ-006 · AD-6 · `MUST` · Priority: LOW

**No Session-Based Authentication**

MCP servers MUST NOT use sessions for authentication.

| Field | Value |
|---|---|
| Category | Prevention |

---

### MCP-REQ-007 · AD-7 · `SHOULD` · Priority: INFO

**Rate Limiting & Loop Detection**

Implement rate limiting, quota controls, and loop detection to prevent autonomous loop exploits and resource exhaustion.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1106 (Impact – ATK-TA0040) |
| CoSAI Control | Resource Governance (T10) |

---

### MCP-REQ-008 · AD-8 · `SHOULD` · Priority: INFO

**Tool Output Truncation**

Implement tool output truncation to prevent excessively large responses from overwhelming the LLM context.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | Medium |
| Implementation Complexity | Low |
| SAFE-MCP-ID | SAFE-M-23 |

---

### MCP-REQ-009 · AD-9 · `SHOULD` · Priority: INFO

**Defense-in-Depth Architecture**

Adopt defense-in-depth: Foundation (control/data separation) → Prevention (crypto + input validation) → Detection (monitoring + logging) → Response (audit trail + incident response).

| Field | Value |
|---|---|
| Category | Prevention |

---

## AA — Authentication & Authorization

### MCP-REQ-010 · AA-1 · `MUST` · Priority: LOW

**Mandatory Request Verification**

MCP servers implementing authorization MUST verify all inbound requests. No anonymous access to sensitive operations.

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Authentication & Authorization (T1) |

---

### MCP-REQ-011 · AA-2 · `MUST` · Priority: HIGH

**OAuth 2.1 with PKCE**

Use OAuth 2.1 (or later) with PKCE for remote server authentication. Do not use the implicit flow.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Medium |
| Mitigated Tactics | SAFE-T1408 (Credential Access – ATK-TA0006) |
| SAFE-MCP-ID | SAFE-M-13 |
| CoSAI Control | Authentication & Authorization (T1) |

---

### MCP-REQ-012 · AA-3 · `MUST` · Priority: HIGH

**Progressive Least-Privilege Scopes**

Implement a progressive, least-privilege scope model: start with minimal initial scope and require incremental elevation via targeted WWW-Authenticate challenges for privileged operations.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Low |
| Mitigated Tactics | SAFE-T1308 (Credential Access – ATK-TA0006) |
| SAFE-MCP-ID | SAFE-M-16 |
| CoSAI Control | Authentication & Authorization (T1) |

---

### MCP-REQ-013 · AA-4 · `MUST` · Priority: LOW

**Cryptographically Secure Session IDs**

Use secure, non-deterministic session IDs generated with a cryptographically secure RNG. Avoid predictable or sequential identifiers. Rotate or expire session IDs.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1501 (Defense Evasion – ATK-TA0005) |

---

### MCP-REQ-014 · AA-5 · `MUST` · Priority: LOW

**Per-Client Proxy Consent**

MCP proxy servers MUST implement per-client consent before forwarding to third-party authorization servers. Maintain a registry of approved `client_id` values per user.

| Field | Value |
|---|---|
| Category | Prevention |

---

### MCP-REQ-015 · AA-6 · `MUST` · Priority: HIGH

**Strict Redirect URI Validation**

Validate that `redirect_uri` in authorization requests exactly matches the registered URI. Use exact string matching — no wildcards, no pattern matching.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Low |
| SAFE-MCP-ID | SAFE-M-17 |

---

### MCP-REQ-016 · AA-7 · `MUST` · Priority: LOW

**Cryptographic State Values**

Generate a cryptographically secure random state value for each authorization request. Store server-side only after consent approval. Validate at callback. Values MUST be single-use with short expiration (≤10 min).

| Field | Value |
|---|---|
| Category | Prevention |

---

### MCP-REQ-017 · AA-8 · `MUST` · Priority: LOW

**Short-Lived Access Tokens**

Access tokens MUST have short lifetimes. Refresh tokens MUST be stored as securely as access tokens.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1202 (Credential Access – ATK-TA0006) |
| CoSAI Control | Authentication & Authorization (T1) |

---

### MCP-REQ-018 · AA-9 · `MUST` · Priority: LOW

**Minimal Scope Publication**

Do not publish all possible scopes in `scopes_supported`. Do not use wildcard or omnibus scopes. Emit precise scope challenges; never return the full catalog.

| Field | Value |
|---|---|
| Category | Prevention |

---

### MCP-REQ-019 · AA-10 · `MUST` · Priority: HIGH

**Tool Definition Concealment**

Conceal tool definitions from unauthenticated clients to prevent reconnaissance before authorization.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Low |
| Mitigated Tactics | SAFE-T1602 (Discovery – ATK-TA0007) |
| SAFE-MCP-ID | SAFE-M-28 |

---

### MCP-REQ-020 · AA-11 · `SHOULD` · Priority: INFO

**User-Bound Session IDs**

Bind session IDs to user-specific information (e.g., key format `<user_id>:<session_id>`).

| Field | Value |
|---|---|
| Category | Prevention |

---

### MCP-REQ-021 · AA-12 · `SHOULD` · Priority: INFO

**Token Exchange (RFC 8693)**

Use token exchange (RFC 8693) instead of passing OAuth tokens through to downstream services. Maintains full accountability across request chains.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1307 (Credential Access – ATK-TA0006) |
| CoSAI Control | Authentication & Authorization (T1) |

---

### MCP-REQ-022 · AA-13 · `SHOULD` · Priority: INFO

**SPIFFE/SPIRE Workload Identity**

Evaluate SPIFFE/SPIRE for cryptographic workload identities for end-to-end agent traceability.

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Authentication & Authorization (T1) |

---

### MCP-REQ-023 · AA-14 · `SHOULD` · Priority: INFO

**Proof of Possession Tokens**

Implement strict token scope validation. Use Proof of Possession (PoP) tokens where possible to prevent token relay attacks.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1304 (Privilege Escalation – ATK-TA0004), SAFE-T1706 (Credential Access – ATK-TA0006) |

---

## IV — Input Validation

### MCP-REQ-024 · IV-1 · `MUST` · Priority: LOW

**JSON Schema Validation**

Validate all tool inputs against strict JSON schemas. Reject any input not conforming to the expected schema.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1101 (Execution – ATK-TA0002) |
| CoSAI Control | Input Validation & Secure Coding (T3) |

---

### MCP-REQ-025 · IV-2 · `MUST` · Priority: LOW

**Input Sanitization**

Sanitize all inputs for command injection, SQL injection, path traversal (`../../`), and SSRF payloads before processing.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1101 (Execution – ATK-TA0002), SAFE-T1105 (Collection – ATK-TA0009) |
| CoSAI Control | Input Validation & Secure Coding (T3) |

---

### MCP-REQ-026 · IV-3 · `MUST` · Priority: HIGH

**Hidden Instruction Stripping**

Strip or encode hidden instructions from tool descriptions and metadata: zero-width characters, Unicode control characters, HTML comments, steganographic content.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Low |
| Mitigated Tactics | SAFE-T1402 (Defense Evasion – ATK-TA0005) |
| SAFE-MCP-ID | SAFE-M-4 |
| CoSAI Control | Prompt Injection & Content Security (T4) |

---

### MCP-REQ-027 · IV-4 · `MUST` · Priority: LOW

**File Path Validation**

File-handling tools MUST normalize and validate file paths, reject relative path components, and enforce an allowlist of permitted directories.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1105 (Collection – ATK-TA0009) |

---

### MCP-REQ-028 · IV-5 · `MUST` · Priority: LOW

**Treat Server Outputs as Untrusted**

Treat all content returned from MCP servers — tool definitions, resources, prompts, and responses — as untrusted input requiring rigorous validation.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1102 (Initial Access – ATK-TA0001) |
| CoSAI Control | Prompt Injection & Content Security (T4) |

---

### MCP-REQ-029 · IV-6 · `SHOULD` · Priority: INFO

**Tool Description Length Limits**

Enforce maximum length limits on tool descriptions. Reject descriptions with unusual formatting that may indicate embedded instructions.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1001 (Initial Access – ATK-TA0001), SAFE-T1501 (Defense Evasion – ATK-TA0005) |

---

### MCP-REQ-030 · IV-7 · `SHOULD` · Priority: INFO

**Semantic Instruction Pattern Detection**

Implement semantic filtering to detect instruction-like patterns embedded in data fields (content that resembles system prompts or commands).

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | Medium-High |
| Implementation Complexity | High |
| SAFE-MCP-ID | SAFE-M-3, SAFE-M-22 |

---

### MCP-REQ-031 · IV-8 · `SHOULD` · Priority: INFO

**Multimodal Content Disarm**

For multimodal inputs (images, audio), implement Content Disarm and Reconstruction (CDR) or equivalent scanning to remove embedded adversarial payloads.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1110 (Execution – ATK-TA0002) |

---

### MCP-REQ-032 · IV-9 · `SHOULD` · Priority: INFO

**Semantic Output Validation**

Validate that tool outputs match expected formats and do not contain instruction patterns (semantic output validation).

| Field | Value |
|---|---|
| Category | Detection |
| Effectiveness | Medium-High |
| Implementation Complexity | High |
| SAFE-MCP-ID | SAFE-M-22 |

---

## SM — Secrets Management

### MCP-REQ-033 · SM-1 · `MUST` · Priority: LOW

**No Plaintext Secret Storage**

API keys, tokens, and secrets MUST NOT be stored in plaintext in configuration files, environment variables exposed in logs, or source code. Use a secrets manager (e.g., Vault, KMS).

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1503 (Credential Access – ATK-TA0006), SAFE-T1206 (Credential Access – ATK-TA0006) |
| CoSAI Control | Sensitive Data Protection (T5) |

---

### MCP-REQ-034 · SM-2 · `MUST` · Priority: LOW

**No Credential Logging**

Credentials MUST NOT be logged, included in error messages, or exposed in URL parameters.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1506 (Exfiltration – ATK-TA0010) |
| CoSAI Control | Sensitive Data Protection (T5) |

---

### MCP-REQ-035 · SM-3 · `MUST` · Priority: LOW

**Secure Consent Cookies**

Consent cookies (if used) MUST use `__Host-` prefix, set `Secure`, `HttpOnly`, `SameSite=Lax`, and be cryptographically signed. They MUST bind to the specific `client_id`.

| Field | Value |
|---|---|
| Category | Prevention |

---

### MCP-REQ-036 · SM-4 · `SHOULD` · Priority: INFO

**Secret Rotation**

Rotate secrets regularly with automated expiration policies.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1206 (Credential Access – ATK-TA0006) |

---

### MCP-REQ-037 · SM-5 · `SHOULD` · Priority: INFO

**Environment Variable Allowlisting**

Restrict environment variable access from tool code to an explicit allowlist. Deny access to `.env` files and system environment by default.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1503 (Credential Access – ATK-TA0006) |

---

## RI — Runtime Isolation

### MCP-REQ-038 · RI-1 · `MUST` · Priority: LOW

**Sandboxed Execution for Host-Access Servers**

MCP servers that access the host environment (files, commands, network) or execute LLM-generated code MUST run in a sandbox with minimal default privileges. LLM-generated code MUST NOT run with full user privileges.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1303 (Privilege Escalation – ATK-TA0004), SAFE-T1305 (Privilege Escalation – ATK-TA0004) |
| CoSAI Control | Least Privilege & Isolation (T2) |

---

### MCP-REQ-039 · RI-2 · `MUST` · Priority: LOW

**Least Privilege System Permissions**

MCP servers MUST operate under least privilege. Grant only the minimum required system permissions (filesystem, network, process).

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1104 (Privilege Escalation – ATK-TA0004) |
| CoSAI Control | Least Privilege & Isolation (T2) |

---

### MCP-REQ-040 · RI-3 · `MUST` · Priority: LOW

**Default-Deny Network Egress**

Network egress MUST be restricted to only necessary destinations using allowlists. Default-deny all outbound connections.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1913 (Exfiltration – ATK-TA0010), SAFE-T1901 (Exfiltration – ATK-TA0010) |
| CoSAI Control | Transport & Network Security (T7) |

---

### MCP-REQ-041 · RI-4 · `SHOULD` · Priority: INFO

**Layered Sandboxing**

Containers alone are not a strong security boundary. Layer additional sandboxing (gVisor, Kata Containers, SELinux/AppArmor) for stronger isolation.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1303 (Privilege Escalation – ATK-TA0004) |
| CoSAI Control | Least Privilege & Isolation (T2) |

---

### MCP-REQ-042 · RI-5 · `SHOULD` · Priority: INFO

**Trusted Execution Environments**

For high-security deployments, use TEEs (Trusted Execution Environments) with remote attestation to verify server integrity. Complement TEEs with runtime controls and sandboxing.

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Data Integrity & Cryptographic Verification (T6) |

---

### MCP-REQ-043 · RI-6 · `SHOULD` · Priority: INFO

**Resource Limits per Tool**

Enforce resource limits (CPU, memory, execution time) per tool to prevent denial-of-service via infinite loops or excessive consumption.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1106 (Impact – ATK-TA0040) |
| CoSAI Control | Resource Governance (T10) |

---

### MCP-REQ-044 · RI-7 · `SHOULD` · Priority: INFO

**Prefer stdio Transport Locally**

Local MCP servers SHOULD prefer stdio transport to limit access to just the MCP client and eliminate DNS rebinding risks. If using HTTP, require an authorization token or use unix domain sockets.

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Transport & Network Security (T7) |

---

## SS — Supply Chain Security

### MCP-REQ-045 · SS-1 · `MUST` · Priority: HIGH

**Cryptographic Package Signing**

All MCP server packages MUST be cryptographically signed. Provide verifiable signatures for all releases.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Medium |
| Mitigated Tactics | SAFE-T1002 (Persistence – ATK-TA0003) |
| SAFE-MCP-ID | SAFE-M-2 |
| CoSAI Control | Supply Chain Security (T11) |

---

### MCP-REQ-046 · SS-2 · `MUST` · Priority: HIGH

**SBOM Generation**

Generate and distribute a Software Bill of Materials (SBOM) with every release.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Medium |
| SAFE-MCP-ID | SAFE-M-24 |
| CoSAI Control | Supply Chain Security (T11) |

---

### MCP-REQ-047 · SS-3 · `MUST` · Priority: LOW

**Dependency SCA Scanning**

Scan all dependencies for known vulnerabilities using SCA tools before release.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1002 (Persistence – ATK-TA0003) |
| CoSAI Control | Supply Chain Security (T11) |

---

### MCP-REQ-048 · SS-4 · `MUST` · Priority: LOW

**Versioned & Integrity-Protected Tool Definitions**

Tool definitions (schemas, descriptions, metadata) MUST be versioned and integrity-protected. Changes must be detectable.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1201 (Persistence – ATK-TA0003), SAFE-T1205 (Defense Evasion – ATK-TA0005) |

---

### MCP-REQ-049 · SS-5 · `SHOULD` · Priority: INFO

**Reproducible Builds**

Use reproducible builds to allow independent verification of build artifacts.

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Supply Chain Security (T11) |

---

### MCP-REQ-050 · SS-6 · `SHOULD` · Priority: INFO

**CI/CD Security Gates**

Implement CI/CD checks that fail the build on unsigned artifacts, missing SBOMs, or known-vulnerable dependencies.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1002 (Persistence – ATK-TA0003) |

---

### MCP-REQ-051 · SS-7 · `SHOULD` · Priority: INFO

**Dependency Hash Pinning**

Pin all dependencies by hash/digest, not just version number.

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Supply Chain Security (T11) |

---

## TD — Tool Definitions

### MCP-REQ-052 · TD-1 · `MUST` · Priority: HIGH

**Tool Description Transparency**

Tool descriptions visible to the LLM MUST match what is displayed to the user. No hidden instructions, divergent descriptions, or invisible metadata that the LLM can process but the user cannot see.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Medium |
| Mitigated Tactics | SAFE-T1001 (Initial Access – ATK-TA0001) |
| SAFE-MCP-ID | SAFE-M-7 |

---

### MCP-REQ-053 · TD-2 · `MUST` · Priority: LOW

**Strict Tool Schemas**

Tool schemas MUST define strict types, required fields, allowed values, and bounds for every parameter. Reject calls with unexpected or extra parameters.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1501 (Defense Evasion – ATK-TA0005) |
| CoSAI Control | Prompt Injection & Content Security (T4) |

---

### MCP-REQ-054 · TD-3 · `MUST` · Priority: LOW

**Namespace Isolation**

Implement namespace isolation: each MCP server's tools MUST be namespaced to prevent name collisions and cross-server tool shadowing.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1008 (Defense Evasion – ATK-TA0005), SAFE-T1301 (Defense Evasion – ATK-TA0005) |

---

### MCP-REQ-055 · TD-4 · `MUST` · Priority: LOW

**Immutable Tool Definitions (Rug-Pull Detection)**

Tool definitions MUST be immutable once approved within a session. Any server-side change to tool metadata must trigger a re-approval flow (rug-pull detection).

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1201 (Persistence – ATK-TA0003) |

---

### MCP-REQ-056 · TD-5 · `SHOULD` · Priority: INFO

**Non-Prompt-Like Descriptions**

Tool descriptions SHOULD avoid prompt-like language or execution instructions. Keep descriptions factual and minimal.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1001 (Initial Access – ATK-TA0001) |

---

### MCP-REQ-057 · TD-6 · `SHOULD` · Priority: INFO

**Cryptographic Tool Registry**

Implement a tool registry with cryptographic verification of tool definitions before loading.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Medium |
| SAFE-MCP-ID | SAFE-M-6 |

---

## LM — Logging & Monitoring

### MCP-REQ-058 · LM-1 · `MUST` · Priority: HIGH

**Immutable Tool Invocation Audit Log**

Log all tool invocations — parameters, caller identity, timestamp, result status — in an immutable audit trail.

| Field | Value |
|---|---|
| Category | Detection |
| Effectiveness | Medium |
| Implementation Complexity | Low |
| SAFE-MCP-ID | SAFE-M-12 |
| CoSAI Control | Logging, Monitoring & Observability (T12) |

---

### MCP-REQ-059 · LM-2 · `MUST` · Priority: LOW

**Authentication Event Logging**

Log all authentication events: success, failure, token refresh, scope elevation. Include correlation IDs.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1506 (Exfiltration – ATK-TA0010) |
| CoSAI Control | Logging, Monitoring & Observability (T12) |

---

### MCP-REQ-060 · LM-3 · `MUST` · Priority: LOW

**Log Redaction**

Logs MUST NOT contain secrets, tokens, PII, or sensitive request/response payloads. Implement log redaction.

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Sensitive Data Protection (T5) |

---

### MCP-REQ-061 · LM-4 · `SHOULD` · Priority: INFO

**Behavioral Anomaly Monitoring**

Implement behavioral monitoring for anomalies: unusual tool call patterns, rapid privilege escalation, cross-tool credential usage, excessive data reads.

| Field | Value |
|---|---|
| Category | Detection |
| Effectiveness | Medium-High |
| Implementation Complexity | High |
| SAFE-MCP-ID | SAFE-M-11, SAFE-M-20 |

---

### MCP-REQ-062 · LM-5 · `SHOULD` · Priority: INFO

**OpenTelemetry Tracing**

Use OpenTelemetry or equivalent for end-to-end request tracing across agent → client → server → tool.

| Field | Value |
|---|---|
| Category | Detection |
| CoSAI Control | Logging, Monitoring & Observability (T12) |

---

### MCP-REQ-063 · LM-6 · `SHOULD` · Priority: INFO

**Tool Definition Change Monitoring**

Monitor for tool definition changes, unauthorized server registrations, and shadow MCP deployments.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1201 (Persistence – ATK-TA0003), SAFE-T1601 (Discovery – ATK-TA0007) |

---

### MCP-REQ-064 · LM-7 · `SHOULD` · Priority: INFO

**Token Usage Pattern Logging**

Log token usage patterns and cross-tool authentication attempts. Alert on tokens used outside their intended scope.

| Field | Value |
|---|---|
| Category | Detection |
| Effectiveness | Medium-High |
| Implementation Complexity | Medium |
| Mitigated Tactics | SAFE-T1304 (Privilege Escalation – ATK-TA0004) |
| SAFE-MCP-ID | SAFE-M-19 |

---

## CH — Consent & Human Controls

### MCP-REQ-065 · CH-1 · `MUST` · Priority: LOW

**Exact Command Display for Local Servers**

If the MCP client supports one-click local server configuration, it MUST display the exact command to be executed (untruncated, including arguments) and require explicit user approval before proceeding.

| Field | Value |
|---|---|
| Category | Prevention |

---

### MCP-REQ-066 · CH-2 · `MUST` · Priority: LOW

**Secure Consent UI**

Consent UI MUST clearly identify the requesting MCP client by name, display requested scopes, and show the registered `redirect_uri`. Implement CSRF protection and prevent clickjacking (`frame-ancestors` CSP or `X-Frame-Options: DENY`).

| Field | Value |
|---|---|
| Category | Prevention |

---

### MCP-REQ-067 · CH-3 · `SHOULD` · Priority: INFO

**Dangerous Pattern Highlighting**

Highlight dangerous command patterns in consent dialogs (e.g., `sudo`, `rm -rf`, network operations, access to SSH keys, system directories). Warn that MCP servers run with client privileges.

| Field | Value |
|---|---|
| Category | Prevention |

---

### MCP-REQ-068 · CH-4 · `SHOULD` · Priority: INFO

**Consent Fatigue Resistance**

Design consent flows to resist consent fatigue: group related permissions, highlight high-risk operations distinctly, avoid desensitizing users with repeated benign prompts.

| Field | Value |
|---|---|
| Category | Prevention |
| Mitigated Tactics | SAFE-T1403 (Defense Evasion – ATK-TA0005) |

---

## TN — Transport & Network Security

### MCP-REQ-069 · TN-1 · `MUST` · Priority: LOW

**TLS 1.2+ for Remote Servers**

All communication with remote MCP servers MUST use TLS 1.2+ with valid certificates.

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Transport & Network Security (T7) |

---

### MCP-REQ-070 · TN-2 · `MUST` · Priority: LOW

**stdio Transport for Local MCP**

Use stdio transport for local MCP to eliminate DNS rebinding risks. If HTTP-based transport is used locally, bind to loopback only and require an authorization token.

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Transport & Network Security (T7) |

---

### MCP-REQ-071 · TN-3 · `SHOULD` · Priority: INFO

**End-to-End Message Integrity**

Implement end-to-end integrity verification (signatures) for messages between client and server, not just transport-level encryption.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | Medium |
| SAFE-MCP-ID | SAFE-M-2 |
| CoSAI Control | Data Integrity & Cryptographic Verification (T6) |

---

## DP — Data Provenance

### MCP-REQ-072 · DP-1 · `MUST` · Priority: HIGH

**Authorized Vector Store Writes Only**

MCP servers MUST NOT write to or modify shared vector stores, databases, or memory systems without explicit authorization and integrity verification.

| Field | Value |
|---|---|
| Category | Prevention |
| Effectiveness | High |
| Implementation Complexity | High |
| Mitigated Tactics | SAFE-T2106 (Persistence – ATK-TA0003 / Impact – ATK-TA0040), SAFE-T1702 (Persistence – ATK-TA0003) |
| SAFE-MCP-ID | SAFE-M-30 |

---

### MCP-REQ-073 · DP-2 · `SHOULD` · Priority: INFO

**Data Provenance Tracking**

Implement data provenance tracking to detect poisoned or unauthorized content in tool outputs and shared data stores.

| Field | Value |
|---|---|
| Category | Detection |
| Effectiveness | High |
| Implementation Complexity | High |
| SAFE-MCP-ID | SAFE-M-26, SAFE-M-33 |

---

### MCP-REQ-074 · DP-3 · `SHOULD` · Priority: INFO

**Sensitive Data Encryption at Rest**

Encrypt sensitive data at rest that MCP servers may access.

| Field | Value |
|---|---|
| Category | Prevention |
| CoSAI Control | Sensitive Data Protection (T5) |

---

### MCP-REQ-075 · DP-4 · `SHOULD` · Priority: INFO

**Continuous Vector Store Monitoring**

Implement continuous vector store monitoring to detect integrity violations or poisoning over time.

| Field | Value |
|---|---|
| Category | Detection |
| Effectiveness | Medium-High |
| Implementation Complexity | High |
| SAFE-MCP-ID | SAFE-M-30, SAFE-M-32 |

---

## ST — Security Testing

### MCP-REQ-076 · ST-1 · `MUST` · Priority: LOW

**OWASP Testing Coverage**

Test for OWASP Top 10 vulnerabilities (injection, broken auth, SSRF, etc.) AND the OWASP Top 10 for LLM Applications (prompt injection, insecure output handling, supply chain).

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1101 (Execution – ATK-TA0002), SAFE-T1102 (Initial Access – ATK-TA0001) |
| CoSAI Control | Input Validation & Secure Coding (T3) |

---

### MCP-REQ-077 · ST-2 · `MUST` · Priority: LOW

**Fuzz Testing**

Fuzz-test all tool inputs with malformed, oversized, and adversarial payloads.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1101 (Execution – ATK-TA0002) |

---

### MCP-REQ-078 · ST-3 · `MUST` · Priority: LOW

**SCA Before Release**

Perform SCA scanning on all dependencies before every release.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1002 (Persistence – ATK-TA0003) |

---

### MCP-REQ-079 · ST-4 · `SHOULD` · Priority: INFO

**Prompt Injection Testing**

Test for prompt injection: verify tool descriptions, resource content, and tool outputs cannot manipulate the LLM into unauthorized actions.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1001 (Initial Access – ATK-TA0001), SAFE-T1102 (Initial Access – ATK-TA0001) |

---

### MCP-REQ-080 · ST-5 · `SHOULD` · Priority: INFO

**Tool Poisoning & Rug-Pull Testing**

Test for tool poisoning and rug-pull: verify dynamic tool definition changes are detected and blocked.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1201 (Persistence – ATK-TA0003) |

---

### MCP-REQ-081 · ST-6 · `SHOULD` · Priority: INFO

**Credential Leakage Testing**

Test for credential leakage: secrets must not appear in logs, error responses, URL parameters, or tool outputs.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1503 (Credential Access – ATK-TA0006), SAFE-T1506 (Exfiltration – ATK-TA0010) |

---

### MCP-REQ-082 · ST-7 · `SHOULD` · Priority: INFO

**Path Traversal Testing**

Test path traversal in all file-handling tools.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1105 (Collection – ATK-TA0009) |

---

### MCP-REQ-083 · ST-8 · `SHOULD` · Priority: INFO

**Sandbox Escape Testing**

Perform sandbox escape testing for containerized/sandboxed MCP servers.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1303 (Privilege Escalation – ATK-TA0004) |

---

### MCP-REQ-084 · ST-9 · `SHOULD` · Priority: INFO

**OAuth Flow Testing**

Test OAuth flows for authorization code interception, token replay, scope escalation, and confused deputy scenarios.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1007 (Initial Access – ATK-TA0001), SAFE-T1307 (Credential Access – ATK-TA0006), SAFE-T1308 (Credential Access – ATK-TA0006) |

---

### MCP-REQ-085 · ST-10 · `SHOULD` · Priority: INFO

**Static Analysis (Semgrep)**

Run static analysis (e.g., Semgrep) with rules targeting MCP-specific patterns: unsanitized tool inputs, hardcoded secrets, overly permissive file access, missing auth checks.

| Field | Value |
|---|---|
| Category | Detection |
| CoSAI Control | Input Validation & Secure Coding (T3) |

---

### MCP-REQ-086 · ST-11 · `SHOULD` · Priority: INFO

**Multimodal Injection Testing**

Test for multimodal injection vectors: adversarial images, audio with embedded instructions (steganography, OCR exploitation).

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1110 (Execution – ATK-TA0002) |

---

### MCP-REQ-087 · ST-12 · `SHOULD` · Priority: INFO

**Credential Relay Chain Testing**

Test for credential relay chains: verify one tool cannot steal tokens and feed them to another higher-privilege tool.

| Field | Value |
|---|---|
| Category | Detection |
| Mitigated Tactics | SAFE-T1304 (Privilege Escalation – ATK-TA0004) |
