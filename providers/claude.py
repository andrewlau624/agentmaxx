from __future__ import annotations

import json
import shutil
from pathlib import Path

from .base import Provider


class ClaudeProvider(Provider):
    name = "claude"

    @classmethod
    def is_installed(cls) -> bool:
        # Config dir counts as installed: a provider usable without its binary
        # on this shell's PATH (e.g. opencode under ~/.opencode/bin) must not
        # be silently skipped by `make install`.
        return shutil.which("claude") is not None or (Path.home() / ".claude").is_dir()

    @property
    def global_root(self) -> Path:
        return Path.home() / ".claude"

    @property
    def global_rules_filename(self) -> str:
        return "CLAUDE.md"

    @property
    def local_rules_filename(self) -> str:
        return "CLAUDE.local.md"

    def install_mcp(self) -> None:
        """Register agentmaxx tools in Claude Code's user-scope MCP config."""
        config_path = Path.home() / ".claude.json"
        entry = {
            "command": "python3",
            "args": [str(self.source_root / "mcp" / "better_mcp.py")],
        }

        try:
            data = (
                json.loads(config_path.read_text())
                if config_path.exists()
                else {}
            )
        except json.JSONDecodeError:
            print(f"skip  mcp: {config_path} is not valid JSON")
            return

        servers = data.setdefault("mcpServers", {})
        if servers.get("agentmaxx") == entry:
            return

        if config_path.exists():
            backup = config_path.parent / (config_path.name + ".agentmaxx.bak")
            backup.write_bytes(config_path.read_bytes())

        servers["agentmaxx"] = entry
        config_path.write_text(json.dumps(data, indent=2))
        print(f"mcp   {config_path} -> agentmaxx")