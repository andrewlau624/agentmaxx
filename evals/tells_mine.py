#!/usr/bin/env python3
"""Find words and patterns over-used in model-written prose relative to human prose.

    python3 evals/tells_mine.py [--days 30] [--min 15]

Model corpus: .md/.txt files the agent wrote (Write tool content) in
~/.claude/projects transcripts, plus generation outputs from the bench.
Human corpus: pre-2022 docs and commit messages from the repos in
~/.cache/agentmaxx-bench/human (see tells_baseline.py). Ranks by smoothed
log-odds; the corpora differ in topic, so treat the list as candidates to
check against sources, not as rules.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import time
from collections import Counter
from pathlib import Path

WORD = re.compile(r"[a-z][a-z'-]+")
H = Path.home() / ".cache" / "agentmaxx-bench" / "human"
# discourse connectives and sentence-level glue: present in any topic
CONNECTIVES = set("""additionally moreover furthermore however therefore thus hence overall ultimately notably
importantly essentially basically crucially consequently meanwhile instead rather whereas although though while
also still just really actually simply clearly indeed specifically particularly generally typically often""".split())
QUOTES_TELLS = re.compile(r"tells|SKILL\.md|human-voice|design-system-ui|no-ai|slop|ultra-optimize|LEDGER|RESULTS", re.I)
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)


def model_docs(days: int) -> list[str]:
    cutoff, docs = time.time() - days * 86400, []
    for p in (Path.home() / ".claude" / "projects").rglob("*.jsonl"):
        if p.stat().st_mtime < cutoff:
            continue
        for line in p.open(errors="ignore"):
            if '"Write"' not in line:
                continue
            try:
                blocks = (json.loads(line).get("message") or {}).get("content") or []
            except json.JSONDecodeError:
                continue
            for b in blocks:
                if isinstance(b, dict) and b.get("name") == "Write":
                    i = b.get("input") or {}
                    path = str(i.get("file_path", ""))
                    # catalogs and style guides quote the tells they describe
                    if QUOTES_TELLS.search(path):
                        continue
                    if path.endswith((".md", ".txt")) and len(i.get("content", "")) > 300:
                        docs.append(i["content"])
    bench = Path(__file__).resolve().parent / "bench" / "results.jsonl"
    for line in bench.open() if bench.exists() else []:
        r = json.loads(line)
        if r.get("task") in ("g1_readme", "g4_adr", "g5_security"):
            f = {"g1_readme": "README.md", "g4_adr": "docs/adr/0001-money-representation.md", "g5_security": "SECURITY_REVIEW.md"}[r["task"]]
            path = Path(r["dir"]) / f
            if path.exists():
                docs.append(path.read_text(errors="ignore"))
    return docs


def human_docs() -> list[str]:
    docs = []
    for repo in sorted(H.iterdir()) if H.exists() else []:
        sh = lambda c: subprocess.run(c, shell=True, cwd=repo, capture_output=True, text=True, errors="ignore").stdout
        sha = sh("git rev-list -n1 --before=2021-06-01 HEAD").strip()
        for f in sh(f"git ls-tree -r --name-only {sha}").split():
            if f.endswith((".md", ".rst")):
                text = sh(f"git show {sha}:{f}")
                if len(text) > 300:
                    docs.append(text)
    return docs


def features(text: str) -> Counter:
    text = CODE.sub(" ", text)
    c = Counter(WORD.findall(text.lower()))
    words = sum(c.values()) or 1
    c["<em dash>"] = text.count("—")
    c["<bold-label bullet>"] = len(re.findall(r"^\s*[-*] \*\*[^*\n]+\*\*", text, re.M))
    c["<heading>"] = len(re.findall(r"^#{1,6} ", text, re.M))
    c["<colon heading-less label line>"] = len(re.findall(r"^\*\*[^*\n]+:\*\*", text, re.M))
    c["<arrow>"] = text.count("→")
    c["__words__"] = words
    return c


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--min", type=int, default=15, help="minimum documents a word must appear in (model side)")
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--style", action="store_true", help="only -ly adverbs, connectives and format features (topic-light)")
    args = ap.parse_args()
    m_docs, h_docs = model_docs(args.days), human_docs()
    m, h, m_df, h_df = Counter(), Counter(), Counter(), Counter()
    for d in m_docs:
        f = features(d); m.update(f); m_df.update(k for k, v in f.items() if v)
    for d in h_docs:
        f = features(d); h.update(f); h_df.update(k for k, v in f.items() if v)
    mw, hw = m.pop("__words__"), h.pop("__words__")
    print(f"model: {len(m_docs)} docs, {mw:,} words   human: {len(h_docs)} docs, {hw:,} words\n")
    rows = []
    for w in set(m) | set(h):
        if m_df[w] < args.min:
            continue
        if args.style and not (w.startswith("<") or w in CONNECTIVES or (w.endswith("ly") and len(w) > 4)):
            continue
        # per-1k-word rates with add-0.5 smoothing; log-odds over both corpora
        lm, lh = math.log((m[w] + .5) / mw), math.log((h[w] + .5) / hw)
        rows.append((lm - lh, w, m[w] * 1000 / mw, h[w] * 1000 / hw, m_df[w], h_df[w]))
    rows.sort(reverse=True)
    print(f"{'feature':28} {'log ratio':>9} {'model/1k':>9} {'human/1k':>9} {'m docs':>7} {'h docs':>7}")
    for r in rows[:args.top]:
        print(f"{r[1]:28} {r[0]:9.2f} {r[2]:9.3f} {r[3]:9.3f} {r[4]:7} {r[5]:7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
