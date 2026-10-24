#!/usr/bin/env python3
"""Catch the two request-reading failures before the model acts on them.

UserPromptSubmit. Reads the event JSON on stdin, prints additionalContext
only when a guard fires, otherwise nothing. Pure regex, no file I/O.

  misread guard     short prompt that is easy to read wrong: a bare "it/that/
                    this/the other one" with nothing in the prompt to point at,
                    a correction opener ("no", "wait", "i meant"), or several
                    typo'd words. Asks for a one-line restatement of the
                    reading before acting. Skips acknowledgments ("ok", "go"),
                    slash commands and pasted content.
  assumption guard  implementation task with 2+ unknowns: hedges ("should",
                    "probably", "maybe"), an integrate/refactor/migrate/deploy/
                    build request that names no file or symbol, or "make X work
                    with Y". Asks for all load-bearing assumptions at once, each
                    with how it will be checked; ask only for the uncheckable.

Both lines are re-sent on every later turn, so each is kept short and the
guards are tuned to fire on a minority of prompts (replayed over 30 days of
this machine's typed prompts: misread ~20%, assumption ~8%). Evidence:
23/68 corrections in that window were misreads; ClarifyCodeBench shows models
catch a second ambiguity under 10% of the time and users override most pauses,
so the default is check, not ask. Disable with AGENTMAXX_PROMPT_GUARD=0.
"""
from __future__ import annotations

import json
import os
import re
import sys

I = re.IGNORECASE
MISREAD_WORDS = 15
GENERIC_WORDS = 8
ASSUMPTION_MIN_WORDS = 6

MISREAD_LINE = ("Short prompt: restate your reading in one line before acting (which object, which repo/file, which "
                "earlier message it refers to); act on that reading; ask only if two readings mean materially "
                "different work.")
ASSUMPTION_LINE = ("Before editing, list the load-bearing assumptions (aim for all of them at once, not one), and for "
                   "each say how you will check it: read the file, run a command, or ask. Ask only for ones you "
                   "cannot check yourself.")

ACK = re.compile(r"^(ok(ay)?|yes|yep|yeah|y|sure|go|go ahead|do it|continue|proceed|next|done|k|kk|thanks|thank you|"
                 r"ty|nice|cool|great|good|perfect|lgtm|yes please|please|not yet|stop)[\s.!,]*$", I)
SLASH = re.compile(r"^\s*/[\w-]+")
PASTED = re.compile(r"<pasted_content|```|^\s*[{\[<]|\n[^\n]*\n[^\n]*\n|https?://\S{40,}", I)
# A bare pointer with nothing in the prompt to point at.
DEICTIC = re.compile(r"\b(it|that|this|these|those|them|the other one|the same|same thing|like that|like this|"
                     r"there|here|again|the rest|the others?|one more)\b", I)
# Something in the prompt the pointer could refer to: a path, URL, symbol, number, quote or Name.
REFERENT = re.compile(r"\w+/|/\w|~/|https?://|\b\w+[_.]\w+\b|\b[a-z]+[A-Z]\w*|\b[A-Z][a-z]{2,}|\d|[`\"]")
CORRECTION = re.compile(r"^\W*(no|nope|wait|hold on|actually|hmm|i meant|i mean|not that|not this|not like that|"
                        r"thats not|that's not|wrong|instead)\b", I)

HEDGE = re.compile(r"\b(should|shouldn'?t|probably|maybe|perhaps|i think|i guess|i believe|i assume|i'?m guessing|"
                   r"not sure|idk|i don'?t know|might|possibly|somehow|or something|kinda|sort of|i'?m (thinking|"
                   r"envisioning|imagining)|for now|hopefully|presumably|if possible|whatever works|"
                   r"you (decide|choose|pick))\b", I)
INTEGRATE = re.compile(r"\b(integrat\w*|refactor\w*|migrat\w*|deploy\w*|hook (it )?up|wire (it )?(up|in)|connect\w*|"
                       r"set ?up|port(ing)?|upgrad\w*|switch (to|over)|move (to|over)|replace\w*|rewrite|restructur\w*|"
                       r"consolidat\w*|merge|sync\w*|automate|pipeline|auth|env|config\w*|schema|database|supabase|"
                       r"backend|frontend|server|api|repo)\b", I)
IMPLEMENT = re.compile(r"\b(implement\w*|build|create|add|make|fix|change|update|write|set ?up|wire|hook|integrat\w*|"
                       r"refactor\w*|migrat\w*|deploy\w*|automate|convert|port|generate|install|configure|enable|"
                       r"support|get .{0,40}\b(working|to work)|execute|do it all|everything)\b", I)
WORK_WITH = re.compile(r"\b(work(s|ing)? with|compatible with|talk to|play(s)? (nice|well) with|on top of)\b", I)
NAMED = re.compile(r"[/~\\][\w./~-]+|\.\w{1,4}\b|\b\w+[_.]\w+\b|\b[a-z]+[A-Z]\w*|`[^`]+`|https?://|\b\w+\(\)")

# Words a typo is measured against: common English plus everyday dev words. A lowercase
# alphabetic token not in this set that is one edit away from one of these is a probable typo.
COMMON = set("""
the be to of and a in that have i it for not on with he as you do at this but his by from they we say her she or an
will my one all would there their what so up out if about who get which go me when make can like time no just him
know take people into year your good some could them see other than then now look only come its over think also back
after use two how our work first well way even new want because any these give day most us is are was were been has
had did does doing done am being here there where why whom whose very really much many more less few lot lots okay ok
yes yeah yep nope maybe please thanks thank sorry hey hi hello wow great nice cool fine bad better best worse worst big
small little long short high low old right wrong same different next last early late again still already yet ever
never always often sometimes once twice before during while until since ago soon later today tomorrow yesterday
tonight week month minute minutes second seconds hour hours day days year years time times tho though although
anyway anyways actually basically literally probably definitely exactly kinda sort kind stuff thing things something
anything nothing everything someone anyone everyone nobody somewhere anywhere each every both either neither another
own such only own same too also quite rather pretty almost enough around through across along against between
among within without under over above below behind beside near far down off onto upon toward towards inside outside
instead whether either per via plus minus except unless because since therefore however otherwise meanwhile
should shouldnt would wouldnt could couldnt might must shall may need needs needed want wants wanted let lets
try tried trying start started starting stop stopped stopping keep kept keeping run ran running show showed showing
tell told telling ask asked asking help helped helping check checked checking test tested testing build built
building fix fixed fixing add added adding remove removed removing delete deleted change changed changing update
updated updating create created creating make made making write wrote written writing read reading find found
finding look looked looking see saw seen use used using put puts turn turned move moved moving set setting get got
getting give gave given go went gone going come came coming leave left bring brought send sent push pushed pull
pulled commit committed merge merged deploy deployed install installed open opened close closed save saved load
loaded call called clean cleaned copy copied paste pasted click clicked type typed scroll search searched browse
work worked working play played learn learned study studied buy bought sell sold pay paid win won lose lost
think thought feel felt mean meant say said believe guess hope wish like love hate mind care seem seems seemed
happen happened break broke broken crash crashed fail failed error errors bug bugs issue issues problem problems
question questions answer answers idea ideas plan plans strategy strategies result results stat stats data number
numbers money dollar dollars price prices cost costs trade trades trading market markets stock stocks option options
alert alerts signal signals chart charts graph table list item items file files folder path paths line lines code
repo repos branch branches diff commit commits test tests script scripts tool tools command commands terminal shell
server client app apps site page pages ui ux design logo svg png pdf ppt docx doc docs document slide slides
slideshow pitch deck email text message messages chat prompt prompts model models agent agents hook hooks skill
skills env config setup api key keys token tokens auth login user users account accounts password database db
schema table tables query queries function functions class method variable value values string int bool array
object json yaml html css js ts python node npm pip git github pr prs mr main master dev prod staging local remote
version versions release build builds package packages module import export default true false null none
true false yes no on off up down in out new old now then here there this that these those it its them they
good job great nice done ready working broken loading slow fast quick easy hard simple complex clear unclear
free paid real fake actual current latest previous original final draft full partial whole entire exact exactly
dont cant didnt isnt wasnt arent wont wouldnt couldnt shouldnt havent hasnt im ive youre theyre hes shes thats whats
hows wheres theres lets gonna wanna gotta yea yup ya nah hmm huh lol haha etc idk rn btw tho
end ends hold leg legs loop loops status least news vice versa side sides top bottom left right front back middle
edge edges case cases step steps part parts point points level levels rate rates size sizes range order orders
risk return returns gain gains loss losses profit profits fee fees entry exit position positions bet bets odds
percent percentage amount total average mean max min sum count ratio weight window period session sessions
round rounds run runs loop study studies research paper papers source sources forum forums post posts thread
feed feedback note notes name names title word words sentence paragraph section sections summary overview
example examples detail details reason reasons effect effects cause causes rule rules limit limits goal goals
task tasks job jobs role roles team member members company product products service services feature features
screen screens button buttons menu tab tabs field fields form forms image images icon icons color colors font
border margin padding layout grid header footer sidebar modal popup card cards row rows column columns cell
link links route routes request requests response responses event events state status store storage cache
thread threads process processes memory disk network device devices phone laptop browser extension window
school class classes course courses homework exam quiz lecture notes proof proofs problem set chapter unit
morning night overnight weekend monday tuesday wednesday thursday friday saturday sunday
live lives lived mine grow grew able unable mode modes shame theme themes known black white swing fund funded funding
saving savings dead fill fills filled head headed heading lean leaning town shadow shadows combo graph graphs
""".split())
SUFFIXES = ("s", "es", "ed", "d", "ing", "er", "ers", "ly")


def known(w: str) -> bool:
    if w in COMMON:
        return True
    for suf in SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            stem = w[: -len(suf)]
            if stem in COMMON or stem + "e" in COMMON or (stem[-1] == stem[-2:-1] and stem[:-1] in COMMON):
                return True
    return False
TYPO_MIN_LEN = 4
LETTERS = "abcdefghijklmnopqrstuvwxyz"


def near_common(w: str) -> bool:
    """True when w is a known word with one letter dropped, doubled/added, or two swapped.
    Substitutions are left out: too many real words are one letter off a common one (loop/look)."""
    for i in range(len(w)):
        if known(w[:i] + w[i + 1:]):
            return True
        if i + 1 < len(w) and w[i] != w[i + 1] and known(w[:i] + w[i + 1] + w[i] + w[i + 2:]):
            return True
    for i in range(len(w) + 1):
        for c in LETTERS:
            if known(w[:i] + c + w[i:]):
                return True
    return False


def typo_count(words: list[str]) -> int:
    n = 0
    for w in words:
        if len(w) >= TYPO_MIN_LEN and w.isalpha() and w.islower() and not known(w) and near_common(w):
            n += 1
    return n


def misread(prompt: str) -> bool:
    words = prompt.split()
    if not words or len(words) > MISREAD_WORDS or ACK.match(prompt) or SLASH.match(prompt) or PASTED.search(prompt):
        return False
    if CORRECTION.match(prompt):
        return True
    if DEICTIC.search(prompt) and not REFERENT.search(prompt):
        return True
    tokens = [t.replace("'", "") for t in re.findall(r"[a-z']+", prompt.lower())]
    if typo_count(tokens) >= 2:
        return True
    # Nothing concrete at all: every word is everyday vocabulary and nothing names a thing.
    # One- to three-word prompts ("push", "so", "run it") are commands or acks, not misread risks.
    return 4 <= len(words) <= GENERIC_WORDS and not REFERENT.search(prompt) and all(known(t) for t in tokens if t)


def assumption(prompt: str) -> bool:
    words = prompt.split()
    if len(words) < ASSUMPTION_MIN_WORDS or SLASH.match(prompt) or PASTED.search(prompt):
        return False
    if not IMPLEMENT.search(prompt) and not INTEGRATE.search(prompt):
        return False
    unknowns = min(2, len({m.group(0).lower() for m in HEDGE.finditer(prompt)}))
    if INTEGRATE.search(prompt) and not NAMED.search(prompt):
        unknowns += 1
    if WORK_WITH.search(prompt):
        unknowns += 1
    return unknowns >= 2


def guard(prompt: str) -> str:
    prompt = prompt.strip()
    lines = []
    if misread(prompt):
        lines.append(MISREAD_LINE)
    if assumption(prompt):
        lines.append(ASSUMPTION_LINE)
    return "\n".join(lines)


def main() -> int:
    if os.environ.get("AGENTMAXX_PROMPT_GUARD", "1") == "0":
        return 0
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if event.get("hook_event_name", "UserPromptSubmit") != "UserPromptSubmit":
        return 0
    prompt = event.get("prompt")
    if not isinstance(prompt, str):
        return 0
    note = guard(prompt)
    if not note:
        return 0
    json.dump({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": note}}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
