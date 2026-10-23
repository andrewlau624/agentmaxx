#!/usr/bin/env python3
"""agentmaxx doctor: find where this machine's Claude Code tokens go, and what to change.

Reads ~/.claude/projects transcripts (deduped per API response) and
~/.claude/settings.json. Read-only, unless --apply (which backs up first).

    python3 evals/doctor.py [--days N] [--apply | --dry-run]
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corrections  # noqa: E402
import residency  # noqa: E402

PROJECTS = Path.home() / ".claude" / "projects"
SETTINGS = Path.home() / ".claude" / "settings.json"
# Costs are $ per million tokens at each request's model price (residency.PRICES).
COMPACT_BUFFER = 33_000


def load_sessions(days: int) -> list[dict]:
    cutoff = time.time() - days * 86400
    sessions = []
    for path in PROJECTS.rglob("*.jsonl"):
        if path.stat().st_mtime >= cutoff and (s := residency.load(path)):
            s["results"] = [(at, name, size) for kind, at, *rest in s["events"] if kind == "result"
                            for name, _, size in [rest]]
            sessions.append(s)
    return sessions


def context_of(u: dict) -> int:
    return sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


def simulate_window(sessions: list[dict], window: int | None, summary: int = 12_000) -> float:
    total = 0.0
    for s in sessions:
        contexts = [context_of(u) for u in s["usage"]]
        offset, prefix = 0, contexts[0]
        for c, u in zip(contexts, s["usage"]):
            effective = c - offset
            if window and effective > window - COMPACT_BUFFER:
                total += effective * residency.read_rate(u) + summary * (5 + 1.25) * residency.price(u)[0]
                offset, effective = c - (prefix + summary), prefix + summary
            total += effective * residency.read_rate(u)
    return total


def simulate_ttl(sessions: list[dict], ttl: int) -> float:
    """Bill if every write used `ttl` seconds: a gap longer than the TTL turns the cached prefix into a rewrite."""
    price = 2.0 if ttl > 300 else 1.25
    total = 0.0
    for s in sessions:
        for i, u in enumerate(s["usage"]):
            read = u.get("cache_read_input_tokens", 0) or 0
            write = u.get("cache_creation_input_tokens", 0) or 0
            if i and read and s["times"][i] - s["times"][i - 1] > ttl:
                write, read = write + read, 0
            total += residency.request_cost({**u, "cache_creation_input_tokens": write, "cache_read_input_tokens": read}, price)
    return total


def pct(values: list[int], q: float) -> int:
    values = sorted(values)
    return values[int(q * (len(values) - 1))] if values else 0


def best_uniform_ttl(total: float, five_min: float, one_hour: float) -> tuple[str, float] | None:
    """(ttl, savings fraction) when a uniform switch beats the observed bill by >3%.

    Compares against what you actually paid, not against the other
    counterfactual: on a machine already mixed (main 1h, subagents 5m),
    neither uniform switch wins even though 1h beats 5m head-to-head.
    """
    ttl, cost = ("1h", one_hour) if one_hour < five_min else ("5m", five_min)
    return (ttl, (total - cost) / total) if (total - cost) / total > 0.03 else None


def installed_skills() -> set[str]:
    """Frontmatter names of every SKILL.md in the user skill trees."""
    names = set()
    for root in (Path.home() / ".agents" / "skills", Path.home() / ".claude" / "skills"):
        try:
            files = list(root.rglob("SKILL.md"))
        except OSError:
            continue
        for f in files:
            try:
                head = f.read_text(errors="ignore")[:2000]
            except OSError:
                continue
            m = re.search(r"^name:\s*(\S+)", head, re.M)
            if m:
                names.add(m.group(1).strip("'\""))
    return names


def compute_plan(settings: dict, effective: dict, env_updates: dict[str, str]) -> dict:
    """Pure: what --apply would change. Never overwrites a value you set.

    `effective` is settings env overlaid with the real environment: a value
    already effective (however set) is a noop, and a shell value that would
    override the file is a conflict, not a write. Skill hides stay report-only:
    absence from 14d of transcripts also matches methodology skills the user
    wants auto-available, so that call needs a human.
    """
    plan: dict = {"env": []}
    cur_env = settings.get("env") or {}
    for k, v in env_updates.items():
        f, e = cur_env.get(k), effective.get(k)
        if e == v:
            status, shown = "noop", e
        elif f is not None and f != v:
            status, shown = "conflict", f
        elif e is not None:
            status, shown = "conflict", f"{e} (shell)"
        else:
            status, shown = "write", None
        plan["env"].append((k, v, shown, status))
    return plan


def apply_plan(path: Path, settings: dict, plan: dict) -> Path:
    """Write the writes only, backing up first. Returns the backup path."""
    backup = path.with_name(path.name + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
    backup.write_text(path.read_text() if path.exists() else "{}\n")
    writes = [e for e in plan["env"] if e[3] == "write"]
    if writes:
        env = dict(settings.get("env") or {})
        for k, v, _, _ in writes:
            env[k] = v
        settings["env"] = env
    path.write_text(json.dumps(settings, indent=2) + "\n")
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--apply", action="store_true",
                        help="write the env recommendations to settings.json (backup first, never overwrites your values)")
    parser.add_argument("--dry-run", action="store_true", help="show what --apply would change")
    args = parser.parse_args()

    sessions = load_sessions(args.days)
    if not sessions:
        print(f"no Claude Code sessions in the last {args.days}d")
        return 0
    settings = json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {}
    env = {**settings.get("env", {}), **{k: v for k, v in os.environ.items() if k.startswith(("ENABLE_", "CLAUDE_", "ANTHROPIC_"))}}

    tokens, weighted = Counter(), Counter()
    for s in sessions:
        for u in s["usage"]:
            tokens["input"] += u.get("input_tokens", 0) or 0
            hour = (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) or 0
            tokens["write1h"] += hour
            tokens["write"] += (u.get("cache_creation_input_tokens", 0) or 0) - hour
            tokens["read"] += u.get("cache_read_input_tokens", 0) or 0
            tokens["output"] += u.get("output_tokens", 0) or 0
            p, rd = residency.price(u)
            weighted["input"] += (u.get("input_tokens", 0) or 0) * p
            weighted["write"] += ((u.get("cache_creation_input_tokens", 0) or 0) - hour) * 1.25 * p
            weighted["write1h"] += hour * 2.0 * p
            weighted["read"] += (u.get("cache_read_input_tokens", 0) or 0) * rd * p
            weighted["output"] += (u.get("output_tokens", 0) or 0) * 5.0 * p
    total = sum(weighted.values())
    contexts = [context_of(u) for s in sessions for u in s["usage"]]
    prefixes = [context_of(s["usage"][0]) for s in sessions if not s["subagent"]]
    tool_tokens = Counter()
    for s in sessions:
        for _, name, size in s["results"]:
            tool_tokens[name.split("__")[1] if name.startswith("mcp__") else name] += size / 3.6

    print(f"{len(sessions)} sessions, {len(contexts):,} requests, last {args.days}d\n")
    print("Where the weighted cost goes")
    print(f"  cache read   {weighted['read'] / total:6.1%}")
    print(f"  cache write  {(weighted['write'] + weighted['write1h']) / total:6.1%}"
          f"  ({tokens['write1h'] / max(1, tokens['write'] + tokens['write1h']):.0%} at the 1h price)")
    for k in ("output", "input"):
        print(f"  {k:12}", f"{weighted[k] / total:6.1%}")
    print(f"\nContext per request: p50 {pct(contexts, .5):,}  p90 {pct(contexts, .9):,}  "
          f"(>200k on {sum(c > 200_000 for c in contexts) / len(contexts):.0%} of requests)")
    print(f"Fixed prefix at session start: p50 {pct(prefixes, .5):,} tokens")
    # What agentmaxx can't shrink for you but you can: the attachments Claude Code adds to the first turn.
    mains = [s for s in sessions if not s["subagent"]]
    first_turn = Counter()
    per_file: dict[str, list[float]] = {}
    reinjected = 0.0
    for s in mains:
        for kind, at, *rest in s["events"]:
            if kind == "instructions":
                path, tok = rest
                if at == 0:
                    first_turn["CLAUDE.md files"] += tok
                    per_file.setdefault(path, []).append(tok)
                else:
                    reinjected += tok
            elif kind == "skills" and at == 0:
                first_turn["skill listing"] += rest[0]
            elif kind == "injected" and at == 0:
                first_turn[rest[0]] += rest[1]
    n = max(1, len(mains))
    if first_turn:
        parts = ", ".join(f"{k} {v / n / 1000:.1f}k" for k, v in first_turn.most_common(5))
        print(f"  of which, per session on average: {parts}; the rest is Claude Code's own system prompt and tool schemas")
        print(f"  CLAUDE.md re-attached mid-session (changed or new dir): {reinjected / n / 1000:.1f}k tokens per session")
    big_files = sorted(((sum(v) / len(v), p, len(v)) for p, v in per_file.items()), reverse=True)[:3]
    print("Largest tool-result sources (tokens added):", ", ".join(
        f"{n} {t / 1e6:.1f}M" for n, t in tool_tokens.most_common(4)))
    print("\nCompression backends (better-compress router; enable: AGENTMAXX_SQUEEZE_ROUTER=1)")
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            bc_spec = importlib.util.spec_from_file_location(
                "better_compress_doctor", Path(__file__).resolve().parent.parent
                / "tools" / "better-compress" / "better_compress.py")
            bc = importlib.util.module_from_spec(bc_spec)
            assert bc_spec.loader
            bc_spec.loader.exec_module(bc)
            hr = "ready" if bc.load_headroom() is not None else "missing (make compress-deps)"
        except Exception:
            hr = "router not found"
    print(f"  headroom (JSON crush): {hr}")
    print(f"  lowfat (command wrap): {shutil.which('lowfat') or 'missing (make compress-deps)'}")

    print("\nCorrections (the closest free proxy for agent quality)")
    print("\n".join(corrections.report(corrections.scan(args.days))))

    print("\nRecommendations")
    advice = 0
    updates: dict[str, str] = {}
    hide: list[str] = []
    proxy = env.get("ANTHROPIC_BASE_URL", "")
    if proxy and "anthropic.com" not in proxy and env.get("ENABLE_TOOL_SEARCH") != "true":
        advice += 1
        updates["ENABLE_TOOL_SEARCH"] = "true"
        print(f"  {advice}. ANTHROPIC_BASE_URL={proxy} silently disables tool search, so every tool schema\n"
              "     rides in the prefix. Set env ENABLE_TOOL_SEARCH=true (bench: prefix 63k -> 17k, -16%/task).")
    elif pct(prefixes, .5) > 40_000 and env.get("ENABLE_TOOL_SEARCH") != "true":
        advice += 1
        print(f"  {advice}. Prefix is {pct(prefixes, .5):,} tokens. Check /context; set ENABLE_TOOL_SEARCH=true and drop unused MCP servers.")
    window = env.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW")
    base = simulate_window(sessions, int(window) if window else None)
    # Not below 300k: each compaction can drop task detail. Forcing compaction mid-task cut Haiku's pass
    # rate on the real-repo bench from 17/20 to 13/21 (evals/RESULTS.md), and 200k compacts 2.4x as often
    # as 300k for about one point of modeled savings.
    best = min((simulate_window(sessions, w), w) for w in (300_000, 400_000))
    if (base - best[0]) / total > 0.05:
        advice += 1
        updates["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = str(best[1])
        print(f"  {advice}. Auto-compact window {window or 'model default (~1M on [1m] models)'}: replaying your sessions at "
              f"{best[1] // 1000}k\n     saves ~{(base - best[0]) / total:.0%} of the bill. "
              f"Set env CLAUDE_CODE_AUTO_COMPACT_WINDOW={best[1]} if you can live with compaction dropping detail.")
    one_hour, five_min = simulate_ttl(sessions, 3600), simulate_ttl(sessions, 300)
    if rec := best_uniform_ttl(total, five_min, one_hour):
        advice += 1
        better, saved = rec
        updates["CLAUDE_CODE_PROMPT_CACHE_TTL"] = better
        print(f"  {advice}. Cache TTL: replaying your request gaps, {better} costs "
              f"{saved:.0%} less than what you run now.\n"
              f"     Set env CLAUDE_CODE_PROMPT_CACHE_TTL={better}.")
    sub_writes = Counter()
    for s in sessions:
        if s["subagent"]:
            for i, u in enumerate(s["usage"]):
                cc = u.get("cache_creation") or {}
                sub_writes["5m" if cc.get("ephemeral_5m_input_tokens") else "1h"] += 1
                if i and (u.get("cache_creation_input_tokens", 0) or 0) > 20_000 \
                        and (u.get("cache_read_input_tokens", 0) or 0) < 0.3 * context_of(s["usage"][i - 1]) \
                        and s["times"][i] - s["times"][i - 1] > 300:
                    sub_writes["rewrite_tokens"] += u.get("cache_creation_input_tokens", 0) or 0
                    sub_writes["rewrites"] += 1
    if sub_writes["5m"] > sub_writes["1h"] and sub_writes["rewrite_tokens"] > 0.03 * (tokens["write"] + tokens["write1h"]):
        # Not advice: replaying subagent transcripts, 1h writes at 2x cost more than the rewrites they avoid
        # (LEDGER.md iteration 16: +18.7% on 274 subagents). Printed so the number isn't mistaken for waste to fix.
        subs = [s for s in sessions if s["subagent"]]
        delta = simulate_ttl(subs, 3600) / max(1, simulate_ttl(subs, 300)) - 1
        print(f"  note: {sub_writes['rewrites']} subagent requests came after a 5m+ gap on the 5m TTL and rewrote their prefix "
              f"({sub_writes['rewrite_tokens'] / 1e6:.1f}M tokens,\n        {sub_writes['rewrite_tokens'] / (tokens['write'] + tokens['write1h']):.0%} of cache writes). "
              f"Moving subagents to 1h (CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL) would cost {delta:+.0%}: leave it.")
    for tok, path, count in big_files:
        if tok > 8_000:
            advice += 1
            subs = sum(1 for s in sessions if s["subagent"])
            print(f"  {advice}. {path} is {tok / 1000:.0f}k tokens, attached to every request in {count} sessions and to every\n"
                  f"     subagent ({subs} in {args.days}d). It costs {tok * 0.1 / 1000:.1f}k token-equivalents per request as cache reads alone.\n"
                  "     Keep CLAUDE.md to rules the agent needs every turn (~2k tokens); move reference material into docs/ it reads on demand.")
    hit = tokens["read"] / max(1, tokens["read"] + tokens["write"] + tokens["write1h"] + tokens["input"])
    if hit < 0.85:
        advice += 1
        print(f"  {advice}. Cache hit {hit:.0%}: the prefix keeps being rewritten (idle past TTL, /model switches,\n"
              "     late-connecting MCP servers). Avoid mid-session model switches; consider CLAUDE_CODE_PROMPT_CACHE_TTL=1h.")
    if tool_tokens.get("Bash", 0) > 0.4 * sum(tool_tokens.values()) and "squeeze" not in json.dumps(settings.get("hooks", {})):
        advice += 1
        print(f"  {advice}. Bash output is {tool_tokens['Bash'] / sum(tool_tokens.values()):.0%} of tool-result tokens. "
              "Install the agentmaxx squeeze hook (make install).")
    listing = sum(tok * (1.8 * residency.price(s["usage"][0])[0] + residency.read_rate(s["usage"][0]) * max(0, len(s["usage"]) - at))
                  for s in sessions
                  for kind, at, *rest in s["events"] if kind == "skills" for tok in rest[:1])
    if listing / total > 0.015:
        used = {rest[0] for s in sessions for kind, _, *rest in s["events"] if kind == "invoked" and rest}
        hide = sorted(installed_skills() - used - set((settings.get("skillOverrides") or {})))
        advice += 1
        print(f"  {advice}. The skill listing rides in every request: {listing / total:.1%} of your bill. In {args.days}d Claude\n"
              f"     invoked {len(used)} skills on its own: {', '.join(sorted(used))}.\n"
              '     Hide the ones you only run by hand with settings.json\n'
              '     "skillOverrides": {"<name>": "user-invocable-only"} (they stay available as /name).'
              + (f"\n     Never invoked in {args.days}d: {', '.join(hide)}" if hide else ""))
    opus_sub = sum(residency.request_cost(u) for s in sessions if s["subagent"] for u in s["usage"]
                   if (u.get("model") or "").startswith("claude-opus"))
    if opus_sub / total > 0.05 and "CLAUDE_CODE_SUBAGENT_MODEL" not in env:
        advice += 1
        updates["CLAUDE_CODE_SUBAGENT_MODEL"] = "claude-sonnet-5-5"
        updates["CLAUDE_CODE_SUBAGENT_MODEL_FORCE"] = "1"
        print(f"  {advice}. Opus subagents are {opus_sub / total:.0%} of your bill. On the real-repo bench, Sonnet 5.5 subagents\n"
              "     under an Opus parent passed 8/10 vs 7/10 at -22% per task (Haiku saved nothing). Set env\n"
              "     CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5-5 and CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1 (without FORCE,\n"
              "     Explore keeps the parent's model; with it, models named in your own agents are overridden too).")
    if not advice:
        print("  nothing major; run `make telemetry` for per-session detail")
    if args.apply or args.dry_run:
        plan = compute_plan(settings, env, updates)
        print(f"\nApply plan ({SETTINGS}):")
        for k, v, cur, status in plan["env"]:
            detail = {"write": f"= {v}", "noop": "(already set)",
                      "conflict": f"(you have {cur!r}; skipped)"}[status]
            print(f"  env {k} {detail} [{status}]")
        if not plan["env"]:
            print("  nothing appliable")
        elif args.apply:
            n = sum(1 for e in plan["env"] if e[3] == "write")
            if not n:
                print("  nothing to change")
            else:
                backup = apply_plan(SETTINGS, settings, plan)
                print(f"  wrote {n} change(s); backup at {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
