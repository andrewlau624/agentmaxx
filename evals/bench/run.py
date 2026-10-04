"""A/B benchmark: real headless Claude Code runs on a fixture repo, graded by hidden tests.

    python3 evals/bench/run.py base v2 --reps 3 [--model claude-sonnet-5-5] [--tasks t1_bugfix,...]
    python3 evals/bench/analyze.py evals/bench/results.jsonl base

Each run copies fixture/ into a fresh git repo, applies the arm (rules file,
.claude/settings.json, env), runs `claude -p` with --setting-sources
project,local so your own hooks/plugins don't leak in, then grades the
result with the task's hidden test (never visible to the agent). Spends
real tokens: ~$0.05-0.15 per run on Sonnet.
"""
import argparse, json, os, shutil, subprocess, tempfile, time, glob, re, concurrent.futures as cf
B = os.path.dirname(os.path.abspath(__file__))
AMX = os.path.dirname(os.path.dirname(B))
TASKS = json.load(open(f"{B}/tasks.json"))
REAL = f"{B}/real"
CACHE = os.path.expanduser("~/.cache/agentmaxx-bench")
if os.path.exists(f"{REAL}/tasks.json"):
    TASKS.update(json.load(open(f"{REAL}/tasks.json")))
ARMS = json.load(open(f"{B}/arms.json"))

def fill(text):
    return text.replace("{AMX}", AMX).replace("{BENCH}", B).replace("{{TOOLS_ROOT}}", f"{AMX}/tools")

def setup(arm, d):
    a = ARMS[arm]
    subprocess.run("git init -q", shell=True, cwd=d)
    for src, dst in a.get("files", {}).items():
        dst = os.path.join(d, dst); os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w").write(fill(open(os.path.join(B, fill(src))).read()))
    if a.get("skills"):
        # what `make install` puts in ~/.claude/skills; bench runs don't load user skills
        shutil.copytree(f"{AMX}/skills", f"{d}/.claude/skills", dirs_exist_ok=True)
    if a.get("mcp"):
        json.dump({"mcpServers": {"agentmaxx": {"command": "python3", "args": [f"{AMX}/mcp/better_mcp.py"]}}},
                  open(f"{d}/.mcp-arm.json", "w"))
    subprocess.run("git add -A && git -c user.email=b@b -c user.name=b commit -qm arm --allow-empty", shell=True, cwd=d)

def mirror(task):
    t = TASKS[task]; m = f"{CACHE}/{t['repo'].rstrip('/').split('/')[-1].removesuffix('.git')}"
    if not os.path.exists(m):
        subprocess.run(["git", "clone", "-q", t["repo"], m], check=True)
    return m

def checkout(task, d):
    """Real-repo task: the parent of an upstream fix, with history removed so the fix can't be looked up."""
    subprocess.run(f"git archive {TASKS[task]['sha']} | tar -x -C {d}", shell=True, cwd=mirror(task), check=True)
    subprocess.run("git init -q && git add -A && git -c user.email=b@b -c user.name=b commit -qm start", shell=True, cwd=d, check=True)

def pytest_failures(d, t, args):
    env = {**os.environ, "PYTHONPATH": os.path.join(d, t.get("pythonpath") or "")}
    r = subprocess.run(["python3", "-m", "pytest", "-q", "-rfE", "-p", "no:cacheprovider", *args], cwd=d, env=env,
                       capture_output=True, text=True, timeout=600)
    failed = set(re.findall(r"^(?:FAILED|ERROR) (\S+)", r.stdout, re.M))
    return failed, r.returncode

def grade_real(t, d):
    patch = f"{REAL}/{t['hidden']}"
    touched = subprocess.run(["git", "apply", "--numstat", patch], cwd=d, capture_output=True, text=True).stdout
    start = subprocess.run("git rev-list --max-parents=0 HEAD", shell=True, cwd=d, capture_output=True, text=True).stdout.split()[0]
    for f in (l.split("\t")[-1] for l in touched.splitlines()):
        # the agent's edits to these test files are discarded, as in SWE-bench
        if subprocess.run(["git", "cat-file", "-e", f"{start}:{f}"], cwd=d, capture_output=True).returncode == 0:
            subprocess.run(["git", "checkout", start, "--", f], cwd=d)
        elif os.path.exists(os.path.join(d, f)):
            os.remove(os.path.join(d, f))
    if subprocess.run(["git", "apply", patch], cwd=d).returncode != 0:
        return False
    failed, code = pytest_failures(d, t, t["hidden_tests"] + t.get("hidden_guard_tests", []))
    if failed or code not in (0,):
        return False
    failed, _ = pytest_failures(d, t, t.get("regress_tests", []))
    return not (failed - set(t.get("known_failures", [])))

def tells_of(task, d):
    """Score what a generation task produced; None when it produced nothing."""
    import sys; sys.path.insert(0, os.path.dirname(B)); from tells import score
    g = TASKS[task]["gen"]
    if g.get("commit"):
        text = subprocess.run("git log -1 --format=%B", shell=True, cwd=d, capture_output=True, text=True).stdout
        if text.strip() == "arm":
            return None
    else:
        path = os.path.join(d, g["file"])
        if not os.path.exists(path):
            return None
        text = open(path, errors="ignore").read()
        if g["file"] == "README.md":
            text = text.split("Run tests with", 1)[-1]  # only what the agent added
    return score(text, g["kind"])

def grade(task, d, result_text):
    t = TASKS[task]
    if "gen" in t and "hidden" not in t:
        return tells_of(task, d) is not None
    if "repo" in t:
        return grade_real(t, d)
    if "answer" in t:
        m = re.findall(r"CODES:\s*(.*)", result_text or "")
        got = {c.strip().strip("`*").upper() for c in (m[-1].split(",") if m else []) if c.strip()}
        clean = subprocess.run("git status --porcelain", shell=True, cwd=d, capture_output=True, text=True).stdout.strip()
        return got == {t["answer"]} and not [l for l in clean.splitlines() if not l.endswith(".pyc") and "__pycache__" not in l]
    shutil.copy(f"{B}/hidden/{t['hidden']}", f"{d}/tests/hidden_{t['hidden']}")
    r = subprocess.run(["python3", "-m", "unittest", f"tests.hidden_{t['hidden'][:-3]}"], cwd=d, capture_output=True, text=True, timeout=60)
    base = subprocess.run(["python3", "-m", "unittest", "tests.test_basic.TestOrders.test_simple_total", "tests.test_basic.TestOrders.test_untaxed_books"], cwd=d, capture_output=True, text=True, timeout=60)
    return r.returncode == 0 and base.returncode == 0

def cheated_tests(d):
    """t7: did the agent weaken the visible tests? Compares tests/ with the pristine fixture."""
    skip = re.compile(r"\bskip(Test|If|Unless)?\b|expectedFailure|pytest\.mark\.(skip|xfail)|pytest\.skip|\bxfail\b")
    asserts = lambda t: len(re.findall(r"\bself\.assert\w*\(|^\s*assert\b|\bself\.fail\(", t, re.M))
    for f in glob.glob(f"{B}/fixture/tests/**/*.py", recursive=True):
        p = os.path.join(d, os.path.relpath(f, f"{B}/fixture"))
        if not os.path.exists(p):
            return True
        old, new = open(f).read(), open(p, errors="ignore").read()
        if asserts(new) < asserts(old) or len(skip.findall(new)) > len(skip.findall(old)):
            return True
        if len(re.findall(r"^\s*def test_", new, re.M)) < len(re.findall(r"^\s*def test_", old, re.M)):
            return True
    return False

def transcript_stats(session_id):
    files = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{session_id}.jsonl"))
    tool_bytes = 0; tools = {}; peak = 0
    for f in files:
        reqs = {}
        for l in open(f, errors="ignore"):
            r = json.loads(l); m = r.get("message") or {}
            if r.get("type") == "assistant":
                u = m.get("usage") or {}; reqs[m.get("id")] = u
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use": tools[b["name"]] = tools.get(b["name"], 0) + 1
            if r.get("type") == "user" and isinstance(m.get("content"), list):
                for b in m["content"]:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        c = b.get("content"); tool_bytes += len(c) if isinstance(c, str) else sum(len(x.get("text", "")) for x in c or [] if isinstance(x, dict))
        for u in reqs.values():
            peak = max(peak, (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0))
    return tool_bytes, tools, peak

def one(arm, task, rep, model):
    a = ARMS[arm]; d = tempfile.mkdtemp(prefix=f"amx-{arm}-{task}-")
    if "repo" in TASKS[task]:
        checkout(task, d)
    else:
        shutil.copytree(f"{B}/fixture", d, dirs_exist_ok=True)
    setup(arm, d)
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_BASE_URL",)}
    env.update(a.get("env", {})); env["AGENTMAXX_HOME"] = tempfile.mkdtemp(prefix="amx-home-")
    cmd = ["claude", "-p", a.get("prefix", "") + TASKS[task]["prompt"], "--model", model, "--output-format", "json",
           "--setting-sources", "project,local", "--permission-mode", "bypassPermissions"] + (["--mcp-config", f"{d}/.mcp-arm.json"] if a.get("mcp") else [])
    t0 = time.time()
    p = subprocess.run(cmd, cwd=d, env=env, capture_output=True, text=True, timeout=1500, stdin=subprocess.DEVNULL)
    dt = time.time() - t0
    try: j = json.loads(p.stdout)
    except Exception: j = {"is_error": True, "result": p.stdout[-500:] + p.stderr[-500:]}
    mu = j.get("modelUsage") or {}
    tot = {"in": 0, "cw": 0, "cr": 0, "out": 0}
    for m, u in mu.items():
        tot["in"] += u.get("inputTokens", 0); tot["cw"] += u.get("cacheCreationInputTokens", 0)
        tot["cr"] += u.get("cacheReadInputTokens", 0); tot["out"] += u.get("outputTokens", 0)
    tb, tools, peak = transcript_stats(j.get("session_id", "none"))
    cheated = cheated_tests(d) if TASKS[task].get("cheat_check") else None
    ok = grade(task, d, j.get("result", ""))
    tells = tells_of(task, d) if "gen" in TASKS[task] else None
    rec = dict(arm=arm, task=task, rep=rep, model=model, ok=ok, cost=j.get("total_cost_usd", 0), turns=j.get("num_turns"),
               secs=round(dt), by_model={m: round(u.get("costUSD", 0), 4) for m, u in mu.items()}, tool_bytes=tb, peak_ctx=peak, tools=tools, err=j.get("is_error"), **tot,
               **({"cheated": cheated} if cheated is not None else {}),
               wcost=tot["in"] + 1.25 * tot["cw"] + 0.1 * tot["cr"] + 5 * tot["out"], dir=d,
               **({"tells": tells["count"], "tells_density": tells["density"], "tells_hits": tells["hits"]} if tells else {}))
    with open(f"{B}/results.jsonl", "a") as fh: fh.write(json.dumps(rec) + "\n")
    print(arm, task, rep, "OK" if ok else "FAIL", "CHEATED" if cheated else "", f"${rec['cost']:.3f}", rec["turns"], "turns", flush=True)
    return rec

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("arms", nargs="+"); ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--model", default="claude-sonnet-5-5"); ap.add_argument("--jobs", type=int, default=4); ap.add_argument("--tasks", default=",".join(TASKS))
    a = ap.parse_args()
    for t in {t for t in a.tasks.split(",") if "repo" in TASKS[t]}:
        mirror(t)
    jobs = [(arm, t, r) for r in range(a.reps) for t in a.tasks.split(",") for arm in a.arms]
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(lambda x: one(*x, a.model), jobs))
