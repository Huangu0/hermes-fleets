# ADR-0010 · Gateway restart is host-scoped

- Status: accepted (stage 1, contract g, research S2)

## Context
v0.23.1 runs exactly one host gateway that multiplexes every profile; `hermes -p X gateway restart` exits
78. Config changes only reach new sessions.

## Decision
- Apply responses carry `restart_required: true` whenever MCP servers, toolsets, plugins or memory
  changed (skills changes are picked up by new sessions without a restart; still flagged as
  `new_session_required`).
- `POST /v1/gateway/restart` runs `hermes gateway restart --detach` (host-wide, default home) and adds
  `-y` only when the request sets `interrupt=true`. It is never triggered automatically.
