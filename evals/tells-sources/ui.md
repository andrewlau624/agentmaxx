# AI-generated UI tells: sources

Scope: visual and code-level signs that a web page (HTML, CSS, Tailwind,
React) was produced by a model with no design direction. Every page below was
fetched in this session (2026-10-03) and every quote in the catalog was copied
from the fetched text and then checked against it by script. Pages that could
not be fetched, or claims with no quote behind them, are listed under "Not
verified" and are not in the catalog.

Weight the sources accordingly. S1 to S4 are Anthropic's own guidance and
describe what Claude produces when unguided. S5 is the Tailwind creator's own
statement. S6 and S7 are the only sources that ran a deterministic detector
against real pages (1,590 Show HN landing pages, 5 to 10 percent false
positives by the author's manual check), so their thresholds are the closest
thing to a tested spec. S8 to S17 are secondary: blog posts, community skills
and vendor content, several of which sell a de-slopping product or service.
None of the sources claims a single pattern proves model authorship; S6, S15
and S16 all score clusters of patterns instead.

## Sources

| ID | Title | Author | Date | URL |
|---|---|---|---|---|
| S1 | frontend-design skill, SKILL.md (current) | Anthropic | last commit 2026-09-02 | https://raw.githubusercontent.com/anthropics/claude-code/main/plugins/frontend-design/skills/frontend-design/SKILL.md |
| S2 | frontend-design skill, SKILL.md (first version, commit 62c3cbc) | Anthropic | 2025-11-12 | https://raw.githubusercontent.com/anthropics/claude-code/62c3cbc47147ddbf666b210be13a91133e7d449e/plugins/frontend-design/skills/frontend-design/SKILL.md |
| S3 | Frontend Aesthetics: A Prompting Guide (cookbook notebook) | Anthropic | not dated in the notebook | https://raw.githubusercontent.com/anthropics/claude-cookbooks/main/coding/prompting_for_frontend_aesthetics.ipynb |
| S4 | Improving frontend design through Skills | Anthropic Applied AI team: Prithvi Rajasekaran, Justin Wei, Alexander Bricken | 2025-11-12 | https://claude.com/blog/improving-frontend-design-through-skills |
| S5 | Post on X | Adam Wathan | 2025-08-07 | https://x.com/adamwathan/status/1953510802159219096 (text fetched via https://api.fxtwitter.com/adamwathan/status/1953510802159219096) |
| S6 | Scoring Show HN submissions for AI design patterns | Adrian Krebs | 2026-04-20 | https://adriankrebs.ch/blog/design-slop/ |
| S7 | design-slop-cop (detector source: src/patterns/*.js, src/lib/color.js, src/lib/slop-fonts.js) | Adrian Krebs | repo last pushed 2026-07-07 | https://github.com/AdrianKrebs/design-slop-cop |
| S8 | Hacker News thread on S6 (secondary) | various commenters | 2026-04-22 | https://news.ycombinator.com/item?id=47864393 (fetched via https://hn.algolia.com/api/v1/items/47864393) |
| S9 | Why Every AI-Built Website Looks the Same (Blame Tailwind's Indigo-500) | Alan West | 2026-03-25 | https://dev.to/alanwest/why-every-ai-built-website-looks-the-same-blame-tailwinds-indigo-500-3h2p |
| S10 | Why Your AI Keeps Building the Same Purple Gradient Website | Pragnesh (prg.sh) | 2025-10-26 | https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website |
| S11 | Why Does Every AI-Generated Website Look the Same? | Paco Valdez | 2025-11-10 | https://pacovaldez.substack.com/p/why-does-every-ai-generated-website |
| S12 | AI Slop Fonts and Gradients: The Tells That Give Away AI Design | 925Studios (design agency; "Reviewed by Yusuf") | 2026-06-14 | https://www.925studios.co/blog/ai-slop-design-tells |
| S13 | Why v0, Bolt, and Lovable all ship the same look | Laith Aljunaidy (uxskill, sells a design-lint tool) | 2026-05-29 | https://uxskill.laithjunaidy.com/blog/ai-app-builders-generic-design.html |
| S14 | impeccable skill, reference/craft-floor.md | pbakaus (GitHub) | last commit 2026-08-14 | https://raw.githubusercontent.com/pbakaus/impeccable/HEAD/.agent/skills/impeccable/reference/craft-floor.md |
| S15 | avoid-ai-design README | funboy322 (GitHub) | repo created 2026-05-30, pushed 2026-09-24 | https://github.com/funboy322/avoid-ai-design |
| S16 | Anti-AI-UI README | Vanszs (GitHub) | 2026-06-19 | https://github.com/Vanszs/Anti-AI-UI |
| S17 | AI Slop in 2026: The State of the AI-Generated Web | Sailop (organization, commercial) | 2026-04-28 | https://www.sailop.com/blog/ai-slop-2026-state-of-the-ai-generated-web |

Also fetched but not cited: Developers Digest, "AI Design Slop: 16 Patterns
That Out Your App as Vibe-Coded" (2026-04-22,
https://www.developersdigest.tech/blog/ai-design-slop-and-how-to-spot-it),
which restates S6's list and adds nothing checkable.

## Catalog

Detection hints in the second column are this document's proposal for a
static scan of HTML/CSS/JSX; where a source ships its own threshold (S7), the
hint says so. Quotes are verbatim, including any typos or dropped apostrophes
in the original.

### Color

| Pattern | Detection in code | Source | Quote |
|---|---|---|---|
| Indigo / violet primary accent | Tailwind `bg-indigo-*`, `text-indigo-*`, `bg-violet-*`, `bg-purple-*` on buttons and links; any CSS color whose HSL hue is 250 to 300 with saturation above 0.25 and lightness 0.15 to 0.85 (S7's `isPurple`), counted on filled CTAs (`a`, `button`, `.btn`, `.cta`) | S5 | "I'd like to formally apologize for making every button in Tailwind UI `bg-indigo-500` five years ago, leading to every AI generated UI on earth also being indigo." |
| (same) | (same) | S7 | "return hsl.h >= 250 && hsl.h <= 300 && hsl.s > 0.25 && hsl.l > 0.15 && hsl.l < 0.85;" |
| (same) | (same) | S9 | "And those components all had bg-indigo-500 buttons, text-indigo-600 headings, and from-indigo-500 to-purple-600 gradients." |
| (same) | (same) | S6 | "“VibeCode Purple”" |
| (same) | (same) | S13 | "A violet or indigo primary, the same one you have seen on a hundred other generated apps." |
| Purple gradient, especially on a white background | `bg-gradient-to-*` with `from-indigo-*`/`from-blue-*`/`from-violet-*` and `to-purple-*`/`via-purple-*`; `linear-gradient(` whose stops include a purple-hue color; page background white or near-white | S3 | "Clichéd color schemes (particularly purple gradients on white backgrounds)" |
| (same) | (same) | S4 | "it will almost always conform to Inter fonts, purple gradients on white backgrounds, and minimal animations." |
| (same) | (same) | S2 | "cliched color schemes (particularly purple gradients on white backgrounds)" |
| (same) | (same) | S12 | "The blue-to-purple gradient is the single loudest AI tell in 2026." |
| Tailwind blue-600 to purple-600 palette, with emerald success accent | literal classes `from-blue-600 to-purple-600`; hex `#3b82f6`, `#2563eb`, `#8b5cf6`, `#7c3aed`; `emerald-500` / `#10b981` for success states | S17 | "A primary palette built around Tailwind's blue-500 / 600 (#3b82f6 / #2563eb) and purple-500 / 600 (#8b5cf6 / #7c3aed), with a gradient running between them, plus a neutral gray scale and an accent of \"AI green\" ( emerald-500 , #10b981) for success states." |
| Gradients used broadly as decoration | count elements with `background-image: *-gradient(` that has a non-transparent stop; S7 flags 4 or more | S6 | "Gradient everything" |
| (same) | (same) | S7 | "minBgGradients: 4" |
| (same) | (same) | S1 | "the same soft grey shadow (rgba(0,0,0,.1)) under each, and gradient washes as decoration" |
| Gradient-filled headline text | `bg-clip-text text-transparent` with a gradient class on `h1`/`h2`; CSS `background-clip: text` or `-webkit-background-clip: text` over a gradient | S9 | "Hero section with gradient text" |
| (same) | (same) | S7 | "Hero H1 with `background-clip: text` over a gradient (one element)" |
| (same) | (same) | S14 | "Gradient text. Emphasis comes from weight or size." |
| (same) | (same) | S16 | "❌ gradient bg-clip-text headlines" |
| Large colored glows / colored box-shadows | `box-shadow` (or Tailwind `shadow-<color>-*`, `shadow-[0_0_..._<color>]`) whose color is saturated (not grey) with blur radius 15px or more; S7 fires on 2 or more | S6 | "Large colored glows and colored box-shadows" |
| (same) | (same) | S7 | "Colored box-shadows / glows. Saturated, non-grey shadow colors with" |
| Permanent dark mode with medium-grey, low-contrast body text | dark `body` background (e.g. `bg-gray-900`, `bg-slate-950`, `#0a0a0a`) and body text below 7:1 contrast (`text-gray-400`, `text-slate-400`); no light theme | S6 | "Perma dark mode with medium-grey body text and all-caps section labels" |
| (same) | (same) | S7 | "Detected via WCAG contrast: % of body text below AAA (7:1) on a dark surface." |
| Second-order default: warm cream background, high-contrast serif, terracotta accent | background near `#F4F1EA`; accent near `#D97757`; serif display face | S1 | "a warm cream background (near #F4F1EA) with a high-contrast serif display and a terracotta or warm-clay accent (often near #D97757 — Anthropic's own Claude-interaction accent, so on a user's brief it reads as a tell)" |
| Second-order default: near-black background with one acid-green or vermilion accent | near-black page background plus a single saturated green (e.g. lime/chartreuse) or red-orange accent and no other hues | S1 | "a near-black background with a single bright acid-green or vermilion accent" |
| Tinted near-black instead of black | literal `#0B0B0B`, `#111`, `#111111` as text or background | S1 | "tinted near-black (#0B0B0B, #111) standing in for black" |

### Typography

| Pattern | Detection in code | Source | Quote |
|---|---|---|---|
| Inter (and other generic families) as the only face | `font-family` whose first family is Inter, Roboto, Arial, Open Sans, Lato or `system-ui`/`-apple-system`; Google Fonts link for `family=Inter`; `next/font/google` import of `Inter`; Tailwind `font-sans` with no theme override | S3 | "Overused font families (Inter, Roboto, Arial, system fonts)" |
| (same) | (same) | S3 | "**Never use:** Inter, Roboto, Open Sans, Lato, default system fonts" |
| (same) | (same) | S4 | "Tell Claude to \"avoid Inter and Roboto\" or \"use atmospheric backgrounds instead of solid colors,\" and results improve immediately." |
| (same) | (same) | S6 | "Inter used for everything, but especially the centered hero headlines" |
| (same) | (same) | S13 | "Inter for everything, set at the same large display sizes the demos use." |
| "Tasteful" fallback display faces | font family Space Grotesk, Instrument Serif, Geist, Fraunces, Bricolage Grotesque, Sora, Young Serif, Bodoni, Syne (S7's list; it flags when they cover 25 percent or more of text) | S3 | "You still tend to converge on common choices (Space Grotesk, for example) across generations." |
| (same) | (same) | S6 | "LLM tend to use certain font combos like Space Grotesk, Instrument Serif and Geist" |
| (same) | (same) | S7 | "Templated display fonts — Space Grotesk, Instrument Serif, Syne, Fraunces" |
| (same) | (same) | S17 | "Inter for body, Inter Display or Geist for headings, occasional flirtation with Cal Sans for the hero headline only." |
| One word in the headline set apart by italic, serif, color or gradient | inside the hero `h1`, a child `span`/`em`/`i` with a different `font-family`, `italic`, a color class, or `bg-clip-text` | S1 | "Accenting just a single word or phrase in a headline, like putting one word in italic/bold or a different color." |
| (same) | (same) | S6 | "Serif italic for one accent word in an otherwise-Inter hero" |
| (same) | (same) | S7 | "a large hero headline that sets one word apart by switching" |
| Tracked-out all-caps eyebrow / section labels | `uppercase` plus `tracking-wide`/`tracking-widest`/`tracking-[0.2em]`, or `text-transform: uppercase` with positive `letter-spacing` (S7 uses 0.5px or more), on a short element directly above a heading | S1 | "a tracked-out ALL-CAPS eyebrow label above every heading" |
| (same) | (same) | S6 | "All-caps headings and section labels" |
| (same) | (same) | S14 | "A kicker or eyebrow above a heading. This one is a ban, not a default: no brief earns it back." |
| Monospace face for small labels that are not code | `font-mono` / `monospace` on labels, badges, captions outside `code`/`pre` | S1 | "a monospace face for small data labels" |
| (same) | (same) | S14 | "Monospace as a costume for \"technical\" rather than for code, data, or measurement." |

### Layout

| Pattern | Detection in code | Source | Quote |
|---|---|---|---|
| Centered hero in a generic sans | first section with `text-center` / `text-align: center` / `items-center justify-center`, large `h1`, subhead, CTA buttons; paired with an Inter/system font | S6 | "Centered hero set in a generic sans" |
| (same) | (same) | S10 | "Hero section with centered text and a CTA button" |
| (same) | (same) | S13 | "A centered hero with a headline, a one-line subhead, and a soft gradient washing the background." |
| Two CTAs under the hero | two adjacent buttons/links (primary filled plus secondary outline/ghost) immediately after the hero subhead | S17 | "Centered hero with large H1, smaller subhead, two CTAs (primary + secondary), then a lg:grid-cols-3 features section" |
| Pill badge / eyebrow directly above the hero H1 | `rounded-full` (or boxed) short element with background or border immediately before the hero `h1`, often with "New", "Introducing", or ✨ | S6 | "Badge right above the hero H1" |
| (same) | (same) | S7 | "\"New · AI-powered\", \"✨ AI-powered\", small uppercase tracker labels." |
| Three identical feature cards, each with an icon on top | `grid-cols-3` / `md:grid-cols-3` / `lg:grid-cols-3` (or `repeat(3, ...)`) whose 3 children share one class list and each start with an icon (`svg`, Lucide component, emoji) then a heading and short text | S9 | "Three-column feature grid with icons" |
| (same) | (same) | S10 | "Three features in boxes below, each with an icon" |
| (same) | (same) | S6 | "Identical feature cards, each with an icon on top" |
| (same) | (same) | S14 | "Same-size cards of icon plus heading plus text as the page structure." |
| (same) | (same) | S12 | "Open almost any AI-generated landing page and you will find a row of three feature cards, rounded corners, soft shadow, thin-line icon at the top of each." |
| Stock section order | sections in order hero, logo wall, features grid, testimonials, pricing, repeated CTA, four-column footer | S17 | "then a logo wall, then a testimonial carousel, then a pricing table, then a CTA repeat, then a footer with four columns." |
| Bento grid as the "alternative" feature section | grid with mixed `col-span-2`/`row-span-2` cards in the features section | S17 | "the bento grid is no longer the safe alternative; it has become its own tell" |
| Numbered 01 / 02 / 03 step markers | 3 or more consecutive ascending numerals ("1", "01", "Step 1") in styled badges or large type, in reading order | S1 | "Many generic designs use numbered markers (01 / 02 / 03), but that's only appropriate if the content actually is a sequence" |
| (same) | (same) | S6 | "Numbered “1, 2, 3” step sequences" |
| (same) | (same) | S14 | "Section numbers (01 / 02 / 03) unless the sequence itself carries information the reader needs." |
| Stat banner / hero metric row | 3 to 6 sibling elements each holding a short large number such as "10K+", "99.9%", "4.9★" (S7: big text 22px or more, 10 characters or fewer) | S6 | "Stat banner rows" |
| (same) | (same) | S7 | "Stat banner row. \"10K+ users · 99.9% uptime · 4.9★\" pattern: 3–6 sibling" |
| (same) | (same) | S1 | "a big number with a small label, supporting stats, and a gradient accent is the default treatment" |
| (same) | (same) | S14 | "The hero-metric template: big number, small label, supporting stats, accent." |
| FAQ accordion at the bottom of a landing page | 3 or more `<details>` elements, or a section titled FAQ with 3 or more question-shaped items, in the lower half of the page | S7 | "Generic FAQ accordion at the bottom of a landing page. Almost every" |
| Three-tier pricing with a "Most Popular" middle column | pricing grid of 3 columns, middle one carrying a "Most Popular" badge | S17 | "a pricing table with a middle column tagged \"Most Popular\"" |
| Broadsheet look (second-order default) | `border-radius: 0` everywhere, 1px hairline rules, multi-column dense text | S1 | "a broadsheet-style layout with hairline rules, zero border-radius, and dense newspaper-like columns" |

### Components and surfaces

| Pattern | Detection in code | Source | Quote |
|---|---|---|---|
| One radius on everything, usually large | the same `rounded-xl`/`rounded-2xl` (or `border-radius: 0.5rem`/`1rem`) on most cards, buttons and inputs regardless of hierarchy | S1 | "the SaaS-card kit: content chopped into identical rounded cards, one border-radius on everything regardless of hierarchy" |
| (same) | (same) | S9 | "Rounded corners on everything (border-radius: 0.5rem)" |
| (same) | (same) | S15 | "**Components** wrapped in `rounded-2xl`, `shadow-lg`, and `backdrop-blur`, straight from the shadcn defaults." |
| (same) | (same) | S16 | "❌ rounded-2xl uniformity" |
| (same) | (same) | S17 | "Every card has rounded-2xl and shadow-md ." |
| Same soft grey shadow under every card | `box-shadow` with `rgba(0,0,0,0.1)` (or `.1`), Tailwind `shadow`, `shadow-md`, `shadow-lg` repeated on every card | S1 | "the same soft grey shadow (rgba(0,0,0,.1)) under each" |
| (same) | (same) | S10 | "Subtle shadows (exactly 0.1 opacity)" |
| (same) | (same) | S9 | "Subtle box shadows at low opacity" |
| Glassmorphism (frosted translucent panels) | `backdrop-blur-*` / `backdrop-filter: blur(` with a translucent background (`bg-white/10`, `rgba(255,255,255,0.1)`) on cards or panels; S7 excludes sticky nav and footer bars | S6 | "Glassmorphism" |
| (same) | (same) | S7 | "Glassmorphism — translucent backdrop-blur cards or panels." |
| (same) | (same) | S14 | "Glass and blur as decoration rather than as a specific effect." |
| (same) | (same) | S16 | "❌ glassmorphism backdrop-blur nav" |
| Colored accent stripe on the left or top edge of cards | `border-l-4`/`border-l-[3px]`/`border-t-4` with a color class and other sides 0; CSS `border-left: Npx solid <saturated color>` with N of 2 or more; narrow absolutely-positioned `::before` bar | S6 | "A designer recently told me that “colored left borders are almost as reliable a sign of AI-generated design as em-dashes for text”, so I started to notice them on many pages." |
| (same) | (same) | S7 | "Accent stripe on cards (top or left edge)." |
| (same) | (same) | S14 | "A colored `border-left` or `border-right` above 1px on cards, list items, callouts, or alerts." |
| (same) | (same) | S8 | "AI definitely does seem to want to add coloured left borders, tags and superfluous numbers all over the place from my experience, you have to tell it specifically not to" |
| Hard offset (zero-blur) shadow outside a neobrutalist design | `box-shadow: 4px 4px 0` or `shadow-[4px_4px_0_...]` | S14 | "Hard offset shadows (`box-shadow: 4px 4px 0`) outside a world that is actually neobrutalist." |
| Untouched shadcn/ui defaults | shadcn component imports (`@/components/ui/*`) with the stock theme tokens unchanged | S6 | "shadcn/ui" |
| (same) | (same) | S15 | "untouched shadcn palettes" |

### Icons and glyphs

| Pattern | Detection in code | Source | Quote |
|---|---|---|---|
| Emoji used as icons (feature cards, nav, sidebar) | emoji code points (e.g. 🚀 ⚡ ✨ 📊) as the first child of nav links, list items, or card headers; S7 fires when 40 percent or more of sidebar links contain emoji | S6 | "Sidebar or nav with emoji icons" |
| (same) | (same) | S7 | "Sidebar/nav with emoji icons. Common AI-generated dashboard pattern." |
| (same) | (same) | S14 | "Unicode glyphs or emoji standing in for an icon system." |
| (same) | (same) | S16 | "❌ emoji icons (🚀⚡✨)" |
| Sparkle icon for AI features | ✨ emoji, Lucide `Sparkles`, Heroicons `SparklesIcon` | S15 | "the worn Lucide set and the sparkle-for-AI" |
| Lucide icons used decoratively | `lucide-react` imports such as `Check`, `Zap`, `Shield` placed in every feature card | S17 | "Lucide icons used decoratively" |
| Arrow appended to link and button text | link or button text ending in "→" (or an `ArrowRight` icon after the label) | S1 | "a '→' appended to link and button text" |
| (same) | (same) | S15 | "arrows welded to CTAs" |
| Middle-dot meta strings and "WORD — fragment" labels | text matching `\w+ · \w+ · \w+`; labels of the form `UPPERCASE — words` | S1 | "meta strings joined with middle dots ('A · B · C'); labels built as 'WORD — fragment' with a spaced em dash" |

### Motion

| Pattern | Detection in code | Source | Quote |
|---|---|---|---|
| Fade-and-slide-up entrance on every section | Framer Motion `initial={{ opacity: 0, y: 20 }}` with `whileInView` or `animate`, repeated per section; CSS keyframes from `opacity: 0; transform: translateY(...)` on many sections; `animate-fade-in-up` style classes | S1 | "fade-and-slide-up entrances on each section and hover transitions on every card are the generic default and read as AI-generated." |
| (same) | (same) | S17 | "Framer Motion fade-in-from-below as elements enter the viewport, with a stagger of 0.1s ( initial={{opacity:0, y:20}} , whileInView )." |
| Hover lift / scale on every card | `hover:-translate-y-1`, `hover:scale-105`, `hover:shadow-lg` repeated on all cards | S17 | "Hover states that lift cards by 4px and add a shadow-lg ." |
| (same) | (same) | S16 | "❌ hover:scale-105 on cards" |
| No reduced-motion handling | animations present but no `prefers-reduced-motion` media query or `motion-reduce:` variant | S16 | "❌ no prefers-reduced-motion" |

### Copy (detectable as string literals in markup)

| Pattern | Detection in code | Source | Quote |
|---|---|---|---|
| Hype verbs in headlines | headline or CTA text containing "Elevate", "Seamless", "Supercharge", "Unlock", "Powerful" | S15 | "**Copy** that opens with \"Elevate your workflow\" and ends with a \"Get Started\" button." |
| (same) | (same) | S16 | "❌ \"Supercharge/Unlock/Seamless\" copy" |
| Generic CTA label | button text "Get Started", "Get started free", "Submit" | S12 | "There is a gradient button that says \"Get Started.\"" |
| (same) | (same) | S1 | "A CTA says exactly what happens when it is used: \"Save changes,\" not \"Submit.\"" |
| "Trusted by" logo strip | text "Trusted by" above a logo row | S16 | "\"Trusted by\"" |
| Placeholder testimonial identities | testimonial names drawn from a small generic set (S17's example names), stock avatar images | S17 | "The testimonial avatars were stock-photo faces with generated-sounding name pairs (\"Sarah Chen\", \"Marcus Williams\")" |

## Not verified

These were searched for or commonly claimed but are not in the catalog,
because no fetched page supported them with a quote, or the page could not be
fetched.

A statement from Tailwind's own documentation or Tailwind Labs (other than
Adam Wathan's post, S5) that indigo is a default. Nothing fetched. S9 adds the
caveat that Tailwind CSS itself has no default button color and the indigo
came from Tailwind UI examples; S11 says the opposite ("the default value for
the background color of buttons in Tailwind"). Treat the mechanism as
disputed; the pattern itself is well sourced.

Fabricated or made-up statistics as a tell. Sources flag the stat-banner
layout (S6, S7, S1, S14) and S7 calls it "trust-padding", but no fetched
source claims that the numbers themselves are invented by the model, so a
"fake stats" rule has no source here beyond the layout check.

Sparkle icon as a broader AI cliche. Essays by Josh Clark ("Your Sparkles Are
Fizzling", bigmedium.com), Matt Hogg, Jurgen Gravestein and Geoff Graham
appeared in search results but were not fetched; they also concern AI product
features rather than AI-generated page code. Only S15 and S16 (community
skills) and S7's comment mention the sparkle as a generated-UI tell.

Kai Ni, "Design Observation: Why Do AI-Generated Websites Always Favour
Blue-Purple Gradients?" (Medium): fetch blocked by Cloudflare. Not used.

Anna Arteeva's v0/Lovable/Bolt comparison (annaarteeva.substack.com): fetched,
but the "ShadCN look" quote that search summaries attribute to her is in a
different post that was not fetched. Not used.

Attribution of the Anthropic cookbook (S3) to Prithvi Rajasekaran, October
2025: claimed by search summaries, not stated in the fetched notebook. S4
names him among the blog's authors, which is what the Sources table uses.

VibeCodeKit's guide (vibecodekit.dev/ai-slop-design), which search summaries
say names the colored left-border strip as "the single most reliable AI tell"
and "rounded-2xl shadow-lg p-6" as the shadcn default card: the fetch returned
nothing. The same patterns are in the catalog from other sources.

Specific Lovable color signature ("purple and pink"): appears only in S17's
per-tool notes, a single vendor source with no method; left out.
