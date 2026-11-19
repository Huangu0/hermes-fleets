#!/usr/bin/env python3
"""Cheap secret / forbidden-file gate for a PUBLIC repository.

Modes:
  --staged   files staged for commit (pre-commit hook)
  --all      every tracked + untracked-not-ignored file
  --history  every blob reachable from any ref (full history scan)

Checks: forbidden paths (.env, keys, sqlite DBs, venvs, caches), detect-secrets
default plugins, and a few extra patterns (JWTs, credentials in URLs, private keys).
Lines containing ``pragma: allowlist secret`` are skipped.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FORBIDDEN = [
    ".env",
    "*/.env",
    ".env.*",
    "*/.env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "*/id_rsa*",
    "id_ed25519*",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.db-wal",
    "*.db-shm",
    ".venv/*",
    "*/.venv/*",
    "venv/*",
    "*/site-packages/*",
    ".cache/*",
    "*/__pycache__/*",
    "*.pyc",
    "ov.conf",
    "*/ov.conf",
    "fernet.key",
]
ALLOWED = [".env.example", "*/.env.example"]

EXTRA = [
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("url-credentials", re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@'\"]{3,}:[^@\s'\"]{6,}@[^\s'\"]+")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b")),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
]
ALLOW_MARK = "pragma: allowlist secret"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def forbidden(path: str) -> bool:
    if any(fnmatch.fnmatch(path, a) for a in ALLOWED):
        return False
    return any(fnmatch.fnmatch(path, f) for f in FORBIDDEN)


def scan_text(name: str, text: str) -> list[str]:
    hits: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARK in line:
            continue
        for label, rx in EXTRA:
            if rx.search(line):
                hits.append(f"{name}:{i}: {label}")
    return hits


def detect_secrets_scan(files: dict[str, str]) -> list[str]:
    try:
        from detect_secrets import SecretsCollection
        from detect_secrets.settings import default_settings
    except ImportError:  # pragma: no cover
        print("warning: detect-secrets not installed; extra patterns only", file=sys.stderr)
        return []
    hits: list[str] = []
    with tempfile.TemporaryDirectory() as td, default_settings():
        mapping: dict[str, str] = {}
        for i, (name, text) in enumerate(files.items()):
            p = Path(td) / f"f{i}{Path(name).suffix}"
            p.write_text(text)
            mapping[str(p)] = name
        coll = SecretsCollection()
        for p in mapping:
            coll.scan_file(p)
        for fname, secret in coll:
            name = mapping.get(fname, fname)
            line = files[name].splitlines()[secret.line_number - 1] if secret.line_number else ""
            if ALLOW_MARK in line:
                continue
            hits.append(f"{name}:{secret.line_number}: detect-secrets {secret.type}")
    return hits


def read_worktree(paths: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in paths:
        fp = Path(p)
        if fp.is_file() and fp.stat().st_size < 2_000_000:
            try:
                out[p] = fp.read_text()
            except UnicodeDecodeError:
                continue
    return out


def history_blobs() -> dict[str, str]:
    out: dict[str, str] = {}
    seen: set[str] = set()
    for rev in git("rev-list", "--all").split():
        for row in git("ls-tree", "-r", rev).splitlines():
            meta, path = row.split("\t", 1)
            _, kind, sha = meta.split()
            if kind != "blob" or sha in seen:
                continue
            seen.add(sha)
            if forbidden(path):
                out[f"FORBIDDEN@{rev[:8]}:{path}"] = ""
                continue
            data = subprocess.run(["git", "cat-file", "-p", sha], capture_output=True).stdout
            if len(data) > 2_000_000:
                continue
            try:
                out[f"{rev[:8]}:{path}"] = data.decode()
            except UnicodeDecodeError:
                continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged", action="store_true")
    g.add_argument("--all", action="store_true")
    g.add_argument("--history", action="store_true")
    a = ap.parse_args()

    problems: list[str] = []
    if a.history:
        files = history_blobs()
        problems += [f"{k}: forbidden file in history" for k in files if k.startswith("FORBIDDEN@")]
        files = {k: v for k, v in files.items() if not k.startswith("FORBIDDEN@")}
    else:
        if a.staged:
            paths = git("diff", "--cached", "--name-only", "--diff-filter=ACMR").split("\n")
        else:
            paths = git("ls-files", "--cached", "--others", "--exclude-standard").split("\n")
        paths = [p for p in paths if p]
        problems += [f"{p}: forbidden file (secrets/db/venv/cache)" for p in paths if forbidden(p)]
        files = read_worktree([p for p in paths if not forbidden(p)])

    for name, text in files.items():
        problems += scan_text(name, text)
    problems += detect_secrets_scan(files)

    if problems:
        print("secret scan FAILED:", file=sys.stderr)
        for p in sorted(set(problems)):
            print("  " + p, file=sys.stderr)
        return 1
    print(f"secret scan ok ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
