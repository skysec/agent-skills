# SecDeepWiki — Execution Detail

## Phase 2 — Per-Component Module Guides

### 2.1 classify

**Goal**: Determine which component types apply. A component can match multiple classifications.

Detection strategy (run in order, all non-exclusive):

1. **Dependency signals**: scan manifest dependencies for framework names
   - `express`, `fastapi`, `flask`, `django`, `rails`, `spring-boot` → `api_service`
   - `react`, `vue`, `angular`, `svelte`, `next`, `nuxt` → `web_application`
   - `langchain`, `llamaindex`, `autogen`, `crewai`, `semantic-kernel` → `ai_agent`
   - `@modelcontextprotocol/sdk`, `mcp`, `fastmcp` → `mcp_server`
   - `click`, `typer`, `cobra`, `clap`, `argparse` → `cli_tool`

2. **Config file signals**: scan for known config files
   - `openapi.yaml`, `swagger.json` → `api_service`
   - `mcp.json`, any file with `tools:` + `name:` + `inputSchema:` → `mcp_server`
   - `Dockerfile` or `docker-compose.yml` → `infrastructure_as_code`
   - `*.tf`, `*.tfvars`, `cloudformation*.yaml` → `infrastructure_as_code`

3. **Entry point patterns**: scan for main/bin patterns
   - `"bin"` field in package.json, `[project.scripts]` in pyproject.toml → `cli_tool`
   - `if __name__ == "__main__"` with HTTP server → likely `api_service`
   - Library-only exports (no main, no HTTP) → `library_or_sdk`

4. **Source pattern signals**: scan for route decorators, event handlers, blockchain code
   - `@app.get`, `router.post`, `Route`, `@Controller` → `api_service`
   - Event handler registrations (`on('message')`, `subscribe(`) → `event_consumer_or_worker`
   - `pragma solidity`, `#[program]`, `#[near_bindgen]` → `smart_contract`

For ambiguous cases (no clear signals), use LLM to read the component's README and main
entry file, then classify based on architecture intent.

**Evidence**: populate `evidence: string[]` with specific file paths that confirmed each
classification, e.g., `["package.json: langchain dependency", "src/agent.py: ChatOpenAI import"]`.

---

### 2.2 stack-analyze

**Goal**: Identify languages, frameworks, package managers, runtime. Pure file parsing — no LLM.

- **Languages**: from file extension survey in Phase 1. Include `role` based on directory
  (files in `test/`, `spec/`, `*.test.ts` → `test`; `*.sh`, `Makefile` → `scripting`).
- **Package managers**: presence of `package.json` → `npm`/`yarn`/`pnpm`; `pyproject.toml` →
  `uv`/`pip`/`poetry`; `Cargo.toml` → `cargo`; `go.mod` → `go`; `pom.xml` → `maven`.
  Mark `lockfile_present` if `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`,
  `uv.lock`, `Cargo.lock`, `go.sum`, etc. exist.
- **Frameworks**: parse dependency list for version-pinned framework entries. Extract version
  string from manifest. Assign `category` based on framework type.
- **Runtime**: check `Dockerfile FROM` for base image. Check `engines` field in package.json.
  Check `python_requires` in pyproject.toml.

---

### 2.3 entry-point-scan

**Goal**: Catalog every inbound path with auth status, input validation, and file-handling info.

**Per classification, what to scan:**

**api_service (REST)**:
Scan for route decorators and router definitions. For each route extract:
- HTTP method and path pattern
- Middleware chain (look for auth middleware: `authenticate`, `requireAuth`, `@JWT`, `Depends(get_current_user)`)
- Request body type from type annotations, schema references, or `Content-Type` hints
- Input validation: presence of schema validators (Pydantic model, Zod schema, Joi schema)
- `authentication_required`: `yes` if auth middleware is in chain; `no` if no middleware;
  `conditional` if there's an if-branch on auth; `unknown` if middleware chain unclear

**api_service (GraphQL)**:
Parse schema file for Query, Mutation, Subscription types. Each field = an entry point.
Check resolvers for auth directives (`@auth`, `@requiresAuth`, shield rules).

**api_service (gRPC)**:
Parse `.proto` files for service definitions. Each RPC = an entry point.
Check interceptors for auth handling.

**mcp_server**:
Parse tool, resource, and prompt definitions. Each = an entry point with `type: mcp_tool`,
`mcp_resource`, or `mcp_prompt`. For tools: extract `inputSchema` and `risk_classification`
from what the tool does (read file = `read_only`, write file = `write`, shell exec = `code_execution`).

**cli_tool**:
Parse command definitions. Each command/subcommand = an entry point.
Check if commands accept `--file` / `--input` / `--url` parameters.

**event_consumer_or_worker**:
Identify event handler registrations and their event source.
Check for input validation on the event payload.

---

### 2.4 auth-analyze

**Goal**: Describe all authentication mechanisms, session management, and credential handling
as they exist in source. LLM-assisted.

**Authentication mechanisms** — scan for:
- JWT: look for `jwt.verify`, `jose.jwtVerify`, `PyJWT.decode`, `jsonwebtoken` imports
- OAuth2/OIDC: look for authorization code flow, token exchange, `oidc-client`, `passport`
- Session cookie: look for `session_secret`, `express-session`, `flask.session`
- API key: look for request header extraction of `X-API-Key`, `Authorization: Bearer` checked against DB
- Basic auth: look for `Authorization: Basic` parsing

For each mechanism found, identify:
- `provider`: Auth0, Cognito, Keycloak, custom, etc. (from config or import names)
- `configuration_source`: where does the JWT secret / OAuth client secret come from?
  (`env_var`, `config_file`, or `hardcoded`)
- `token_storage`: where does the client store the token? (from frontend code if present)
- `mfa_enforced`: any 2FA/TOTP enforcement visible in auth code?

**Session management** (Tier 2 — record what is visible; leave null if not determinable):
- Server-side: look for session store config (Redis, DB)
- JWT stateless: verify signature checked, expiry enforced

**Credential storage** (only if password handling found):
- Scan for password hashing: `bcrypt.hash`, `argon2.hash`, `hashlib.sha256`, plain string storage

**Service-to-service auth**:
- Look for mTLS cert loading, JWT signing for downstream calls, API key headers in HTTP clients

**Authorization**:
- Identify the model from permission checks in code
- Find enforcement points: middleware, decorators, inline checks
- Check `coverage`: do all routes/entry points have auth enforcement?

---

### 2.5 crypto-analyze

**Goal**: Find and enumerate all cryptographic operations. Deterministic.

Scan for imports of crypto libraries, then trace to usage sites:

| Pattern | Algorithm |
|---|---|
| `hashlib.md5`, `MD5`, `crypto.createHash('md5')` | MD5 |
| `hashlib.sha1`, `SHA1` | SHA-1 |
| `DES`, `3DES`, `RC4`, `RC2` | Weak symmetric |
| `AES` | AES (note mode if detectable) |
| `ECB` mode | AES-ECB |
| Hardcoded key/IV/salt literals | Note in algorithm field |
| `math/rand`, `random.random()`, `Math.random()` | Non-CSPRNG |
| `==` comparison of HMAC/password hashes | Timing-vulnerable compare |
| `RSA` | RSA (note padding if detectable) |

For each finding, populate: `operation`, `algorithm`, `library`, `file`, `line`.

---

### 2.6 observability-scan

**Goal**: Describe what logging and audit infrastructure is present.

- **Logging framework**: identify which logging library is used
  (`python logging`, `winston`, `zap`, `slf4j`, `pino`, `bunyan`, `structlog`, etc.)
- **Audit trail**: look for explicit audit logging of authentication events (login/logout),
  authorization decisions, or data access to sensitive resources. Set `audit_trail_present: true`
  only if dedicated audit log statements exist (not just error logging).

---

### 2.7 data-store-detect

**Goal**: Identify every data store the component connects to and describe its configuration.

**Detection** — scan for ORM imports, driver imports, connection string patterns:
- `sqlalchemy`, `prisma`, `typeorm`, `hibernate`, `gorm`, `active_record` → rdbms
- `pymongo`, `mongoose`, `mongodb-driver` → nosql
- `redis`, `ioredis`, `jedis`, `stackexchange.redis` → cache
- `boto3.client('s3')`, `@aws-sdk/client-s3`, `google-cloud-storage` → object_storage
- `chromadb`, `pinecone`, `weaviate`, `pgvector`, `qdrant` → vector_db
- `pika`, `kafka-python`, `confluent-kafka` → message_queue
- `elasticsearch`, `opensearch` → search_engine

**Connection config source** — describe where the connection string comes from:
- `os.environ.get('DATABASE_URL')`, `process.env.DB_URL` → `env_var`
- Config file load: `config.database.url` → `config_file`
- Literal string like `postgresql://user:pass@localhost` → `hardcoded`

**Data classification** (LLM-assisted) — infer from model/schema field names:
- `email`, `phone`, `ssn`, `address`, `dob`, `ip_address` → `pii`
- `diagnosis`, `medication`, `patient` → `phi`
- `card_number`, `cvv`, `billing` → `pci`
- Internal business logic only → `internal`

---

### 2.8 confidence-compute

Assign `overall` confidence (0.0–1.0) based on:

| Condition | Confidence Penalty |
|---|---|
| Heavy use of dynamic dispatch (eval, getattr, dynamic routing) | -0.2 |
| Large portion of codebase is generated (proto, openapi gen) | -0.1 |
| No clear entry point pattern found | -0.15 |
| Auth implemented in external service not in repo | -0.1 |
| Polyglot (3+ languages with significant LOC) | -0.1 |
| Clear framework with well-known patterns | +0.1 |
| OpenAPI spec matches code (drift checked) | +0.1 |

Set `manual_review_recommended: true` if `overall < 0.6`.

Populate `limitations[]` with plain-English notes about what reduced confidence.

---

## Phase 4 — Cross-Component Synthesis Detail

### 4.1 relationship-map

For each component pair, scan for:

1. **API calls**: HTTP client usage (`requests.get(url)`, `axios.get(url)`, `fetch(url)`)
   where the URL points to another component's base URL (from env vars or config)
2. **Library imports**: one component importing another component's package/module path
3. **Event patterns**: one component publishing to a queue/topic that another consumes
4. **Shared DB**: multiple components connecting to the same DB technology + connection string env var name

For each relationship:
- `type`: most specific type that applies
- `authentication`: what does the client send? (from the client component's HTTP calls)
- `data_classification`: what kind of data flows? (infer from endpoint semantics)
- `trust_boundary_crossing`: true if the two components are in different trust zones

### 4.2 dfd-generate

Build DFDs bottom-up from the component analysis data:

**L0 Context DFD** — identify external actors (end users, third-party APIs, admin users)
and draw the system boundary. Show only high-level flows. Mermaid template:
```mermaid
graph LR
  User([External User]) -->|HTTPS| System[/System Boundary/]
  System -->|API calls| ThirdParty([Third Party Service])
```

**L1 Container DFD** — one box per component. Annotate:
- Trust zones as subgraph boundaries
- Data flows with: protocol, auth status, data classification
- Trust boundary crossings with a dashed line

**L2 Component DFD** — for complex components (more than 5 entry points OR AI agent OR MCP
server): internal flow from entry point through key processing steps to data stores.

For each data flow, describe factually: protocol, encryption_in_transit, authentication,
crosses_trust_boundary, and boundary_crossed (if applicable). Generate Mermaid syntax.

### 4.3 auth-flow-diagram

Generate a Mermaid `sequenceDiagram` for each distinct auth flow:

```mermaid
sequenceDiagram
  participant Client
  participant API
  participant IdP
  Client->>API: POST /login {credentials}
  API->>IdP: Verify credentials
  IdP-->>API: Token
  API-->>Client: Set-Cookie: session_id
```

Cover: login, token refresh (if JWT), logout, service-to-service auth.

### 4.4 attack-surface-aggregate

Walk all `components[*].entry_points[]` and aggregate into:
- `unauthenticated_entry_points`: `authentication_required: no`
- `file_upload_endpoints`: `file_upload_accepted: true`
- `admin_interfaces`: entry points with authorization model containing "admin" or "ADMIN" role
- `debug_endpoints`: paths matching `/debug`, `/healthz` (with data), `/__admin`, `/actuator`
  with data exposure, GraphQL introspection enabled in production

