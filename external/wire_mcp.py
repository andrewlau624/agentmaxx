#!/usr/bin/env python3
"""Wire an MCP server entry into every detected provider's config.

Usage: python3 wire_mcp.py NAME COMMAND [ARGS...]

Idempotent per host: existing identical entries are left alone, and each
config file is backed up before its first modification.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def backup(path: Path) -> None:
    marker = path.with_name(path.name + ".agentmaxx.bak")
    if path.exists() and not marker.exists():
        marker.write_bytes(path.read_bytes())


def strip_jsonc(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"^\s*//.*$", "", text, flags=re.M)


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: wire_mcp.py NAME COMMAND [ARGS...]")
        return 1
    name, command, args = sys.argv[1], sys.argv[2], sys.argv[3:]

    # Claude Code: ~/.claude.json -> mcpServers
    try:
        path = Path.home() / ".claude.json"
        data = json.loads(path.read_text()) if path.exists() else {}
        servers = data.setdefault("mcpServers", {})
        if servers.get(name) != {"command": command, "args": args}:
            backup(path)
            servers[name] = {"command": command, "args": args}
            path.write_text(json.dumps(data, indent=2))
        print(f"mcp   claude: {name}")
    except Exception as error:
        print(f"warn  claude wiring failed: {error}")

    # Codex: ~/.codex/config.toml -> [mcp_servers.NAME]
    try:
        path = Path.home() / ".codex" / "config.toml"
        text = path.read_text() if path.exists() else ""
        if f"[mcp_servers.{name}]" not in text:
            backup(path)
            block = (
                f"\n[mcp_servers.{name}]\n"
                f'command = "{command}"\n'
                f"args = {json.dumps(args)}\n"
            )
            path.write_text(text.rstrip("\n") + "\n" + block.lstrip("\n"))
        print(f"mcp   codex: {name}")
    except Exception as error:
        print(f"warn  codex wiring failed: {error}")

    # OpenCode: ~/.config/opencode/opencode.jsonc -> mcp
    try:
        path = Path.home() / ".config" / "opencode" / "opencode.jsonc"
        data = {}
        if path.exists():
            data = json.loads(strip_jsonc(path.read_text()))
        servers = data.setdefault("mcp", {})
        wanted = {
            "type": "local",
            "command": [command, *args],
            "enabled": True,
        }
        if servers.get(name) != wanted:
            backup(path)
            servers[name] = wanted
            path.write_text(json.dumps(data, indent=2))
        print(f"mcp   opencode: {name}")
    except Exception as error:
        print(f"warn  opencode wiring failed: {error}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
