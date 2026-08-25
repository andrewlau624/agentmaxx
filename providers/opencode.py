from __future__ import annotations

import os
import shutil
from pathlib import Path

from .base import Provider


class OpenCodeProvider(Provider):
    name = "opencode"
    supports_local_rules = False

    @classmethod
    def is_installed(cls) -> bool:
        return shutil.which("opencode") is not None

    @property
    def global_root(self) -> Path:
        # Same resolution order opencode itself uses.
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        config_root = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
        return config_root / "opencode"

    @property
    def global_rules_filename(self) -> str:
        return "AGENTS.md"

    @property
    def local_rules_filename(self) -> str:
        # opencode has no auto-discovered per-repo personal rules file; custom
        # instruction files require entries in a committed opencode.json, which
        # init must not touch. Guarded by supports_local_rules = False.
        raise NotImplementedError(
            "opencode has no per-repo personal rules file; "
            "global install covers every repo"
        )

    def install_global(self) -> None:
        # opencode stops reading ~/.claude/CLAUDE.md once this global AGENTS.md
        # exists (first matching global file wins), so flag anything the user
        # kept there beyond the agentmaxx block.
        rules_path = self.global_root / self.global_rules_filename
        rules_existed = rules_path.exists()
        super().install_global()
        claude_global = Path.home() / ".claude" / "CLAUDE.md"
        if not rules_existed and claude_global.exists():
            print(
                f"note  {rules_path} created: opencode now reads it instead of "
                f"{claude_global}; move over any non-agentmaxx global rules "
                "you relied on"
            )

    def install_skills(self) -> None:
        # opencode discovers ~/.claude/skills natively and skill names must be
        # unique across discovery locations, so only copy skills the Claude
        # install does not already provide.
        claude_skills = Path.home() / ".claude" / "skills"
        source_root = self.source_root / "skills"

        if not source_root.exists():
            return

        for skill_dir in source_root.iterdir():
            if not skill_dir.is_dir():
                continue

            if (claude_skills / skill_dir.name / "SKILL.md").exists():
                continue

            self._copy_directory(
                skill_dir,
                self.global_root / "skills" / skill_dir.name,
            )
