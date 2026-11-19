# hermes-fleet task runner. `just check` is the local CI gate (also run by pre-commit).
set dotenv-load := false

export UV_LINK_MODE := "copy"

default: check

# ruff + mypy + all tests except e2e
check: lint typecheck test

lint:
    uv run ruff check src tests scripts
    uv run ruff format --check src tests scripts

fmt:
    uv run ruff format src tests scripts
    uv run ruff check --fix src tests scripts

typecheck:
    uv run mypy

test:
    uv run pytest -q -m "not e2e"

test-unit:
    uv run pytest -q -m unit

test-hermes:
    uv run pytest -q -m hermes

# secret scan of the working tree (also a pre-commit hook)
scan-secrets:
    uv run python scripts/check_secrets.py --all  # pragma: allowlist secret

# install hermes-agent v0.23.1 via its own setup script (into $FLEET_OPT or ./.cache/opt)
install-hermes:
    bash scripts/install-hermes.sh

migrate:
    uv run alembic -c alembic.ini upgrade head

serve:
    uv run uvicorn hermes_fleet.main:app --host 127.0.0.1 --port 8088
