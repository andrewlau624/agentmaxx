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

# Every rule names its evidence: source ids from evals/tells-sources/{prose,ui,code}.md, or "measured"
# for a feature that separated model from human docs in evals/tells-sources/measured.md. Rules with
# neither were removed on 2026-10-03, along with the GPT-era word lists' claim to cover current models:
# on this machine's Claude 5.x docs they occur at the human rate (measured.md).

# Rare words with large measured excess in GPT-4-era text (Kobak, Liang, Reinhart, Juzek & Ward, Wikipedia)
GPT_ERA = ("delve|delves|delved|delving|tapestry|underscores?|underscoring|showcasing|showcases|meticulous|meticulously|"
           "intricate|intricacies|pivotal|commendable|camaraderie|palpable|amidst|realm|boasts|garnered|interplay|"
           "unwavering|testament")

PROSE = {
    "spaced em dash": (re.compile(r" — "), "W, F (Claude Opus 4.6 9.09/1k vs human mean 3.23/1k), measured"),
    "inline-header list item": (re.compile(r"^\s*([-*•–]|\d+\.)\s*\*\*[^*\n]+\*\*", M), "W, measured (weak: 114/209 vs 53/334 docs)"),
    "bold label line": (re.compile(r"^\*\*[^*\n]+:\*\*|^\*\*[^*\n]+\*\*:", M), "W (variant), measured (66/209 vs 24/334 docs)"),
    "arrow in prose": (re.compile(r"→"), "measured only (34/209 vs 0/334 docs)"),
    "emoji marker": (re.compile(r"^\s*(#+ |[-*] )?[\U0001F300-\U0001FAFF✅❌⚠✨⭐]", M), "W"),
    "GPT-era word": (re.compile(rf"\b({GPT_ERA})\b", I), "K, L1, L2, R, J, W (GPT-4/4o era; at human rate on Claude 5.x here)"),
    "significance padding": (re.compile(r"\b(stands|serves) as an? (testament|reminder)\b|\bis a testament to\b|\bplays? an? (crucial|pivotal|vital|significant|key) role\b|"
                                        r"\b(evolving|ever-evolving) landscape\b|\bindelible mark\b|\bsetting the stage for\b|\bdeeply rooted\b", I), "W, RU"),
    "negative parallelism": (re.compile(r"\bnot only\b.{0,80}\bbut( also)?\b|\bit['’]?s not (just |only |merely )?[^.;\n]{1,40}[,;—-]+ (it['’]?s|it is)\b|\bit['’]?s not about\b.{0,60}\bit['’]?s about\b", I), "W, RU"),
    "participle tail": (re.compile(r", (highlighting|underscoring|reflecting|ensuring|showcasing|emphasizing|symbolizing|contributing to|fostering) (the|its|their|a|how)\b", I), "W, R (participial clauses 5.3x human rate in GPT-4o)"),
    "copula avoidance": (re.compile(r"\b(serves|stands|functions) as (a|an|the)\b|\bboasts an?\b", I), "W"),
    "vague attribution": (re.compile(r"\b(industry reports|observers have (cited|noted)|experts (argue|say|note)|some critics argue|several (sources|publications))\b", I), "W"),
    "chatbot phrasing": (re.compile(r"\b(i hope this helps|you['’]re absolutely right|is there anything else|let me know if|would you like me to|more detailed breakdown)\b|^\s*(certainly|of course)!", I | M), "W"),
    "section summary": (re.compile(r"^\s*(in summary|in conclusion|to summarize)\b|^#+ conclusion\s*$", I | M), "W, RU"),
    "knowledge-cutoff disclaimer": (re.compile(r"\b(as of my last (knowledge|training) update|up to my last training update|as an ai language model|as a large language model)\b", I), "W"),
    "placeholder": (re.compile(r"\[(your name|describe[^\]]*|insert[^\]]*)\]|20\d\d-(xx|XX)-(xx|XX)", I), "W"),
    "citation artifact": (re.compile(r"contentReference\[oaicite:\d+\]|oai_citation|\[cite: ?\d+\]|turn\d+search\d+|grok_card|【\d+†"), "W"),
}

COMMIT = {
    "emoji prefix": (re.compile(r"^[\U0001F300-\U0001FAFF✅✨⭐⚡]"), "S18 (Wikipedia via Gentoo policy)"),
    "spaced em dash": (re.compile(r" — "), "S18"),
    "inline-header list item": (PROSE["inline-header list item"][0], "S18"),
    "chatbot phrasing": (PROSE["chatbot phrasing"][0], "S18"),
    "GPT-era word": (PROSE["GPT-era word"][0], "K, J, W"),
}

UI = {
    "indigo/violet utility class": (re.compile(r"\b(bg|text|from|via|to|border|ring)-(indigo|violet|purple)-\d{2,3}\b"), "S5, S6, S7, S9, S13"),
    "purple gradient": (re.compile(r"\b(from|via|to)-(indigo|violet|purple|fuchsia)-\d{3}\b[^\"'`]*\b(from|via|to)-\w+-\d{3}|linear-gradient\([^)]*(indigo|violet|purple)", I), "S2, S3, S4, S12"),
    "blue-600 to purple-600": (re.compile(r"from-blue-600[^\"'`]*to-purple-600"), "S17"),
    "gradient text": (re.compile(r"\bbg-clip-text\b|-webkit-background-clip:\s*text|background-clip:\s*text", I), "S7, S9, S14, S16"),
    "glassmorphism": (re.compile(r"\bbackdrop-blur(-\w+)?\b|backdrop-filter:\s*blur", I), "S6, S7, S14, S16"),
    "colored left border": (re.compile(r"\bborder-l-(2|4|8)\b[^\"'`]*\bborder-\w+-\d{3}\b|border-left:\s*([2-9]|\d\d)px solid", I), "S6, S14"),
    "large uniform radius + shadow": (re.compile(r"rounded-(2xl|3xl)[^\"'`]*shadow-(md|lg|xl|2xl)|shadow-(md|lg|xl|2xl)[^\"'`]*rounded-(2xl|3xl)"), "S1, S15, S16, S17"),
    "tracked uppercase label": (re.compile(r"\buppercase\b[^\"'`]*\btracking-(wide|wider|widest|\[0?\.\d+em\])|text-transform:\s*uppercase;[^}]*letter-spacing:\s*0?\.[1-9]", I), "S1, S6, S14"),
    "three-column card grid": (re.compile(r"\b(md:|lg:)?grid-cols-3\b|grid-template-columns:\s*repeat\(3,", I), "S6, S9, S10, S12, S14"),
    "pill badge": (re.compile(r"\brounded-full\b[^\"'`]*\b(px-3|text-xs)\b[^>]*>\s*[^<]{0,40}\b(new|introducing|announcing|beta)\b", I), "S6, S7"),
    "emoji as icon": (re.compile(r">\s*[\U0001F300-\U0001FAFF✨⚡⭐]\s*<"), "S6, S7, S14"),
    "sparkle icon": (re.compile(r"\b(Sparkles|Sparkle)\b|✨"), "S15, S16 (community skills only)"),
    "hype copy": (re.compile(r"\b(supercharge|unlock the (power|potential)|elevate your|seamless(ly)?)\b", I), "S15, S16"),
    "generic sans as the only face": (re.compile(r"font-family:\s*['\"]?(Inter|Roboto|Arial|Open Sans|Lato)['\"]?\s*,\s*(sans-serif|system-ui|-apple-system)|family=Inter\b|from ['\"]next/font/google['\"].*\bInter\b", I), "S3, S4, S6, S13"),
    "fallback display face": (re.compile(r"\b(Space Grotesk|Instrument Serif|Geist|Fraunces|Bricolage Grotesque|Sora|Young Serif|Syne)\b"), "S3, S6, S7, S17"),
    "tinted near-black": (re.compile(r"#(0b0b0b|111111|111)\b", I), "S1"),
}

CODE = {
    "swallowed exception": (re.compile(r"except( Exception| BaseException)?( as \w+)?:\s*(\n\s*)?(pass|return None|continue)\b|catch\s*\(\w*\)\s*\{\s*\}", M), "S4, S20"),
    "log-only error handler": (re.compile(r"except Exception( as \w+)?:\s*\n\s*(logger|logging|log|print)\b[^\n]*\n(?!\s*raise)|catch\s*\((e|err|error)\)\s*\{\s*console\.(error|log)\([^)]*\);?\s*\}", M), "S20"),
    "placeholder": (re.compile(r"\b(TODO: implement|your code here|add your \w+ here|implement (this|me|here)|replace (this )?with your( own)? implementation|placeholder (implementation|logic))\b", I), "S1, S20"),
    "narrating comment": (re.compile(r"^\s*(#|//)\s*(step \d+[:.]|first,? we|now we|next,? we|here we|this (function|method|code) (will|does))\b", I | M), "S20"),
    "section banner comment": (re.compile(r"^\s*(#|//)\s*[=\-*#]{8,}\s*$", M), "S20"),
    "chat residue": (re.compile(r"^(here('s| is) (the|an?|your) (updated|complete|full|revised)\b|```\w*\s*$)", I | M), "S21"),
    "debug print": (re.compile(r"^\s*(print\(f?[\"'](debug|DEBUG|>>>|---)|console\.log\(|System\.out\.println\(|\w+\.printStackTrace\(\))", M), "S1, S3"),
}
EXT_KIND = {".md": "prose", ".txt": "prose", ".rst": "prose", ".html": "ui", ".css": "ui", ".jsx": "ui",
            ".tsx": "ui", ".vue": "ui", ".svelte": "ui", ".py": "code", ".js": "code", ".ts": "code",
            ".go": "code", ".rs": "code", ".java": "code", ".rb": "code", ".sh": "code"}
RULES = {"prose": PROSE, "commit": COMMIT, "ui": UI, "code": CODE}
SOURCES = {kind: {name: src for name, (_, src) in rules.items()} for kind, rules in RULES.items()}


def _hsl(h: str) -> tuple[float, float, float]:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hi, lo = max(r, g, b), min(r, g, b)
    l = (hi + lo) / 2
    if hi == lo:
        return 0.0, 0.0, l
    d = hi - lo
    s = d / (2 - hi - lo) if l > 0.5 else d / (hi + lo)
    hue = (g - b) / d % 6 if hi == r else (b - r) / d + 2 if hi == g else (r - g) / d + 4
    return hue * 60, s, l


def color_hits(text: str) -> dict:
    """Hex-color tells. Purple uses design-slop-cop's isPurple thresholds (ui S7). The cream and
    terracotta windows are this repo's approximation of "near #F4F1EA" and "near #D97757" (ui S1)."""
    hits: dict[str, list[str]] = {}
    for h in dict.fromkeys(x.lower() for x in re.findall(r"#([0-9a-fA-F]{6})\b", text)):
        hue, sat, light = _hsl(h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        if 250 <= hue <= 300 and sat > 0.25 and 0.15 < light < 0.85:
            hits.setdefault("purple color", []).append("#" + h)
        if r >= 240 and g >= 235 and b >= 220 and 3 <= r - b <= 30:
            hits.setdefault("cream background (second-order default)", []).append("#" + h)
        if 190 <= r <= 235 and 95 <= g <= 135 and 70 <= b <= 110:
            hits.setdefault("terracotta accent (second-order default)", []).append("#" + h)
    return hits


SOURCES["ui"].update({"purple color": "S7 thresholds; S5, S6, S9", "cream background (second-order default)": "S1 (window approximated)",
                      "terracotta accent (second-order default)": "S1 (window approximated)"})
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
    for name, (rx, _) in RULES[kind].items():
        if allow_emoji and name == "emoji prefix":
            continue
        found = [m.group(0).strip() for m in rx.finditer(body)]
        if found:
            hits[name] = found
    if kind == "ui":
        hits.update(color_hits(body))
    words = len(body.split())
    lines = sum(1 for l in text.splitlines() if l.strip())
    n = sum(len(v) for v in hits.values())
    if kind in ("prose", "commit"):
        # Human prose averages 3.23 em dashes per 1k words (prose F); only a rate well above that counts
        dashes = len(hits.get("spaced em dash", []))
        if dashes and dashes * 1000 / max(words, 1) < 5 and dashes < 3:
            n -= dashes
            hits.pop("spaced em dash")
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
            print(f"  {name} x{len(found)}: {sample}   [{SOURCES[kind].get(name, '?')}]")
    return 1 if over else 0


if __name__ == "__main__":
    raise SystemExit(main())
