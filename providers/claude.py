from __future__ import annotations

import shutil
from pathlib import Path

from .base import Provider


class ClaudeProvider(Provider):
    name = "claude"

    @classmethod
    def is_installed(cls) -> bool:
        return shutil.which("claude") is not None

    @property
    def global_root(self) -> Path:
        return Path.home() / ".claude"

    @property
    def global_rules_filename(self) -> str:
        return "CLAUDE.md"

    @property
    def local_rules_filename(self) -> str:
        return "CLAUDE.local.md"