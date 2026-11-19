# hermes-fleets

**hermes-fleet** is a small, backend-only control plane for [hermes-agent](https://github.com/NousResearch/hermes-agent)
multi-profile deployments. It keeps the *desired state* of every Hermes profile — skills, MCP servers,
toolsets, OpenViking memory and knowledge-base access — in a database, and reconciles it into each
profile's `config.yaml` / `.env` with **plan → apply → rollback → drift** semantics.

- Target: hermes-agent **v0.23.1** (pinned tag, installed with its own `setup-hermes.sh`)
- Memory / knowledge: [OpenViking](https://github.com/volcengine/OpenViking) **0.5.5** (one profile = one OV user)
- Stack: Python 3.12, FastAPI, SQLAlchemy 2 + Alembic (SQLite in dev), ruamel.yaml, filelock, httpx

> Status: under active development, see [docs/implementation-plan.md](docs/implementation-plan.md).

## Quick start

```bash
uv sync                                  # service venv (Python 3.12)
FLEET_OPT=$PWD/.cache/opt scripts/install-hermes.sh   # hermes-agent v0.23.1 (own Python 3.14)
cp .env.example .env                     # then edit; .env is git-ignored
just check                               # ruff + mypy + pytest -m "not e2e"
just serve                               # http://127.0.0.1:8088/docs
```

## Documentation

- [docs/design.md](docs/design.md) — architecture (desired state + reconcile)
- [docs/implementation-plan.md](docs/implementation-plan.md) — stages 0–9 and acceptance criteria
- [docs/adr/](docs/adr/) — architecture decision records

## License

MIT — see [LICENSE](LICENSE). OpenViking itself is AGPL-3.0 and is used only as a separate HTTP service.
