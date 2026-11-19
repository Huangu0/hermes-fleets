# ADR-0003 · Public repository hygiene

- Status: accepted (stage 0)

## Context
D1 changed from "local git only" to "push to the public GitHub repo `Huangu0/hermes-fleets`". The dev
sandbox environment contains proxy credentials, and the service handles API keys and OV user keys.

## Decision
- A thorough `.gitignore`: `.env*` (except `.env.example`), keys/certs, SQLite DBs and WAL files, venvs,
  tool caches, runtime data dirs, Hermes homes, OpenViking data/config, model files and archives.
- `scripts/check_secrets.py` runs as the first pre-commit hook (`--staged`) and can scan the work tree
  (`--all`) or every blob in history (`--history`). It blocks forbidden paths, runs detect-secrets'
  default plugins and extra patterns (JWTs, credentials embedded in URLs, private keys, GitHub/OpenAI/AWS
  key shapes). Intentional test fixtures carry `pragma: allowlist secret`.
- Nothing in tests or docs uses a real credential; test keys are generated per test (Fernet) or are
  obviously fake.
- Every push is preceded by a full-history scan.

## Consequences
Hooks are `language: system` (no network at commit time); they need `uv` and `just` on PATH.
