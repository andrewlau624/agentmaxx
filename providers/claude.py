from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .base import Provider

# Measured on the bench in evals/bench and on real transcripts; see
# evals/RESULTS.md. setdefault semantics: a value the user already set wins.
SETTINGS_ENV = {
    # Defer tool schemas. Claude Code silently turns this off behind any
    # non-first-party ANTHROPIC_BASE_URL (proxies, routers): 63k -> 17k
    # prefix and -16% per task when forced back on.
    "ENABLE_TOOL_SEARCH": "true",
    # 1M-context models otherwise compact at ~967k, so median requests carry
    # 100k-270k tokens. Replaying real sessions: -25% of the bill at 300k.
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "300000",
}

# event -> (matcher, hook script, extra args, timeout seconds)
HOOKS = [
    ("PreToolUse", "Bash|Read|Write|Edit|MultiEdit", "guard.py", "", 10),
    ("PostToolUse", "Bash", "squeeze.py", "", 20),
    ("PostToolUse", "WebFetch|WebSearch|mcp__.*", "inject_scan.py", "", 10),
    ("SessionStart", None, "verify.py", "", 10),
    ("SessionStart", None, "repo_audit.py", " hook", 10),
    ("Stop", None, "verify.py", "", 180),
    ("SessionStart", None, "lessons.py", " hook session-start", 10),
    ("UserPromptSubmit", None, "lessons.py", " hook prompt", 10),
]
HOOK_MARKER = "/agentmaxx/hooks/"


class ClaudeProvider(Provider):
    name = "claude"

    @classmethod
    def is_installed(cls) -> bool:
        # Config dir counts as installed: a provider usable without its binary
        # on this shell's PATH (e.g. opencode under ~/.opencode/bin) must not
        # be silently skipped by `make install`.
        return shutil.which("claude") is not None or (Path.home() / ".claude").is_dir()

    @property
    def global_root(self) -> Path:
        return Path.home() / ".claude"

    @property
    def global_rules_filename(self) -> str:
        return "CLAUDE.md"

    @property
    def local_rules_filename(self) -> str:
        return "CLAUDE.local.md"

    def install_global(self) -> None:
        super().install_global()
        self.install_hooks()
        self.install_settings()

    @property
    def hooks_root(self) -> Path:
        return self.global_root / "agentmaxx" / "hooks"

    def install_hooks(self) -> None:
        shutil.rmtree(self.hooks_root, ignore_errors=True)
        self._copy_directory(self.source_root / "hooks", self.hooks_root)

    def install_settings(self) -> None:
        """Merge env defaults, hooks, and the statusline into settings.json.

        Owns only hook entries whose command runs from the agentmaxx hooks
        directory: those are replaced on every install, everything else in
        the file is left alone. A user-set env value or statusline wins.
        """
        path = self.global_root / "settings.json"
        try:
            data = json.loads(path.read_text()) if path.exists() else {}
        except json.JSONDecodeError:
            print(f"skip  settings: {path} is not valid JSON")
            return
        before = json.dumps(data, sort_keys=True)

        env = data.setdefault("env", {})
        for key, value in SETTINGS_ENV.items():
            env.setdefault(key, value)

        hooks = data.setdefault("hooks", {})
        for event in list(hooks):
            kept = []
            for group in hooks[event]:
                group = dict(group)
                group["hooks"] = [h for h in group.get("hooks", []) if HOOK_MARKER not in h.get("command", "")]
                if group["hooks"]:
                    kept.append(group)
            hooks[event] = kept
        for event, matcher, script, args, timeout in HOOKS:
            group = {"hooks": [{
                "type": "command",
                "command": f"python3 {self.hooks_root / script}{args}",
                "timeout": timeout,
            }]}
            if matcher:
                group = {"matcher": matcher, **group}
            hooks.setdefault(event, []).append(group)
        for event in [e for e, groups in hooks.items() if not groups]:
            del hooks[event]

        data.setdefault("statusLine", {
            "type": "command",
            "command": f"python3 {self.hooks_root / 'statusline.py'}",
            "padding": 0,
        })

        if json.dumps(data, sort_keys=True) == before:
            return
        if path.exists():
            backup = path.with_name(path.name + ".agentmaxx.bak")
            if not backup.exists():
                backup.write_bytes(path.read_bytes())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"settings {path}")

    def install_mcp(self) -> None:
        """Remove the agentmaxx MCP server from Claude Code unless opted in.

        Benchmarked: the model never called the better-* MCP tools (native
        Grep/Read/Edit cover them), and the server connecting after the first
        request changed the tool list, forcing a full prefix cache rewrite
        (+89% per task). Set AGENTMAXX_CLAUDE_MCP=1 to keep registering it.
        """
        config_path = Path.home() / ".claude.json"
        if os.environ.get("AGENTMAXX_CLAUDE_MCP") != "1":
            try:
                data = json.loads(config_path.read_text()) if config_path.exists() else {}
            except json.JSONDecodeError:
                return
            if data.get("mcpServers", {}).pop("agentmaxx", None) is not None:
                config_path.write_text(json.dumps(data, indent=2))
                print(f"mcp   {config_path} -> removed agentmaxx (see install_mcp docstring)")
            return
        entry = {
            "command": "python3",
            "args": [str(self.source_root / "mcp" / "better_mcp.py")],
        }

        try:
            data = (
                json.loads(config_path.read_text())
                if config_path.exists()
                else {}
            )
        except json.JSONDecodeError:
            print(f"skip  mcp: {config_path} is not valid JSON")
            return

        servers = data.setdefault("mcpServers", {})
        if servers.get("agentmaxx") == entry:
            return

        if config_path.exists():
            backup = config_path.parent / (config_path.name + ".agentmaxx.bak")
            backup.write_bytes(config_path.read_bytes())

        servers["agentmaxx"] = entry
        config_path.write_text(json.dumps(data, indent=2))
        print(f"mcp   {config_path} -> agentmaxx")