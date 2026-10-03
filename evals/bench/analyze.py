import os, json, sys, statistics as st, collections
MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")
recs = [r for r in (json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else "results.jsonl")) if r["model"] == MODEL]
base = sys.argv[2] if len(sys.argv) > 2 else "base"
by = collections.defaultdict(list)
for r in recs: by[(r["arm"], r["task"])].append(r)
arms = sorted({r["arm"] for r in recs}, key=lambda a: (a != base, a)); tasks = sorted({r["task"] for r in recs})
print(f"{'arm':10} {'pass':>7} {'$/task med':>10} {'vs base':>8} {'cw med':>8} {'cr med':>9} {'out med':>8} {'turns':>6} {'peak ctx':>9} {'toolKB':>7}")
for a in arms:
    rs = [r for r in recs if r["arm"] == a]
    # per-task medians, then mean over tasks (equal task weight)
    def m(k): return st.mean(st.median(x[k] for x in by[(a, t)]) for t in tasks if by[(a, t)])
    rel = st.mean(st.median(x["cost"] for x in by[(a, t)]) / st.median(x["cost"] for x in by[(base, t)]) for t in tasks if by[(a, t)] and by[(base, t)])
    print(f"{a:10} {sum(r['ok'] for r in rs):>3}/{len(rs):<3} {m('cost'):>10.3f} {(rel-1)*100:>+7.0f}% {m('cw'):>8.0f} {m('cr'):>9.0f} {m('out'):>8.0f} {m('turns'):>6.1f} {m('peak_ctx'):>9.0f} {m('tool_bytes')/1024:>7.1f}")
print()
for t in tasks:
    print(t, "  ".join(f"{a}:{sum(x['ok'] for x in by[(a,t)])}/{len(by[(a,t)])} ${st.median(x['cost'] for x in by[(a,t)]):.3f}" for a in arms if by[(a,t)]))
