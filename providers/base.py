from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import re
import shutil


BLOCK_START = "<!-- agentmaxx:start -->"
BLOCK_END = "<!-- agentmaxx:end -->"


class Provider(ABC):
    name: str

    def __init__(self, source_root: Path, force: bool = False):
        self.source_root = source_root
        self.force = force

    @classmethod
    @abstractmethod
    def is_installed(cls) -> bool:
        pass

    @property
    @abstractmethod
    def global_root(self) -> Path:
        """Where this provider's global config lives, e.g. ~/.claude."""

    @property
    @abstractmethod
    def rules_filename(self) -> str:
        """The per-repo rules file this provider reads, e.g. CLAUDE.md."""

    def install_global(self) -> None:
        """Install skills and tools into this provider's global config.

        Run once, e.g. from `make install`. Every repo on the machine picks
        these up without further setup.
        """
        self.install_skills()
        self.install_tools()

    def install_repo(self, repo_root: Path) -> None:
        """Inject the output-contract template into one repo's rules file.

        Run from inside a project, e.g. `agentmaxx init`. Scoped to
        `repo_root` only — never touches global provider config.
        """
        self._inject_rules(repo_root / self.rules_filename)

    def _inject_rules(self, destination: Path) -> None:
        contract = (self.source_root / "templates" / "CLAUDE.md").read_text().rstrip("\n")
        block = f"{BLOCK_START}\n{contract}\n{BLOCK_END}\n"

        existing = destination.read_text() if destination.exists() else ""

        if BLOCK_START in existing:
            if not self.force:
                print(f"skip  {destination}")
                return
            existing = re.sub(
                f"{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)}\n?",
                "",
                existing,
                flags=re.DOTALL,
            )

        if existing.strip():
            destination.write_text(existing.rstrip("\n") + "\n\n" + block)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(block)

        print(f"copy  {destination}")

    def install_skills(self) -> None:
        self._copy_directory(
            self.source_root / "skills",
            self.global_root / "skills",
        )

    def install_tools(self) -> None:
        self._copy_directory(
            self.source_root / "tools",
            self.global_root / "agentmaxx" / "tools",
        )

    def _copy(self, source: Path, destination: Path) -> None:
        if destination.exists() and not self.force:
            print(f"skip  {destination}")
            return

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"copy  {destination}")

    def _copy_directory(
        self,
        source: Path,
        destination: Path,
    ) -> None:
        if not source.exists():
            return

        for path in source.rglob("*"):
            if not path.is_file():
                continue

            relative = path.relative_to(source)

            if any(
                part in {".git", "__pycache__"}
                for part in relative.parts
            ):
                continue

            self._copy(path, destination / relative)