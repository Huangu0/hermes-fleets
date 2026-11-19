#!/usr/bin/env bash
# Reproducibly install hermes-agent v0.23.1 (commit 3b421578) via the tag's own
# setup-hermes.sh. pip install is blocked upstream (setup.py refuses packaging) and
# the tag ships its own Python 3.14, so Hermes lives in its own tree and is only
# ever invoked as a subprocess through scripts/hermes.
#
#   FLEET_OPT   install root (default: <repo>/.cache/opt). Keep it on persistent disk.
#
# Idempotent: re-running with an existing, correct checkout only re-runs setup.
set -euo pipefail

TAG="v0.23.1"
COMMIT="3b421578588243f920886e6fe79a6faa87ea026e"  # pragma: allowlist secret (git sha)
REPO_URL="https://github.com/NousResearch/hermes-agent"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
opt="${FLEET_OPT:-$here/.cache/opt}"
src="$opt/hermes-src"
mkdir -p "$opt"

if [ -d "$src/.git" ]; then
  have="$(git -C "$src" rev-parse HEAD)"
  if [ "$have" != "$COMMIT" ]; then
    echo "existing checkout at $src is $have, expected $COMMIT" >&2
    exit 1
  fi
else
  git clone --quiet --depth 1 --branch "$TAG" "$REPO_URL" "$src"
  have="$(git -C "$src" rev-parse HEAD)"
  [ "$have" = "$COMMIT" ] || { echo "tag $TAG resolved to $have, expected $COMMIT" >&2; exit 1; }
fi

# Keep Hermes' runtime store, caches and its owning home off the (ephemeral) root disk.
# The owning home MUST be the directory that contains the checkout: Hermes keeps the
# dependency venv under <home>/installs/<key>, and a launch under any other HERMES_HOME
# (every test's temporary home, every fleet-managed home) "borrows" the venv from the
# root the checkout sits in (pm/environments.py: owning_home_root).
export HERMES_RUNTIME_DIR="$opt/hermes-runtime"
export HERMES_HOME="$opt"
( cd "$src" && bash ./setup-hermes.sh )

launcher="$src/.hermes/bin/hermes"
[ -x "$launcher" ] || { echo "launcher not found at $launcher" >&2; exit 1; }
ver="$("$here/scripts/hermes" --version | head -1)"
echo "$ver"
case "$ver" in
  *"v0.23.1"*) echo "hermes-agent installed: $launcher" ;;
  *) echo "unexpected hermes version: $ver" >&2; exit 1 ;;
esac
