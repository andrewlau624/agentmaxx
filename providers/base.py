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

    # Whether this provider auto-discovers a personal, uncommitted rules file
    # inside a repo (local_rules_filename). False means install_repo() would
    # create a file the agent never reads; the CLI skips init for such
    # providers.
    supports_local_rules: bool = True

    def __init__(self, source_root: Path):
        self.source_root = source_root

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
    def global_rules_filename(self) -> str:
        """This provider's machine-wide rules file, inside `global_root`.

        Not committed anywhere, so `install` owns it the same way it owns
        the tools tree.
        """

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
        """Install the contract, skills, and tools machine-wide.

        Re-run after any change to `templates/`, `tools/`, or `skills/`: all
        three are derived from this repo, so install always overwrites. Every
        repo on the machine picks the new version up without further setup —
        `init` is only needed to scope the contract to a single repo.
        """
        self._inject_rules(self.global_root / self.global_rules_filename)
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
            # The markers delimit the only part of this file agentmaxx owns,
            # so refresh it in place. Anything outside them is the user's and
            # survives untouched. A lambda replacement keeps re.sub from
            # interpreting backslashes in the contract as group references.
            updated = re.sub(
                f"{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)}\n?",
                lambda _: block,
                existing,
                flags=re.DOTALL,
            )
        elif existing.strip():
            updated = existing.rstrip("\n") + "\n\n" + block
        else:
            updated = block

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(updated)

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
        # This directory is owned entirely by agentmaxx, so clearing it is
        # what makes a deleted tool actually disappear from the install.
        shutil.rmtree(self.tools_root, ignore_errors=True)

        self._copy_directory(
            self.source_root / "tools",
            self.tools_root,
        )

    def _copy(self, source: Path, destination: Path) -> None:
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