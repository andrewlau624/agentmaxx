## Memory (GrayMatter)

If `memory_search` is available: agent_id is the repo root dir name; `__shared__` holds project-wide facts.
- Search when the task continues earlier work or depends on a past decision. Skip it for self-contained tasks.
- Store one sentence per fact: user preferences, non-obvious decisions with the reason, workarounds. Corrections go
  through `memory_reflect` action=update (it takes `agent`, not `agent_id`). Nothing already in the code, no secrets.
- `checkpoint_save` when stopping mid-task; `checkpoint_resume` when picking it back up.
