# MCP Server - Security Principles

## High-Risk Classification Principles for MCP Servers and Tools

### Principle 1 — Unbounded External Communication
A tool is high-risk if it can initiate or receive communication with external, untrusted, or user/LLM-determined endpoints. This includes web requests, email, messaging, webhooks, and arbitrary API calls. The risk is bidirectional: outbound exfiltration of context or sensitive data, and inbound prompt injection from attacker-controlled content.

### Principle 2 — Data Store Access
A tool is high-risk if it can query, read, or modify data in databases, data warehouses, business intelligence platforms, object stores, or any structured/unstructured data repository. Authorization boundaries are difficult to enforce at the row, object, or field level through an LLM intermediary, creating risk of unauthorized data access or modification. Write and delete capabilities elevate the risk further.

### Principle 3 — Code and Command Execution
A tool is high-risk if it executes code, shell commands, or system operations — whether generated dynamically by the LLM, derived from user input, or parameterized from untrusted sources. This includes direct execution (shell, REPL, eval) and indirect execution where the tool produces artifacts (IaC, CI/CD configs, scripts) intended for downstream execution.

### Principle 4 — Filesystem and Local Resource Access
A tool is high-risk if it can read, write, create, or delete files on the host filesystem or mounted volumes. This includes access to configuration files, credentials on disk, logs, and the ability to traverse directory structures beyond a narrowly scoped working directory.

### Principle 5 — Credential and Secret Access
A tool is high-risk if it holds, manages, brokers, or operates with privileged credentials, API keys, tokens, or session material. Compromise or misuse of such a tool can lead to credential leakage, lateral movement, or privilege escalation beyond the tool's intended scope.

### Principle 6 — Cross-Tool Orchestration and Self-Modification
A tool is high-risk if it can invoke other tools, install or configure MCP servers, modify agent behavior, or alter system prompts and tool permissions. These capabilities create transitive risk where a single manipulated tool call can escalate into broader system compromise.


## Assessment Modifiers (apply within each principle)
When a tool falls into one or more high-risk categories, assessors should further evaluate:

**Scope**: Is the tool's reach bounded (allowlisted destinations, specific tables, scoped directories) or unbounded (arbitrary targets determined at runtime)?
**Mutability**: Is the tool read-only, or can it create, modify, or delete resources?
**Input trust**: Are the tool's parameters derived from trusted, validated sources, or from LLM-generated or user-supplied input susceptible to injection?
**Sandboxing**: Does the tool operate in an isolated environment with constrained blast radius, or does it have direct access to production systems and resources?
**Credential privilege**: Does the tool operate with least-privilege credentials scoped to its function, or does it inherit broad permissions?

A tool matching multiple high-risk principles or scoring poorly across multiple modifiers should receive the highest scrutiny and the strictest controls during assessment.