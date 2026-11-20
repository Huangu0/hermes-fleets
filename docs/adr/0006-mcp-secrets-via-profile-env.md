# ADR-0006 · MCP secrets: placeholders in config.yaml, values in a fleet-managed .env block

- Status: accepted (stage 1, contract e/e2)

## Context
Contract e: Hermes expands `${VAR}` inside `mcp_servers` at spawn time from the profile's own `.env`
(secret scope), and keeps the placeholder in `config.yaml`. Contract e2: an unset `${VAR}` in a stdio
`env` entry is dropped, so a missing secret shows up as "unset" in the server rather than as a literal
placeholder.

## Decision
- The catalog stores MCP definitions with `${NAME}` placeholders only; plaintext secrets are rejected.
- `config.yaml` always receives the placeholder; secret **values** go into the profile `.env` inside a
  marker-delimited block owned by hermes-fleet (`# >>> hermes-fleet managed >>>` … `# <<< … <<<`).
  Lines outside the block are never touched; the file stays mode 600.
- Secret values that themselves contain `${` are rejected (they would be re-expanded by Hermes).
- Missing secrets are reported by plan/readiness instead of being written as empty values.

## Consequences
Secrets never appear in YAML, diffs, audit summaries or API responses; only in the 600 `.env` files.
