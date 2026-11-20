# ADR-0008 · OpenViking plugin: `--no-deps` install + `plugins.enabled`

- Status: accepted (stage 1, contract f/f2/f3)

## Context
`hermes -p X plugins install openviking --yes-deps --enable` is the documented non-interactive path.
In the sandbox it fails while resolving dependencies (a GitHub release asset returns HTTP 401); it still
exits 0 and leaves the plugin installed but **not enabled**. The plugin is installed per profile
(`profiles/<p>/plugins/openviking`), which answers research item S1.

## Decision
Memory apply does, per profile:
1. if `plugins/openviking/plugin.yaml` is absent: `hermes -p X plugins install openviking --no-deps`
   (re-installing an existing plugin is an error, so the directory is checked first);
2. write `memory.provider: openviking` and add `openviking` to `plugins.enabled` (owned entries);
3. write `OPENVIKING_ENDPOINT/API_KEY/ACCOUNT/USER` into the managed `.env` block.

## Consequences
The plugin's optional Python deps are not installed; Hermes reports them through `memory status`.
If the upstream asset becomes reachable, `--yes-deps --enable` can replace step 1 without schema change.
