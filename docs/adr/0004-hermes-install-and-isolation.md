# ADR-0004 · Installing and isolating hermes-agent v0.23.1

- Status: accepted (stage 0), re-verified 2026-11-20

## Context
- v0.23.1 exists only as a GitHub tag (commit `3b421578`); PyPI stops at 0.19.0.
- `setup.py` refuses to be packaged, so `pip install` is not possible; the tag's `setup-hermes.sh` is the
  supported path. It stages a pinned uv and its own **Python 3.14**, then builds a hash-verified venv.
- The venv is selected at boot from `$HERMES_HOME/installs/<sha256(checkout)[:16]>`
  (`pm/environments.py::activate_dependencies`). Only the *tool store* (Python, node...) is borrowed from
  the owning home; the dependency venv is not. A fresh isolated `HERMES_HOME` therefore fails with
  `ModuleNotFoundError: No module named 'ruamel'` (observed 2026-11-20).
- `/tmp` and the root disk of the sandbox are not persistent.

## Decision
- `scripts/install-hermes.sh` clones the tag into `${FLEET_OPT:-.cache/opt}/hermes-src`, verifies the
  commit, and runs `setup-hermes.sh` with `HERMES_RUNTIME_DIR=$FLEET_OPT/hermes-runtime` and
  `HERMES_HOME=$FLEET_OPT` (the checkout's parent), so any isolated `HERMES_HOME` can borrow the venv.
- `scripts/hermes` is a thin launcher that execs the checkout's published launcher. When `HERMES_HOME` is
  set and has no `installs/`, it symlinks `$HERMES_HOME/installs -> $FLEET_OPT/installs`, so every isolated
  home (tests, fleet-managed homes) reuses the one committed venv instead of building its own.
- The service only ever runs Hermes as a subprocess (`FLEET_HERMES_BIN`); its own venv (3.12) never
  imports Hermes.
- Tests and the service pass an explicit `HERMES_HOME`; nothing touches `~/.hermes`.

## Consequences
Re-installing is one script; a fresh sandbox needs ~5–10 min (downloads). Each CLI call costs several
seconds on the slow workspace filesystem, so hermes-marked tests are kept few and coarse.
