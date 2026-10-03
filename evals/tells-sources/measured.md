# Measured on this machine

Model corpus: 212 .md/.txt files the agent wrote through the Write tool in
the last 30 days of transcripts (Claude Opus/Sonnet 5.x, mixed projects),
plus the bench's README, ADR and security-review outputs. 303,650 words.
Human corpus: 334 .md/.rst docs from requests, flask, httpx and fastapi at
their mid-2021 commits. 245,187 words. Commands: `python3
evals/tells_mine.py --days 30 --min 10 --style` and the rule check below.

Caveats. The corpora differ in topic (math notes, finance, course work vs
library docs), so content words are not comparable; only topic-light
features are listed. Some model docs are this repo's own skills, which quote
the tells they warn against. One machine, one user's prompting style.

## Features that separate (per 1k words)

| Feature | Model | Human | Docs with it (model / human) |
|---|---|---|---|
| Line starting with a bold label ending in a colon (`**Label:**`) | 1.53 | 0.024 | 66 / 2 |
| Em dash | 1.90 | 0.033 | 61 / 6 |
| Arrow `→` in prose | 0.63 | 0 | 35 / 0 |
| "exactly" | 2.14 | 0.17 | 96 / 31 |
| "silently" | 0.16 | 0.008 | 45 / 2 |
| "genuinely" | 0.079 | 0 | 17 / 0 |
| "roughly" | 0.13 | 0.004 | 31 / 1 |
| "precisely" | 0.115 | 0.004 | 18 / 1 |
| "strictly" | 0.27 | 0.020 | 23 / 4 |

## The existing tells.py prose rules on the same corpora (per 1k words)

| Rule | Model | Human |
|---|---|---|
| filler word list | 0.118 | 0.108 |
| not X, it's Y | 0.026 | 0.028 |
| bold-label bullet | 1.905 | 1.675 |
| em dash (after the pileup allowance) | 1.483 | 0.032 |
| openers, wrap-ups, closing offers, narration, hedges, participle tails, significance padding, vague attribution | 0.000-0.005 | 0.000-0.040 |

Only the em dash rule separates. The filler-word hits in model docs are
mostly "leverage"/"leveraged" in finance notes (40 + 20) where the word is
literal. The ChatGPT-era lexicon does not describe this output.
