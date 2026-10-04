---
name: teach-me
description: Teaches the user the key invariants of a codebase, module, PR, or concept, so they can reason about it themselves, using prediction questions and recall checks instead of a lecture. Use when the user says "teach me", "help me understand", "what do I need to know about", "explain how X works so I get it", or wants to learn rather than just get an answer.
argument-hint: "[path, PR, or topic]"
disable-model-invocation: true
---

# Teach me

The goal is that the user ends up holding the theory of the thing: they can say why each part is the way it is, and predict what breaks if it changes. Peter Naur called this the programmer's "theory": someone who has it "can explain why each part of the program is what it is" ("Programming as Theory Building", 1985). A summary doesn't do that. The learning-science review by Dunlosky et al. (2013) rates rereading, highlighting, and summarization as low utility, and practice testing as high utility. So this skill asks the user questions more than it gives them answers.

## 1. Find the invariants first

Before saying anything, study the target. For code, read the data model, types, constructors, validation, assertions, tests, and the comments that explain "why". For a PR, read the diff and what it protects. For a concept, use the sources the user points at.

An invariant is something that must always be true for the system to be correct: "every order's total equals the sum of its lines minus discounts, plus tax on the discounted amount", "a job is in exactly one queue", "the cache is never newer than the DB". Find the 3 to 7 that matter most. For each, know:

- the statement, in one sentence
- where it's enforced (file:line), and where it's only assumed
- what breaks, concretely, if it's violated
- why the design chose it over the obvious alternative

If you can't find where an invariant is enforced, say so. It's often the most useful thing to learn.

## 2. Ask what they already know

Ask one short question about their level and goal ("Are you changing this, reviewing it, or on call for it?"). Skip what they already have.

## 3. Teach one invariant at a time

For each invariant, in this order:

1. Predict. Pose a concrete scenario and ask what happens before showing anything: "An order has a $10 coupon and $8 of goods. What's the tax base?" Wait for the answer. Guessing first improves recall even when the guess is wrong (Richland, Kornell & Kao 2009, the pretesting effect).
2. Reveal. Show the answer with the smallest real snippet that proves it (file:line, 5 to 15 lines), and state the invariant in one sentence.
3. Ask why. "Why does it clamp at zero here and not in the coupon parser?" Questions of the form "why this and not that" make the reason stick. Give the answer only after they try.
4. Break it. Show or describe what goes wrong when it's violated: a failing test, a past bug, a commit that fixed it (`git log -S`).

Use one worked example per invariant early on. Drop the examples once the user is answering well; experts learn less from worked examples than from problems (the expertise reversal effect).

Keep each turn short. One idea, one question, then stop and wait.

## 4. Check recall at the end

Ask 3 to 5 questions that mix the invariants together, without the code on screen: "A refund arrives for an order whose coupon expired yesterday. Which invariants are in play, and what should happen?" Correct the misses briefly and come back to them once more.

## 5. Leave a card

Finish with a short reference the user can keep: each invariant in one line, with the file:line that enforces it and the failure it prevents. Offer to save it (for example `docs/invariants.md`) only if the user wants it in the repo.

Never invent an invariant to fill the list. If the code doesn't enforce something it seems to rely on, teach that as a gap, not as a rule.
