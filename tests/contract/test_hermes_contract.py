"""Stage 1: Hermes v0.23.1 contract tests -> docs/hermes-contract.md.

These pin the behaviour the adapter relies on. A module-scoped home with one
`--no-skills` profile keeps the (slow) CLI calls to a minimum.
"""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import REPO, hermes_available, run_hermes

ECHO = REPO / "tests" / "fixtures" / "echo_mcp_server.py"
TOKEN = "contract-token-value"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def env(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Any]]:
    if not hermes_available():
        pytest.skip("hermes-agent v0.23.1 not installed")
    bin_ = str(REPO / "scripts" / "hermes")
    root = tmp_path_factory.mktemp("contract")
    home = root / "home"
    home.mkdir()
    r = run_hermes(bin_, home, "profile", "create", "ct", "--no-alias", "--no-skills")
    assert r.returncode == 0, r.stdout + r.stderr
    prof = home / "profiles" / "ct"
    ext = root / "ext"
    for name, desc in (("extskill", "external skill"), ("dupskill", "EXTERNAL copy")):
        (ext / name).mkdir(parents=True)
        (ext / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n# x\n")
    (prof / "skills" / "dupskill").mkdir(parents=True)
    (prof / "skills" / "dupskill" / "SKILL.md").write_text(
        "---\nname: dupskill\ndescription: LOCAL copy\n---\n# y\n"
    )
    rec_set, rec_unset = root / "rec-set", root / "rec-unset"
    (prof / "config.yaml").write_text(
        "# hand-written comment\n"
        "mcp_servers:\n"
        "  echo:\n"
        f"    command: {sys.executable}\n"
        f"    args: [{ECHO}]\n"
        "    env:\n"
        "      ECHO_TOKEN: ${CT_TOKEN}\n"
        f"      ECHO_RECORD: {rec_set}\n"
        "  echo_unset:\n"
        f"    command: {sys.executable}\n"
        f"    args: [{ECHO}]\n"
        "    env:\n"
        "      ECHO_TOKEN: ${CT_UNSET_TOKEN}\n"
        f"      ECHO_RECORD: {rec_unset}\n"
        "  dead:\n"
        "    url: http://127.0.0.1:9/mcp\n"
        "skills:\n"
        "  external_dirs:\n"
        f"    - {ext}\n"
        "platform_toolsets:\n"
        "  cli: [web, terminal]\n"
    )
    with (prof / ".env").open("a") as fh:
        fh.write(f"CT_TOKEN={TOKEN}\n")
    yield {"bin": bin_, "home": home, "prof": prof, "rec_set": rec_set, "rec_unset": rec_unset}


def h(env: dict[str, Any], *args: str, **kw: Any) -> Any:
    return run_hermes(env["bin"], env["home"], *args, **kw)


def test_a_profile_layout(env: dict[str, Any]) -> None:
    prof: Path = env["prof"]
    assert prof == env["home"] / "profiles" / "ct"
    assert (prof / ".env").is_file()
    assert (prof / ".env").stat().st_mode & 0o777 == 0o600
    assert (prof / ".no-bundled-skills").is_file()
    assert not (Path.home() / ".local" / "bin" / "ct").exists()  # --no-alias: no wrapper
    r = h(env, "profile", "list")
    assert r.returncode == 0 and " ct " in r.stdout


def test_b_mcp_servers_recognised(env: dict[str, Any]) -> None:
    r = h(env, "-p", "ct", "mcp", "list")
    assert r.returncode == 0
    for name in ("echo", "echo_unset", "dead"):
        assert name in r.stdout


def test_c_external_dirs_and_local_shadowing(env: dict[str, Any]) -> None:
    r = h(env, "-p", "ct", "skills", "list")
    assert r.returncode == 0
    lines = {ln.split("│")[1].strip(): ln for ln in r.stdout.splitlines() if ln.count("│") > 3}
    assert "external" in lines["extskill"]
    # same name in profile-local skills/ and external_dirs: the local one wins
    assert "local" in lines["dupskill"] and "external" not in lines["dupskill"]


def test_d_platform_toolsets(env: dict[str, Any]) -> None:
    r = h(env, "-p", "ct", "tools", "list", "--platform", "cli")
    assert r.returncode == 0
    enabled = {ln.split()[2] for ln in r.stdout.splitlines() if "✓ enabled" in ln}
    assert {"web", "terminal"} <= enabled
    assert "file" not in enabled


def test_e_env_placeholder_expanded_from_profile_env(env: dict[str, Any]) -> None:
    r = h(env, "-p", "ct", "mcp", "test", "echo")
    assert r.returncode == 0, r.stdout
    assert "Tools discovered: 2" in r.stdout
    want = "sha256:" + hashlib.sha256(TOKEN.encode()).hexdigest()
    assert env["rec_set"].read_text() == want
    # config.yaml keeps the placeholder (values never written to yaml)
    assert "${CT_TOKEN}" in (env["prof"] / "config.yaml").read_text()


def test_e2_unset_stdio_var_is_dropped(env: dict[str, Any]) -> None:
    r = h(env, "-p", "ct", "mcp", "test", "echo_unset")
    assert r.returncode == 0
    assert env["rec_unset"].read_text() == "unset"


def test_e3_dead_http_server_fails(env: dict[str, Any]) -> None:
    r = h(env, "-p", "ct", "mcp", "test", "dead")
    assert r.returncode != 0
    assert "failed" in r.stdout.lower()


def test_f_plugin_install_no_deps_then_enable_via_config(env: dict[str, Any]) -> None:
    """`--yes-deps --enable` fails in the sandbox (release asset 401, exit 0 but plugin left
    disabled). Fallback (ADR-0008): install with `--no-deps`, enable via plugins.enabled."""
    r = h(env, "-p", "ct", "plugins", "install", "openviking", "--no-deps")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (env["prof"] / "plugins" / "openviking" / "plugin.yaml").is_file()
    cfg = env["prof"] / "config.yaml"
    cfg.write_text(
        cfg.read_text() + "memory:\n  provider: openviking\nplugins:\n  enabled: [openviking]\n"
    )
    r = h(env, "-p", "ct", "plugins", "list", "--plain", "--no-bundled")
    row = [ln for ln in r.stdout.splitlines() if ln.rstrip().endswith("openviking")]
    assert row and row[0].startswith("enabled")
    r = h(env, "-p", "ct", "memory", "status")
    assert "openviking" in r.stdout and "OPENVIKING_ENDPOINT" in r.stdout
    # re-running install on an existing plugin is an error ("already exists" while disabled,
    # "cannot replace an active plugin" once enabled) -> the adapter must check the dir first
    again = h(env, "-p", "ct", "plugins", "install", "openviking", "--no-deps")
    assert again.returncode != 0


def test_g_gateway_restart_is_host_scoped(env: dict[str, Any]) -> None:
    r = h(env, "-p", "ct", "gateway", "restart", "--detach")
    assert r.returncode == 78
    assert "does not get a gateway of its own" in r.stdout + r.stderr
    helptext = h(env, "gateway", "restart", "--help").stdout
    assert "--detach" in helptext and "--interrupt" in helptext


def test_h_clone_flags(env: dict[str, Any]) -> None:
    r = h(env, "profile", "create", "ct2", "--no-alias", "--no-skills", "--clone-from", "ct")
    assert r.returncode != 0 and "mutually exclusive" in r.stdout + r.stderr
    r = h(env, "profile", "create", "ct3", "--no-alias", "--clone-from", "ct")
    assert r.returncode == 0
    assert "mcp_servers" in (env["home"] / "profiles" / "ct3" / "config.yaml").read_text()
    r = h(env, "profile", "delete", "ct3", "-y")
    assert r.returncode == 0 and not (env["home"] / "profiles" / "ct3").exists()
