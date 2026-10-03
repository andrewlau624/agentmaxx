#!/usr/bin/env python3
"""Human baseline for tells.py: pre-2022 commits, docs and diffs from a few well-known repos.

    for r in psf/requests pallets/flask encode/httpx tiangolo/fastapi; do
      git clone --filter=blob:none https://github.com/$r ~/.cache/agentmaxx-bench/human/$(basename $r); done
    python3 evals/tells_baseline.py
"""
import subprocess, sys, statistics, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tells import score
H = os.path.expanduser("~/.cache/agentmaxx-bench/human")
def sh(cmd, cwd): return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, errors="ignore").stdout
res = collections.defaultdict(list); rules = collections.defaultdict(collections.Counter)
for repo in sorted(os.listdir(H)):
    d = f"{H}/{repo}"
    # commit messages with a body, before 2022, non-merge
    log = sh("git log --no-merges --before=2022-01-01 -n 400 --format='%B%x00'", d)
    for msg in [m.strip() for m in log.split("\x00") if m.strip()]:
        r = score(msg, "commit", repo == "fastapi"); res["commit"].append(r["count"] > 0)
        for k in r["hits"]: rules["commit"][k] += 1
    # docs at a 2021 commit
    sha = sh("git rev-list -n1 --before=2021-06-01 HEAD", d).strip()
    files = [f for f in sh(f"git ls-tree -r --name-only {sha}", d).split() if f.endswith((".md", ".rst")) and "changelog" not in f.lower() and "history" not in f.lower()][:40]
    for f in files:
        text = sh(f"git show {sha}:{f}", d)
        if len(text.split()) < 200: continue
        r = score(text, "prose"); res["prose"].append(r["density"])
        for k, v in r["hits"].items(): rules["prose"][k] += len(v)
    # code diffs pre-2022
    for c in sh("git log --no-merges --before=2022-01-01 -n 60 --format=%H -- '*.py'", d).split():
        diff = sh(f"git show --format= {c} -- '*.py'", d)
        r = score(diff, "code")
        if r["words"] < 30: continue
        res["code"].append(r["density"])
        for k, v in r["hits"].items(): rules["code"][k] += len(v)
print(f"commits: {len(res['commit'])}, share with any tell {sum(res['commit'])/len(res['commit']):.1%}")
print(f"prose docs: {len(res['prose'])}, density per 1k words p50 {statistics.median(res['prose']):.2f} p90 {sorted(res['prose'])[int(.9*len(res['prose']))]:.2f}")
print(f"code diffs: {len(res['code'])}, density per 100 lines p50 {statistics.median(res['code']):.2f} p90 {sorted(res['code'])[int(.9*len(res['code']))]:.2f}")
for k, c in rules.items(): print(k, c.most_common(8))
