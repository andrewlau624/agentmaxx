# Skill authoring and code-quality sources

Research base for new skills aimed at one complaint: "my claude tends to build stuff that doesnt work on prod." Every entry cites a URL fetched on 2026-10-03.

How the quotes were captured: each page was downloaded with curl (raw markdown for the docs.claude.com / code.claude.com / GitHub pages, HTML stripped to text for the rest, pypdf for K1 and K2). Quotes are copied from that text, trimmed with "..." only at the ends. Search-engine summaries were used only to find URLs and are not quoted.

Caveats on source strength: K4, I2-I4 and P1 are Wikipedia, a tertiary source; they are used for definitions only. I1 is a GitHub gist transcription of Naur's 1985 essay, because the university-hosted PDF (pages.cs.wisc.edu/~remzi/Naur.pdf) is a scan with no text layer. P3 is a course page reproducing Pike's rules, because Pike's usual host returned 403.

## Sources

| id | URL | Title |
|---|---|---|
| A1 | https://code.claude.com/docs/en/skills.md | Claude Code docs, Extend Claude with skills |
| A2 | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md | Claude Platform docs, Skill authoring best practices |
| A3 | https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md | anthropics/skills, skill-creator SKILL.md |
| A4 | https://code.claude.com/docs/en/best-practices.md | Claude Code docs, Best practices |
| E1 | https://arxiv.org/abs/2503.15223 | Wang, Pradel et al., Are "Solved Issues" in SWE-bench Really Solved Correctly? |
| E2 | https://arxiv.org/abs/2410.06992 | SWE-Bench+: Enhanced Coding Benchmark for LLMs |
| E3 | https://metr.org/blog/2025-08-12-research-update-towards-reconciling-slowdown-with-time-horizons/ | METR, Research Update: Algorithmic vs. Holistic Evaluation |
| E4 | https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/ | METR, Many SWE-bench-Passing PRs Would Not Be Merged into Main |
| E5 | https://arxiv.org/abs/2509.14745 | Watanabe et al., On the Use of Agentic Coding: An Empirical Study of Pull Requests on GitHub |
| E6 | https://arxiv.org/html/2607.18057 | Test Coverage Analysis of Agentic Pull Requests |
| E7 | https://arxiv.org/abs/2601.03556 | Haque et al., Do Autonomous Agents Contribute Test Code? |
| E8 | https://arxiv.org/html/2605.22534 | Why Are Agentic Pull Requests Merged or Rejected? An Empirical Study |
| V1 | https://abseil.io/resources/swe-book/html/ch12.html | Software Engineering at Google, ch. 12 Unit Testing |
| V2 | https://abseil.io/resources/swe-book/html/ch13.html | Software Engineering at Google, ch. 13 Test Doubles |
| V3 | https://testing.googleblog.com/2013/05/testing-on-toilet-dont-overuse-mocks.html | Google Testing Blog, Testing on the Toilet: Don't Overuse Mocks |
| V4 | https://martinfowler.com/bliki/ContractTest.html | Martin Fowler, Contract Test |
| V5 | https://docs.pact.io/ | Pact docs, Introduction |
| V6 | https://martinfowler.com/articles/practical-test-pyramid.html | Ham Vocke, The Practical Test Pyramid |
| V7 | https://hypothesis.readthedocs.io/en/latest/ | Hypothesis docs, Welcome to Hypothesis |
| V8 | https://research.google/pubs/state-of-mutation-testing-at-google/ | Petrovic, Ivankovic, State of Mutation Testing at Google |
| V9 | https://arxiv.org/abs/2103.07189 | Petrovic et al., Does mutation testing improve testing practices? |
| V10 | https://12factor.net/dev-prod-parity | The Twelve-Factor App, X. Dev/prod parity |
| V11 | https://12factor.net/config | The Twelve-Factor App, III. Config |
| K1 | https://www.whz.de/fileadmin/lehre/hochschuldidaktik/docs/dunloskiimprovingstudentlearning.pdf | Dunlosky et al. 2013, Improving Students' Learning With Effective Learning Techniques |
| K2 | https://learninglab.uchicago.edu/Pre-Testing_files/RichlandKornellKao.pdf | Richland, Kornell, Kao 2009, The Pretesting Effect |
| K4 | https://en.wikipedia.org/wiki/Worked-example_effect | Wikipedia, Worked-example effect |
| I1 | https://gist.githubusercontent.com/onlurking/fc5c81d18cfce9ff81bc968a7f342fb1/raw | Naur 1985, Programming as Theory Building (transcription) |
| I2 | https://en.wikipedia.org/wiki/Invariant_(mathematics) | Wikipedia, Invariant (section: Invariants in computer science) |
| I3 | https://en.wikipedia.org/wiki/Class_invariant | Wikipedia, Class invariant |
| I4 | https://en.wikipedia.org/wiki/Design_by_contract | Wikipedia, Design by contract |
| R1 | https://google.github.io/eng-practices/review/reviewer/standard.html | Google eng-practices, The Standard of Code Review |
| R2 | https://google.github.io/eng-practices/review/reviewer/looking-for.html | Google eng-practices, What to look for in a code review |
| R3 | https://google.github.io/eng-practices/review/developer/small-cls.html | Google eng-practices, Small CLs |
| R4 | https://google.github.io/eng-practices/review/reviewer/comments.html | Google eng-practices, How to write code review comments |
| R5 | https://abseil.io/resources/swe-book/html/ch15.html | Software Engineering at Google, ch. 15 Deprecation |
| R6 | https://research.google/blog/resolving-code-review-comments-with-ml/ | Google Research, Resolving code review comments with ML |
| R7 | https://arxiv.org/abs/2405.13565 | Vijayvergiya et al., AI-Assisted Assessment of Coding Practices in Modern Code Review |
| R8 | https://arxiv.org/abs/2203.09095 | Li et al., Automating Code Review Activities by Large-Scale Pre-training |
| P1 | https://en.wikipedia.org/wiki/Characterization_test | Wikipedia, Characterization test |
| P2 | https://martinfowler.com/bliki/ParallelChange.html | Danilo Sato, Parallel Change |
| P3 | https://www.cs.unc.edu/~stotts/COMP590-059-f24/robsrules.html | Rob Pike's 5 Rules of Programming |
| P4 | https://git-scm.com/docs/git-bisect | git-bisect documentation |
| P5 | https://www.debuggingbook.org/html/Intro_Debugging.html | Zeller, The Debugging Book, Introduction to Debugging |
| P6 | https://sre.google/sre-book/postmortem-culture/ | Google SRE book, ch. 15 Postmortem Culture |
| P7 | https://www.industrialempathy.com/posts/design-docs-at-google/ | Malte Ubl, Design Docs at Google |

(The K3 gap is intentional: candidate learning-science sources that added nothing beyond K1, K2 and K4 were dropped.)

## 1. Writing skills that trigger and work

Description and listing
- The description is the trigger and should front-load the use case; it is capped. A1: "Put the key use case first: the combined `description` and `when_to_use` text is truncated at 1,536 characters in the skill listing to reduce context usage."
- The open spec caps it lower. A2: "Maximum 1,024 characters ... Should describe what the Skill does and when to use it". Write to 1,024 if the skill may ship outside Claude Code.
- Third person. A2: "**Always write in third person**. The description is injected into the system prompt, and inconsistent point-of-view can cause discovery problems."
- Avoid vague descriptions. A2: "Avoid vague descriptions like these: ... `description: Helps with documents`".
- Claude undertriggers; be a little pushy. A3: "currently Claude has a tendency to "undertrigger" skills -- to not use them when they'd be useful. To combat this, please make the skill descriptions a little bit "pushy"."
- Simple tasks may not trigger at all. A3: "simple, one-step queries like "read this PDF" may not trigger a skill even if the description matches perfectly, because Claude can handle them directly with basic tools. Complex, multi-step, or specialized queries reliably trigger skills when the description matches."
- Many skills crowd each other out. A1: "if you have many skills, Claude Code drops some descriptions to fit the listing's character budget, which removes the keywords Claude needs to match your request. The budget scales at 1% of the model's context window."

Body and progressive disclosure
- A1: "Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files."
- A2: "**Keep references one level deep from SKILL.md**. All reference files should link directly from SKILL.md to ensure Claude reads complete files when needed."
- A2: "The [context window] is a public good. Your Skill shares the context window with everything else Claude needs to know".
- Body only loads on invoke. A1: "skill descriptions are loaded into context so Claude knows what's available, but full skill content only loads when invoked."
- Content persists, is not re-read. A1: "Claude Code does not re-read the skill file on later turns, so write guidance that should apply throughout a task as standing instructions rather than one-time steps."
- Explain why rather than shouting. A3: "Try to explain to the model why things are important in lieu of heavy-handed musty MUSTs."
- Match specificity to fragility. A2: "Match the level of specificity to the task's fragility and variability."

Scripts vs instructions
- A2: "**Benefits of utility scripts:** ... More reliable than generated code".
- A2: "For most utility scripts, execution is preferred because it's more reliable and efficient."
- A2: "Utility scripts can be executed through bash without loading their full contents into context. Only the script's output consumes tokens".
- Feedback loops. A2: "**Common pattern:** Run validator → fix errors → repeat".

Invocation control and frontmatter (A1 frontmatter table)
- `disable-model-invocation`: "Set to `true` to prevent Claude from automatically loading this skill. Use for workflows you want to trigger manually with `/name`."
- `user-invocable`: "Set to `false` when only Claude should invoke the skill ... Use for background knowledge users shouldn't invoke directly."
- `argument-hint`: "Hint shown during autocomplete to indicate expected arguments. Example: `[issue-number]`".
- `allowed-tools`: "Tools Claude can use without asking permission during the turn that invokes this skill. The grant clears when you send your next message."
- `context: fork` needs a task, not guidelines: "`context: fork` only makes sense for skills with explicit instructions. If your skill contains guidelines like "use these API conventions" without a task, the subagent receives the guidelines but no actionable prompt, and returns without meaningful output."
- Reference vs task skills. A1: "**Reference content** adds knowledge Claude applies to your current work. Conventions, patterns, style guides, domain knowledge. This content runs inline".
- Unknown fields fail silently. A1: "A field name must match the table exactly, hyphens included: Claude Code ignores a field it doesn't recognize without reporting an error."

Evaluating a skill
- A2: "**Create evaluations BEFORE writing extensive documentation.**" and "**Create evaluations:** Build three scenarios that test these gaps" and "**Establish baseline:** Measure Claude's performance without the Skill".
- A3 runs paired baselines: "For each test case, spawn two subagents in the same turn — one with the skill, one without."
- A3 trigger evals: "Create 20 eval queries — a mix of should-trigger and should-not-trigger." Near-misses matter most: "the most valuable ones are the near-misses — queries that share keywords or concepts with the skill but actually need something different."
- A3 description tuning holds out a test split: "It splits the eval set into 60% train and 40% held-out test, evaluates the current description (running each query 3 times to get a reliable trigger rate)".
- A2 Claude A/Claude B loop: "Work with one instance of Claude ("Claude A") to create a Skill that is used by other instances ("Claude B")."

## 2. Why AI-written code fails in production, and what catches it

Evidence that "tests pass" overstates correctness
- E1: "even more (29.6%) plausible patches induce different behavior than the ground truth patches. These behavioral differences are often due to similar, but divergent implementations (46.8%)".
- E2: "31.08% of the passed patches are suspicious patches due to weak test cases, i.e., the tests were not adequate to verify the correctness of a patch."
- E3: "early-2025 AI agents often implement functionally correct code that cannot be easily used as-is, because of issues with test coverage, formatting/linting, or general code quality." and "when manually reviewing a subset of these PRs, none of them are mergeable as-is."
- E3: "When filtering to runs where the agent passed the human-written test cases, we estimate that these PRs would take on average 26 minutes to fix".
- E4: "on average maintainer merge decisions are about 24 percentage points lower than SWE-bench scores supplied by the automated grader." Rejection categories were "core functionality failure, patch breaks other code or code quality issues."

Evidence from real agent PRs
- E5 (Claude Code PRs): "83.8% of these agent-assisted PRs are eventually accepted and merged by project maintainers, with 54.9% of the merged PRs are integrated without further modification."
- E6: "error-handling constructs (e.g., try and catch blocks) are the most consistently under-tested, with miss rates reaching 86.0% in Java and 81.0% in Python." and only "35.9% of Java and 22.5% of Python Code + Tests PRs show a coverage gain."
- E7: "test-containing PRs are more common over time and tend to be larger and take longer to complete, while merge rates remain largely similar."
- E8 (caution against over-reading rejections): "only 35.7% of rejected PRs reflected clear agentic failures, while 31.2% were driven by workflow constraints and 33.1% lacked observable decision rationale."

Verification practice
- A4: "Give Claude a check it can run: tests, a build, a screenshot to compare." and "Claude stops when the work looks done. Without a check it can run, "looks done" is the only signal available".
- A4: "address the root cause, don't suppress the error".
- A1 bundled `/verify`: "Build and run your app to confirm a code change does what it should, without falling back to tests or type checks". Launch inference fails on non-standard setups: "That inference gets unreliable for projects that need anything beyond a standard launch: a database, an env file,".
- Test through the public entry point. V1: "write tests that invoke the system being tested in the same way its users would; that is, make calls against its public API rather than its implementation details. If tests work the same way as the system's users, by definition, change that breaks a test might also break a user."
- State over interactions. V1: "Test State, Not Interactions".
- Mocks. V2: "Prefer Realism Over Isolation". V2 on interaction testing: "Interaction testing is a way to validate how a function is called without actually calling the implementation of the function." V3: "Overusing mocks can cause several problems: - Tests can be harder to understand."
- Contract tests for doubles. V4: "testing against a double always raises the question of whether the double is indeed an accurate representation of the external service, and what happens if the external service changes its contract?" V5: "a contract is between a consumer (for example, a client that wants to receive some data) and a provider".
- Property-based tests. V7: "you write tests which should pass for all inputs in whatever range you describe, and let Hypothesis randomly choose which of those inputs to check - including edge cases you might not have thought about."
- Mutation testing as a check on tests. V8: "Mutation testing assesses test suite efficacy by inserting small faults into programs and measuring the ability of the test suite to detect them." V9: "developers using mutation testing write more tests, and actively improve their test suites" and "mutants are indeed coupled with real faults."
- Env and config gaps. V10: "The tools gap: Developers may be using a stack like Nginx, SQLite, and OS X, while the production deploy uses Apache, MySQL, and Linux." V11: "strict separation of config from code".
- Definition of done in review. R2: "tests should be added in the same CL as the production code unless the CL is handling an emergency." and "Tests do not test themselves".

Not found: no fetched empirical source isolates migrations, build/dependency drift, or untested entry points as agent-specific failure causes. Those remain plausible but unsourced here.

## 3. Teaching the invariants of a codebase

Learning science
- K1: "Practice testing and distributed practice received high utility assessments because they benefit learners of different ages and abilities".
- K1: "Elaborative interrogation, self-explanation, and interleaved practice received moderate utility assessments ... because the evidence for their efficacy is limited."
- K1 on elaborative interrogation prompts: "the majority of studies have used prompts following the general format, "Why would this fact be true of this [X] and not some other [X]?""
- K1 rates rereading, highlighting, summarization as Low (Table 4: "Summarization Low ... Highlighting Low ... Rereading Low").
- Prediction before reveal. K2: "Posttest performance was better in the test condition than in the extended study condition in all experiments—a pretesting effect— even though only items that were not successfully retrieved on the pretest were analyzed."
- Worked examples, then fade. K4: "improved learning observed when worked examples are used as part of instruction, compared to other instructional techniques such as problem-solving" and "As learners gain expertise in the subject area of interest, worked examples lose their effectiveness due to the expertise reversal effect."

Invariants and program theory
- I2: "an invariant is a logical assertion that is always held to be true during a certain phase of execution of a computer program."
- I3: "A common pattern to implement invariants in classes is for the constructor of the class to throw an exception if the invariant is not satisfied."
- I4: "define formal, precise and verifiable interface specifications for software components, which extend the ordinary definition of abstract data types with preconditions, postconditions and invariants."
- I1: "programming properly should be regarded as an activity by which the programmers form or achieve a certain kind of insight, a theory, of the matters at hand."
- I1: "The programmer having the theory of the program can explain why each part of the program is what it is".
- I1: "The actual state of death becomes visible when demands for modifications of the program cannot be intelligently answered."
- I1: "any documentation being an auxiliary, secondary product."

## 4. Code quality and review

- R1: "reviewers should favor approving a CL once it is in a state where it definitely improves the overall code health of the system being worked on, even if the CL isn't perfect."
- R1: "there is no such thing as "perfect" code—there is only better code."
- R2: "The most important thing to cover in a review is the overall design of the CL."
- R2: "Is what the developer intended good for the users of this code?"
- R2 on over-engineering: "developers have made the code more generic than it needs to be, or added functionality that isn't presently needed by the system. Reviewers should be especially vigilant about over-engineering."
- R2: "Don't accept CLs that degrade the code health of the system. Most systems become complex through many small changes that add up".
- R2 naming: "A good name is long enough to fully communicate what the item is or does, without being so long that it becomes hard to read."
- R2: "look at every line of code that you have been assigned to review."
- R3: "the right size for a CL is one self-contained change. ... The CL makes a minimal change that addresses just one thing."
- R4: "Explain Why ... it helps the developer understand why you are making your comment."
- Deleting code. R5: "code is a liability, not an asset."
- Fresh-context review. A4: "A fresh context improves code review since Claude won't be biased toward code it just wrote."

Learning a specific reviewer
- R6: "fine-tuned for this specific task with reviewed code changes, the reviewer comments, and the edits the author performed to address those comments." Precision trade-off: "The final model was calibrated for a target precision of 50%" and "Incorrect suggested edits take the developers time".
- R7: "AutoCommenter, a system backed by a large language model that automatically learns and enforces coding best practices" and "an end-to-end system for learning and enforcing coding best practices is feasible and has a positive impact on the developer workflow."
- R8 frames review as a learnable task: "Modern code review activities necessitate developers viewing, understanding and even running the programs to assess logic, functionality, latency, style and other factors."

## 5. Other high-leverage SWE skills

- Safe refactoring. P1: "a characterization test (also known as Golden Master Testing) is a means to describe (characterize) the actual behavior of an existing piece of software, and therefore protect existing behavior of legacy code against unintended changes".
- Migrations. P2: "Parallel change, also known as expand and contract, is a pattern to implement backward-incompatible changes to an interface in a safe manner, by breaking the change into three distinct phases: expand, migrate, and contract." and "Most database refactorings follow the parallel change pattern".
- Debugging. P5 lists the method: "Formulate a question ... Invent a hypothesis ... formulate a prediction that can support or refute the hypothesis ... Test the prediction (and thus the hypothesis) in an experiment." and "Fix the problem, not the symptom".
- Bisect. P4: "This command uses a binary search algorithm to find which commit in your project's history introduced a bug." Automatable: "git bisect run <cmd>" where cmd "should exit with code 0 if the current source code is good/old, and exit with a code between 1 and 127 (inclusive), except 125, if the current source code is bad/new."
- Performance. P3: "Rule 2. Measure. Don't tune for speed until you've measured, and even then don't unless one part of the code overwhelms the rest." and "Bottlenecks occur in surprising places".
- Postmortems. P6: "A postmortem is a written record of an incident, its impact, the actions taken to mitigate or resolve it, the root cause(s), and the follow-up actions to prevent the incident from recurring." and "it must focus on identifying the contributing causes of the incident without indicting any individual or team".
- Spec before code. P7: "The design doc documents the high level implementation strategy and key design decisions with emphasis on the trade-offs that were considered". Cost: "Writing design docs is overhead." A4: "Letting Claude jump straight to coding can produce code that solves the wrong problem." and "If you could describe the diff in one sentence, skip the plan."
- Spec interview. A4: "for larger features have Claude interview you and write a spec before you start implementing."

## Summary: most actionable rules

1. Skills: description in third person, key use case first, under 1,024 chars, slightly pushy, with concrete trigger phrases (A1, A2, A3).
2. Skills: SKILL.md under 500 lines, references one level deep, deterministic steps as executed scripts; set `disable-model-invocation` on side-effecting workflows, use `context: fork` only for task skills (A1, A2).
3. Skills: build 3 scenarios plus a no-skill baseline before writing, and 20 trigger queries with near-miss negatives (A2, A3).
4. Prod failures: passing tests is weak evidence; 29.6% of test-passing SWE-bench patches diverge from the reference, and maintainers merge ~24 points fewer than graders pass (E1, E4).
5. Prod failures: agent tests leave error handling untested (81-86% miss); a done-check must exercise failure paths (E6).
6. Verification: run the built app through its real entry point and public API, prefer real dependencies over mocks, add contract tests where doubles stand in for services (A1 /verify, V1-V4).
7. Verification: check config and the dev/prod tools gap explicitly; use property-based tests for input ranges and mutation testing to judge whether tests can fail (V7-V11).
8. Teaching invariants: ask the learner to predict before revealing, quiz with retrieval rather than rereading, use "why this and not that" prompts, start with worked examples then fade (K1, K2, K4). Teach invariants as pre/postconditions and assertions that explain why the code is as it is (I1-I4).
9. Review: approve when the change improves code health, look at design first, flag over-engineering, keep changes to one self-contained thing, treat code as a liability, review in fresh context (R1-R5, A4); mimicking a reviewer means learning from their past comment and fix pairs, tuned for precision (R6, R7).
10. Other skills: characterization tests before refactors, expand/migrate/contract for schema changes, hypothesis-driven debugging plus `git bisect run`, measure before optimizing, blameless postmortems, a short spec or interview before multi-file work (P1-P7, A4).
