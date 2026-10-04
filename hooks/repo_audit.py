#!/usr/bin/env python3
"""List what a repository's Claude Code files can run or redirect, before you trust it.

    python3 repo_audit.py [path]          # report; exit 1 when anything runs code
    python3 repo_audit.py hook            # SessionStart: warn once per repo state

Checks .claude/settings.json, .claude/settings.local.json, .mcp.json, project
skills, commands and agents, and CLAUDE.md imports. Every check maps to a row in
evals/security-sources.md Part B, which says what each key does and whether it
applies before the folder trust dialog. A clone you didn't write is the case
this is for; your own repos will list your own hooks.

In hook mode it shows a warning (systemMessage) the first time a repo's set of
findings is seen, and stays quiet until that set changes. By SessionStart the
project's own hooks may already have run (Part B, B1/B2), so the CLI before
opening a clone is the stronger use. Disable the hook with AGENTMAXX_REPO_AUDIT=0.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

STATE = Path(os.environ.get("AGENTMAXX_HOME", os.path.expanduser("~/.local/share/agentmaxx"))) / "repo-audit"
SETTINGS_KEYS = {  # key: (Part B id, what it does)
    "env": ("B4", "sets environment variables"),
    "apiKeyHelper": ("B5", "runs a command for the API key"),
    "awsAuthRefresh": ("B6", "runs a command for AWS credentials"),
    "awsCredentialExport": ("B6", "runs a command for AWS credentials"),
    "otelHeadersHelper": ("B6", "runs a command for telemetry headers"),
    "statusLine": ("B7", "runs a command for the status line"),
    "fileSuggestion": ("B7", "runs a command for @ completion"),
    "enableAllProjectMcpServers": ("B8", "approves every .mcp.json server"),
    "enabledMcpjsonServers": ("B8", "approves named .mcp.json servers"),
    "extraKnownMarketplaces": ("B17", "registers plugin marketplaces"),
    "enabledPlugins": ("B17", "enables plugins"),
}
RISKY_ENV = re.compile(r"^(ANTHROPIC_BASE_URL|ANTHROPIC_API_KEY|ANTHROPIC_AUTH_TOKEN|.*_PROXY|NODE_OPTIONS|PYTHONSTARTUP|LD_PRELOAD|DYLD_.*)$", re.I)
SHELL_INJECT = re.compile(r"(^|\s)!`[^`\n]+`", re.M)
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---", re.S)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return None


def settings_findings(path: Path, rel: str) -> list[tuple[str, str]]:
    data = load_json(path)
    if not isinstance(data, dict):
        return []
    out = []
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups if isinstance(groups, list) else []:
            for h in (group or {}).get("hooks", []):
                out.append(("B2" if event == "SessionStart" else "B1", f"{rel}: {event} hook runs `{str(h.get('command', h.get('url', '?')))[:80]}`"))
    if data.get("disableAllHooks") is False:
        out.append(("B3", f"{rel}: sets disableAllHooks false, which overrides yours"))
    for key, (bid, what) in SETTINGS_KEYS.items():
        if key not in data:
            continue
        if key == "env":
            risky = [k for k in data["env"] if RISKY_ENV.match(k)]
            if risky:
                out.append((bid, f"{rel}: env {what}, including {', '.join(risky)}"))
            continue
        out.append((bid, f"{rel}: {key} {what}"))
    perms = data.get("permissions") or {}
    if perms.get("allow") or perms.get("additionalDirectories"):
        out.append(("B12", f"{rel}: pre-approves {len(perms.get('allow') or [])} tool rules"
                    + (f", widens access to {perms['additionalDirectories']}" if perms.get("additionalDirectories") else "")))
    return out


def audit(root: Path) -> list[tuple[str, str]]:
    out = []
    for rel in (".claude/settings.json", ".claude/settings.local.json"):
        out += settings_findings(root / rel, rel)
    servers = (load_json(root / ".mcp.json") or {}).get("mcpServers") or {}
    for name, s in servers.items():
        if not isinstance(s, dict):
            continue
        if s.get("command"):
            out.append(("B10", f".mcp.json: server {name} starts `{' '.join([s['command'], *map(str, s.get('args', []))])[:80]}`"))
        if s.get("headersHelper"):
            out.append(("B11", f".mcp.json: server {name} runs headersHelper `{str(s['headersHelper'])[:60]}`"))
    for kind in ("skills", "commands", "agents"):
        base = root / ".claude" / kind
        for f in sorted(base.rglob("*.md")) if base.is_dir() else []:
            rel, text = str(f.relative_to(root)), f.read_text(errors="ignore")
            if kind != "agents" and SHELL_INJECT.search(text):
                out.append(("B13", f"{rel}: runs !`{SHELL_INJECT.search(text).group(0).strip()[2:-1][:60]}` when invoked"))
            fm = FRONTMATTER.search(text)
            head = fm.group(1) if fm else ""
            if kind == "skills" and re.search(r"^allowed-tools:", head, re.M):
                out.append(("B14", f"{rel}: pre-approves tools ({re.search(r'^allowed-tools:(.*)$', head, re.M).group(1).strip()[:60]})"))
            if re.search(r"^hooks:", head, re.M):
                out.append(("B15" if kind == "skills" else "B16", f"{rel}: registers hooks"))
            if kind == "agents" and re.search(r"^mcpServers:", head, re.M):
                out.append(("B16", f"{rel}: starts its own MCP servers"))
    for name in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"):
        f = root / name
        if f.is_file():
            for imp in re.findall(r"(?:^|\s)@((?:~|/|\.\.)[^\s]+)", f.read_text(errors="ignore")):
                out.append(("B18", f"{name}: imports {imp} from outside the repo"))
    return out


def report(findings: list[tuple[str, str]]) -> str:
    return "\n".join(f"  [{bid}] {line}" for bid, line in findings)


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "hook":
        if os.environ.get("AGENTMAXX_REPO_AUDIT") == "0":
            return 0
        try:
            event = json.load(sys.stdin)
        except json.JSONDecodeError:
            return 0
        root = Path(event.get("cwd") or ".")
        findings = audit(root)
        if not findings:
            return 0
        STATE.mkdir(parents=True, exist_ok=True)
        mark = STATE / hashlib.sha1(f"{root.resolve()}\n{findings}".encode()).hexdigest()
        if mark.exists():
            return 0
        mark.touch()
        json.dump({"systemMessage": f"agentmaxx repo audit: {root.resolve().name} has Claude Code files that run code "
                   f"or change credentials (shown once until they change):\n{report(findings)}"}, sys.stdout)
        return 0
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    findings = audit(root)
    if not findings:
        print(f"{root}: no project hooks, helpers, MCP servers, skill commands or external imports")
        return 0
    print(f"{root}: {len(findings)} findings (ids are rows in evals/security-sources.md Part B)\n{report(findings)}")
    print("\nTo open it without these: claude --setting-sources user --strict-mcp-config, "
          "or --settings '{\"disableAllHooks\": true}' (S16, S18).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
