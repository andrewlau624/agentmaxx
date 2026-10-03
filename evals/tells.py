#!/usr/bin/env python3
"""Score text, UI markup, code, and commit messages for signs of machine authorship.

    python3 evals/tells.py README.md page.tsx            # kind from the extension
    git diff | python3 evals/tells.py --kind code -      # added lines only
    git log -1 --format=%B | python3 evals/tells.py --kind commit -

Prints hits per rule and a density (prose: per 1k words, ui: per component
file, code: per 100 added lines). Exit status 1 when any file is over
--max-density. Deterministic and regex-only: it catches the mechanical tells.
Judgement calls (fake specificity, sycophancy in context) need a reader.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

I = re.IGNORECASE
M = re.MULTILINE

FILLER = (
    "delve|delves|delving|tapestry|testament|vibrant|realm|multifaceted|intricate|pivotal|bolster|foster|"
    "seamless|seamlessly|robust|leverage|leveraging|elevate|elevates|empower|empowers|unleash|unlock|"
    "game-changer|cutting-edge|best-in-class|supercharge|streamline|holistic|synergy|paradigm|"
    "meticulous|meticulously|commendable|showcase|showcasing|underscore|underscores|ever-evolving|"
    "embark|navigating the|in the realm of"
)

PROSE = {
    "filler word": re.compile(rf"\b({FILLER})\b", I),
    "crucial/vital/essential as filler": re.compile(r"\b(it is|it's) (crucial|vital|essential|important) to\b|\bplays? an? (crucial|vital|pivotal|key) role\b", I),
    "significance padding": re.compile(r"\b(stands as|serves as) an? (testament|reminder|example)\b|\bin today's (fast-paced|ever-changing|digital|modern)\b", I),
    "not X, it's Y": re.compile(r"\b(it's|it is|this is|that's) not (just |only |merely )?[^.;\n]{1,40}[,;—-]+ (it's|it is|but)\b|\bnot (just|only|merely) [^.;\n]{1,40}, but (also )?\b", I),
    "opener": re.compile(r"^\s*(great question|certainly!|absolutely!|of course!|sure!|i'd be happy to|happy to help)", I | M),
    "wrap-up": re.compile(r"^\s*(in summary|in conclusion|overall|to summarize|to sum up|ultimately)\b,?", I | M),
    "closing offer": re.compile(r"\b(let me know if|feel free to|hope this helps|happy to (help|adjust|elaborate)|want me to)\b", I),
    "narration": re.compile(r"^\s*(let me|i'll now|now i'll|first, i'll)\b", I | M),
    "hedge stack": re.compile(r"\b(may|might|could) (potentially|possibly|perhaps)\b|\bit('s| is) worth (noting|mentioning) that\b|\bit is important to note\b", I),
    "participle tail": re.compile(r", (highlighting|underscoring|reflecting|ensuring|showcasing|emphasizing|demonstrating) (the|its|their|a|how)\b", I),
    "copula dodge": re.compile(r"\b(serves|acts|functions) as (a|an|the)\b", I),
    "vague attribution": re.compile(r"\b(experts (say|agree|note)|is widely (considered|regarded|recognized)|many (believe|argue|find))\b", I),
    "bold-label bullet": re.compile(r"^\s*[-*] \*\*[^*\n]{1,40}:?\*\*:?", M),
    "emoji marker": re.compile(r"^\s*(#+ |[-*] )?[\U0001F300-\U0001FAFF✅❌⚠✨⭐]", M),
    "em dash": re.compile(r"—"),
}

COMMIT = {
    "this commit": re.compile(r"^\s*this (commit|pr|change|pull request)\b", I | M),
    "emoji prefix": re.compile(r"^[\U0001F300-\U0001FAFF✅✨⭐⚡]"),
    "filler word": PROSE["filler word"],
    "summary heading": re.compile(r"^#+ (summary|changes|overview)\b", I | M),
}

UI = {
    "purple/indigo gradient": re.compile(r"\b(from|via|to)-(indigo|violet|purple|fuchsia)-\d{3}\b|linear-gradient\([^)]*(#6366f1|#8b5cf6|#a855f7|#7c3aed|#4f46e5|indigo|violet|purple)", I),
    "gradient text": re.compile(r"\bbg-clip-text\b|-webkit-background-clip:\s*text|background-clip:\s*text", I),
    "glassmorphism": re.compile(r"\bbackdrop-blur(-\w+)?\b|backdrop-filter:\s*blur", I),
    "rounded-2xl + shadow card": re.compile(r"rounded-(2xl|3xl)[^\"'`]*shadow-(lg|xl|2xl)|shadow-(lg|xl|2xl)[^\"'`]*rounded-(2xl|3xl)"),
    "hover lift": re.compile(r"hover:(-translate-y-\d|scale-10[5-9])"),
    "colored left-border strip": re.compile(r"\bborder-l-(4|8)\b[^\"'`]*border-(\w+)-\d{3}|border-left:\s*[3-8]px solid", I),
    "sparkle/robot icon": re.compile(r"\b(Sparkles|Sparkle|Wand2|Bot|BrainCircuit)\b|✨|🤖|🚀"),
    "emoji as icon": re.compile(r">\s*[\U0001F300-\U0001FAFF✨⚡⭐]\s*<"),
    "badge pill above hero": re.compile(r"rounded-full[^\"'`]*(px-3|text-xs)[^\"'`]*\"[^>]*>\s*[^<]{0,40}(new|introducing|announcing|beta|✨)", I),
    "template copy": re.compile(r"\b(unlock the (power|potential)|seamlessly|supercharge|elevate your|take your \w+ to the next level|trusted by (thousands|teams|developers)|built for the (future|modern)|get started (for free|today)|revolutioniz\w+)\b", I),
    "made-up stat": re.compile(r">\s*\d{1,3}(\.\d)?(k|K|M|\+|%|x)\+?\s*<"),
    "inter-only type": re.compile(r"font-family:\s*['\"]?Inter['\"]?\s*,\s*(sans-serif|system-ui)|fontFamily:\s*\{\s*sans:\s*\[\s*['\"]Inter", I),
}

CODE = {
    "comment restates code": re.compile(r"^\s*(#|//)\s*(import|define|initialize|initialise|create|set|get|return|loop (through|over)|iterate (through|over)|check if|call|increment|add|update|print|log)\b[^\n]{0,40}$", I | M),
    "swallowed exception": re.compile(r"except( Exception| BaseException)?( as \w+)?:\s*(\n\s*)?(pass|return None|continue)\b|catch\s*\(\w*\)\s*\{\s*\}", M),
    "broad except + log": re.compile(r"except Exception( as \w+)?:\s*\n\s*(logger|logging|log|print)\b|catch\s*\((e|err|error)\)\s*\{\s*console\.(error|log)", M),
    "placeholder": re.compile(r"\b(TODO: implement|your code here|add your \w+ here|placeholder (implementation|logic)|implement (this|me) later|not implemented yet)\b", I),
    "generic name": re.compile(r"\b(handle|process|manage)(Data|Item|Stuff|Thing|Request|Input)\b|\b(process|handle|manage)_(data|item|stuff|thing|input)\b|\bdo_?[Ss]tuff\b"),
    "version-suffix name": re.compile(r"\b(def|class|function|const|let|var)\s+((enhanced|improved|better|fixed|updated)_?[A-Za-z]\w*|\w+_(v2|new|fixed|improved|enhanced))\b"),
    "emoji in code": re.compile(r"[\U0001F300-\U0001FAFF✅❌✨]"),
    "debug print": re.compile(r"^\s*(print\(f?[\"'](debug|DEBUG|>>>|---)|console\.log\()", M),
}

EXT_KIND = {".md": "prose", ".txt": "prose", ".rst": "prose", ".html": "ui", ".css": "ui", ".jsx": "ui",
            ".tsx": "ui", ".vue": "ui", ".svelte": "ui", ".py": "code", ".js": "code", ".ts": "code",
            ".go": "code", ".rs": "code", ".java": "code", ".rb": "code", ".sh": "code"}
RULES = {"prose": PROSE, "commit": COMMIT, "ui": UI, "code": CODE}
CODE_BLOCK = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def added_lines(diff: str) -> str:
    return "\n".join(l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))


def rhythm(text: str) -> float | None:
    """Coefficient of variation of sentence length; human prose runs ~0.5-0.8, flat model prose lower."""
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text)) if len(s.split()) > 2]
    if len(sentences) < 8:
        return None
    lengths = [len(s.split()) for s in sentences]
    return statistics.pstdev(lengths) / statistics.mean(lengths)


def score(text: str, kind: str, allow_emoji: bool = False) -> dict:
    """allow_emoji: the repo's own commit history uses emoji prefixes (gitmoji), so they aren't a tell there."""
    if kind == "code" and text.lstrip().startswith(("diff --git", "--- ", "@@")):
        text = added_lines(text)
    body = text
    if kind in ("prose", "commit"):
        body = INLINE_CODE.sub("", CODE_BLOCK.sub("", text))
        body = "\n".join(l for l in body.splitlines() if not l.lower().startswith("co-authored-by:"))
    hits = {}
    for name, rx in RULES[kind].items():
        if allow_emoji and name == "emoji prefix":
            continue
        found = [m.group(0).strip() for m in rx.finditer(body)]
        if found:
            hits[name] = found
    words = len(body.split())
    lines = sum(1 for l in text.splitlines() if l.strip())
    n = sum(len(v) for v in hits.values())
    if kind in ("prose", "commit"):
        # an em dash or two is punctuation; a pileup is the tell
        dashes = len(hits.get("em dash", []))
        if dashes and dashes <= max(1, words // 250):
            n -= dashes
            hits.pop("em dash")
        unit, density = "per 1k words", n * 1000 / max(words, 1)
    elif kind == "ui":
        unit, density = "per file", float(n)
    else:
        unit, density = "per 100 lines", n * 100 / max(lines, 1)
    out = {"kind": kind, "hits": hits, "count": n, "words": words, "density": round(density, 2), "unit": unit}
    if kind == "prose" and (cv := rhythm(body)) is not None:
        out["rhythm_cv"] = round(cv, 2)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+", help="paths, or - for stdin")
    ap.add_argument("--kind", choices=sorted(RULES))
    ap.add_argument("--max-density", type=float)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--allow-emoji", action="store_true", help="the repo uses emoji commit prefixes")
    args = ap.parse_args()
    over = False
    for f in args.files:
        text = sys.stdin.read() if f == "-" else Path(f).read_text(errors="ignore")
        kind = args.kind or EXT_KIND.get(Path(f).suffix.lower(), "prose")
        r = score(text, kind, args.allow_emoji)
        over |= args.max_density is not None and r["density"] > args.max_density
        if args.json:
            print(json.dumps({"file": f, **r}))
            continue
        print(f"{f}: {r['count']} tells, {r['density']} {r['unit']}" + (f", rhythm cv {r['rhythm_cv']}" if "rhythm_cv" in r else ""))
        for name, found in r["hits"].items():
            sample = ", ".join(dict.fromkeys(found))[:100]
            print(f"  {name} x{len(found)}: {sample}")
    return 1 if over else 0


if __name__ == "__main__":
    raise SystemExit(main())
