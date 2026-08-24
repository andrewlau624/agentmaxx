from __future__ import annotations

import shutil
from pathlib import Path

from .base import Provider


class CodexProvider(Provider):
    name = "codex"

    @classmethod
    def is_installed(cls) -> bool:
        return shutil.which("codex") is not None

    @property
    def global_root(self) -> Path:
        return Path.home() / ".codex"

    @property
    def global_rules_filename(self) -> str:
        return "AGENTS.md"

    @property
    def local_rules_filename(self) -> str:
        return "AGENTS.override.md"