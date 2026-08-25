import { tool } from "@opencode-ai/plugin"
import { execFile } from "node:child_process"
import { statSync } from "node:fs"
import path from "node:path"

const TOOLS_ROOT =
  process.env.AGENTMAXX_TOOLS_ROOT ??
  `${process.env.HOME}/.config/opencode/agentmaxx/tools`

// execFile (node API) instead of Bun.spawn: opencode's plugin sandbox does
// not expose the Bun global. Runs in the session directory so relative
// paths in tool arguments resolve against the project.
function runPython(scriptPath, argv, cwd) {
  return new Promise((resolve) => {
    execFile(
      "python3",
      [`${TOOLS_ROOT}/${scriptPath}`, ...argv],
      { cwd, maxBuffer: 32 * 1024 * 1024 },
      (error, stdout, stderr) => {
        if (error && !stdout) {
          resolve(
            `exit ${error.code ?? "?"}: ${String(stderr).trim() || error.message}`,
          )
          return
        }
        if (error) {
          resolve(`${stdout}\nexit ${error.code ?? "?"}: ${String(stderr).trim()}`)
          return
        }
        resolve(stdout)
      },
    )
  })
}

const str = (description) => tool.schema.string().describe(description)
const optStr = (description) =>
  tool.schema.string().describe(description).optional()
const optInt = (description) =>
  tool.schema.number().int().describe(description).optional()

// Unbounded reads are the dominant resident-byte source in long sessions:
// a 56KB whole-file read re-bills on every subsequent turn. The before-hook
// redirects oversized reads to ranged alternatives at the moment of choice.
const READ_LIMIT_BYTES = 12 * 1024
const sessionTurns = new Map()

export const BetterToolsPlugin = async () => ({
  tool: {
    better_context: tool({
      description:
        "Search the repository and return matching source with surrounding context in ONE call. Prefer over grep-then-read sequences.",
      args: {
        query: str("one or more search keywords").array().min(1),
        path: optStr("directory to search (default session directory)"),
        max_hits: optInt("maximum number of matches"),
        context_lines: optInt("lines of surrounding context"),
        max_output_chars: optInt("output size cap"),
      },
      async execute(args, context) {
        const argv = args.query.map(String)
        if (args.path) argv.push("--path", args.path)
        if (args.max_hits) argv.push("--max-hits", String(args.max_hits))
        if (args.context_lines)
          argv.push("--context-lines", String(args.context_lines))
        if (args.max_output_chars)
          argv.push("--max-output-chars", String(args.max_output_chars))
        return runPython("better-context/better_context.py", argv, context.directory)
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
      async execute(args, context) {
        const argv = args.query.map(String)
        if (args.path) argv.push("--path", args.path)
        if (args.type) argv.push("--type", args.type)
        if (args.max_results)
          argv.push("--max-results", String(args.max_results))
        return runPython("better-grep/better_grep.py", argv, context.directory)
      },
    }),

    better_cat: tool({
      description:
        "Read bounded file ranges without loading whole files. Spec format: 'path', 'path:12-40', 'path:12'.",
      args: {
        spec: str("file specs").array().min(1),
        max_output_chars: optInt("output size cap"),
      },
      async execute(args, context) {
        const argv = args.spec.map(String)
        if (args.max_output_chars)
          argv.push("--max-output-chars", String(args.max_output_chars))
        return runPython("better-cat/better_cat.py", argv, context.directory)
      },
    }),

    better_find: tool({
      description: "Find files by glob name pattern, bounded results.",
      args: {
        path: optStr("directory to search (default session directory)"),
        name: optStr("glob pattern, e.g. '*.py'"),
        type: optStr("'f' for files, 'd' for directories"),
      },
      async execute(args, context) {
        const argv = []
        if (args.path) argv.push(args.path)
        if (args.name) argv.push("--name", args.name)
        if (args.type) argv.push("--type", args.type)
        return runPython("better-find/better_find.py", argv, context.directory)
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
      async execute(args, context) {
        const argv = [args.task]
        if (args.path) argv.push("--path", args.path)
        if (args.num_candidates)
          argv.push("--num-candidates", String(args.num_candidates))
        if (args.max_searches)
          argv.push("--max-searches", String(args.max_searches))
        return runPython("better-explore/better_explore.py", argv, context.directory)
      },
    }),

    better_edit: tool({
      description:
        "Apply a batch of exact-string edits across files, atomic (all succeed or nothing written). Pass a JSON array of {path, old, new, replace_all?}.",
      args: {
        edits: str("JSON array of {path, old, new, replace_all?} objects"),
      },
      async execute(args, context) {
        return runPython("better-edit/better_edit.py", [args.edits], context.directory)
      },
    }),
  },

  "tool.execute.before": async (input, output) => {
    const turns = (sessionTurns.get(input.sessionID) ?? 0) + 1
    sessionTurns.set(input.sessionID, turns)

    if (input.tool !== "read") return
    const filePath = output.args?.filePath
    if (!filePath) return

    let stats
    try {
      stats = statSync(path.resolve(filePath))
    } catch {
      return
    }
    if (!stats.isFile() || stats.size <= READ_LIMIT_BYTES) return

    const kb = Math.round(stats.size / 1024)
    const lines = Math.round(stats.size / 42)
    const tokens = Math.round(stats.size / 4)
    const remainingTurns = Math.max(700 - turns, 100)
    const tokEqCached = Math.round((tokens * remainingTurns * 0.1) / 1000)

    throw new Error(
      `[agentmaxx] ${kb}KB / ~${lines} lines — a whole-file read here re-bills ` +
        `every remaining turn: ~${tokEqCached}K tok-eq by session end even at ` +
        `cache rates. Read the relevant range instead: better_cat "${filePath}:start-end", ` +
        `or re-issue read with explicit offset+limit.`,
    )
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
