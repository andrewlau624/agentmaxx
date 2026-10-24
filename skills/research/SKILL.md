---
name: research
description: Structured research loop with pre-declared stopping criteria, a disconfirming probe, and a per-repo hypothesis map. Use for any research task, literature or web search, "find out whether / is it true that" questions, strategy or hypothesis hunting, and autonomous research loops (keep looking, find something that works, think of other ideas).
---

# Research

Research fails by repeating itself: the same query in a new session, the same hypothesis in a new costume, no search for the evidence that would kill the answer. Each step below exists because transcripts showed that failure (evals/quality-research.md).

## 1. Before the first search: sufficiency criteria

Write 3-5 lines, each naming evidence that would settle part of the question and what would flip the answer:

```
C1 <claim>: settled by <source type / number>; flips if <finding>
```

Decide them now, not after reading. They are the stop rule.

## 2. Read what this repo already looked up

```sh
python3 ~/.claude/agentmaxx/hooks/research_log.py recent   # or python3 hooks/research_log.py recent from the agentmaxx repo
```

Then read the repo's do-not-redo / exhausted / killed sections if it has them (CLAUDE.md, `docs/research/`). Do not plan a query the log already answers; cite the earlier result instead. The hook denies near-duplicates of logged queries once per session; a deny means change the angle, not rephrase.

## 3. Hypothesis-space map (hypothesis-hunting loops)

Keep `docs/research/hypothesis-space.md` in the repo (create it if absent). It is a matrix: families x mechanisms x data sources, each cell `untested`, `killed (why, date)`, `passed`, or `blocked (what is missing)`.

```markdown
# Hypothesis space
| family \ mechanism | <mechanism A> | <mechanism B> | <mechanism C> |
|---|---|---|---|
| <family 1> | killed 10-04: no edge after costs | untested | blocked: needs tick data |
| <family 2> | passed 10-12 (see run #) | untested | untested |

Data sources: <source 1> (families 1-2), <source 2> (not yet used)
Siblings of killed cells worth one test: <cell> -> <named sibling>
```

Rule: the next study comes from an `untested` cell or a named sibling of a `killed` one. Never a re-costume of a killed cell (same mechanism, new indicator name, new parameter set). Update the cell before reporting the result. If every cell is killed or blocked, say so and stop; do not invent a cell.

## 4. Query plan

Before running, list the queries. The plan must contain at least:

- one broad query (the question as a newcomer would ask it);
- one disconfirming query: `<topic> fails | criticism | limitations | alternatives`;
- one source-type pivot: paper / official docs / forum or issue tracker / dataset, whichever the others did not use.

Pick perspectives from the structure of adjacent topics (how a neighbouring field, a regulator, a vendor, a practitioner would frame it), not by paraphrasing the topic itself. Three perspectives are enough; more without a gap-finder add little.

## 5. After each batch of reads: retrieved but unasked

List facts the sources volunteered that no query asked for. Spawn exactly one follow-up query from that list (the one that touches an uncovered criterion first). Then return to the plan.

## 6. Stop rule

Stop when every criterion in step 1 is covered and the last two searches added no new source domain. Over the limit, stop anyway and name which criteria stayed uncovered and what would cover them. Do not keep searching to feel thorough; do not stop early because the first source agreed.

## 7. Report shape

Two separate sections, always:

- **No edge / killed**: what was tested, the evidence, the date. These go into the hypothesis map and the do-not-redo list.
- **Edge unproven / untested forms**: what was *not* tested, by name (the sibling cell, the data source, the mechanism variant). "Nothing passed" without this section is not a finding.

Then the criteria table from step 1 with each line marked covered / uncovered.
