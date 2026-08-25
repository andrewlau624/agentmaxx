import { tool } from "@opencode-ai/plugin"

const TOOLS_ROOT =
  process.env.AGENTMAXX_TOOLS_ROOT ??
  `${process.env.HOME}/.config/opencode/agentmaxx/tools`

async function runPython(scriptPath, argv) {
  const proc = Bun.spawn(["python3", `${TOOLS_ROOT}/${scriptPath}`, ...argv], {
    stdout: "pipe",
    stderr: "pipe",
    cwd: process.cwd(),
  })
  const [stdout, stderr, code] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ])
  if (code !== 0) {
    return `exit ${code}: ${stderr.trim() || "no stderr"}\n${stdout}`
  }
  return stdout
}

const str = (description) => tool.schema.string().describe(description)
const optStr = (description) =>
  tool.schema.string().describe(description).optional()
const optInt = (description) =>
  tool.schema.number().int().describe(description).optional()

export const BetterToolsPlugin = async () => ({
  tool: {
    better_context: tool({
      description:
        "Search the repository and return matching source with surrounding context in ONE call. Prefer over grep-then-read sequences.",
      args: {
        query: str("one or more search keywords").array().min(1),
        path: optStr("directory to search (default cwd)"),
        max_hits: optInt("maximum number of matches"),
        context_lines: optInt("lines of surrounding context"),
        max_output_chars: optInt("output size cap"),
      },
      async execute(args) {
        const argv = args.query.map(String)
        if (args.path) argv.push("--path", args.path)
        if (args.max_hits) argv.push("--max-hits", String(args.max_hits))
        if (args.context_lines)
          argv.push("--context-lines", String(args.context_lines))
        if (args.max_output_chars)
          argv.push("--max-output-chars", String(args.max_output_chars))
        return runPython("better-context/better_context.py", argv)
      },
    }),

    better_grep: tool({
      description:
        "Ranked repository code search across multiple unrelated patterns at once.",
      args: {
        query: str("search patterns").array().min(1),
        path: optStr("directory to search"),
        type: optStr("file extension filter, e.g. py or ts"),
        max_results: optInt("result cap"),
      },
      async execute(args) {
        const argv = args.query.map(String)
        if (args.path) argv.push("--path", args.path)
        if (args.type) argv.push("--type", args.type)
        if (args.max_results)
          argv.push("--max-results", String(args.max_results))
        return runPython("better-grep/better_grep.py", argv)
      },
    }),

    better_cat: tool({
      description:
        "Read bounded file ranges without loading whole files. Spec format: 'path', 'path:12-40', 'path:12'.",
      args: {
        spec: str("file specs").array().min(1),
        max_output_chars: optInt("output size cap"),
      },
      async execute(args) {
        const argv = args.spec.map(String)
        if (args.max_output_chars)
          argv.push("--max-output-chars", String(args.max_output_chars))
        return runPython("better-cat/better_cat.py", argv)
      },
    }),

    better_find: tool({
      description: "Find files by glob name pattern, bounded results.",
      args: {
        path: optStr("directory to search (default cwd)"),
        name: optStr("glob pattern, e.g. '*.py'"),
        type: optStr("'f' for files, 'd' for directories"),
      },
      async execute(args) {
        const argv = []
        if (args.path) argv.push(args.path)
        if (args.name) argv.push("--name", args.name)
        if (args.type) argv.push("--type", args.type)
        return runPython("better-find/better_find.py", argv)
      },
    }),

    better_explore: tool({
      description:
        "Run FIRST when starting cold on an unfamiliar repo or vague task: ranks candidate files so you read the right one instead of dead-end greps that burn 10x context.",
      args: {
        task: str("task or question description"),
        path: optStr("repository root"),
        num_candidates: optInt("candidates to rank"),
        max_searches: optInt("search budget"),
      },
      async execute(args) {
        const argv = [args.task]
        if (args.path) argv.push("--path", args.path)
        if (args.num_candidates)
          argv.push("--num-candidates", String(args.num_candidates))
        if (args.max_searches)
          argv.push("--max-searches", String(args.max_searches))
        return runPython("better-explore/better_explore.py", argv)
      },
    }),

    better_edit: tool({
      description:
        "Apply a batch of exact-string edits across files, all-or-nothing atomic. Pass a JSON array of {path, old, new, replace_all?}.",
      args: {
        edits: str("JSON array of {path, old, new, replace_all?} objects"),
      },
      async execute(args) {
        return runPython("better-edit/better_edit.py", [args.edits])
      },
    }),
  },

  "experimental.session.compacting": async (input, output) => {
    output.context.push(
      [
        "## Working state (agentmaxx)",
        "Preserve across compaction, in priority order:",
        "- The active task and its acceptance criteria",
        "- Every file modified so far, and why each change was made",
        "- Decisions made, alternatives rejected, and user preferences stated",
        "- Verification status: what was tested, what passed, what remains",
        "- The exact next step to take after this summary",
      ].join("\n"),
    )
  },
})
