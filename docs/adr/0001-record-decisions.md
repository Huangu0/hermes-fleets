# ADR-0001 · Record architecture decisions

- Status: accepted (stage 0)

## Context
The implementation plan lets the implementer take small decisions without asking ("zero-decision"
implementation), as long as they are written down. A previous build was lost in a workspace rollback,
which also showed that decisions living only in chat are fragile.

## Decision
Every non-obvious choice is a short ADR in `docs/adr/NNNN-title.md` (context, decision, consequences),
versioned with the code. Contract findings about Hermes / OpenViking that change a default get an ADR
and a regression test.

## Consequences
ADRs are part of the stage commit that introduced them.
