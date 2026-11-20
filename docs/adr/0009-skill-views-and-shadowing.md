# ADR-0009 · Skills: shared pool + per-profile symlink view, local shadowing is a D2 conflict

- Status: accepted (stage 1, contract c)

## Decision
- Skills are stored once in `<data>/skill-pool/<name>@<sha>`; each profile gets a view directory
  `<data>/skill-views/<p>/` containing one symlink per selected skill, and that single directory is the
  fleet's entry in `skills.external_dirs`.
- Contract c shows a profile-local skill with the same name wins over an external one. Such a skill is a
  D2 conflict: plan reports it, apply refuses, readiness flags it as `shadowed`.
