#!/usr/bin/env python3
"""Prune unused gstack skills from the local skill trees.

Every installed skill's description rides in every session's system prompt,
so dead skills are a permanent per-request tax. Deletes any SKILL.md whose
frontmatter name is not in KEEP, then removes directories left empty.
Re-runnable: gstack upgrades restore deleted skills, so re-run after updates
(make prune).
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

KEEP = {
    # debugging, shipping, session handoff, self-upgrade, second opinions,
    # gateway routing toggles
    "investigate",
    "ship",
    "context-save",
    "context-restore",
    "gstack-upgrade",
    "claude",
    "codex",
    "turbo",
    "nerfguard-routing-on",
    "nerfguard-routing-off",
    "nerfguard-bypass",
}

ROOTS = [
    Path.home() / ".agents" / "skills" / "gstack",
    Path.home() / ".claude" / "skills" / "gstack",
    # gstack's installer also scatters copies at the top level of both trees;
    # the (gstack) body marker below keeps this from touching anything else.
    Path.home() / ".agents" / "skills",
    Path.home() / ".claude" / "skills",
]

NAME_RE = re.compile(r"^name:\s*(\S+)", re.MULTILINE)


def skill_name(path: Path) -> str | None:
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return None
    match = NAME_RE.search(text[:2000])
    if not match:
        return None
    # Only touch skills gstack owns: every gstack description carries this
    # provenance tag, so personal/provider-native skills are never candidates.
    if "(gstack)" not in text[:4000]:
        return None
    return match.group(1).strip("'\"")


def main() -> int:
    removed, kept = 0, 0
    touched_dirs: set[Path] = set()

    for root in ROOTS:
        if not root.is_dir():
            continue
        for skill_file in sorted(root.rglob("SKILL.md")):
            name = skill_name(skill_file)
            if name is None or name in KEEP:
                kept += 1
                continue
            touched_dirs.add(skill_file.parent)
            skill_file.unlink()
            removed += 1

    # Remove directories that only existed to hold deleted skills.
    for directory in sorted(touched_dirs, key=lambda p: -len(p.parts)):
        current = directory
        while current != current.parent and current.name != ".git":
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    print(f"removed {removed} skills, kept {kept}")
    print(f"re-run after gstack upgrades: make prune")
    return 0


if __name__ == "__main__":
    sys.exit(main())
