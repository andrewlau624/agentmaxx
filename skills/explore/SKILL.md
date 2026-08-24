# Repository Exploration

## Purpose

Efficiently discover the minimum necessary code context for a task by using ranked search instead of undifferentiated exploration.

Instead of Claude spending tokens investigating irrelevant search results, `better-explore` pre-filters and ranks candidates by code relationships.

## When to Use

When starting work on:
- A large unfamiliar repository
- A vague task ("something is broken with invitations")
- A specific ticket ("PAC-4611")
- Any task where repository structure is not immediately obvious

## Workflow

```
1. Run better-explore with the task description
   ↓
2. Get ranked candidates with explanations
   ↓
3. Read the top 2-3 candidates using better-context/better-cat
   ↓
4. If a candidate mentions related files (imports/calls/tests),
   discover relationships and re-search with new keywords
   ↓
5. Stop when you have identified the change needed
```

## Example

**Task:** "Add organization invitations to Pacific"

**Explore:**
```
python3 better_explore.py "Add organization invitations" --path /repo
```

**Returns:**
```json
{
  "candidates": [
    "pacific/router/v1/organizations.py",
    "pacific/nerfguard/org/invite/service.py",
    "pacific/router/v1/workos_webhooks.py"
  ],
  "scores": [94, 89, 83],
  "reasoning": [
    "1. organizations.py (score: 94) - exact route match for organization invite",
    "2. invite/service.py (score: 89) - definition found for InvitationService",
    "3. workos_webhooks.py (score: 83) - webhook handler imports invitation logic"
  ]
}
```

Now you read the top candidate instead of the 40-match undifferentiated list.

## Ranking Evidence

The scoring system awards points for:

| Signal | Points |
|--------|--------|
| Task mentions exact file/line | +30 |
| Definition (class/function) | +25 |
| Test file | +15 |
| Source code (not vendor/doc) | +30 |
| Generated/vendor directory | -30 |
| Documentation only | -20 |

Candidates are deduplicated (highest score per file kept), then sorted and returned.

## Refinement Loop

After reading a file and discovering it imports `WorkOS`, you can search again:

```
better_explore.py "WorkOS invitation" --path /repo
```

This is typically handled by Claude as part of the normal exploration flow, not a single predefined command.

## Limitations

- Not a full code graph (no type hierarchy or type-based relationships yet)
- Keyword-based matching, not semantic search
- Doesn't weight by "closeness to main entry point"

These can be added later without changing the interface.

## Integration

The explore skill should be invoked early in task execution:

1. **Agent receives task**
2. **Agent runs better-explore**
3. **Agent reads top candidates**
4. **Agent proceeds with normal implementation flow**

It's most effective when used as the **first** exploration step, not after wandering through 5 false leads.
