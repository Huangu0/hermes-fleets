# Hermes v0.23.1 contract

What hermes-fleet relies on, verified against the real CLI (tag `v0.23.1`, commit `3b421578`) by
`tests/contract/test_hermes_contract.py` (marker `hermes`). Re-run them before bumping Hermes.
Last verified: 2026-11-20 (rebuild), all items re-checked against the real install rather than carried
over from the lost first build.

| # | Item | Result | Test | ADR |
|---|---|---|---|---|
| a | Profile layout | `$HERMES_HOME/profiles/<p>/` with `config.yaml` (absent until first written), `.env` (mode 600, created with a comment header), `skills/`, `plugins/`, `.no-bundled-skills` when created with `--no-skills` | `test_a_profile_layout` | — |
| a2 | `profile create` | must pass `--no-alias`, otherwise a wrapper script is written to `~/.local/bin/<name>` (outside `HERMES_HOME`, shared across homes) | `test_a_profile_layout` | ADR-0007 |
| b | `mcp_servers` written to `config.yaml` | recognised by `hermes -p X mcp list` (stdio `command/args/env`, http `url/headers`) | `test_b_mcp_servers_recognised` | — |
| c | `skills.external_dirs` | external skills listed by `hermes -p X skills list` with source `external`; a **profile-local skill with the same name shadows the external one** (local > external) | `test_c_external_dirs_and_local_shadowing` | ADR-0009 |
| d | `platform_toolsets.<platform>` | reflected by `hermes -p X tools list --platform cli` (`✓ enabled  <name>`) | `test_d_platform_toolsets` | — |
| e | `${VAR}` in `mcp_servers` | expanded at spawn time from the **profile's `.env`** / secret scope; `config.yaml` keeps the placeholder | `test_e_env_placeholder_expanded_from_profile_env` | ADR-0006 |
| e2 | unset `${VAR}` in a stdio `env` entry | the key is **dropped** (child sees it unset, never the literal placeholder) | `test_e2_unset_stdio_var_is_dropped` | ADR-0006 |
| e3 | `hermes -p X mcp test <name>` | exit 0 + `Tools discovered: N` when reachable; non-zero + `Connection failed` otherwise | `test_e_*`, `test_e3_dead_http_server_fails` | — |
| f | `plugins install openviking --yes-deps --enable` | **fails in the sandbox**: dependency resolution downloads a GitHub release asset that returns 401; the command still exits 0 but leaves the plugin *not enabled* | probe (not a test: network-dependent) | ADR-0008 |
| f2 | fallback | `plugins install openviking --no-deps` installs into `profiles/<p>/plugins/openviking` (per-profile, disabled); `plugins.enabled: [openviking]` in `config.yaml` enables it (`plugins list --plain` → `enabled`); `memory.provider: openviking` makes `memory status` require `OPENVIKING_*` env vars | `test_f_plugin_install_no_deps_then_enable_via_config` | ADR-0008 |
| f3 | re-install | installing again fails (non-zero) whether disabled ("already exists") or enabled ("cannot replace an active plugin") → check for the plugin dir first | same | ADR-0008 |
| g | gateway restart per profile | `hermes -p X gateway restart` exits **78** ("does not get a gateway of its own"): one host gateway multiplexes all profiles | `test_g_gateway_restart_is_host_scoped` | ADR-0010 |
| g2 | host restart | `hermes gateway restart --detach` (no installed service) starts the replacement in the background; `-y/--interrupt` restarts even with live sessions (otherwise it asks / refuses without a TTY) | help text asserted; restart verified manually | ADR-0010 |
| h | clone | `--no-skills` is mutually exclusive with `--clone/--clone-from/--clone-all`; `--clone-from` copies config, `.env`, SOUL.md and skills | `test_h_clone_flags` | ADR-0007 |
| h2 | delete | `hermes profile delete <p> -y` removes the directory non-interactively | `test_h_clone_flags` | — |
| i | isolation | the dependency venv is selected from `$HERMES_HOME/installs/`; isolated homes need `installs/` linked to the owning install (done by `scripts/hermes`) | `tests/hermes/test_smoke.py` | ADR-0004 |

## Not used (by design)

- Hermes rewrites nothing it did not create: our hand-written `config.yaml` (comments included) survived
  every CLI call above. Hermes does keep its own `backups/config/config.yaml.good.*` snapshots.
- Remote config backend (`HERMES_CONFIG_BACKEND=remote`): protocol undocumented, only investigated.
- `hermes mcp add` / `hermes config set`: we write YAML ourselves (comment-preserving, locked, atomic,
  backed up) and use the CLI only to verify and to probe.
