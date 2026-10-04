#!/usr/bin/env python3
"""Blind LLM judge for machine-written prose, scored against known human and model docs.

    python3 evals/tells_judge.py [--n 30] [--model claude-sonnet-5-5] [--jobs 4]

Model docs are bench generation outputs (g1/g4/g5, see tells_mine.model_docs with days=0);
human docs are pre-2021 project docs (tells_baseline.py). Each doc is cut to its first
~450 words of prose, shuffled, and shown alone to the judge, which returns P(machine) and the
phrases that gave it away. A cited phrase only counts if it occurs verbatim in the doc.
Reports judge AUC next to the regex detector's AUC on the same docs, and the cited phrases
from correctly judged model docs, which are the candidate rules the regex misses.

--matched removes the topic leak: for each sampled human doc, the model writes a twin from the
same project name, title and headings, once plain ("model") and once with skills/human-voice
loaded ("voice"). Without --matched, model docs are bench outputs about the fixture, the judge
can tell them apart by topic alone, and only the phrase list means anything.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import random
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tells import CODE_BLOCK, score  # noqa: E402
from tells_mine import human_docs, model_docs  # noqa: E402

OUT = Path(__file__).resolve().parent / "bench" / "judge.jsonl"
PROMPT = """You are judging writing style. Below is an excerpt of a project document. Decide how likely it is \
that a language model wrote it rather than a person. Ignore the topic and the project; judge only the writing. \
Reply with JSON only, no prose: {"p_machine": <0..1>, "phrases": [<up to 5 short verbatim excerpts that drove \
your judgement>]}

<document>
%s
</document>"""


def excerpt(text: str, words: int = 450) -> str:
    text = CODE_BLOCK.sub("", text)
    out, n = [], 0
    for line in text.splitlines():
        out.append(line)
        n += len(line.split())
        if n >= words:
            break
    return "\n".join(out).strip()


def judge(doc: dict, model: str) -> dict:
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run(["claude", "-p", PROMPT % doc["text"], "--model", model, "--output-format", "json",
                            "--setting-sources", "project,local", "--tools", ""],
                           cwd=d, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    try:
        j = json.loads(p.stdout)
        body = re.search(r"\{.*\}", j.get("result", ""), re.S)
        verdict = json.loads(body.group(0)) if body else {}
    except (json.JSONDecodeError, AttributeError):
        j, verdict = {}, {}
    phrases = [s for s in verdict.get("phrases", []) if isinstance(s, str)]
    return {**doc, "p": verdict.get("p_machine"), "cost": j.get("total_cost_usd", 0),
            "phrases": [s for s in phrases if s.strip() and s.strip() in doc["text"]],
            "invented": [s for s in phrases if s.strip() and s.strip() not in doc["text"]]}


GEN = """Write the Markdown document `%s` for the open-source Python project %s. Use these headings, \
in this order:
%s
Aim for about %d words. Reply with the document only."""
SKILL = Path(__file__).resolve().parent.parent / "skills" / "human-voice" / "SKILL.md"


def headings(text: str) -> list[str]:
    md = re.findall(r"^#{1,3} .+$", text, re.M)
    rst = [m.group(1) for m in re.finditer(r"^(\S[^\n]{2,80})\n[=\-~^]{3,}\s*$", text, re.M)]
    return (md or ["# " + h for h in rst])[:8]


def twin(doc: dict, model: str, voice: bool, skill: Path = SKILL, arm: str = "") -> dict:
    prompt = GEN % (doc["path"], doc["repo"], "\n".join(doc["heads"]), len(doc["text"].split()))
    if voice:
        prompt = "Follow this writing guide.\n\n" + skill.read_text() + "\n\n" + prompt
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run(["claude", "-p", prompt, "--model", model, "--output-format", "json",
                            "--setting-sources", "project,local", "--tools", ""],
                           cwd=d, capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
    try:
        j = json.loads(p.stdout)
    except json.JSONDecodeError:
        j = {}
    return {"label": 1, "arm": arm or ("voice" if voice else "model"), "text": excerpt(j.get("result", "")),
            "gen_cost": j.get("total_cost_usd", 0), "pair": doc["path"]}


def matched(n: int, gen_model: str, jobs: int, variant: Path | None = None) -> list[dict]:
    from tells_mine import H
    rng = random.Random(11)
    pool = []
    for repo in sorted(H.iterdir()):
        sh = lambda c: subprocess.run(c, shell=True, cwd=repo, capture_output=True, text=True, errors="ignore").stdout
        sha = sh("git rev-list -n1 --before=2021-06-01 HEAD").strip()
        for f in sh(f"git ls-tree -r --name-only {sha}").split():
            if f.endswith((".md", ".rst")) and "changelog" not in f.lower() and "history" not in f.lower():
                text = sh(f"git show {sha}:{f}")
                if len(text.split()) > 250 and len(headings(text)) >= 2:
                    pool.append({"label": 0, "arm": "human", "repo": repo.name, "path": f, "heads": headings(text),
                                 "text": excerpt(text), "pair": f})
    humans = rng.sample(pool, min(n, len(pool)))
    jobs_ = [(h, gen_model, True, variant, variant.stem) for h in humans] if variant else \
        [(h, gen_model, v) for h in humans for v in (False, True)]
    with cf.ThreadPoolExecutor(jobs) as ex:
        twins = list(ex.map(lambda a: twin(*a), jobs_))
    return ([] if variant else humans) + [t for t in twins if len(t["text"].split()) > 120]


def auc(pos: list[float], neg: list[float]) -> float:
    pairs = [(a > b) + 0.5 * (a == b) for a in pos for b in neg]
    return sum(pairs) / len(pairs)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=30, help="docs per class")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--report", action="store_true", help="only summarize judge.jsonl")
    ap.add_argument("--matched", action="store_true", help="topic-matched twins of human docs")
    ap.add_argument("--gen-model", default="claude-opus-5-5")
    ap.add_argument("--variant", type=Path, help="with --matched: add twins written with this guide to judge.jsonl")
    args = ap.parse_args()
    if not args.report and args.matched:
        docs = matched(args.n, args.gen_model, args.jobs, args.variant)
        random.Random(7).shuffle(docs)
        with cf.ThreadPoolExecutor(args.jobs) as ex, OUT.open("a" if args.variant else "w") as fh:
            for r in ex.map(lambda d: judge(d, args.model), docs):
                fh.write(json.dumps({**r, "regex": score(r["text"], "prose")["density"]}) + "\n")
    elif not args.report:
        rng = random.Random(7)
        docs = [{"label": 1, "text": excerpt(t)} for t in rng.sample(model_docs(0), args.n)]
        docs += [{"label": 0, "text": excerpt(t)} for t in rng.sample(human_docs(), args.n)]
        docs = [d for d in docs if len(d["text"].split()) > 120]
        rng.shuffle(docs)
        with cf.ThreadPoolExecutor(args.jobs) as ex, OUT.open("w") as fh:
            for r in ex.map(lambda d: judge(d, args.model), docs):
                fh.write(json.dumps({**r, "regex": score(r["text"], "prose")["density"]}) + "\n")
    rows = [json.loads(l) for l in OUT.open()]
    ok = [r for r in rows if isinstance(r.get("p"), (int, float))]
    pos, neg = [r for r in ok if r["label"]], [r for r in ok if not r["label"]]
    print(f"{len(ok)}/{len(rows)} judged ({len(pos)} model, {len(neg)} human), "
          f"${sum(r['cost'] + r.get('gen_cost', 0) for r in rows):.2f}")
    for arm in sorted({r.get("arm") for r in pos} - {None}):
        a = [r for r in pos if r.get("arm") == arm]
        print(f"  {arm:6} n={len(a)}  judge AUC vs human {auc([r['p'] for r in a], [r['p'] for r in neg]):.2f}  "
              f"regex AUC {auc([r['regex'] for r in a], [r['regex'] for r in neg]):.2f}  "
              f"judged machine {sum(r['p'] >= 0.5 for r in a)}/{len(a)}")
    print(f"judge AUC {auc([r['p'] for r in pos], [r['p'] for r in neg]):.2f}   "
          f"regex AUC {auc([r['regex'] for r in pos], [r['regex'] for r in neg]):.2f}")
    print(f"invented quotes: {sum(len(r['invented']) for r in rows)} of "
          f"{sum(len(r['invented']) + len(r['phrases']) for r in rows)}")
    cited = Counter(p.strip().lower() for r in pos if r["p"] >= 0.5 for p in r["phrases"])
    print("\nphrases cited on model docs judged machine (count):")
    for p, c in cited.most_common(40):
        print(f"  {c}  {p[:90]}")
    fp = Counter(p.strip().lower() for r in neg if r["p"] >= 0.5 for p in r["phrases"])
    print(f"\nhuman docs judged machine: {sum(r['p'] >= 0.5 for r in neg)}/{len(neg)}; their cited phrases:")
    for p, c in fp.most_common(15):
        print(f"  {c}  {p[:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
