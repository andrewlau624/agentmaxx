---
name: human-voice
description: Write like a person. Use when drafting or editing anything meant to read as human writing such as READMEs, documentation, blog posts, commit messages, emails, announcements, or changelogs. Also use when asked to make text sound less AI-generated, more natural, or more human.
---

# Human voice

AI detectors are unreliable; these heuristics are not. They come from Wikipedia's field guide to AI-writing tells, flipped into writing rules.

## The core principle

Language models regress to the statistical mean: they reach for the most likely sentence, averaged over everything ever written. That average is the tell. The countermeasure is specificity. A real writer knows things: the actual number, the actual filename, the actual exception to their own rule. If a sentence could appear unchanged in a document about a different topic, delete it or make it specific.

## Tells to remove

Filler vocabulary: delve, tapestry, vibrant, landscape (metaphorical), realm, journey, unlock, unleash, leverage (verb), robust, seamless, foster, bolster, pivotal, crucial (as filler), testament, showcase (verb), multifaceted, intricate, navigate (metaphorical), elevate, empower, game-changer, cutting-edge, best-in-class.

Patterns:

- **Significance padding.** "Stands as a testament to", "plays a vital role", "underscores its importance", "in today's fast-evolving landscape". If the thing matters, demonstrate why with facts; never assert its importance.
- **Participle tails.** Sentences ending "..., highlighting its impact", "..., reflecting broader trends", "..., ensuring seamless integration". Filler analysis; cut the clause.
- **Negative parallelism.** "Not just X, but Y", "It's not about X — it's about Y." Fine once in a while, a fingerprint when habitual.
- **Rule of three.** Three coordinated adjectives or examples where one or two would do. Humans use three when there happen to be three.
- **Vague attribution.** "Experts say", "is widely considered", "many find". Name the source or drop the claim.
- **Copula avoidance.** "Serves as", "acts as", "functions as" where plain "is" belongs.
- **Formatting tics.** Em-dash pileups, title-case headings on everything, bold-spam, emoji as bullets, tables for two items.

## How people actually write

Sentence length varies, occasionally into fragments. They take positions instead of presenting every view evenhandedly. They concede uncertainty bluntly ("not sure this works") rather than hedging every clause. Contractions, first person, asides, and the odd joke all stay. Headers appear only where a skimming reader needs them, which for most documents means none or two. And they explain their choices when it matters ("I picked SQLite because nothing needed a server") — model writing almost never volunteers a reason.

## Process

1. Draft normally.
2. Edit pass: hunt the vocabulary list and every pattern above. Cut significance padding without mercy.
3. Test each paragraph: could a different author have written this, unchanged, about a different subject? Then it is still generic. Make it specific or remove it.
4. Never mention this skill, or that the text was adjusted to sound human.
