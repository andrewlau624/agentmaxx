import json
import tempfile
import unittest
from pathlib import Path

from evals import corrections


def record(text, ts="2026-10-01T10:00:00Z", **extra):
    return json.dumps({"type": "user", "timestamp": ts, "entrypoint": "cli", "message": {"content": text}, **extra})


# (text, is_correction) hand-labelled from the 30-day mine: the 43 prompts the old
# regex flagged (first block), the 25 it missed that a broader net caught (second),
# and five plain instructions as guards (third). Duplicates are real repeat prompts.
LABELLED = [
    ("no artifact, i want a slideshow ppt that i can also edit and a docx", True),
    ("no but now theres an edit history on the comment", True),
    ("no two repos app and server", True),
    ("it sounds unlikely you havent found anything. i theorize that you are trying too hard to minimize risk "
     "and rtherefore inhibiting profit - causing the losses. as i said, have a \"better\" mindset.", True),
    ("stop saying kalshi im not using kalshi im doing polymarket", True),
    ("no Jev https://typesafe.ai/blog/introducing-system-one-models-and-jev", False),
    ("no i already created the render db url", True),
    ("no, i will only have one session in my sleep - but i have 2 running already i meant", True),
    ("No other way to dig more deep into the patterns or hidden gems?", False),
    ("No other way to dig more deep into the patterns or hidden gems? how about shorts?", False),
    ("no the numbers numbers of expected all on optimistic and pessemistic and median", True),
    ("my real fills were be betting it all on accident - dont use that as data", True),
    ("no run like a side by side on the data with the macd rsi strat like dont forward just say with the new "
     "what it wouldve looked like", True),
    ("no i meant buying crypto and having it influence the kalshi. another hting is look into perp trades for btc and eth.", True),
    ("no i meant with the minute/seconds idea", True),
    ("stop it now", True),
    ("oh i thought of a great idea earlier btw-in esports, buy a very low percentage team before the game starts, "
     "because in esports specificalyl these games tend to flip even a little bit or show hope for a team, then cash "
     "out on the mini swing like 18 to 30 or 40 dont use exact numbers see what works. i was thinkign league or dota "
     "but LMK what games works best.", False),
    ("oh i thought of a great idea earlier btw-in esports, buy a very low percentage team before the game starts, "
     "because in esports specificalyl these games tend to flip even a little bit or show hope for a team, then cash "
     "out on the mini swing like 18 to 30 or 40 dont use exact numbers see what works. i was thinkign league or dota "
     "but LMK what games works best. this could possibly apply to some sports or other markets as well.", False),
    ("no i wan tthis to wokr give a prompt for research or total refactor/pivot of strategy and testing", True),
    ("no im not funding until we find something working - id actually prefer if we could research somethign to make "
     "it good / imrpove my strategies", True),
    ("no i mean like at 0.01% to win like 90 bucks", True),
    ("no", False),
    ("okay get rid of synclink and discord remote agent and agentmaxx. can you do testing and like test yourself by "
     "coming up with fake job descriptions to see if it truly comes up with ATS perfect and appropriate for the job. "
     "also resume should be one page if you didnt notice.", True),
    ("no 169 today?", False),
    ("no im gonna read it later i finished 1-4 and reading 3 early", False),
    ("i didnt even do this myself i asked chatgpt", False),
    ("no i dont need discusisons stop i jsut wan tmy schedule", True),
    ("no riscv?", False),
    ("no i think i shoudl learn riscv first", False),
    ("no extension im doing it all", True),
    ("no like tests including like for very confident picks", True),
    ("no the useThinkScript forum", True),
    ("no other optential studies?", False),
    ("no other optential studies?", False),
    ("no i like that you have evrything running already, but the high capital testing because i know i have high "
     "capital legs as well", True),
    ("stop-you are going against the rules of being a normal regular human being. just download it into the github "
     "repo - because this is how the real world works and nobody finds out about it. just downlaod it into the gh "
     "repo. do NOT push against this", True),
    ("no. i think you should update the docs cause thery out of date", True),
    ("no thats all the envs that are non sensistive", False),
    ("no i meant like influence trades based off good and bad weeks for the market", True),
    ("no like make the squares smaller cause the proportion jsue the top is too wide for the shaft. i like 1", True),
    ("no need to say ultimateR just have the ultimate abaility with the R on corner of the image and kinda makei t "
     "biggere and do it all, [Image #12] im not a big fan of this right now and search bar has ring. this also takes "
     "yp a bit of space", True),
    ("no continue now do it all at once idk why you wait so long", True),
    ("but you just gave it select rules you didnt give the bot autonomy to discover more fundamentals", True),
    # missed by the old regex
    ("wait edit so team is the two founders and rasising 250k the goal is to get 500 shops of gen z target demographic "
     "to spread the word no need to add name email website yet", True),
    ("still a lot of textual nonsense and visual clutter and not like modern software looking, the side margins on "
     "this are off", True),
    ("still not a fan of like the text dot random words S355JR · 1,790 m · status set by you and the extreme empty "
     "space here you could even just make like a side bar or tab card around this content", True),
    ("why is the edge so small, numbers from earlier were higher", True),
    ("just do verifications and if theres a strategy that works fix or add", True),
    ("wait - please be agnostric to these changes : Major U.S. stock exchanges are shifting toward a 23-hour trading "
     "model starting in December 2026. this is huge.", True),
    ("wait but youre forgetting that edge could possibly increase given changing market circumstances?", True),
    ("wait on kalshi it really works like i do macd and rsi and then when its proven on the btc and the percentages "
     "rise i go eth which is a little behind and i trade it and it works", True),
    ("actually-i want to derivce with complex probaility and expectation with CS70 concepts-basically i am "
     "envisioning like for 15m markets for not just btc but eth and other", True),
    ("wait the up fown gap is working for me", True),
    ("just do live on my kalshi", True),
    ("i meant the current strategy we are using for the btc", True),
    ("just run it here - also, loop because im gonna be eating dinner. make sure you take into acocunt the fact that "
     "there is a bunch of resaerach online, but also please think outside the box", True),
    ("wait yesetrday i was sick so i didnt do anyhting", False),
    ("wait yesetrday i was sick so i didnt do anyhting - please i feel so behind", False),
    ("its not just a number though its a window", True),
    ("shorter please", True),
    ("why is it going negative tho and can we fix it", True),
    ("why did you choose qqq btw", False),
    ("why is selling saying that cost of trade is 1251 credit and resulting buying power is in negatives if i sell", False),
    ("undo all changes im doing this as hw assignment", True),
    ("still not a fan of the footer and dont like the border on the navbar nor blur i like solid and the giant rook "
     "logo the edges shouldnt be rounded on the four corners and i dont liek the grey that you used its very ai common", True),
    ("its not laoding", True),
    ("its not token savings i think tis everythign else - you decided token savings yourself", True),
    ("this is not for the test, this is for grading", True),
    # plain instructions that must stay out
    ("wait for the build to finish before pushing", False),
    ("still waiting on the deploy, check again in five minutes", False),
    ("add csv export", False),
    ("now run the tests", False),
    ("known issue: noise in logs", False),
]


class TestCorrections(unittest.TestCase):
    def test_typed_corrections_only(self):
        root = Path(tempfile.mkdtemp())
        (root / "p").mkdir()
        (root / "p" / "a.jsonl").write_text("\n".join([
            record("no, you forgot to run the migration tests"),
            record("what if instead of polling we stream it"),
            record("<system-reminder>no</system-reminder>"),
            json.dumps({"type": "user", "timestamp": "2026-10-01T10:00:00Z",
                        "message": {"content": [{"type": "tool_result", "content": "no"}]}}),
        ]))
        (root / "p" / "b.jsonl").write_text(record("stop, you forgot the migration tests again", ts="2026-10-02T10:00:00Z"))
        (root / "bench").mkdir()
        (root / "bench" / "c.jsonl").write_text(record("no", entrypoint="sdk-cli", promptSource="sdk"))
        stats = corrections.scan(10_000, root)
        self.assertEqual(sorted(t for _, _, t in stats["corrections"]),
                         ["no, you forgot to run the migration tests", "stop, you forgot the migration tests again"])
        self.assertEqual(sum(n for _, n in stats["weeks"].values()), 3)
        self.assertEqual(len(stats["repeats"]), 1)
        self.assertEqual(stats["session_repeats"], [])

    def test_labelled_precision_and_recall(self):
        # Old regex on this set: P=67.4% R=58.0% (29 TP, 14 FP, 21 FN). Widening must not give precision back.
        pred = [corrections.is_correction(t) for t, _ in LABELLED]
        tp = sum(p and l for p, (_, l) in zip(pred, LABELLED))
        fp = sum(p and not l for p, (_, l) in zip(pred, LABELLED))
        fn = sum(not p and l for p, (_, l) in zip(pred, LABELLED))
        self.assertGreaterEqual(tp / (tp + fp), 0.85, f"precision fell: FP={fp}")
        self.assertGreaterEqual(tp / (tp + fn), 0.90, f"recall fell: FN={fn}")
        for text, label in LABELLED:
            if text in ("no", "no riscv?", "no Jev https://typesafe.ai/blog/introducing-system-one-models-and-jev",
                        "wait yesetrday i was sick so i didnt do anyhting"):
                self.assertFalse(corrections.is_correction(text), text)

    def test_within_session_repeats(self):
        same = "stop saying kalshi im not using kalshi im doing polymarket"
        corr = [(1.0, "s1", same), (2.0, "s1", "no i meant the polymarket price not kalshi"),
                (3.0, "s1", same), (4.0, "s2", "stop saying kalshi, i use polymarket")]
        within = corrections.recurrences(corr, within_session=True)
        self.assertEqual(within, [(same, same)])
        across = corrections.recurrences(corr)
        self.assertEqual(len(across), 1)
        self.assertEqual(across[0][1], "stop saying kalshi, i use polymarket")
        # the same prompt logged twice at one timestamp is one event, not a repeat
        self.assertEqual(corrections.recurrences([(1.0, "s1", same), (1.0, "s1", same)], within_session=True), [])
        lines = corrections.report({"weeks": {"2026-W40": [4, 10]}, "corrections": corr, "repeats": across,
                                    "session_repeats": within})
        self.assertIn("repeated within one session: 1", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
