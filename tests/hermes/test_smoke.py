"""Stage 0.6: the Hermes test base works (`pytest -m hermes -k smoke`)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run(bin_: str, home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "HERMES_HOME": str(home)}
    return subprocess.run([bin_, *args], env=env, capture_output=True, text=True, timeout=180)


def test_smoke_version_and_profile(hermes_bin: str, hermes_home: Path) -> None:
    v = run(hermes_bin, hermes_home, "--version")
    assert v.returncode == 0 and "v0.23.1" in v.stdout
    r = run(hermes_bin, hermes_home, "profile", "create", "smoke", "--no-alias")
    assert r.returncode == 0, r.stderr
    assert (hermes_home / "profiles" / "smoke").is_dir()
