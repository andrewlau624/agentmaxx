# Prose tells: sourced catalog

This file lists signs that prose was written by a language model, collected for a deterministic linter. Every catalog row cites a source that was fetched on 2026-10-03, along with a short verbatim quote from it. The Wikipedia text was fetched as raw wikitext (`action=raw`). In those quotes, wiki italic and bold marks ('' and ''') and `<ref>` tags were removed, and nothing else was changed. The arXiv papers were fetched as PDFs and the text was extracted with pypdf. Where a quote runs across a PDF line break, the lines are joined with a single space, and words hyphenated at a line end are rejoined. Rows from different sources measure different things on different corpora and models, so read each number in the context of its own source.

## Sources

| id | title | authors | year | URL | fetched |
|---|---|---|---|---|---|
| W | Wikipedia:Signs of AI writing (revision as fetched 2026-10-03) | WikiProject AI Cleanup editors | 2026 | https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing (raw: https://en.wikipedia.org/w/index.php?title=Wikipedia:Signs_of_AI_writing&action=raw) | yes |
| K | Delving into LLM-assisted writing in biomedical publications through excess vocabulary (arXiv v5, 3 Jul 2025) | Dmitry Kobak, Rita González-Márquez, Emőke-Ágnes Horvát, Jan Lause | 2025 | https://arxiv.org/abs/2406.07016 | yes |
| L1 | Monitoring AI-Modified Content at Scale: A Case Study on the Impact of ChatGPT on AI Conference Peer Reviews | Weixin Liang, Zachary Izzo, Yaohui Zhang, Haley Lepp, Hancheng Cao, Xuandong Zhao, Lingjiao Chen, Haotian Ye, Sheng Liu, Zhi Huang, Daniel A. McFarland, James Y. Zou | 2024 | https://arxiv.org/abs/2403.07183 | yes |
| L2 | Mapping the Increasing Use of LLMs in Scientific Papers | Weixin Liang, Yaohui Zhang, Zhengxuan Wu, Haley Lepp, Wenlong Ji, Xuandong Zhao, Hancheng Cao, Sheng Liu, Siyu He, Zhi Huang, Diyi Yang, Christopher Potts, Christopher D Manning, James Y. Zou | 2024 | https://arxiv.org/abs/2404.01268 | yes |
| R | Do LLMs write like humans? Variation in grammatical and rhetorical styles (arXiv v2, 21 Aug 2025; PNAS) | Alex Reinhart, Ben Markey, Michael Laudenbach, Kachatad Pantusen, Ronald Yurko, Gordon Weinberg, David West Brown | 2025 | https://arxiv.org/abs/2410.16107 | yes |
| J | Why Does ChatGPT "Delve" So Much? Exploring the Sources of Lexical Overrepresentation in Large Language Models | Tom S. Juzek, Zina B. Ward | 2025 | https://arxiv.org/abs/2412.11385 | yes |
| G | Is ChatGPT Transforming Academics' Writing Style? | Mingmeng Geng, Roberto Trotta | 2024 | https://arxiv.org/abs/2404.08627 | yes |
| F | The Last Fingerprint: How Markdown Training Shapes LLM Prose | E. M. Freeburg | 2026 | https://arxiv.org/abs/2603.27006 | yes |
| M | Contrasting Linguistic Patterns in Human and LLM-Generated News Text (Artificial Intelligence Review 57:265) | Alberto Muñoz-Ortiz, Carlos Gómez-Rodríguez, David Vilares | 2024 | https://arxiv.org/abs/2308.09067 | yes |
| RU | People who frequently use ChatGPT for writing tasks are accurate and robust detectors of AI-generated text | Jenna Russell, Marzena Karpinska, Mohit Iyyer | 2025 | https://arxiv.org/abs/2501.15654 | yes |

## Catalog

The "kind" column says whether a row is lexical, meaning a regex or word list can detect it, structural, meaning a regex or simple parse over formatting or headings can detect it, statistical, meaning it needs a computed rate or distribution, or judgment, meaning it needs semantic reading. Pattern cells use `\|` for regex alternation so the table does not break.

### Content patterns (Wikipedia)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Undue emphasis on significance, legacy, broader trends | stands as, serves as, is a testament, is a reminder, a (crucial\|pivotal\|vital\|significant\|key) (role\|moment), underscores its importance, highlights its significance, reflects broader, symbolizing its (ongoing\|enduring\|lasting), contributing to the, setting the stage for, marking the, shaping the, represents a shift, marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted | W | "Words to watch: stands/serves as, is a testament/reminder, a crucial/pivotal/vital/significant/key role/moment, underscores/highlights its importance/significance, reflects broader, symbolizing its ongoing/enduring/lasting, contributing to the, setting the stage for, marking/shaping the, represents/marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted" | lexical |
| Situating subject amid broader debates | generated debate, participated in public discussions, prompted broader reflection, raising (philosophical )?questions, shaped (emerging )?policy discussions | W | "Another common manifestation of this sign is AI chatbots situating an article subject amid broader "debates," or noting that a subject has "participated in public discussions"." | lexical (needs a precision check) |
| Hedged preamble before claiming importance anyway | Though it saw only limited application, it contributes to the broader ... | W | "Sometimes, they add hedging preambles acknowledging that the subject is of relatively low importance, before talking about its importance anyway." | judgment |
| Canned emphasis on notability and media coverage | independent coverage, (local\|regional\|national) media outlets, (music\|business\|tech) outlets, trade publications, (cited\|featured\|profiled) in, written by a leading expert, active social media presence, was identified by | W | "Words to watch: independent coverage, local/regional/national/[country name] media outlets, music/business/tech outlets, trade publications, cited/featured/profiled in, written by a leading expert, active social media presence, was identified by" | lexical |
| "Maintains an active social media presence" | maintain(s)? an? (active\|strong) (social media\|digital) presence | W | "This wording is particularly idiosyncratic to AI text and relatively uncommon on Wikipedia before ~2024." | lexical |
| Superficial analysis via trailing present participle | sentence-final `, (highlighting\|underscoring\|emphasizing\|ensuring\|reflecting\|symbolizing\|contributing to\|cultivating\|fostering\|encompassing\|enhancing)\b[^.]*\.`; also valuable insights, align with, resonate with | W | "This is often done by attaching a present participle ("-ing") phrase at the end of sentences" | lexical (participle regex) |
| Promotional, travel-guide language | boasts a, vibrant, rich, profound, enhancing, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking, renowned, featuring, diverse array | W | "Words to watch: boasts a, vibrant, rich, profound, enhancing, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking, renowned, featuring, diverse array" | lexical |
| Same promo phrases regardless of topic | the promo list above, repeated across unrelated topics | W | "LLMs tend to over-use the same set of promotional phrases no matter what the topic." | lexical |
| Vague connection or association | in connection with, connected (with\|to), in association with, (is\|was\|became\|widely\|particularly) associated with | W | "Words to watch: in connection with/to ..., connected with/to, in association with ..., associated with" | lexical (low precision) |
| Vague attribution, weasel wording | Industry reports, Observers have cited, Experts argue, Some critics argue, several (sources\|publications), such as before a list that is actually complete | W | "Words to watch: Industry reports, Observers have cited, Experts argue, Some critics argue, several sources/publications (when only few sources are cited), such as (before exhaustive word lists)" | lexical plus judgment |
| Outline-like "challenges and future" conclusion | `Despite (its\|their\|these) .{0,60}(faces?\|face) (several \|numerous )?challenges`, Despite these challenges, Challenges and Legacy, Future Outlook, Future Prospects | W | "Words to watch: Despite its... faces several challenges..., Despite these challenges, Challenges and Legacy, Future Outlook" | lexical |
| Note that this row is about the formula, not the word | (same as above) | W | "Note: This sign is about the rigid formula, not simply the mention of challenges or challenging." | caveat |
| "Awards and recognition" / "X and Y" headings | heading matching `^#+ .+ and .+$`, especially `Awards and recognition`, `Recognition` | W | "Section or subsection headers in the format of "X and Y" are common in (but not exclusive to) AI generated articles. An "Awards and recognition" section is particularly common" | structural |

### Language and grammar (Wikipedia)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| High density of "AI vocabulary" | Additionally (sentence-initial), align with, boasts (meaning has), bolstered, crucial, deep dive, delve, emphasizing, enduring, enhance, fostering, garner, highlight (verb), interplay, intricate, intricacies, key (adj), landscape (abstract), meticulous, meticulously, pivotal, robust, showcase, tapestry (abstract), testament, underscore (verb), valuable, vibrant | W | "Words to watch: Additionally (especially beginning a sentence), align with, boasts (meaning "has"), bolstered, crucial, deep dive, delve, emphasizing, enduring, enhance, fostering, garner, highlight (as a verb), interplay, intricate/intricacies, key (as an adjective), landscape (as an abstract noun), meticulous/meticulously, pivotal, robust, showcase, tapestry (as an abstract noun), testament, underscore (as a verb), valuable, vibrant" | lexical (density, not a single hit) |
| Co-occurrence is the signal, not one word | count of distinct list words per text | W | "One or two of these words appearing in an edit may be coincidental, but an edit (post-2022) introducing lots of them, lots of times, is one of the strongest tells for AI use." | statistical |
| Era-specific vocabulary, GPT-4 (2023 to mid-2024) | Additionally, boasts, bolstered, crucial, delve, emphasizing, enduring, garner, intricate, intricacies, interplay, key, landscape, meticulous, meticulously, pivotal, underscore, tapestry, testament, valuable, vibrant | W | "2023 to mid-2024 (GPT-4): Additionally, boasts, bolstered, crucial, delve, emphasizing, enduring, garner, intricate/intricacies, interplay, key, landscape, meticulous/meticulously, pivotal, underscore, tapestry, testament, valuable, vibrant" | lexical |
| Era-specific vocabulary, GPT-4o (mid-2024 to mid-2025) | align with, bolstered, crucial, emphasizing, enhance, enduring, fostering, highlighting, pivotal, showcasing, underscore, vibrant | W | "Mid-2024 to mid-2025 (GPT-4o): align with, bolstered, crucial, emphasizing, enhance, enduring, fostering, highlighting, pivotal, showcasing, underscore, vibrant" | lexical |
| Era-specific vocabulary, GPT-5 (mid-2025 on) | emphasizing, enhance, highlighting, showcasing, plus the notability and media-coverage phrases | W | "Mid-2025 and on (GPT-5): emphasizing, enhance, highlighting, showcasing" | lexical |
| "delve" has declined | delve, delves, delving | W | "the word delve was famously overused by ChatGPT in 2023 and early 2024, but became less frequent later in 2024, then dropped off sharply in 2025." | caveat |
| Grok-specific pseudo-scientific words | causal, empirical, correlate, underscore | W | "Grok output is particularly idiosyncratic: it overuses superficially "scientific" words like causal, empirical, correlate, and continues to overuse underscore as of 2026." | lexical |
| Synonyms do not inherit the tell | (do not expand word lists with synonyms) | W | "a word being overused by AI does not imply that its synonyms are also overused." | caveat |
| Avoidance of basic copulas | (serves\|stands\|functions\|operates) as (a\|an\|the), marks (a\|the), represents (a\|an), (boasts\|features\|maintains\|offers) (a\|an), refers to | W | "Words to watch: serves as/stands as/marks/functions as/operates as/represents [a], boasts/features/maintains/offers [a], refers to" | lexical |
| Elaborate copula replacements | ventured into .* as a, began (his\|her\|their) career as | W | "e.g., ventured into politics as a candidate versus was a candidate, or began his career as versus was." | lexical plus judgment |
| Negative parallelism: not just X, but also Y | `\bnot only\b.{0,80}\bbut( also)?\b`, `\b(it'?s\|it is\|is) not just\b.{0,60}[,;—-]\s*(it'?s\|it is)\b`, `doesn['’]t just` | W | "It is common for LLMs to use parallel constructions involving "not", "but", or "however" such as "Not only ... but ..." or "It is not just ..., it's ..."." | lexical |
| Negative parallelism: not X, but Y | `\b(it'?s\|is\|isn['’]t) not\b.{0,60}[,;—-]\s*(it'?s\|but)\b`, `\bno \w+, no \w+, just\b` | W | "Such constructions are often expressed as "It's not ..., it's ..." or "no ..., no ..., just ..."." | lexical |
| Reversed parallelism: Y rather than X | `\brather than\b` (precision is low on its own) | W | "This pattern may also be reversed, a construction particularly common in Grok output but also present in ChatGPT and Claude output." | lexical plus judgment |
| Lead defining a list or broad title as a proper noun | `^'?[A-Z].{0,80} (refers to\|is the chronological list\|is a curated compilation)` | W | "the first sentence of the lead may introduce or define the article's title as if it were a standalone real-world entity." | judgment |
| Rule of three | `\b\w+, \w+,? and \w+\b` triads, density per paragraph | W | "LLMs overuse the rule of three. This can take different forms, from "adjective, adjective, adjective" to "short phrase, short phrase, and short phrase"." | statistical (triad rate) |

### Style and formatting (Wikipedia)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Title heading at top | first line is a heading repeating the document title | W | "AI chatbots tend to put a heading with the article name before all the content" | structural |
| Title Case section headings | heading where every content word is capitalized | W | "In section headings, AI chatbots strongly tend to capitalize all main words." | structural |
| Headings that contain only other headings | heading immediately followed by a subheading with no body text | W | "AI chatbots may generate a heading that only stores other headings, without text of their own." | structural |
| Overuse of boldface | count of `\*\*[^*]+\*\*` or `'''...'''` per paragraph | W | "AI chatbots may display various phrases in boldface for emphasis in an excessive, mechanical manner." | structural (count) |
| Inline-header vertical lists | `^\s*([-*•–]\|\d+\.)\s*\*\*[^*]+:?\*\*:?\s` | W | "an ordered or unordered list where the list marker (number, bullet, dash, etc.) is followed by an inline boldfaced header, separated with a colon from the remaining descriptive text." | structural |
| Overuse of em dashes | count of `—` per 1,000 words; spaced ` — ` | W | "LLM output uses them more often than nonprofessional human-written text of the same genre, and uses them in places where humans are more likely to use commas, parentheses, colons" | statistical |
| Spaced em dashes | ` — ` (space, U+2014, space) | W | "AI-generated em dashes are usually surrounded by spaces, contrary to common typographic guidelines" | lexical |
| Em dash tell weakening | (lower the weight; varies by model) | W | "A July 2026 study found that of contemporary models only Claude used em dashes more than professional writers, and ChatGPT used them less." | caveat |
| Emoji as heading or bullet decoration | `^(#+\s*\|[-*]\s*)\p{Extended_Pictographic}` | W | "they sometimes decorated section headings or bullet points by placing emoji in front of them." | structural |
| Unusual small tables | small 2-column table that could be prose | W | "Some AIs create small, minimally formatted tables that could be better represented as prose or an infobox." | judgment |
| Curly quotes and apostrophes, or a mix | `[“”‘’]`, especially mixed with straight `"` `'` in one text | W | "ChatGPT and DeepSeek typically use curly quotation marks (“...” or ‘...’) instead of straight quotation marks" | lexical (weak) |
| Curly quotes are a weak signal | (do not use alone; Gemini and Claude do not) | W | "Curly quotes alone do not prove LLM use." | caveat |
| Skipping heading levels | first heading is level 3, or a level jump of more than 1 | W | "AI chatbots tend to skip level 2 headings (==) and start sections from the third level (===)." | structural |
| Thematic breaks between every section | `^(---\|\*\*\*\|___\|----)$` before each heading | W | "AI chatbots sometimes include a thematic break (----) between each section in a text (this is common in Markdown output)." | structural |
| Markdown in a non-Markdown destination | `\*\*`, `^## `, `[text](url)` inside plain text or wikitext | W | "The presence of faulty wikitext syntax mixed with Markdown syntax is a strong indicator that content is LLM-generated" | structural (context-dependent) |

### Communication meant for the user (Wikipedia)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Collaborative chatbot phrasing | I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like, is there anything else, let me know, more detailed breakdown, here is a | W | "Words to watch: I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like..., is there anything else, let me know, more detailed breakdown, here is a" | lexical |
| Knowledge-cutoff and source-availability disclaimers | Up to my last training update, as of my last knowledge update, While specific details are (limited\|scarce), not widely (available\|documented\|disclosed), in the (provided\|available) (sources\|search results), based on available information | W | "Words to watch: Up to my last training update, as of my last knowledge update, While specific details are limited/scarce..., not widely available/documented/disclosed, ...in the provided/available sources / search results..., [claim] should be treated as... rather than..., based on available information" | lexical |
| Unfilled phrasal templates and placeholders | `\[(Your Name\|Describe[^\]]*\|link to[^\]]*\|[A-Z][^\]]{2,40})\]`, `20\d\d-(XX\|xx)-(XX\|xx)`, `INSERT_[A-Z_]+`, `SOURCE_PUBLISHER`, `URL` as a value | W | "AI chatbots may generate responses with fill-in-the-blank phrasal templates ... for the LLM user to replace with words and phrases pertaining to their use case. However, some LLM users forget to fill in those blanks." | lexical |
| Placeholder dates | `20[0-9][0-9]-(XX\|xx)-(XX\|xx)` | W | "Large language models may also insert placeholder dates like "2025-xx-xx" into citation fields" | lexical |
| Letter-style openers in comments | I hope this message finds you well, I trust this message finds you well, Dear ... Team, I am writing to, I understand (the\|your) concerns? (about\|regarding) | W | "I hope/trust this message finds you well." | lexical |

### Markup artifacts (Wikipedia)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| ChatGPT citation artifacts | `contentReference\[oaicite:\d+\]`, `oai_citation`, `turn\d+search\d+`, `attributableIndex`, `\w\+1\b` | W | "ChatGPT sometimes adds code in the form of :contentReference[oaicite:0]{index=0}, Example+1, or oai_citation in place of links to references in output text." | lexical (near-unambiguous) |
| Gemini citation artifacts | `\[cite: ?\d+\]`, `\[span_\d+\]\(start_span\)` | W | "Gemini: [cite: 1], [span_1](start_span)" (section heading) | lexical |
| Grok citation artifacts | `grok_card`, `grok_render_citation_card_json` | W | "Grok: grok_card, grok_render_citation_card_json" (section heading) | lexical |
| DeepSeek citation artifacts | lenticular brackets `【】`, dagger `†` | W | "DeepSeek: lenticular brackets, dagger symbols" (section heading) | lexical |
| Perplexity artifacts | `attached_file`, `ppl-ai-file-upload` | W | "Perplexity: attached_file, ppl-ai-file-upload" (section heading) | lexical |
| Internal markup leaking is unambiguous | (any row in this block) | W | "LLM output sometimes exposes its internal formatting metadata, which is an unambiguous indicator that the text originated with AI." | caveat |

### Historical indicators (Wikipedia; older models)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Didactic disclaimers | it'?s (important\|critical\|crucial) to (note\|remember\|consider), worth noting, may vary | W | "Words to watch: it's important/critical/crucial to note/remember/consider, worth noting, may vary" | lexical |
| Section summaries | In summary, In conclusion, Overall, a heading named Conclusion | W | "Words to watch: In summary, In conclusion, Overall" | lexical |
| Restating summary at paragraph end | last sentence of a paragraph restates the first | W | "often ended paragraphs or sections by summarizing and restating its core idea." | judgment |
| Prompt refusal | as an AI language model, as a large language model, I cannot offer medical advice, but I can, I'm sorry | W | "Words to watch: as an AI language model, as a large language model, I cannot offer medical advice, but I can..., I'm sorry" | lexical |
| Elegant variation (repetition penalty) | many distinct referring expressions for one entity | W | "Older AI models may include a repetition penalty, meant to discourage it from reusing words too often." | judgment |
| Transition words alone are weak | Additionally, Consequently, Notably at sentence start | W | "only a few transition words and phrases are known to be overused by AI in this way. This pattern also has precedence in essay-like writing by humans and is accepted by many style guides, so this is not a strong tell." | caveat |

### Features more common in human text (Wikipedia; absence is weak evidence)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Plain is/has phrasing | there is a, it has a | W | "Simple is/has phrases, such as there is a, it has a." | lexical (inverse) |
| Stiff synonyms preferred by AI | authored, relocated, utilized, attempted, passed away (versus wrote, moved, used, tried, died) | W | "Words with complex, stiff or euphemistic synonyms, such as wrote (versus authored), moved (versus relocated), used (versus utilized), tried (versus attempted), died (versus passed away)." | lexical |
| Superlatives and definitive statements | one of the best, is the only, was the first | W | "Superlative or definitive statements, such as one of the best, is the only, was the first" | lexical (inverse) |
| Hedges and intensifiers | very, perhaps, tends to | W | "Hedging qualifiers and intensifiers, such as very, perhaps, tends to." | lexical (inverse) |
| Isolated wordy constructions | as a result of, in order to, all of the, a part of, the fact that | W | "Isolated wordy constructions such as as a result of, in order to, all of the, a part of, or the fact that." | lexical (inverse) |

### Excess vocabulary in biomedical abstracts (Kobak et al.)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Rare excess style words with high frequency ratios | delves, underscores, showcasing (and inflections) | K | "Less common words with strong excess usage included delves (r = 28.0), underscores (r = 13.8), and showcasing (r = 10.7), together with their grammatical inflections" | lexical |
| Common excess style words with high frequency gap | potential, findings, crucial | K | "More common words with strong excess usage included potential (δ = 0.052), findings (δ = 0.041), and crucial (δ = 0.037)" | lexical (weak per word) |
| Common marker set (10 words) | across, additionally, comprehensive, crucial, enhancing, exhibited, insights, notably, particularly, within | K | "This led to the following set of 10 words: across, additionally, comprehensive, crucial, enhancing, exhibited, insights, notably, particularly, within." | lexical |
| Rare marker set (291 words, Figure S6) | accentuates, acknowledges, adept, akin, align, aligns, alongside, amidst, avenue, bolster, bolstered, burgeoning, commendable, compelling, crafting, culminating, delve, delves, delving, discern, elucidate, embracing, emphasizing, encapsulates, encompassing, endeavors, enduring, enhancing, ensuring, exceptional, facilitating, fostering, foundational, garnered, groundbreaking, harnessing, illuminating, imperative, intricacies, intricate, invaluable, leveraging, meticulous, meticulously, multifaceted, notable, noteworthy, nuanced, paving, pinpoint, pioneering, pivotal, poised, pronounced, realm, remarkable, renowned, revolutionize, scrutinize, seamless, seamlessly, shedding, showcasing, solidify, spurred, streamline, surpass, swiftly, transformative, uncharted, underexplored, underscore, underscores, underscoring, unparalleled, unraveling, unveil, unveiling, uphold, versatility (selection; the full list is in Figure S6) | K | "Figure S6: All 291 excess style words in 2024 with frequency below 0.02" | lexical |
| Excess words are verbs and adjectives, not nouns | part of speech of the flagged words | K | "out of all 379 excess style words in 2024, 66% were verbs and 14% were adjectives" | statistical |
| Example flowery collocations | meticulously delving into the intricate web, takes a deep dive, intricate interplay, is pivotal for, delve into the intricacies of | K | "By meticulously delving into the intricate web connecting [...] and [...], this comprehensive chapter takes a deep dive into their involvement" | lexical |
| Corpus-level effect size | (calibration only) | K | "suggests that at least 13.5% of 2024 abstracts were processed with LLMs." | caveat |

### AI-preferred adjectives and adverbs in peer reviews (Liang et al.)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Fold increases for specific adjectives | commendable, meticulous, intricate | L1 | "adjectives such as “commendable”, “meticulous”, and “intricate” showing 9.8, 34.7, and 11.2-fold increases in probability of occurring in a sentence." | lexical |
| Top 100 adjectives used disproportionately by AI (first 30 shown) | commendable, innovative, meticulous, intricate, notable, versatile, noteworthy, invaluable, pivotal, potent, fresh, ingenious, cogent, ongoing, tangible, profound, methodical, laudable, lucid, appreciable, fascinating, adaptable, admirable, refreshing, proficient, intriguing, thoughtful, credible, exceptional, digestible | L1 | "Table 2: Top 100 adjectives disproportionately used more frequently by AI. commendable innovative meticulous intricate notable versatile noteworthy invaluable pivotal potent" | lexical |
| Top 100 adverbs used disproportionately by AI (first 30 shown) | meticulously, reportedly, lucidly, innovatively, aptly, methodically, excellently, compellingly, impressively, undoubtedly, scholarly, strategically, intriguingly, competently, intelligently, hitherto, thoughtfully, profoundly, undeniably, admirably, creatively, logically, markedly, thereby, contextually, distinctly, judiciously, cleverly, invariably, successfully | L1 | "Table 3: Top 100 adverbs disproportionately used more frequently by AI. meticulously reportedly lucidly innovatively aptly" | lexical |
| Top 4 LLM-preferred words in arXiv CS abstracts | realm, intricate, showcasing, pivotal | L2 | "the top 4 words most disproportionately used by LLM compared to humans, as measured by the log odds ratio. The words are:realm, intricate, showcasing, pivotal." | lexical |

### Grammatical and rhetorical style (Reinhart et al.)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Present participial clauses (overused) | clause headed by a V-ing participle, e.g. ", leaning on his agility," and ", evading ..." | R | "GPT-4o uses present participial clauses at 5.3 times the rate of humans (paired Cohen’sd = 1.38)" | statistical (POS tagger) |
| Present participial clauses, range across models | as above | R | "the instruction-tuned LLMs used present participial clauses at 2 to 5 times the rate of human text" | statistical |
| "That" clauses as subject (overused) | `^That\b` clause as sentence subject | R | "‘that’ clauses as subject 2.6 times as often (d = 0.77)" | statistical (parser) |
| Nominalizations (overused) | -tion, -ment, -ness, -ity nouns derived from verbs or adjectives | R | "nominalizations 2.1 times as often ( d = 1.23)" | statistical (suffix heuristic) |
| Nominalizations, range across models | as above | R | "They also use nominalizations at 1.5 to 2 times the rate of humans" | statistical |
| Phrasal coordination (overused) | X and Y joining phrases, not clauses | R | "phrasal coordination 1.9 times as often (d = 0.81)" | statistical (parser) |
| Agentless passive (underused by GPT-4o) | be + past participle with no by-phrase | R | "GPT-4o uses the agentless passive voice at roughly half the rate as human texts" | statistical (inverse) |
| Downtoners (GPT-4o over, Llama under) | barely, nearly | R | "both GPT-4o models use downtoners (such as barely or nearly) more frequently than humans, all Llama 3 variants avoid them." | lexical (model-specific) |
| Clausal coordination avoided by GPT-4o | ", and" joining independent clauses | R | "both GPT-4o models avoid clausal coordination, while all Llama 3 variants use it more frequently than humans" | statistical (model-specific) |
| Noun-heavy, informationally dense register | high nominal density in casual genres | R | "instruction-tuned models, which are trained to answer questions and solve problems, have a distinct noun-heavy, informationally dense writing style, even when prompted to match the style of informal speech and writing." | statistical |
| GPT-4o overrepresented words, rate relative to human | camaraderie 162, tapestry 155, intricate 119, underscore 107, unspoken 102, amidst 100, palpable 95, solace 95, fleeting 84, unravel 83 | R | "camaraderie 162 ... tapestry 155 ... intricate 119 ... underscore 107 ... unspoken 102 ... amidst 100 ... palpable 95 ... solace 95 ... fleeting 84 ... unravel 83" (Table 1, GPT-4o column) | lexical |
| GPT-4o Mini overrepresented words | camaraderie 171, tapestry 147, palpable 145, grapple 131, intricate 129, fleeting 124, ignite 122, vibrant 92, amidst 90, cacophony 89 | R | "camaraderie 171 ... tapestry 147 ... palpable 145 ... grapple 131 ... intricate 129 ... fleeting 124 ... ignite 122 ... vibrant 92 ... amidst 90 ... cacophony 89" (Table 1, GPT-4o Mini column) | lexical |
| Llama 3 Instruct overrepresented words | unease, palpable, continuation, shoutout, pang, reminder, prioritize, policymaker, rut, waft | R | "Instruction-tuned variants of Llama 3 also favor words like camaraderie and palpable, as well as unease and reminder" | lexical |
| Per-document prevalence | tapestry, amidst | R | "“tapestry” appeared in 23% of GPT-4o outputs and “amidst” in 27%" | lexical |
| Words implying complex relation, plus positive items | tapestry, intricate, camaraderie, cacophony, amidst, vibrant, solace | R | "these words together may signal a preference for grandiose, if hollow, summative sentences." | lexical |
| Obscenities underused | profanity rate near zero | R | "they use certain obscenities more than 100 times less often" | lexical (inverse) |

### Focal words (Juzek and Ward)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| 21 focal words, PubMed opm increase 2020 to 2024 | delves (+6697%), delved (+2240%), delving (+1817%), showcasing (+1396%), delve (+1375%), boasts (+918%), underscores (+904%), comprehending (+899%), intricacies (+773%), surpassing (+667%), intricate (+611%), underscoring (+537%), garnered (+437%), showcases (+422%), emphasizing (+397%), underscore (+391%), realm (+381%), surpasses (+368%), groundbreaking (+330%), advancements (+278%), aligns (+267%) | J | "delves 0.21 14.38 6697.14 ... intricate 6.22 44.22 611.24 ... aligns 1.55 5.68 266.97 Table 2: Our 21 focal words." | lexical |
| Delve at the start of an abstract | `^(This\|The) (article\|paper\|study) delves into` | J | "the word “delve” in the first sentence of an abstract (e.g., ’This article delves into ...’)" | lexical |
| Model drift (GPT-4o-mini) | boasts and delve down, underscore up | J | "’boasts’ is no longer overused; ’delve’ is still overused, but to a lesser extent; and the usage of ’underscore’ has increased significantly." | caveat |

### Copula decline (Geng and Trotta)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Fewer "is" and "are" | rate of `\b(is\|are)\b` per sentence (low suggests LLM revision) | G | "The counts in 10,000 abstracts of these two words were quite stable before 2023. However, the frequency of these two terms has dropped by more than 10% in 2023." | statistical (inverse) |
| A simple revision prompt reproduces it | "Revise the following sentences:" | G | "Many words have different frequencies before and after ChatGPT processing, such as the words “is”, “are”, and “significant”" | statistical |

### Em dash rates by model (Freeburg)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Human em dash baseline | `—` per 1,000 words | F | "the weighted mean across our sample was 3.23 per 1,000 words (median 3.83; range 0.33–17.12)." | statistical |
| Model rates, unconstrained | GPT-4.1 10.62, Claude Opus 4.6 9.09, Claude Sonnet 4 8.29, Claude Haiku 3.5 7.51, DeepSeek V3 6.95, GPT-4o Mini 4.16, GPT-4o 4.12, Gemini 2.5 Pro 3.53, GPT-5.4 1.43, Gemini 2.5 Flash 1.28, Llama 0.00 | F | "OpenAI’s GPT-4.1 produces 10.62 per 1,000 words, Anthropic’s Claude Opus 4.6 produces 9.09, DeepSeek V3 produces 6.95—while Meta’s Llama models [21, 22] produce zero." | statistical |
| Persistence when told to avoid markdown | em dashes remain while headers and bullets go away | F | "GPT-4.1 drops only from 10.62 to 9.10 per 1,000 words (a 14% reduction)." | statistical |
| Em dash is not a universal overuse | (threshold must be model-aware) | F | "The finding is therefore not that LLMs uniformly “overuse” em dashes relative to all human writing" | caveat |

### Sentence-length uniformity and other news-text features (Muñoz-Ortiz et al.)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| Low sentence-length variance ("burstiness") | standard deviation or IQR of sentence length in tokens; mass concentrated in 10 to 30 tokens | M | "Human texts exhibit more scattered sentence length distributions, more variety of vocabulary" | statistical |
| Sentence lengths cluster mid-range | share of sentences in the 10 to 30 token range | M | "the models exhibit a higher frequency of sentence generation within the 10 to 30 token range compared to humans, whereas humans tend to produce longer sentences with greater frequency." | statistical |
| Lower lexical variety | type-token ratio or MTLD | M | "more variety of vocabulary" (attributed to human texts) | statistical |
| More numbers, symbols, auxiliaries, pronouns | POS rates for NUM, SYM, AUX, PRON | M | "LLM outputs use more numbers, symbols and auxiliaries (suggesting objective language) than human texts, as well as more pronouns." | statistical |
| Less negative emotion, more joy | sentiment lexicon rates | M | "Humans tend to exhibit stronger negative emotions (such as fear and disgust) and less joy compared to text generated by LLMs" | statistical |

### Expert-annotator clues (Russell et al.)

| tell | concrete pattern | source | verbatim quote | kind |
|---|---|---|---|---|
| AI vocabulary is the most cited clue | the vocabulary lists below | RU | "VOCABULARY 53.1% LLMs use specific words and phrases more often than human writers" | lexical |
| Detection-guide nouns | aspect, challenges, climate, community, component, development, dreams, environment, exploration, grand scheme, health, hidden, importance, landscape, life, manifold, multifaceted, nuance, possibilities, professional, quest, realm, revolution, roadmap, role, significance, tapestry, testament, toolkit, whimsy | RU | "Nouns: aspect, challenges, climate, community, component, development, dreams, environment, exploration, grand scheme, health, hidden, importance, landscape, life, manifold, multifaceted, nuance, possibilities, professional, quest, realm, revolution, roadmap, role, significance, tapestry, testament, toolkit, whimsy" | lexical (low precision for common nouns) |
| Detection-guide verbs | capturing, delve/dive into, elevate, embrace, empower, enact, enhance, engage, ensure, evoking, evolving, explore, fostering, guiding, harness, highlights, integrate, jeopardizing, journey, navigating, navigate, notes, offering, partaking, resonate, revolutionize, shape, seamlessly, tailor, transcend, underscores | RU | "Verbs: capturing, change, consider, delve/dive into, elevate, embrace, empower, enact, enhance, engage, ensure, evoking, evolving, explore, fostering, guiding, harness, highlights, improve, integrate, intricate, jeopardizing, journey, navigating, navigate" | lexical |
| Detection-guide adjectives and adverbs | authentic, comprehensive, crafted, crucial, curated, deeper, diverse, elegant, essential, groundbreaking, key, meaningful, paramount, pivotal, powerful, profound, quirky, robust, seamless, significant, transformative, valuable, vast, vibrant, vivid, whimsical; additionally, aptly, creatively, moreover, successfully | RU | "Adjectives: authentic, complex, comprehensive, crafted, creative, critical, crucial, curated, deeper, diverse, elegant, essential, groundbreaking, key, meaningful, paramount, pivotal, powerful, profound, quirky, robust, seamless" | lexical |
| Detection-guide phrases | as we [verb] the topic, cautionary tale, has shaped the, in a world (of\|where), in conclusion, in summary, it's crucial to, it's important to note, it's not about ___ it's about ___, not only ___ but also, packs a punch, paving the way, personal growth, remember that, simple yet ___, when it comes to | RU | "Phrases: as we [verb] the topic, cautionary tale, connect with, has shaped the, in a world of/where, in conclusion, in summary, it’s crucial to, it’s important to note, it’s not about ___ it’s about ___" | lexical |
| Predictable sentence structure, triads | not only ... but also; three-item lists | RU | "AI-generated sentences follow predictable patterns (e.g., high frequency of “not only . . . but also . . . ”, or consistently listing three items), while human-written sentences vary more in terms of length." | lexical plus statistical |
| "It's not just this, it's this" | `it['’]?s not just .{0,40}, it['’]?s` | RU | "the comparison of ‘it’s not just this, it’s this’ and I’m seeing it here, along with listings of specifically three ideas." | lexical |
| Grammatically perfect; avoids dashes and ellipses | low typo rate; absent `...`; absent dashes (contradicts em-dash row for some models) | RU | "AI-generated text is usually grammatically perfect (also avoiding dashes and ellipses), while human-written text often contains minor errors." | statistical (inverse) |
| Bold-header bullets with colon | `^\s*[-*]\s*\*\*[^*]+\*\*:` | RU | "When AI makes lists, it typically uses the format of creating a bold header per bullet point, followed by a colon and then description of that list item." | structural |
| Always italicizes titles | every book title italicized | RU | "If a book title is referenced in a text, AI-generated text will always italicize the title" | judgment |
| Complex sentences throughout | low share of simple sentences | RU | "AI-generated sentences often follow the complex sentence structure, with multiple dependent and independent clauses" | statistical (parser) |
| "is a testament to" sentence | `\bis a testament to\b` | RU | "“When it comes to celebrating Halloween, this holiday is a testament to the importance of empathy and community.”" | lexical |
| Reflective, uplifting tone toward the end | positive sentiment in last paragraph | RU | "AI tends to be inherently positive, attempting to emotionally uplift the reader, especially towards the conclusion." | judgment |
| Scene-setting opener | `^On (a\|an) \w+ \w+ (morning\|evening\|night\|day)` or `^On [A-Z][a-z]+ \d{1,2}, \d{4},` | RU | "AI-written introductions often contain a strong scene-opener with a description of a specific time or place, such as "On a drab November morning..."" | lexical |
| Neat, summarizing conclusion | final paragraph restates earlier content; In conclusion, In summary | RU | "AI-generated conclusions are often overly long and summarize everything that has already been written in an article" | judgment |
| Optimistically vague conclusions | upbeat generic closer | RU | "Close behind are formulaic sentence and document structures (e.g., optimistically vague conclusions)" | judgment |
| No profanity, even mild | absence of darn and similar words | RU | "AI will avoid any type of swear word, including mild ones like ‘darn’" | lexical (inverse) |
| Quotes sound like the narrator | quoted speech matches the surrounding register | RU | "AI-generated quotes sound overly formal, lack the varied nuances of real conversation, and often mirror the article’s main text too closely in style." | judgment |

## Not verified

The items below were looked for or cited by a fetched page, but this session did not confirm them against a fetched primary source. They are left out of the catalog, except where a fetched page reported them, and the relevant row says so.

The title given in the request, "Delving into ChatGPT usage in academic writing through excess vocabulary", was not verified. The fetched arXiv v5 of 2406.07016 is titled "Delving into LLM-assisted writing in biomedical publications through excess vocabulary". The Science Advances version (vol. 11, issue 27, 2 July 2025) is known only from Wikipedia's citation and was not fetched.

The PNAS published version of Reinhart et al. was not fetched; the catalog uses arXiv v2. The paper's supplementary tables were not fetched either: S4 to S6, which hold rates for all 66 Biber features, and S7 to S8, the per-document word prevalence. That means the direction and size of the hedge feature ("hedging phrases (such as something like or almost)") was not verified.

The July 2026 study that Wikipedia cites for "only Claude used em dashes more than professional writers" is an Economist article, "How to spot AI writing", 30 July 2026. It is paywalled and was not fetched. That sentence appears in the catalog only as Wikipedia's claim.

Wikipedia cites several other sources that were not fetched: the Washington Post style analysis (Merrill, Chen and Kumer, 13 November 2025), Kriss in the New York Times (3 December 2025), Geng and Trotta's "Human-LLM Coevolution: Evidence from Academic Writing", Huang et al.'s "Wikipedia in the Era of LLMs: Evolution and Risks", Sussman and Carter on sentiment (arXiv 2504.19556), and the Ars Technica report on GPT-5.1 em dash suppression. None of their specific numbers appear in the catalog.

"Burstiness" was not verified as a named, defined metric, for example the GPTZero perplexity-variance metric. The catalog uses only the sentence-length dispersion finding from Muñoz-Ortiz et al.

Two web-search leads appeared during the search but were not fetched: arXiv 2606.27052, "Human–LLM Collaboration Is Transforming Complexity Metrics in Scientific Texts", which covers dash usage trends, and arXiv 2604.14111, "Interpretable Stylistic Variation in Human and LLM Writing Across Genres, Models, and Decoding Strategies".

Wikipedia's edit-summary, AfC, wikitext-template, and citation-field signs (for example outdated access-date, invalid DOIs, and pre-placed maintenance templates) were read but left out because they are specific to Wikipedia rather than to prose. The "Pronounced shift in writing style" and "Differences between LLMs" sections were also read and left out, because no deterministic pattern can be drawn from them.
