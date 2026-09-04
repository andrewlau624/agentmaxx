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
const optBool = (description) =>
  tool.schema.boolean().describe(description).optional()

// The better-* tools, one opencode registration each. Every script under
// agentmaxx/tools is registered here so the contract's advertised set and the
// native tool list never diverge — a tool the agent is told exists but cannot
// call is the failure mode "abilities not applying" describes.
const TOOLS = [
  {
    name: "better_context",
    script: "better-context/better_context.py",
    description:
      "Search the repository and return matching source with surrounding context in ONE call. Prefer over grep-then-read sequences.",
    buildArgs(args) {
      const argv = args.query.map(String)
      if (args.path) argv.push("--path", args.path)
      if (args.max_hits) argv.push("--max-hits", String(args.max_hits))
      if (args.context_lines)
        argv.push("--context-lines", String(args.context_lines))
      if (args.max_output_chars)
        argv.push("--max-output-chars", String(args.max_output_chars))
      return argv
    },
    args: {
      query: str("one or more search keywords").array().min(1),
      path: optStr("directory to search (default session directory)"),
      max_hits: optInt("maximum number of matches"),
      context_lines: optInt("lines of surrounding context"),
      max_output_chars: optInt("output size cap"),
    },
  },
  {
    name: "better_grep",
    script: "better-grep/better_grep.py",
    description:
      "Search repository code with ranked, bounded results. Accepts multiple patterns in one call.",
    buildArgs(args) {
      const argv = args.query.map(String)
      if (args.path) argv.push("--path", args.path)
      if (args.max_results) argv.push("--max-results", String(args.max_results))
      if (args.max_output_chars)
        argv.push("--max-output-chars", String(args.max_output_chars))
      return argv
    },
    args: {
      query: str("one or more search patterns").array().min(1),
      path: optStr("directory to search (default session directory)"),
      type: optStr("file extension filter, e.g. py or ts"),
      max_results: optInt("result cap"),
      max_output_chars: optInt("output size cap"),
    },
  },
  {
    name: "better_cat",
    script: "better-cat/better_cat.py",
    description:
      "Read bounded file ranges without loading whole files. Accepts multiple specs: path, path:12-40, path:12- or path:12.",
    buildArgs(args) {
      return args.spec.map(String)
    },
    args: {
      spec: str("file specs: path, path:12-40, path:12- or path:12").array().min(1),
      max_output_chars: optInt("output size cap"),
    },
  },
  {
    name: "better_find",
    script: "better-find/better_find.py",
    description:
      "Find repository files with bounded, structured results, skipping generated/dependency directories.",
    buildArgs(args) {
      const argv = []
      if (args.path) argv.push(String(args.path))
      if (args.name) argv.push("--name", String(args.name))
      if (args.type) argv.push("--type", String(args.type))
      if (args.max_results) argv.push("--max-results", String(args.max_results))
      return argv
    },
    args: {
      path: optStr("directory to search (default session directory)"),
      name: optStr("glob pattern, e.g. '*.py'"),
      type: optStr("'f' for files, 'd' for directories"),
      max_results: optInt("result cap"),
    },
  },
  {
    name: "better_explore",
    script: "better-explore/better_explore.py",
    description:
      "Repository code discovery agent. Finds candidate files for a task, ranks by code relationships, and returns a prioritized reading list.",
    buildArgs(args) {
      const argv = [String(args.task)]
      if (args.path) argv.push("--path", args.path)
      if (args.num_candidates)
        argv.push("--num-candidates", String(args.num_candidates))
      if (args.max_searches)
        argv.push("--max-searches", String(args.max_searches))
      return argv
    },
    args: {
      task: str("task or question description"),
      path: optStr("repository root"),
      num_candidates: optInt("candidates to rank"),
      max_searches: optInt("search budget"),
    },
  },
  {
    name: "better_edit",
    script: "better-edit/better_edit.py",
    description:
      "Apply a batch of exact-string edits across files, atomic (all succeed or nothing written). Pass a JSON array of {path, old, new, replace_all?}.",
    buildArgs(args) {
      return [args.edits]
    },
    args: {
      edits: str("JSON array of {path, old, new, replace_all?} objects"),
    },
  },
  {
    name: "better_tree",
    script: "better-tree/better_tree.py",
    description:
      "Bounded directory tree, skipping generated/dependency directories by default.",
    buildArgs(args) {
      const argv = []
      if (args.path) argv.push(String(args.path))
      if (args.depth) argv.push("--depth", String(args.depth))
      if (args.max_entries) argv.push("--max-entries", String(args.max_entries))
      if (args.hidden) argv.push("--hidden")
      if (args.include_ignored) argv.push("--include-ignored")
      return argv
    },
    args: {
      path: optStr("directory to tree"),
      depth: optInt("max depth"),
      max_entries: optInt("max entries"),
      hidden: optBool("include hidden files"),
      include_ignored: optBool("include ignored files"),
    },
  },
  {
    name: "better_blame",
    script: "better-blame/better_blame.py",
    description: "Compact git blame — one file, optional line range or revision.",
    buildArgs(args) {
      const argv = [String(args.path)]
      if (args.L) argv.push("-L", String(args.L))
      if (args.revision) argv.push("-r", String(args.revision))
      if (args.context) argv.push("--context", String(args.context))
      if (args.max_lines) argv.push("--max-lines", String(args.max_lines))
      return argv
    },
    args: {
      path: str("file path"),
      L: optStr("line range, e.g. '12-40'"),
      revision: optStr("git revision"),
      context: optInt("context lines"),
      max_lines: optInt("max output lines"),
    },
  },
  {
    name: "better_git",
    script: "better-git/better_git.py",
    description:
      "Repository state, history, diffs, conflicts, branches, stashes, tags, remotes, and PR context.",
    buildArgs(args) {
      return [String(args.command), ...(args.args ?? []).map(String)]
    },
    args: {
      command: str(
        "status, branch, diff, diff-summary, changed, recent, log, inspect, show, conflicts, check, context, review, review-branch, commit-context, fix-context, merge-context, rebase-context, ship-context, branch-context, verify-context, stash, tag, remote, pr-context",
      ),
      args: str("arguments for the command").array().optional(),
    },
  },
  {
    name: "better_check",
    script: "better-check/better_check.py",
    description:
      "Compact project verification — runs test/lint/typecheck/build and reports structured results.",
    buildArgs(args) {
      const argv = []
      for (const [flag, value] of [
        ["--test", args.test],
        ["--lint", args.lint],
        ["--typecheck", args.typecheck],
        ["--build", args.build],
      ]) {
        if (value?.length) for (const cmd of value) argv.push(flag, String(cmd))
      }
      if (args.timeout) argv.push("--timeout", String(args.timeout))
      if (args.max_output) argv.push("--max-output", String(args.max_output))
      if (args.stop_on_failure) argv.push("--stop-on-failure")
      if (args.quiet) argv.push("--quiet")
      return argv
    },
    args: {
      test: str("test command").array().optional(),
      lint: str("lint command").array().optional(),
      typecheck: str("typecheck command").array().optional(),
      build: str("build command").array().optional(),
      timeout: optInt("timeout seconds"),
      max_output: optInt("max output bytes"),
      stop_on_failure: optBool("stop on first failure"),
      quiet: optBool("quiet output"),
    },
  },
  {
    name: "better_lint",
    script: "better-lint/better_lint.py",
    description:
      "Compact lint interface — auto-detects a linter or runs an explicit command.",
    buildArgs(args) {
      const argv = []
      if (args.linter) argv.push("--linter", String(args.linter))
      if (args.timeout) argv.push("--timeout", String(args.timeout))
      if (args.max_output) argv.push("--max-output", String(args.max_output))
      if (args.quiet) argv.push("--quiet")
      if (args.command) argv.push(...args.command.map(String))
      return argv
    },
    args: {
      linter: optStr("ruff, flake8, pylint, eslint, biome, clippy, go-vet"),
      timeout: optInt("timeout seconds"),
      max_output: optInt("max output bytes"),
      quiet: optBool("quiet output"),
      command: str("explicit lint command").array().optional(),
    },
  },
  {
    name: "better_test",
    script: "better-test/better_test.py",
    description: "Run tests with bounded, structured output.",
    buildArgs(args) {
      const argv = []
      if (args.framework) argv.push("--framework", String(args.framework))
      if (args.command) argv.push("--command", String(args.command))
      if (args.timeout) argv.push("--timeout", String(args.timeout))
      if (args.max_output) argv.push("--max-output", String(args.max_output))
      if (args.quiet) argv.push("--quiet")
      return argv
    },
    args: {
      framework: optStr("pytest, unittest, or npm"),
      command: optStr("test command"),
      timeout: optInt("timeout seconds"),
      max_output: optInt("max output bytes"),
      quiet: optBool("quiet output"),
    },
  },
  {
    name: "better_symbol",
    script: "better-symbol/better_symbol.py",
    description:
      "Universal symbol finder. Locate definitions, usages, and implementations of classes, functions, types.",
    buildArgs(args) {
      const argv = [String(args.symbol)]
      if (args.kind) argv.push("--kind", String(args.kind))
      if (args.path) argv.push("--path", args.path)
      if (args.max_results) argv.push("--max-results", String(args.max_results))
      return argv
    },
    args: {
      symbol: str("symbol name"),
      kind: optStr("definition, usage, or implementation"),
      path: optStr("directory to search"),
      max_results: optInt("result cap"),
    },
  },
  {
    name: "better_trace",
    script: "better-trace/better_trace.py",
    description:
      "Call graph tracer. Understand what calls a function and what it calls.",
    buildArgs(args) {
      const argv = [String(args.function)]
      if (args.direction) argv.push("--direction", String(args.direction))
      if (args.depth) argv.push("--depth", String(args.depth))
      if (args.path) argv.push("--path", args.path)
      if (args.show_entry_points) argv.push("--show-entry-points")
      if (args.max_results) argv.push("--max-results", String(args.max_results))
      return argv
    },
    args: {
      function: str("function name"),
      direction: optStr("callers, callees, or both"),
      depth: optInt("max depth"),
      path: optStr("directory to search"),
      show_entry_points: optBool("show entry points"),
      max_results: optInt("result cap"),
    },
  },
  {
    name: "better_related",
    script: "better-related/better_related.py",
    description:
      "File relationship mapper. Find imports, imported_by, tests, and dependents in one call.",
    buildArgs(args) {
      const argv = [String(args.file)]
      if (args.kind) argv.push("--kind", String(args.kind))
      if (args.path) argv.push("--path", args.path)
      if (args.max_results) argv.push("--max-results", String(args.max_results))
      return argv
    },
    args: {
      file: str("file path"),
      kind: optStr("all, imports, imported_by, tests, or dependents"),
      path: optStr("directory to search"),
      max_results: optInt("result cap"),
    },
  },
  {
    name: "better_types",
    script: "better-types/better_types.py",
    description:
      "Type/interface signature extractor. Get type definitions without implementation.",
    buildArgs(args) {
      const argv = [String(args.typename)]
      if (args.kind) argv.push("--kind", String(args.kind))
      if (args.path) argv.push("--path", args.path)
      return argv
    },
    args: {
      typename: str("type name"),
      kind: optStr("all, class, interface, type, or struct"),
      path: optStr("directory to search"),
    },
  },
  {
    name: "better_error",
    script: "better-error/better_error.py",
    description:
      "Exception parser. Extract actionable error context from stack traces.",
    buildArgs(args) {
      const argv = []
      if (args.file) argv.push("--file", String(args.file))
      if (args.content) argv.push("--content", String(args.content))
      return argv
    },
    args: {
      file: optStr("path to a stack trace file"),
      content: optStr("stack trace text"),
    },
  },
  {
    name: "better_diff",
    script: "better-diff/better_diff.py",
    description: "Ranked diff generator. Show what changed with minimal context.",
    buildArgs(args) {
      const argv = [String(args.path)]
      if (args.since) argv.push("--since", String(args.since))
      if (args.commits) argv.push("--commits", String(args.commits))
      if (args.max_output) argv.push("--max-output", String(args.max_output))
      return argv
    },
    args: {
      path: str("file or directory path"),
      since: optStr("time, e.g. '1 week ago'"),
      commits: optInt("number of commits"),
      max_output: optInt("output size cap"),
    },
  },
  {
    name: "better_contract",
    script: "better-contract/better_contract.py",
    description:
      "API contract extractor. Get routes, request/response types, and handlers.",
    buildArgs(args) {
      const argv = [String(args.path)]
      if (args.format) argv.push("--format", String(args.format))
      return argv
    },
    args: {
      path: str("file or directory path"),
      format: optStr("json or openapi"),
    },
  },
  {
    name: "better_structure",
    script: "better-structure/better_structure.py",
    description:
      "Architecture graph generator. Show dependency tree, entry points, and layers.",
    buildArgs(args) {
      const argv = []
      if (args.path) argv.push("--path", args.path)
      if (args.max_depth) argv.push("--max-depth", String(args.max_depth))
      if (args.show_cycles) argv.push("--show-cycles")
      return argv
    },
    args: {
      path: optStr("directory to analyze"),
      max_depth: optInt("max depth"),
      show_cycles: optBool("show cycles"),
    },
  },
]

// Unbounded reads are the dominant resident-byte source in long sessions:
// a 56KB whole-file read re-bills on every subsequent turn. The before-hook
// redirects oversized reads to ranged alternatives at the moment of choice.
const READ_LIMIT_BYTES = 12 * 1024
const sessionTurns = new Map()

export const BetterToolsPlugin = async () => ({
  tool: Object.fromEntries(
    TOOLS.map(({ name, description, args, buildArgs, script }) => [
      name,
      tool({
        description,
        args,
        async execute(args, context) {
          return runPython(script, buildArgs(args), context.directory)
        },
      }),
    ]),
  ),

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
