#!/usr/bin/env python3
"""Minimal stdio MCP server (stdlib only) used as a probe/contract fixture.

Tools: ``echo`` (returns its ``text`` argument) and ``env`` (returns the value of the
``ECHO_TOKEN`` env var, so tests can observe ``${VAR}`` expansion without printing it
anywhere else). Speaks newline-delimited JSON-RPC 2.0 as the MCP stdio transport does.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

TOOLS = [
    {
        "name": "echo",
        "description": "Echo the given text",
        "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}},
    },
    {
        "name": "env",
        "description": "Report whether ECHO_TOKEN is set (and its length)",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def reply(id_: object, result: object) -> None:
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": id_, "result": result}) + "\n")
    sys.stdout.flush()


def record_env() -> None:
    """If ECHO_RECORD names a file, write what this process saw for ECHO_TOKEN:
    ``unset``, a literal ``${...}`` placeholder marker, or the sha256 of the value."""
    path = os.environ.get("ECHO_RECORD")
    if not path:
        return
    tok = os.environ.get("ECHO_TOKEN")
    if tok is None:
        state = "unset"
    elif tok.startswith("${"):
        state = "literal"
    else:
        state = "sha256:" + hashlib.sha256(tok.encode()).hexdigest()
    with open(path, "w") as fh:
        fh.write(state)


def main() -> None:
    if os.environ.get("ECHO_FAIL"):
        sys.exit(3)
    record_env()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        method, id_ = msg.get("method"), msg.get("id")
        if id_ is None:
            continue  # notification
        if method == "initialize":
            reply(
                id_,
                {
                    "protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"),
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "echo", "version": "1.0.0"},
                },
            )
        elif method == "tools/list":
            reply(id_, {"tools": TOOLS})
        elif method == "tools/call":
            p = msg.get("params", {})
            if p.get("name") == "env":
                tok = os.environ.get("ECHO_TOKEN")
                text = f"set:{len(tok)}" if tok else "unset"
            else:
                text = str(p.get("arguments", {}).get("text", ""))
            reply(id_, {"content": [{"type": "text", "text": text}], "isError": False})
        elif method == "ping":
            reply(id_, {})
        else:
            sys.stdout.write(
                json.dumps(
                    {"jsonrpc": "2.0", "id": id_, "error": {"code": -32601, "message": "no method"}}
                )
                + "\n"
            )
            sys.stdout.flush()


if __name__ == "__main__":
    main()
