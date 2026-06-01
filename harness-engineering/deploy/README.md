# deploy

This directory contains deployment scaffolding for V4.1 MVP phase 1.

Current state:

| File | Purpose |
|---|---|
| `../services/agent-api/Dockerfile` | Agent API image with dependencies installed at build time |
| `docker-compose.platform.yml` | Prototype-compatible platform control plane plus PostgreSQL target dependency |
| `docker-compose.agent.yml` | Prototype-compatible Agent data plane, parallel FastAPI Agent entrypoint, PostgreSQL, Redis, Qdrant, worker placeholders |
| `env.platform.example` | Platform environment template without business data |
| `env.agent.example` | Agent environment template without model API key plaintext |
| `env.example` | Backward-compatible combined prototype template |
| `../scripts/validate-deploy-config.py` | Pre-delivery security validation for env examples and Compose boundaries |
| `../scripts/scan-delivery-artifacts.py` | Pre-delivery scan for secret, path, and case-content leaks in delivery artifacts |
| `../scripts/check-delivery-package.py` | Pre-delivery package boundary manifest and runtime-artifact exclusion check |
| `../scripts/export-delivery-package.py` | Reproducible tar.gz export based on the validated delivery manifest |
| `../scripts/verify-delivery-package.py` | Post-export archive manifest, exclusion-rule, and checksum verification |
| `../scripts/export-delivery-acceptance-report.py` | Metadata-only JSON evidence report for delivery acceptance checks |
| `../scripts/verify-delivery-acceptance-report.py` | Schema and required-check verification for the acceptance evidence report |
| `../scripts/export-delivery-bundle.py` | One-command export of archive, checksum, acceptance report, and bundle manifest |
| `../scripts/verify-delivery-bundle.py` | Independent verification for the exported delivery bundle directory |

Security boundary:

```text
Platform compose must not include file storage, document parser, RAG, vector payload processing, or model proxy services.
Agent compose owns local files, parsing, vectorization, RAG, model calls, and audit logs.
```

Agent production notes:

```text
Copy env.agent.example to a local .env file outside version control.
Keep AGENT_RUNTIME=stdlib for conservative startup, or set AGENT_RUNTIME=fastapi for FastAPI gray rollout.
Generate strong AGENT_ADMIN_PASSWORD and AGENT_SECRET_KEY values before first startup.
Generate strong AGENT_POSTGRES_PASSWORD and update AGENT_LOCAL_DATABASE_URL consistently before formal deployment.
Set AGENT_ALLOWED_DATA_ROOTS to the explicit case-material roots approved by the lawyer/law firm.
Keep AGENT_FORBIDDEN_DATA_ROOTS and AGENT_FORBIDDEN_PATH_PARTS enabled.
Only configure AGENT_OCR_COMMAND with executables listed in AGENT_OCR_ALLOWED_COMMANDS.
Model and Qdrant URLs must point to localhost, private network, link-local, or .local addresses.
```

Agent runtime notes:

```text
agent-api exposes the legacy stdlib prototype on port 8200.
agent-api-fastapi exposes the M20 FastAPI adapter on port 8201.
Both runtimes reuse the same Store business methods; separate compose volumes avoid SQLite write contention during parallel testing.
```

Delivery verification:

```bash
bash scripts/verify-mvp.sh
```

The verification entrypoint runs environment checks, pytest regression, OpenAPI export, redacted diagnostics preview, platform-invisibility report export, shell syntax checks, deployment config security validation, delivery artifact leak scanning, delivery package boundary checks, delivery archive smoke export, delivery archive self-verification, SHA-256 checksum verification, metadata-only delivery acceptance report export, and Docker Compose config validation when Docker is available.

Deployment config security validation:

```bash
python3 scripts/validate-deploy-config.py --mode example
python3 scripts/validate-deploy-config.py --mode production --agent-env path/to/agent.env --platform-env path/to/platform.env
```

The validator rejects weak plaintext secrets in env examples and Compose files, missing critical security variables, public Agent-side endpoint URLs, and platform Compose services that would violate the platform-invisibility boundary.

Delivery artifact leak scanning:

```bash
python3 scripts/scan-delivery-artifacts.py
```

The scanner checks delivery docs and deployment materials for high-confidence API keys, private keys, concrete database passwords, personal workstation paths, and seeded case-content examples before packaging.

Delivery package boundary check:

```bash
python3 scripts/check-delivery-package.py
python3 scripts/check-delivery-package.py --output /tmp/delivery-manifest.json
```

The package boundary check builds the candidate delivery manifest from source, docs, deploy, scripts, tests, and module roots while excluding runtime databases, diagnostics exports, dependency directories, virtual environments, caches, private env files, logs, and build artifacts.

Delivery archive export:

```bash
python3 scripts/export-delivery-package.py --output /tmp/harness-engineering-delivery.tar.gz
```

The export command reuses the validated delivery package manifest, writes `DELIVERY-MANIFEST.json` into the archive, writes a same-name `.sha256` sidecar, and requires the output path to be outside the project root by default.

Delivery archive verification:

```bash
python3 scripts/verify-delivery-package.py --archive /tmp/harness-engineering-delivery.tar.gz --require-checksum --extract-smoke
```

The verifier checks the archive path layout, rejects path traversal and runtime artifacts, proves the embedded manifest exactly matches the archive contents, verifies the SHA-256 sidecar when required, and can safely extract to a temporary directory to check required handoff entry files plus run a non-recursive post-extract reverification command from the extracted package.

Delivery acceptance evidence report:

```bash
python3 scripts/export-delivery-acceptance-report.py --archive /tmp/harness-engineering-delivery.tar.gz --output /tmp/delivery-acceptance-report.json
```

The report records check status, Python/Docker/Compose environment fingerprints, Platform/Agent Compose config status, archive SHA-256, checksum sidecar status, safe extraction smoke status, manifest counts, V5 P0 evidence summaries for knowledge governance, AI risk controls, quality feedback, historical citations, platform invisibility, delivery redlines, and redaction guarantees without exporting archive file contents, test outputs, database values, or business data.

Delivery acceptance evidence report verification:

```bash
python3 scripts/verify-delivery-acceptance-report.py --report /tmp/delivery-acceptance-report.json
```

The report verifier checks schema version, required check names, checksum/extract-smoke evidence, environment fingerprints, archive metadata, V5 P0 required evidence items, and redaction guarantees.

One-command delivery bundle export:

```bash
python3 scripts/export-delivery-bundle.py --output-dir /tmp/harness-engineering-delivery-bundle
```

The bundle command writes the archive, `.sha256`, acceptance report, and `delivery-bundle-manifest.json`, then verifies the archive and report before returning success. The bundle manifest includes an acceptance-report summary with schema, pass status, metadata-only flags, and V5 P0 evidence names.

Delivery bundle verification:

```bash
python3 scripts/verify-delivery-bundle.py --manifest /tmp/harness-engineering-delivery-bundle/delivery-bundle-manifest.json
```

The verifier checks bundle manifest schema, artifact presence, step statuses, archive verification, acceptance report verification, and V5 P0 evidence-summary consistency so the exported bundle can be rechecked independently.

Delivery artifacts:

| Artifact | Command or path |
|---|---|
| Agent OpenAPI schema | `.venv-agent-api/bin/python scripts/export-agent-openapi.py --output docs/agent-api-openapi.json` |
| Agent API contract | `docs/agent-api-contract.md` |
| Redacted diagnostics preview | `bash scripts/export-diagnostics.sh` |
| Redacted diagnostics export | `bash scripts/export-diagnostics.sh --confirm` |
| Platform-invisibility report | `.venv-agent-api/bin/python scripts/export-platform-invisibility-report.py --output docs/platform-invisibility-report.json` |
| Deployment config security validation | `python3 scripts/validate-deploy-config.py --mode example` |
| Delivery artifact leak scan | `python3 scripts/scan-delivery-artifacts.py` |
| Delivery package boundary check | `python3 scripts/check-delivery-package.py` |
| Delivery archive export | `python3 scripts/export-delivery-package.py --output /tmp/harness-engineering-delivery.tar.gz` |
| Delivery archive verification | `python3 scripts/verify-delivery-package.py --archive /tmp/harness-engineering-delivery.tar.gz --require-checksum --extract-smoke` |
| Delivery acceptance evidence report | `python3 scripts/export-delivery-acceptance-report.py --archive /tmp/harness-engineering-delivery.tar.gz --output /tmp/delivery-acceptance-report.json` |
| Delivery acceptance evidence report verification | `python3 scripts/verify-delivery-acceptance-report.py --report /tmp/delivery-acceptance-report.json` |
| One-command delivery bundle export | `python3 scripts/export-delivery-bundle.py --output-dir /tmp/harness-engineering-delivery-bundle` |
| Delivery bundle verification | `python3 scripts/verify-delivery-bundle.py --manifest /tmp/harness-engineering-delivery-bundle/delivery-bundle-manifest.json` |
| Extracted bundle smoke | `python3 scripts/smoke-delivery-bundle-extract.py --bundle-dir /tmp/harness-engineering-delivery-bundle` |
| Acceptance report redline scan | `python3 scripts/scan-delivery-acceptance-report.py --report /tmp/delivery-acceptance-report.json` |
| MVP verification | `bash scripts/verify-mvp.sh` |

Diagnostics exports are whitelist-only and require explicit confirmation. They must not include case names, file names, file paths, document text, chunks, vectors, questions, answers, prompts, model secrets, or database credentials.

The platform-invisibility report is metadata-only. It checks platform table names, column names, row counts, forbidden-field coverage, whitelist overlap, and a forbidden-field injection probe without exporting stored database values.
