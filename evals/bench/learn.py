"""Cross-session learning benchmark: does a correction in one session change the next one?

    SCENARIO=commit python3 evals/bench/learn.py nolessons,lessons 5

Session 1 does a task; the user then corrects a convention (commit with a
'shopkit: ' prefix, or add a CHANGELOG entry). Session 2 is a fresh process
on a fresh clone doing a different task. Graded: does session 2 follow the
convention unprompted? The lessons arm has the agentmaxx lessons hooks;
both arms get the same lean contract and the same correction.
"""
import json, os, shutil, subprocess, sys, tempfile, concurrent.futures as cf
B = os.path.dirname(os.path.abspath(__file__)); AMX = os.path.dirname(os.path.dirname(B))
TASKS = json.load(open(f"{B}/tasks.json"))
SCENARIO = os.environ.get("SCENARIO", "changelog")
CORRECT_COMMIT = ("You didn't commit your work. In this repo, always commit your finished work yourself "
                  "when a task is done, with a commit message that starts with 'shopkit: '. Please do that now.")
CORRECT = ("You forgot to add an entry to CHANGELOG.md. In this repo every behavior change needs a "
           "one-line CHANGELOG entry under ## Unreleased. Please add it.")

def settings(home):
    l = f"AGENTMAXX_HOME={home} python3 {AMX}/hooks/lessons.py hook"
    return {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": f"{l} session-start"}]}],
                      "UserPromptSubmit": [{"hooks": [{"type": "command", "command": f"{l} prompt"}]}]},
            "env": {"AGENTMAXX_HOME": home}}

def fresh(arm, home):
    d = tempfile.mkdtemp(prefix=f"amxl-{arm}-"); shutil.copytree(f"{B}/fixture", d, dirs_exist_ok=True)
    shutil.copy(f"{B}/changelog.md", f"{d}/CHANGELOG.md")
    shutil.copy(f"{AMX}/templates/CLAUDE.md", f"{d}/CLAUDE.md")
    # Fixed author/date so every clone shares one root commit: lessons are keyed by it.
    subprocess.run("git init -q && git add -A && GIT_AUTHOR_DATE=2026-01-01T00:00:00 GIT_COMMITTER_DATE=2026-01-01T00:00:00 "
                   "git -c user.email=b@b -c user.name=b commit -qm init", shell=True, cwd=d)
    if arm == "lessons":
        os.makedirs(f"{d}/.claude", exist_ok=True); json.dump(settings(home), open(f"{d}/.claude/settings.json", "w"))
    subprocess.run("git add -A && git -c user.email=b@b -c user.name=b commit -qm arm", shell=True, cwd=d)
    return d

def claude(d, prompt, home, resume=None):
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_BASE_URL"}
    env.update(ENABLE_TOOL_SEARCH="true", CLAUDE_CODE_DISABLE_AUTO_MEMORY="1", AGENTMAXX_HOME=home)
    cmd = ["claude", "-p", prompt, "--model", "claude-sonnet-5-5", "--output-format", "json",
           "--setting-sources", "project,local", "--permission-mode", "bypassPermissions"] + (["--resume", resume] if resume else [])
    p = subprocess.run(cmd, cwd=d, env=env, capture_output=True, text=True, timeout=1500, stdin=subprocess.DEVNULL)
    return json.loads(p.stdout)

def changelog_touched(d):
    diff = subprocess.run("git diff HEAD -- CHANGELOG.md", shell=True, cwd=d, capture_output=True, text=True).stdout
    return any(l.startswith("+") and not l.startswith("+++") and l.strip("+ ").strip() for l in diff.splitlines())

def committed(d):
    log = subprocess.run("git log --format=%s -n 5", shell=True, cwd=d, capture_output=True, text=True).stdout
    return any(l.startswith("shopkit:") for l in log.splitlines())

def one(arm, rep):
    home = tempfile.mkdtemp(prefix="amxhome-")
    d1 = fresh(arm, home)
    j1 = claude(d1, TASKS["t2_feature"]["prompt"], home)
    check = committed if SCENARIO == "commit" else changelog_touched
    s1 = check(d1)
    j1b = claude(d1, CORRECT_COMMIT if SCENARIO == "commit" else CORRECT, home, resume=j1["session_id"])
    s1b = check(d1)
    d2 = fresh(arm, home)
    j2 = claude(d2, TASKS["t6_regions"]["prompt"], home)
    s2 = check(d2)
    lessons = open(f"{home}/lessons/" + os.listdir(f"{home}/lessons")[0]).read() if os.path.isdir(f"{home}/lessons") and os.listdir(f"{home}/lessons") else ""
    rec = dict(arm=arm, rep=rep, scenario=SCENARIO, s1=s1, s1_after_fix=s1b, s2=s2, lesson=lessons.strip(),
               cost=sum(j.get("total_cost_usd", 0) for j in (j1, j1b, j2)), s2_cost=j2.get("total_cost_usd", 0))
    open(f"{B}/learn_{SCENARIO}.jsonl", "a").write(json.dumps(rec) + "\n"); print(rec, flush=True)

if __name__ == "__main__":
    arms = sys.argv[1].split(","); reps = int(sys.argv[2])
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda x: one(*x), [(a, r) for r in range(reps) for a in arms]))
