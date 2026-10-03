#!/usr/bin/env python3
"""PreToolUse hook: deny destructive or exfiltrating actions with a reason.

Permission deny rules match command prefixes, so `/bin/rm -rf ~`, `sh -c
'rm -rf ~'` and `git -C . push --force` slip through them. This hook
tokenizes each shell segment and checks what it does. It is a guardrail, not
a sandbox: pair it with Claude Code's sandbox for a real boundary.

A deny returns permissionDecision "deny" plus a reason, so the model can
pick a safer route instead of failing blind.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

SECRET_FILE = re.compile(
    r"(^|/)(\.env(\.[\w.-]+)?|id_(rsa|ed25519|ecdsa)|[^/]*\.pem|[^/]*\.p12|\.netrc|\.npmrc|\.pypirc|credentials(\.json)?)$"
)
# ~/.ssh is covered by the id_* key names above; its config and known_hosts aren't secrets.
SECRET_DIR = re.compile(r"(^|/)(\.aws|\.gnupg|\.config/gcloud|\.kube)(/|$)")
SAFE_SECRET = re.compile(r"\.env\.(example|sample|template|dist)$")
SECRET_VALUE = re.compile(
    r"(AKIA[0-9A-Z]{16}|sk-ant-[\w-]{20,}|sk-[A-Za-z0-9]{32,}|ghp_[A-Za-z0-9]{36}|github_pat_\w{40,}|"
    r"xox[baprs]-[\w-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)
PROTECTED_BRANCH = {"main", "master", "production", "prod", "release"}
# Solo repos push to main all day; blocking that is a tax, not safety. Opt in per team.
PROTECT_MAIN = os.environ.get("AGENTMAXX_GUARD_PROTECT_MAIN") == "1"
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)(?:^|\n)\s*\2\s*(?:\n|$)", re.DOTALL)
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\n")
WRAPPERS = {"sudo", "env", "nohup", "time", "command", "exec", "xargs", "nice"}
# Commands that can take a secrets path without printing its contents.
NON_PRINTING = {
    "ls", "stat", "test", "[", "touch", "chmod", "chown", "rm", "mv", "cp", "ln", "rsync", "wc", "file",
    "source", ".", "realpath", "dirname", "basename", "echo", "printf", "mkdir",
}
ONE_LINER = re.compile(r"""\b(?:python[\d.]*|node|ruby|perl|php|deno|bun)\s+(?:-\w+\s+)*(?:-c|-e|-r|-E|--eval)\s+(['"])(.*?)\1""", re.S)
PRINTED_READ = re.compile(r"\b(print|console\.log|puts|p|sys\.stdout\.write|process\.stdout\.write)\s*\(?\s*[^;\n]{0,60}"
                          r"\b(open|readFileSync|read_text|read_bytes|File\.read|readFile)\s*\(")
QUOTED = re.compile(r"""['"]([^'"\n]{1,200})['"]""")
ENV_DUMP = re.compile(r"\b(print|pprint|json\.dumps|console\.log|JSON\.stringify|p|puts)\s*\(?\s*(dict\()?(os\.environ|process\.env|ENV)\s*\)?\s*\)?\s*(;|$|\n)")
GIT_HOOKS = re.compile(r"(^|/)\.git/hooks/|\.husky/")
# git subcommands that print file contents; the rest (commit -m "...env...", add, rm) don't.
GIT_PRINTS = {"show", "diff", "log", "cat-file", "blame", "grep"}


def _is_secret_path(path: str) -> bool:
    path = os.path.expanduser(path.strip("'\""))
    return bool(SECRET_FILE.search(path) or SECRET_DIR.search(path)) and not SAFE_SECRET.search(path)


def _argv(segment: str) -> list[str]:
    try:
        argv = shlex.split(segment, posix=True)
    except ValueError:
        argv = segment.split()
    while argv and (argv[0] in WRAPPERS or re.match(r"^\w+=", argv[0])):
        argv = argv[1:]
    if argv:
        argv[0] = os.path.basename(argv[0])
    return argv


def _rm_target_dangerous(target: str, assigned: set[str]) -> bool:
    t = target.rstrip("/")
    var = re.fullmatch(r"\$\{?(\w+)\}?(/\*?)?", target.rstrip("/") if target.endswith("/") else target)
    if var and var.group(1) not in assigned:
        return True  # rm -rf $DIR, $DIR/ or $DIR/* with DIR unset hits cwd or /
    if t in ("", "~", "$HOME", "/", ".", "..", "*", "/*", "~/*"):
        return True
    return t.startswith(("/Users", "/home", "/etc", "/usr", "/var", "/System")) and t.count("/") <= 2


def check_command(command: str) -> str | None:
    # Heredoc bodies are file contents, not commands; scanning them flags
    # every script that merely mentions .env or curl | sh.
    command = HEREDOC.sub(lambda m: f"<<{m.group(2)}\n", command)
    assigned = set(re.findall(r"(?:^|[\s;&|])(\w+)=", command))
    # VAR=$(grep KEY .env) captures the value without printing it: the safe pattern.
    command = re.sub(r"\b(\w+)=\$\((?:[^()]|\([^()]*\))*\)", r"\1=CAPTURED", command)
    lowered = command.lower()
    if re.search(r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z|da)?sh\b", lowered):
        return "piping a download straight into a shell runs unreviewed code; download, inspect, then run"
    for inner in re.findall(r"\b(?:ba|z)?sh\s+-c\s+(['\"])(.+?)\1", command):
        reason = check_command(inner[1])
        if reason:
            return reason
    if re.search(r">>?\s*\S*\.git/hooks/\S+|\b(cp|mv|ln|install|tee)\b[^|;&]*\.git/hooks/", command):
        return "git hooks run on every commit and survive the session; show the user the hook and let them install it"
    # one-liners can hold ; and |, so check them before splitting into segments
    for _, code in ONE_LINER.findall(command):
        # reading .env into a client config is fine; printing what was read is the leak
        if any(_is_secret_path(q) for q in QUOTED.findall(code)) and PRINTED_READ.search(code):
            return "this one-liner reads a secrets file into the transcript; reference the variable name instead"
        if ENV_DUMP.search(code):
            return "dumping the environment would leak secrets into the transcript; print the one variable you need"
    for segment in SEGMENT_SPLIT.split(command):
        for piece in segment.split("|"):
            argv = _argv(piece)
            if not argv:
                continue
            cmd, args = argv[0], argv[1:]
            flags = "".join(a.lstrip("-") for a in args if a.startswith("-") and not a.startswith("--"))
            if cmd == "rm" and "r" in flags.lower() and "f" in flags:
                targets = [a for a in args if not a.startswith("-")]
                if any(_rm_target_dangerous(t, assigned) for t in targets):
                    return f"rm -rf on {' '.join(targets)} could delete far more than intended; name the exact path"
            if cmd == "git":
                sub = [a for a in args if not a.startswith("-")]
                if "-C" in args:
                    i = args.index("-C")
                    sub = [a for a in args[:i] + args[i + 2:] if not a.startswith("-")]
                if sub[:1] == ["push"]:
                    if any(a in ("--force", "-f") or a.startswith("--force=") for a in args) and "--force-with-lease" not in args:
                        return "force-push rewrites shared history; use --force-with-lease on a feature branch or ask the user"
                    refs = {r.split(":")[-1].removeprefix("refs/heads/") for r in sub[1:]}
                    if PROTECT_MAIN and refs & PROTECTED_BRANCH:
                        return "pushing directly to a protected branch; push a feature branch or ask the user first"
                if sub[:2] == ["reset", "--hard"] or (sub[:1] == ["reset"] and "--hard" in args):
                    return "git reset --hard discards uncommitted work; stash first or ask the user"
                if sub[:1] == ["clean"] and "f" in flags:
                    return "git clean -f deletes untracked files permanently; list them with -n first"
            # curl -d @.env / -F f=@.env / --data-binary @file upload a file's contents
            if cmd in ("curl", "wget", "http", "xh") and any(_is_secret_path(re.sub(r"^[^@]*@", "", a)) for a in args if "@" in a):
                return "this request would send a secrets file to a remote host"
            if cmd == "git" and "config" in args and any(a.lower() == "core.hookspath" for a in args) and len(
                    [a for a in args if not a.startswith("-")]) > 2:
                return "changing core.hooksPath makes git run different code on every commit; ask the user first"
            counting = cmd in ("grep", "rg", "egrep") and any(a in ("-c", "-l", "-L", "-q", "--count", "--quiet") for a in args)
            git_quiet = cmd == "git" and not ({a for a in args if not a.startswith("-")} & GIT_PRINTS)
            if cmd not in NON_PRINTING and not counting and not git_quiet:
                if any(_is_secret_path(a.split("=", 1)[-1]) for a in args if not a.startswith("-") or "=" in a):
                    return "reading a secrets file would put credentials in the transcript; reference the variable name instead"
            if cmd in ("printenv", "env") and not args or (cmd == "set" and not args):
                return "dumping the environment would leak secrets into the transcript; print the one variable you need"
            if cmd in ("chmod",) and "777" in args and any(a in ("-R", "-r") for a in args):
                return "recursive chmod 777 makes everything world-writable"
            if cmd in ("dd", "mkfs", "diskutil") and any(a.startswith(("of=/dev", "/dev/")) or a == "eraseDisk" for a in args):
                return "writing to a raw device destroys data"
    return None


def check(tool: str, tool_input: dict) -> str | None:
    if tool == "Bash":
        return check_command(tool_input.get("command", ""))
    if tool == "Read":
        if _is_secret_path(tool_input.get("file_path", "")):
            return "reading a secrets file would put credentials in the transcript; reference the variable name instead"
    if tool in ("Write", "Edit", "MultiEdit"):
        text = tool_input.get("content") or tool_input.get("new_string") or ""
        for edit in tool_input.get("edits") or []:
            text += edit.get("new_string", "")
        path = tool_input.get("file_path", "")
        if GIT_HOOKS.search(path):
            return "git hooks run on every commit and survive the session; show the user the hook and let them install it"
        if SECRET_VALUE.search(text) and not _is_secret_path(path):
            return "this write contains what looks like a live credential; load it from the environment instead"
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    reason = check(event.get("tool_name", ""), event.get("tool_input") or {})
    if reason:
        json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                          "permissionDecisionReason": f"agentmaxx guard: {reason}"}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
