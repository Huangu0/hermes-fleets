# ADR-0005 · Test tiers and the local CI gate

- Status: accepted (stage 0)

## Decision
Markers are assigned from the test directory (`tests/conftest.py`):

| marker | directory | needs |
|---|---|---|
| unit | tests/unit | nothing |
| hermes | tests/hermes, tests/contract | real hermes v0.23.1 (`scripts/install-hermes.sh`), skipped otherwise |
| ovfake | tests/ovfake | in-process Fake OpenViking |
| ovreal | tests/ovreal | a real openviking-server at `FLEET_OV_REAL_URL`, skipped otherwise |
| e2e | tests/e2e | real Hermes + real OpenViking (`just e2e`) |

`just check` = `ruff check` + `ruff format --check` + `mypy --strict` + `pytest -m "not e2e"`; it is the
pre-commit gate (no GitHub Actions, see D1).

## Consequences
`ovreal` tests are part of `just check` but skip without a server; `just e2e` starts/reuses one.
