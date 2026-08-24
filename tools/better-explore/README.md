# better-explore

Fast repository discovery for coding tasks.

## Purpose

Reduces exploration-phase token cost by directing agents to the minimum necessary files to complete a task.

Instead of:
```
task → grep → read 500 lines → not here → search again → read 800 lines → ...
```

better-explore does the mechanical work:
```
task → cheap searches → rank candidates → return ranked list
```

The ranking understands code relationships (imports, calls, tests), so you get:
```
1. organizations.py (score: 94)
2. invite/service.py (score: 89)
3. workos_webhooks.py (score: 83)
```

Instead of:
```
40 matches (undifferentiated)
```

## Usage

```bash
better_explore.py "Add Pacific organization invitations" \
  --path /path/to/repo \
  --num-candidates 5 \
  --max-searches 30
```

## Output

JSON with:
- `candidates`: ranked file paths
- `scores`: score for each candidate
- `reasoning`: explanation of ranking
- `total_matched`: total matches found
- `total_unique`: unique files matched

## Implementation

The ranking system assigns evidence points:

| Evidence | Points |
|----------|--------|
| Explicit mention in task | +30 |
| Definition (class/func) | +25 |
| Test file | +15 |
| Source code | +30 |
| Generated/vendor | -30 |

Candidates are then sorted and deduplicated, keeping the highest score for each file.

## Iterative Refinement

After reading a candidate, you can discover related imports/calls and re-rank to guide the next search. This is typically handled by the agent calling better-explore, not the tool itself.
