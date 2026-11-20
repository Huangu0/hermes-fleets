# ADR-0007 · Profile CLI flags

- Status: accepted (stage 1, contract a2/h)

## Decision
- Always `hermes profile create <p> --no-alias`: without it Hermes writes `~/.local/bin/<p>`, outside
  `HERMES_HOME` and shared by all homes on the host.
- Default to `--no-skills` for fleet-created profiles (skills are delivered through the fleet's skill
  views); a request may opt back into bundled skills.
- Clones use `--clone-from <src>` and never `--no-skills` (mutually exclusive, exit 1).
- Delete uses `hermes profile delete <p> -y`.
- Profile names: `^[a-z][a-z0-9_-]{0,62}$` (Hermes requires lowercase alphanumerics) and `default` is
  reserved.
