#!/usr/bin/env python3
"""Install and wire third-party agent tools listed in external/tools.json.

Each entry names a binary to check for, one or more install methods keyed by
the package manager that provides them (first available wins), and optional
wire commands that connect the tool to installed agents.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent / "tools.json"
REPO_ROOT = MANIFEST.parent.parent


def run(cmd: list[str]) -> bool:
    print(f"run   {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        print(f"error {' '.join(cmd)} exited {result.returncode}")
        return False
    return True


def install_entry(entry: dict) -> bool:
    name = entry["name"]

    if shutil.which(entry["check"]):
        print(f"skip  {name}: already installed")
    else:
        methods = entry.get("install", {})
        for manager, cmd in methods.items():
            if shutil.which(manager):
                if not run(cmd):
                    return False
                break
        else:
            print(
                f"error {name}: no supported package manager found "
                f"(tried: {', '.join(methods)})"
            )
            return False

    for cmd in entry.get("wire", []):
        if shutil.which(cmd[0]) and not run(cmd):
            return False

    return True


def main() -> int:
    entries = json.loads(MANIFEST.read_text())
    failed = [e["name"] for e in entries if not install_entry(e)]

    if failed:
        print(f"external tools failed: {', '.join(failed)}")
        return 1

    print("external tools complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
