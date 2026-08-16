from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import re
import shutil


BLOCK_START = "<!-- agentmaxx:start -->"
BLOCK_END = "<!-- agentmaxx:end -->"
TOOLS_ROOT_PLACEHOLDER = "{{TOOLS_ROOT}}"


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
    def local_rules_filename(self) -> str:
        """This provider's personal, uncommitted per-repo rules file.

        Deliberately not the shared file (CLAUDE.md / AGENTS.md): `init` is
        a personal opt-in and must not change what teammates get.
        """

    @property
    def tools_root(self) -> Path:
        """Where install_global() puts the tools for this provider."""
        return self.global_root / "agentmaxx" / "tools"

    def install_global(self) -> None:
        """Install skills and tools into this provider's global config.

        Run once, e.g. from `make install`. Every repo on the machine picks
        these up without further setup.
        """
        self.install_skills()
        self.install_tools()

    def install_repo(self, repo_root: Path) -> None:
        """Inject the output contract into one repo, for this user only.

        Writes the provider's personal rules file and excludes it via
        .git/info/exclude, which is per-clone and untracked. Never edits
        the shared rules file or .gitignore — both are committed, so
        changing them would push this opt-in onto everyone else.
        """
        self._inject_rules(repo_root / self.local_rules_filename)
        self._exclude_locally(repo_root, self.local_rules_filename)

    def _inject_rules(self, destination: Path) -> None:
        contract = (
            (self.source_root / "templates" / "CLAUDE.md")
            .read_text()
            .replace(TOOLS_ROOT_PLACEHOLDER, str(self.tools_root))
            .rstrip("\n")
        )
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

    def _exclude_locally(self, repo_root: Path, filename: str) -> None:
        """Ignore `filename` for this clone only, via .git/info/exclude."""
        git_dir = repo_root / ".git"

        if not git_dir.is_dir():
            return

        exclude_path = git_dir / "info" / "exclude"
        existing = (
            exclude_path.read_text()
            if exclude_path.exists()
            else ""
        )

        if filename in existing.split():
            return

        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        separator = "" if not existing or existing.endswith("\n") else "\n"
        exclude_path.write_text(f"{existing}{separator}{filename}\n")

        print(f"ignore  {exclude_path} ({filename})")

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