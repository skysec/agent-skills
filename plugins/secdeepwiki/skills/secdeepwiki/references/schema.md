# SecDeepWiki — Complete YAML Schema

## Table of Contents

- [§5 Root Document](#5-root-document)
- [§6 Repository Structure](#6-repository-structure)
- [§7 Shared Analysis](#7-shared-analysis)
- [§8 Component Analysis](#8-component-analysis)
  - [§8.1 Component Root](#81-component-root)
  - [§8.2 Classification](#82-classification)
  - [§8.3 Tech Stack](#83-tech-stack)
  - [§8.4 Entry Points](#84-entry-points)
  - [§8.5 Authentication](#85-authentication)
  - [§8.6 Authorization](#86-authorization)
  - [§8.7 Cryptography](#87-cryptography)
  - [§8.8 Observability](#88-observability)
  - [§8.9 Data Stores](#89-data-stores)
  - [§8.10 Confidence](#810-confidence)
- [§9 Cross-Component Analysis](#9-cross-component-analysis)
  - [§9.1 Relationships](#91-relationships)
  - [§9.2 Data Flow Diagrams](#92-data-flow-diagrams)
  - [§9.3 Attack Surface Summary](#93-attack-surface-summary)
- [§10 Delta Report](#10-delta-report)

---

## §5 Root Document

```yaml
secdeepwiki:
  schema_version: "3.0.0"

  snapshot:
    id: string                       # sha256(repo_url + commit_sha + schema_version + analyzer_version)

  repository:
    url: string
    name: string
    branch: string
    commit_sha: string
    commit_date: datetime
    commit_author: string
    commit_message: string

  analysis:
    generated_at: datetime
    duration_seconds: float
    mode: enum[full, incremental]
    analyzer_version: string
    modules_executed: string[]
    modules_skipped: string[]        # incremental: unchanged components
    llm_assisted_modules: string[]
    overall_confidence: float        # 0.0 to 1.0

  previous_snapshot:                 # null on first run
    id: string
    commit_sha: string
    commit_date: datetime
    generated_at: datetime

  repo_structure: ...                # §6
  shared: ...                        # §7
  components: []                     # §8
  cross_component: ...               # §9
  delta_report: ...                  # §10 — null on first run
```

---

## §6 Repository Structure

```yaml
repo_structure:
  is_monorepo: bool
  languages_summary:
    - language: string               # e.g., "Python", "TypeScript"
  classifications_summary: string[]  # union of all component classifications
                                     # e.g., ["api_service", "mcp_server", "cli_tool"]
```

---

## §7 Shared Analysis

```yaml
shared:
  ci_cd:
    platform: enum[github_actions, gitlab_ci, jenkins, circleci, azure_devops,
                   bitbucket_pipelines, aws_codepipeline, google_cloud_build,
                   travisci, argo_workflows, tekton, buildkite, other, none]
    security_gates:
      sast: bool
      dast: bool
      secret_scan: bool
      code_review_required: bool
```

---

## §8 Component Analysis

### §8.1 Component Root

```yaml
components:
  - id: string                       # kebab-case, unique: "api-gateway", "auth-service"
    name: string                     # display name
    path: string                     # relative to repo root; "." for single-component repos
    description: string              # LLM-generated 2-3 sentence summary
    owner: string                    # from CODEOWNERS, or null

    analysis_provenance:
      source: enum[fresh_analysis, carried_forward]
      from_snapshot_id: string       # null if fresh
      from_commit_sha: string
      modules_rerun: string[]        # which modules ran fresh
      carried_forward_reason: string # "no files changed in component path"

    classification: ...              # §8.2
    tech_stack: ...                  # §8.3
    entry_points: []                 # §8.4
    authentication: ...              # §8.5
    authorization: ...               # §8.6
    cryptography: ...                # §8.7
    observability: ...               # §8.8
    data_stores: []                  # §8.9
    confidence: ...                  # §8.10
```

### §8.2 Classification

A component can have multiple classifications simultaneously.

```yaml
classification:
  web_application:
    detected: bool
    sub_type: enum[spa, ssr, mpa, static_site, pwa, hybrid]
    frontend_framework: string
    backend_framework: string
    evidence: string[]

  api_service:
    detected: bool
    style: enum[rest, graphql, grpc, soap, websocket, event_driven, json_rpc, odata, other]
    framework: string
    spec_file:
      present: bool
      format: enum[openapi_3, openapi_2_swagger, asyncapi, protobuf, wsdl, raml, graphql_schema]
      path: string
    evidence: string[]

  ai_agent:
    detected: bool
    framework: string               # langchain, llamaindex, autogen, crewai, semantic-kernel, custom
    models_referenced:
      - provider: string            # openai, anthropic, google, huggingface, local
        model_id: string
        api_key_source: string      # env_var, config_file, hardcoded
    tools_defined:
      - name: string
        description: string
        risk_surface: string        # file_access, network, code_exec, credential_access, db_access
    rag_detected: bool
    memory_mechanism: string        # in-process, vector_db, file_system, none
    guardrails_present: bool
    evidence: string[]

  mcp_server:
    detected: bool
    framework: string
    transport: enum[stdio, sse, streamable_http, custom]
    tools:
      - name: string
        description: string
        input_schema: string        # JSON schema inline or path reference
        risk_classification: enum[read_only, write, network, code_execution, credential_access]
    resources:
      - uri_template: string
        description: string
    prompts:
      - name: string
        description: string
    authentication: string          # none, api_key, oauth2, etc.
    evidence: string[]

  cli_tool:
    detected: bool
    framework: string               # click, typer, cobra, clap, argparse, etc.
    entry_point: string
    commands:
      - name: string
        description: string
        accepts_file_input: bool
        accepts_url_input: bool
    evidence: string[]

  library_or_sdk:
    detected: bool
    package_registry: string        # pypi, npm, crates.io, etc.
    evidence: string[]

  infrastructure_as_code:
    detected: bool
    frameworks:
      - name: enum[terraform, opentofu, cloudformation, cdk, pulumi, ansible,
                   kubernetes_manifests, helm, kustomize, docker_compose,
                   dockerfiles, vagrant, packer, crossplane, bicep, salt]
        paths: string[]
        providers_or_targets: string[]
        state_backend: string
    evidence: string[]

  event_consumer_or_worker:
    detected: bool
    queue_technology: string        # sqs, rabbitmq, kafka, redis, nats, pubsub
    event_sources: string[]
    processing_model: enum[batch, stream, scheduled, on_demand]
    evidence: string[]

  scheduled_job:
    detected: bool
    scheduler: string               # cron, celery-beat, cloudwatch-events, cloud-scheduler
    jobs:
      - name: string
        description: string
    evidence: string[]

  proxy_or_gateway:
    detected: bool
    type: enum[api_gateway, reverse_proxy, bff, load_balancer, service_mesh_gateway]
    technology: string
    routes_to: string[]
    evidence: string[]

  smart_contract:
    detected: bool
    blockchain: string
    language: string
    evidence: string[]

  mobile_application:
    detected: bool
    platform: enum[ios, android, cross_platform]
    framework: string
    evidence: string[]

  browser_extension:
    detected: bool
    target_browsers: string[]
    manifest_version: string
    permissions_requested: string[]
    evidence: string[]

  data_pipeline:
    detected: bool
    framework: string
    evidence: string[]

  machine_learning_model:
    detected: bool
    ml_framework: string
    training_pipeline: bool
    inference_server: bool
    evidence: string[]

  database_migration:
    detected: bool
    migration_framework: string
    database_type: string
    pii_columns_detected: string[]
    evidence: string[]

  fork_or_vendor_copy:
    detected: bool
    upstream_url: string
    upstream_commit: string
    local_modifications: bool
    evidence: string[]
```

### §8.3 Tech Stack

```yaml
tech_stack:
  languages:
    - name: string
      version_constraint: string    # e.g., ">=3.11", "^18.0"
      role: enum[application, infrastructure, test, scripting]

  package_managers:
    - name: string
      lockfile_present: bool
      lockfile_path: string

  frameworks:
    - name: string
      version: string
      category: enum[web, api, orm, auth, logging, monitoring, ai_ml, security, other]

  runtime:
    name: string
    version: string
    container_base_image: string
```

### §8.4 Entry Points

The primary attack surface catalog. Every inbound path into the component.

```yaml
entry_points:
  - id: string                      # stable identifier for cross-referencing, e.g., "EP-001"
    type: enum[http_route, grpc_method, graphql_query, graphql_mutation,
               cli_command, event_handler, scheduled_job, websocket_handler,
               file_watcher, queue_consumer, webhook_receiver, plugin_hook,
               mcp_tool, mcp_resource, user_interface_action]
    path_or_name: string            # route path, method name, command name, tool name
    http_method: string             # GET, POST, PUT, DELETE, PATCH — for http_route only
    authentication_required: enum[yes, no, conditional, unknown]
    authorization_model: string     # RBAC role name, ABAC policy ref, scope, "none", "unknown"
    input_validation:
      present: bool
      framework: string             # zod, joi, pydantic, marshmallow, bean-validation
      schema_path: string
    rate_limited: bool              # in-code only; gateway rate limiting is Tier 2
    file_upload_accepted: bool
    request_body_type: string       # json, form, multipart, xml, protobuf, graphql, none
    source_file: string
    line_number: int
```

### §8.5 Authentication

```yaml
authentication:
  mechanisms:
    - type: enum[oauth2, oidc, saml, jwt, api_key, basic_auth, mtls,
                 session_cookie, magic_link, passkey_webauthn, ldap,
                 kerberos, custom_token, mfa_totp, mfa_sms, mfa_push,
                 social_login, certificate_auth, none]
      provider: string              # Auth0, Cognito, Keycloak, custom, etc.
      configuration_source: string  # env_var, config_file, hardcoded
      token_storage: enum[httponly_cookie, localstorage, sessionstorage, memory, header, none]
      mfa_enforced: bool
      evidence: string[]

  session_management:               # Tier 2: session timeout may live in IdP; null if not visible
    mechanism: enum[server_side, jwt_stateless, jwt_with_blacklist, signed_cookie, none]
    session_store: string           # redis, db, memory, none, unknown

  credential_storage:               # only populate if component handles passwords
    password_hashing: string        # bcrypt, argon2, scrypt, pbkdf2, sha256, plaintext
    salt_strategy: string
    evidence: string[]

  service_to_service_auth:          # Tier 2: may be injected by service mesh; null if not visible
    detected: bool
    mechanism: string               # mtls, jwt, api_key, iam_role, service_mesh, none
    evidence: string[]
```

### §8.6 Authorization

```yaml
authorization:
  model: enum[rbac, abac, pbac, acl, ownership, capability_based, hybrid, none, unknown]
  framework: string                 # casbin, oso, cerbos, opa, cedar, spring-security, custom
  policy_location: string           # code, config_file, external_service, database

  resource_types:
    - name: string
      access_patterns: string[]     # read, write, delete, admin — operations on this resource

  enforcement_points:
    - location: string              # middleware, decorator, interceptor, gateway, database, inline
      coverage: enum[all_routes, most_routes, some_routes, inconsistent, none]

  api_key_management:
    scoping: string                 # per-resource, global, none
    rotation_supported: bool
    revocation_supported: bool
```

### §8.7 Cryptography

```yaml
cryptography:
  operations_detected:
    - operation: enum[hashing, signing, encryption, key_derivation, random_generation]
      algorithm: string             # e.g., "AES-256-GCM", "MD5", "PBKDF2", "math/rand"
      library: string               # e.g., "cryptography", "jose", "bcrypt"
      file: string
      line: int
```

### §8.8 Observability

```yaml
observability:
  logging_framework: string         # python logging, winston, zap, slf4j, etc. — null if none
  audit_trail_present: bool         # explicit audit logging of auth/access events
```

### §8.9 Data Stores

```yaml
data_stores:
  - type: enum[rdbms, nosql, cache, object_storage, file_system,
               vector_db, message_queue, search_engine]
    technology: string             # PostgreSQL, MongoDB, Redis, S3, etc.
    name: string                   # logical name or null
    connection_config_source: string  # env_var, config_file, hardcoded
    data_classification: enum[public, internal, confidential, restricted, pii, phi, pci, unknown]
    evidence: string[]
```

### §8.10 Confidence

```yaml
confidence:
  overall: float                   # 0.0 to 1.0
  manual_review_recommended: bool
  limitations: string[]            # e.g., "auth middleware uses factory pattern — chain not statically traceable"
```

---

## §9 Cross-Component Analysis

### §9.1 Relationships

```yaml
cross_component:
  relationships:
    - source: string               # component id
      target: string               # component id
      type: enum[calls_api, imports_library, publishes_events_to, consumes_events_from,
                 reads_from_store, writes_to_store, proxies_to, shares_database_with]
      protocol: string             # HTTP, gRPC, AMQP, SQL, etc.
      authentication: string       # jwt, api_key, mtls, none, unknown
      data_classification: string  # pii, confidential, internal, public, unknown
      trust_boundary_crossing: bool
```

### §9.2 Data Flow Diagrams

```yaml
  data_flow_diagrams:
    - level: enum[context, container, component]

      actors:
        - id: string
          name: string
          type: enum[external_user, internal_user, admin, system,
                     api_consumer, third_party_service]
          trust_level: enum[untrusted, partially_trusted, trusted, highly_trusted]

      processes:
        - id: string
          name: string
          component_ref: string    # component id
          trust_zone: string       # logical trust zone name
          technology: string

      data_stores:
        - id: string
          name: string
          type: string
          data_classification: string

      data_flows:
        - id: string
          source: string
          destination: string
          data_description: string
          data_classification: string
          protocol: string
          encryption_in_transit: enum[tls, mtls, none, unknown]
          authentication: string
          crosses_trust_boundary: bool
          boundary_crossed: string

      trust_boundaries:
        - id: string
          name: string
          type: enum[network, process, machine, cloud_account, vpc, container,
                     namespace, region, compliance_zone, third_party]
          contains: string[]       # ids of processes/data_stores inside this boundary

      mermaid: string              # generated Mermaid diagram syntax
```

### §9.3 Attack Surface Summary

```yaml
  attack_surface:
    total_external_entry_points: int
    total_internal_entry_points: int
    unauthenticated_entry_points:
      - component: string
        entry_point_id: string
        path_or_name: string
    file_upload_endpoints:
      - component: string
        entry_point_id: string
        path_or_name: string
    admin_interfaces:
      - component: string
        entry_point_id: string
        path_or_name: string
    debug_endpoints:
      - component: string
        entry_point_id: string
        path_or_name: string
```

---

## §10 Delta Report

Present when a previous snapshot exists. Null on first run.

```yaml
delta_report:
  comparison:
    from_snapshot:
      id: string
      commit_sha: string
      commit_date: datetime
    to_snapshot:
      id: string
      commit_sha: string
      commit_date: datetime

  git_summary:
    commits_between: int
    files_changed: int
    authors: string[]

  components:
    added:
      - id: string
        path: string
        classifications: string[]
        entry_points_count: int

    removed:
      - id: string
        path: string

    modified:
      - id: string
        modules_rerun: string[]
        entry_points_diff:
          added:
            - path_or_name: string
              type: string
              authentication_required: string
          removed:
            - path_or_name: string
              type: string
```
