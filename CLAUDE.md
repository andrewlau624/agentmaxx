<!-- graymatter:instructions:begin — managed by `graymatter init`; edits inside this block are overwritten -->
## Memory (GrayMatter)

You have persistent memory through the `graymatter` MCP tools. Wiring the MCP
server only makes them available; nothing calls them for you. That is your job,
every session.

This block can be installed globally, so it may reach a project that has no
GrayMatter wired. If `memory_search` is not in your toolbelt for this session,
skip the rest of this section. That is a check on what tools exist, not a
judgement call about whether memory seems useful: if the tools are there,
everything below applies.

### Your identity

Your `agent_id` is the name of this repository's root directory, used verbatim
every session. Add a `-<role>` suffix only when several agents share the repo
(`myapp-backend`, `myapp-frontend`). Inventing a new id per session scatters
your facts across namespaces and looks exactly like memory being broken.

Facts every agent in the project should see go to the reserved id `__shared__`.

### Every session, without exception

1. **Before your first reply**, call `memory_search` with the user's request as
   the query. Then call it again with `agent_id` set to `__shared__`. Fold both
   results into your working context before you answer.
2. **Resuming long-running work**: `checkpoint_resume` first.
3. **Before you stop**, store what you learned (see the table) and call
   `checkpoint_save` if the task is unfinished.

### What triggers a call

| When this happens | Call |
|---|---|
| You start any task | `memory_search` |
| The user states a preference | `memory_add` |
| You discover a project convention | `memory_add` with `agent_id: "__shared__"` |
| You make a non-obvious decision | `memory_add`, include the reasoning |
| You fix a non-trivial bug or find a workaround | `memory_add` |
| The user corrects you | `memory_reflect` with `action="update"` |
| A stored fact became wrong | `memory_reflect` with `action="forget"` |

Err toward storing. A fact you never needed costs nothing. One you failed to
store costs the same mistake a second time.

### The tools

| Tool | Required | Optional |
|---|---|---|
| `memory_search` | `agent_id`, `query` | `top_k` (default 8) |
| `memory_add` | `agent_id`, `text` | |
| `memory_reflect` | `action`, `agent` | `text`, `target` |
| `checkpoint_save` | `agent_id` | `state` |
| `checkpoint_resume` | `agent_id` | |

⚠ `memory_reflect` takes `agent`, not `agent_id`. The other four take
`agent_id`. Mixing them up fails validation.

### Store conclusions, not transcripts

One idea per call. Skip anything already in the code or the README, anything
transient (that is what checkpoints are for), and never store secrets.
<!-- graymatter:instructions:end -->
