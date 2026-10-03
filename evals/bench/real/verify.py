#!/usr/bin/env python3
"""Verify the real-repo bench tasks in tasks.json (stdlib only).

For each task:
  1. clone (or fetch) the repo into ~/.cache/agentmaxx-bench/<name>
  2. create a fresh detached worktree at `sha` (the parent commit)
  3. apply hidden.patch; every `hidden_tests` node must FAIL,
     every `hidden_guard_tests` node must PASS
  4. apply fix.patch; every hidden + guard node must PASS
  5. run `regress_tests`; failures must be a subset of `known_failures`

Usage: python3 verify.py [task_id ...] [--no-regress] [--keep]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.expanduser("~/.cache/agentmaxx-bench")


def run(cmd, cwd=None, env=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def git(*args, cwd=None):
    r = run(["git", *args], cwd=cwd)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def ensure_clone(url, sha):
    name = url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    path = os.path.join(CACHE, name)
    if not os.path.isdir(path):
        os.makedirs(CACHE, exist_ok=True)
        git("clone", "-q", url, path)
    if run(["git", "cat-file", "-e", sha + "^{commit}"], cwd=path).returncode:
        git("fetch", "-q", "origin", cwd=path)
    return path


def pytest_env(task):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env["PYTHONPATH"] = task.get("pythonpath") or ""
    return env


def node_passes(wt, task, node):
    """True = passed, False = failed, None = not collected / usage error."""
    r = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", node],
            cwd=wt, env=pytest_env(task))
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        return False
    return None


def regress_failures(wt, task):
    xml = os.path.join(wt, ".verify-junit.xml")
    run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "--junitxml", xml, *task.get("regress_tests", ["tests"])],
        cwd=wt, env=pytest_env(task), timeout=1800)
    fails, total = [], 0
    for tc in ET.parse(xml).getroot().iter("testcase"):
        total += 1
        if tc.find("failure") is not None or tc.find("error") is not None:
            fails.append(f"{tc.get('classname')}::{tc.get('name')}")
    return fails, total


def known(name, task):
    # junit names look like "tests.test_x.Class::test_y"; known_failures are node ids
    for k in task.get("known_failures", []):
        mod_cls, _, test = name.rpartition("::")
        if k.endswith("::" + test) and k.replace(".py", "").replace("/", ".").startswith(mod_cls.split("::")[0]):
            return True
    return False


def verify(tid, task, do_regress=True, keep=False):
    problems = []
    repo = ensure_clone(task["repo"], task["sha"])
    wt = tempfile.mkdtemp(prefix=f"bench-{tid}-")
    os.rmdir(wt)
    git("worktree", "add", "-q", "--detach", wt, task["sha"], cwd=repo)
    info = {}
    try:
        git("apply", os.path.join(HERE, task["hidden"]), cwd=wt)
        for n in task["hidden_tests"]:
            r = node_passes(wt, task, n)
            if r is not False:
                problems.append(f"hidden test did not fail before fix ({'passed' if r else 'not collected'}): {n}")
        for n in task.get("hidden_guard_tests", []):
            if node_passes(wt, task, n) is not True:
                problems.append(f"guard test not passing before fix: {n}")
        git("apply", os.path.join(HERE, task["fix"]), cwd=wt)
        for n in task["hidden_tests"] + task.get("hidden_guard_tests", []):
            if node_passes(wt, task, n) is not True:
                problems.append(f"test not passing after fix: {n}")
        if do_regress:
            fails, total = regress_failures(wt, task)
            info["regress_total"] = total
            unexpected = [f for f in fails if not known(f, task)]
            if unexpected:
                problems.append(f"unexpected regress failures after fix: {unexpected[:5]}")
    except Exception as e:  # noqa: BLE001
        problems.append(f"error: {e}")
    finally:
        if keep:
            info["worktree"] = wt
        else:
            run(["git", "worktree", "remove", "--force", wt], cwd=repo)
    return problems, info


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_regress = "--no-regress" not in sys.argv
    keep = "--keep" in sys.argv
    tasks = json.load(open(os.path.join(HERE, "tasks.json")))
    ids = args or list(tasks)
    ok = 0
    for tid in ids:
        t = tasks[tid]
        problems, info = verify(tid, t, do_regress, keep)
        status = "PASS" if not problems else "FAIL"
        ok += not problems
        extra = f" regress={info['regress_total']} tests" if "regress_total" in info else ""
        print(f"{status}  {tid:42s} hidden={len(t['hidden_tests'])} fail->pass"
              f" guard={len(t.get('hidden_guard_tests', []))}{extra}", flush=True)
        for p in problems:
            print("      " + p, flush=True)
        if keep:
            print("      worktree: " + info["worktree"])
    print(f"\n{ok}/{len(ids)} tasks verified")
    sys.exit(0 if ok == len(ids) else 1)


if __name__ == "__main__":
    main()
