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

- Significance padding. "Stands as a testament to", "plays a vital role", "underscores its importance", "in today's fast-evolving landscape". If the thing matters, demonstrate why with facts; never assert its importance.
- Participle tails. Sentences ending "..., highlighting its impact", "..., reflecting broader trends", "..., ensuring seamless integration". Filler analysis; cut the clause.
- Negative parallelism. "Not just X, but Y", "It's not about X; it's about Y." Fine once in a while, a fingerprint when habitual.
- Rule of three. Three coordinated adjectives or examples where one or two would do. Humans use three when there happen to be three.
- Vague attribution. "Experts say", "is widely considered", "many find". Name the source or drop the claim.
- Copula avoidance. "Serves as", "acts as", "functions as" where plain "is" belongs.
- Formatting tics. Em-dash pileups, title-case headings on everything, bold-spam, emoji as bullets, tables for two items.

## Shape tells (the ones that survive a clean vocabulary)

Text with none of the words above still reads as machine-written when every paragraph has the same arc: a framing line, a reveal, a closing beat. People answering a question do not narrate. They say the thing.

- Reveal structure. "The hard part wasn't ranking. It was keeping the index correct." "Not the model part. The part where the data is messy." State the hard part directly; no decoy first.
- Framing before the answer. "Honestly, probably...", "I'll say that up front:", "The short version is", "The reason is that". Delete the frame, keep what follows.
- The moral. A last sentence that says what it meant: "That's a harder bar, and I like that." "Which I'd do differently now." "It never felt clean." Cut it. End on the last fact.
- Easy/hard mirror. "A crawler is easy to write once. Keeping it correct is not." Say what was hard and why, once.
- Fragments for emphasis. "Not another chat product." "No ticket, no design review, nobody to tell me." Write full sentences or drop them.
- Parallel example triads. "At Pacific, X. At Apple, Y. At Berkeley, Z." Pick the one example that answers the question; give it detail instead.
- Uniform paragraphs. Four paragraphs of three sentences each, every one ending on a punchline. Real answers are lumpy: one long paragraph of facts, one line, a list.
- Restating the question as the first sentence. Answer it instead: the first sentence carries the fact the reader asked for.
- Self-aware humility as decoration. "I know I'm early." "Which is a little circular." Only say it if it changes what the reader should do.

Target shape for an answer to a question: first sentence is the answer. Following sentences are the facts that support it, in the order they happened, with the numbers and names. It stops when the facts stop. It is fine for the last sentence to be boring.

The word list above was measured on GPT-4-era text. On Claude-written docs it barely shows up; what does show up, measured against human docs in this repo (`evals/tells-sources/measured.md`), is spaced em dashes (about 57 times the human rate in software docs), lines that open with a bold label and a colon, and `→` used as prose punctuation.

## Process

1. Draft normally.
2. Edit pass: hunt the vocabulary list and every pattern above. Cut significance padding without mercy.
3. Test each paragraph: could a different author have written this, unchanged, about a different subject? Then it is still generic. Make it specific or remove it.
4. Shape pass: for each paragraph, find the turn ("but", "not X, it was Y", a fragment) and the closing beat. Flatten the turn into a statement and delete the beat. If the paragraphs are all the same length, merge or split until they are not.
5. Never mention this skill, or that the text was adjusted to sound human.
