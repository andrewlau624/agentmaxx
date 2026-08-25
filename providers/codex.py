from __future__ import annotations

import shutil
from pathlib import Path

from .base import Provider


class CodexProvider(Provider):
    name = "codex"

    @classmethod
    def is_installed(cls) -> bool:
        return shutil.which("codex") is not None or (Path.home() / ".codex").is_dir()

    @property
    def global_root(self) -> Path:
        return Path.home() / ".codex"

    @property
    def global_rules_filename(self) -> str:
        return "AGENTS.md"

    @property
    def local_rules_filename(self) -> str:
        return "AGENTS.override.md"

    def install_mcp(self) -> None:
        """Register agentmaxx tools in Codex's TOML MCP config."""
        config_path = Path.home() / ".codex" / "config.toml"
        server_path = self.source_root / "mcp" / "better_mcp.py"
        block = (
            "\n# added by agentmaxx\n"
            "[mcp_servers.agentmaxx]\n"
            'command = "python3"\n'
            f'args = ["{server_path}"]\n'
        )

        text = config_path.read_text() if config_path.exists() else ""
        if "mcp_servers.agentmaxx" in text:
            return

        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(text.rstrip("\n") + "\n" + block.lstrip("\n"))
        print(f"mcp   {config_path} -> agentmaxx")

        try:
            import tomllib

            tomllib.loads(config_path.read_text())
        except ImportError:
            pass
        except Exception as error:
            print(f"warn  {config_path} failed TOML validation: {error}")