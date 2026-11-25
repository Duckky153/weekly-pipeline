"""Tests that need no paid call. Run by test.sh.

    python3 tests/test_engine.py
"""
import json
import pathlib
import re
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import engine  # noqa: E402
import notes_check  # noqa: E402
import pipeline  # noqa: E402

FIXTURE = HERE / "fixture" / "export"
FIX_LIMITS = FIXTURE / "limits.json"
PRACTICE = ROOT / "sample" / "practice"
LIMITS = ROOT / "limits.json"
PY = sys.executable


def run(*args):
    return subprocess.run([PY, *map(str, args)], capture_output=True, text=True, cwd=ROOT)


class Counts(unittest.TestCase):
    def test_fixture_engine_recount_and_hand_count_agree(self):
        r = run(HERE / "compare.py", FIXTURE, "--limits", FIX_LIMITS, "--expected", HERE / "fixture" / "expected.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_practice_engine_recount_and_key_agree(self):
        r = run(HERE / "compare.py", PRACTICE, "--limits", LIMITS, "--key", HERE / "keys" / "practice.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_counted_plus_held_out_is_the_export(self):
        for folder, lim in ((FIXTURE, FIX_LIMITS), (PRACTICE, LIMITS)):
            res = engine.run(folder, json.loads(lim.read_text()))
            this, held = res["data"]["this"], res["held_out"]
            counted = [k for k in this if k not in held]
            self.assertEqual(len(counted) + len(held), len(this))
            total = sum(d["amount_v"] or 0 for d in this.values())
            self.assertEqual(sum(this[k]["amount_v"] or 0 for k in counted) + res["numbers"]["held_out"]["value"], total)

    def test_every_clean_qualified_open_deal_that_meets_a_push_rule_is_listed(self):
        res = engine.run(PRACTICE, json.loads(LIMITS.read_text()))
        data, held, push = res["data"], res["held_out"], res["push"]
        for k, d in data["this"].items():
            if k in held or d["stage"] not in engine.OPEN_QUAL:
                self.assertNotIn(k, push)
                continue
            self.assertEqual(bool(engine.push_tags(d, data, res["limits"])), k in push, k)

    def test_limits_file_matches_practice(self):
        self.assertEqual(json.loads(LIMITS.read_text()), engine.compute_limits(engine.load(PRACTICE)))


class Fence(unittest.TestCase):
    def test_flip_practice(self):
        changed, _ = pipeline.flip(str(PRACTICE), "practice", None, LIMITS)
        self.assertEqual(changed, [])

    def test_flip_catches_a_leak(self):
        """A planted fault: the card count reads the notes check. The flip test must fail."""
        real = pipeline.build

        def leaky(folder, name, notes_mode="real", limits=None, limits_path=None):
            week, result, settled = real(folder, name, notes_mode, limits, limits_path)
            week["card"]["count"] += sum(1 for s in settled.values() if notes_check.tags(s))
            return week, result, settled

        pipeline.build = leaky
        try:
            changed, _ = pipeline.flip(str(PRACTICE), "practice", None, LIMITS)
        finally:
            pipeline.build = real
        self.assertNotEqual(changed, [])

    def test_rule_tags_lead_every_row_in_every_flip_mode(self):
        """The rows' rule tags can't be pushed off by the notes check: in every mode they come first."""
        for mode in notes_check.MODES:
            week = pipeline.build(str(PRACTICE), "practice", mode, None, LIMITS)[0]
            for r in week["push"]:
                self.assertEqual(r["tags"][:min(2, len(r["push_tags"]))], r["push_tags"][:2], (mode, r["id"]))

    def test_every_keyed_scored_deal_was_read(self):
        key = json.loads((HERE / "keys" / "scored.json").read_text())
        res = engine.run(ROOT / "sample" / "scored", json.loads(LIMITS.read_text()))
        out = notes_check.run(res["data"], res["held_out"], "scored", mode="real")
        self.assertEqual([k for k in key["notes"] if out.get(k, {}).get("read") != "read"], [])

    def test_join(self):
        r = run(HERE / "test_join.py", PRACTICE, HERE / "keys" / "practice.json", LIMITS)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_files_that_decide_the_page_never_open_the_keys(self):
        for f in ["engine.py", "pipeline.py", "notes_check.py", "jev_check.py", "limits.py", "site/app.js", "site/index.html"]:
            text = (ROOT / f).read_text()
            self.assertNotRegex(text, r"tests/keys|keys/|practice\.json|expected\.json", f)

    def test_recount_shares_no_code_with_the_engine(self):
        text = (ROOT / "recount.py").read_text()
        self.assertNotRegex(text, r"^\s*(import|from)\s+(engine|pipeline|notes_check|score)\b", )
        for line in text.splitlines():
            if line.startswith(("import ", "from ")):
                self.assertNotRegex(line, r"\b(engine|pipeline|notes_check|score|limits)\b", line)

    def test_no_network_outside_the_paid_read(self):
        for f in ["engine.py", "pipeline.py", "notes_check.py", "limits.py", "recount.py"]:
            text = (ROOT / f).read_text()
            self.assertNotRegex(text, r"(import|from) (urllib|http\.client|requests|socket)", f)
        self.assertNotRegex((ROOT / "site" / "app.js").read_text(), r"https?://")


class Scored(unittest.TestCase):
    """After the lock: the scored sample, read once."""
    SCORED = ROOT / "sample" / "scored"

    def test_scored_engine_recount_and_key_agree(self):
        r = run(HERE / "compare.py", self.SCORED, "--limits", LIMITS, "--key", HERE / "keys" / "scored.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_flip_scored(self):
        changed, _ = pipeline.flip(str(self.SCORED), "scored", None, LIMITS)
        self.assertEqual(changed, [])

    def test_page_shows_the_scored_sample_from_the_code(self):
        week = json.loads((ROOT / "site" / "data" / "week.json").read_text())
        fresh = pipeline.build(str(self.SCORED), "scored", "real", None, LIMITS)[0]
        for k in ("card", "numbers", "held_out", "push", "chart"):
            self.assertEqual(json.loads(json.dumps(fresh[k])), week[k], k)

    def test_every_scored_read_is_saved(self):
        res = engine.run(self.SCORED, json.loads(LIMITS.read_text()))
        out = notes_check.run(res["data"], res["held_out"], "scored", mode="real")
        self.assertFalse([k for k, s in out.items() if s["read"] in ("missing", "broken")])


class Locked(unittest.TestCase):
    def test_locks_hold(self):
        r = run(ROOT / "lock.py", "check")
        self.assertEqual(r.returncode, 0, r.stdout)

    @unittest.skipUnless((ROOT / "PLAN.md").exists(), "the plan is private")
    def test_definitions_match_the_plan(self):
        plan = (ROOT / "PLAN.md").read_text()
        body = (ROOT / "DEFINITIONS.md").read_text().split("## 3.0 Inputs", 1)[1]
        for line in body.splitlines():
            if line.strip() and not line.startswith("## 3.1 Stages"):
                self.assertIn(line.lstrip("#").strip(), plan)


class Wording(unittest.TestCase):
    W = json.loads((ROOT / "wording.json").read_text())
    D = json.loads((ROOT / "definitions.json").read_text())

    def test_next_step_lines_fit(self):
        lines = list(self.W["waiting"].values()) + list(self.W["by_stage"].values()) + [self.W["QUIET"], self.W["NONE BOOKED"]]
        for line in lines:
            self.assertLessEqual(len(line), 38, line)
            self.assertTrue(line.startswith("Next: "), line)

    def test_definitions_fit(self):
        for d in self.D["card"]:
            self.assertLessEqual(len((d["term"] + " " + d["text"]).split()), 30, d["term"])

    def test_tags_share_no_word_with_the_companys_own_tags(self):
        theirs = {"DEMAND", "APPROVAL", "NUDGE", "CHASE", "READY"}
        for t in engine.TAGS + notes_check.NOTE_TAGS:
            self.assertFalse(set(t.split()) & theirs, t)
            self.assertLessEqual(len(t), 12, t)

    def test_reason_lines_fit(self):
        for r in engine.REASONS.values():
            self.assertLessEqual(len(r), 30, r)

    def test_page_rows_fit_their_limits(self):
        week = pipeline.build(str(PRACTICE), "practice", "none", None, LIMITS)[0]
        for r in week["push"]:
            self.assertLessEqual(len(r["firm"]), 22)
            self.assertLessEqual(len(r["status"]), 34, r["status"])
            self.assertLessEqual(len(r["next"]), 38, r["next"])

    def test_practice_next_steps_fit(self):
        data = engine.load(PRACTICE)
        for d in data["this"].values():
            self.assertLessEqual(len(d.get("next_step", "")), 32, d["deal_id"])

    def test_no_company_name_on_the_page(self):
        for f in ["site/index.html", "site/app.js", "definitions.json", "wording.json", "questions.json"]:
            self.assertNotIn("finch", (ROOT / f).read_text().lower(), f)

    def test_banned_words_on_the_page(self):
        text = " ".join((ROOT / f).read_text() for f in ["site/index.html", "site/app.js", "definitions.json", "wording.json"]).lower()
        for w in ["fee", "referral", "client", "settlement", "lawsuit", "committed", "blind", "unofficial", "affiliated", "made by"]:
            self.assertIsNone(re.search(r"\b" + re.escape(w) + r"s?\b", text), w)
        self.assertNotIn("—", text)


class Notes(unittest.TestCase):
    def test_settling_rules(self):
        body = {"state": {"stage": "Pilot proposed", "next_step": "Send the order form", "latest_note": "x"},
                "questions": {q: {} for q in ["step_specific", "step_done", "stage_said", "stage_pick", "waiting_said", "waiting_pick"]}}
        def read(p_step, p_done, p_ss, stage, p_stage, p_ws, wait, p_wait):
            return {"answers": {"step_specific": {"noul": p_step}, "step_done": {"noul": p_done},
                                "stage_said": {"noul": p_ss}, "stage_pick": {"choice": stage, "probabilities": {stage: p_stage}},
                                "waiting_said": {"noul": p_ws}, "waiting_pick": {"choice": wait, "probabilities": {wait: p_wait}}}}
        s = notes_check.settle(body, read(0.9, 0.1, 0.9, "Won", 0.9, 0.9, "signature", 0.8), read(0.85, 0.2, 0.85, "Won", 0.85, 0.8, "signature", 0.75))
        self.assertEqual((s["step"], s["stage_from_notes"], s["waiting"]), ("real", "Won", "signature"))
        s = notes_check.settle(body, read(0.9, 0.1, 0.9, "Won", 0.9, 0.9, "signature", 0.8), read(0.79, 0.2, 0.85, "Lost", 0.85, 0.7, "signature", 0.75))
        self.assertEqual((s["step"], s["stage_from_notes"], s["waiting"]), ("unsure", None, None))
        self.assertIn("step_specific", s["near_bar"])
        s = notes_check.settle(body, read(0.2, 0.9, 0.9, "Pilot proposed", 0.9, 0.9, "other", 0.9), read(0.3, 0.85, 0.9, "Pilot proposed", 0.9, 0.9, "other", 0.9))
        self.assertEqual((s["step"], s["stage_from_notes"], s["waiting"]), ("not_a_step", None, None))
        s = notes_check.settle(body, read(0.9, 0.9, 0.2, "Won", 0.9, 0.2, "quiet", 0.9), read(0.9, 0.81, 0.2, "Won", 0.9, 0.2, "quiet", 0.9))
        self.assertEqual((s["step"], s["stage_from_notes"], s["waiting"]), ("done", None, None))

    def test_no_read_means_no_tags(self):
        res = engine.run(PRACTICE, json.loads(LIMITS.read_text()))
        out = notes_check.run(res["data"], res["held_out"], "practice", mode="none")
        self.assertTrue(all(not notes_check.tags(s) for s in out.values()))

    def test_model_sees_no_amount_date_or_owner(self):
        res = engine.run(PRACTICE, json.loads(LIMITS.read_text()))
        data = res["data"]
        for k in notes_check.readable(data, res["held_out"]):
            body = notes_check.request_for(data, data["this"][k])
            if body is None:
                continue
            self.assertEqual(set(body["state"]) - {"stage", "stages", "next_step", "latest_note", "earlier_notes"}, set())
            text = json.dumps(body["state"])
            d = data["this"][k]
            self.assertNotIn(d["owner"], text)
            if d["amount_v"] and d["amount_v"] >= 1000:
                self.assertNotRegex(text, r"\b" + str(int(d["amount_v"])) + r"\b")
            self.assertNotRegex(text, r"\d{4}-\d{2}-\d{2}")
            self.assertLessEqual(notes_check.jev_check.high_tokens(body), 8000)
            self.assertNotIn("finch", text.lower())


if __name__ == "__main__":
    unittest.main(verbosity=1)
