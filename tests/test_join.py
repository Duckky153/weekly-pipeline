"""The join test (PLAN.md section 7): with the answer key standing in for the notes check, every planted note
problem on the push list is tagged on the page, no clean deal is tagged, and the expected next-step wording shows.
Run before any paid read, so a plumbing fault can't be mistaken for a model's miss.

    python3 tests/test_join.py [export folder] [key] [limits.json]
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import notes_check  # noqa: E402
import pipeline  # noqa: E402

WORDING = json.loads((ROOT / "wording.json").read_text())


def settled_from_key(entry):
    waiting = entry.get("waiting") if entry.get("waiting_said") and entry.get("waiting") != "other" else None
    return {"read": "key", "step": entry["step"] if entry["step"] != "none" else "none",
            "stage_from_notes": entry.get("stage_from_notes"), "waiting": waiting, "near_bar": [], "reads": {}}


def expected_next(row_deal_step, push_tags, stage, entry):
    """PLAN section 3.6, written again here from the table, not from notes_check."""
    if entry and entry["step"] == "real" and row_deal_step:
        s = row_deal_step
        return "Next: " + (s[0].lower() + s[1:] if len(s) > 1 and not s[1].isupper() else s)
    w = entry.get("waiting") if entry and entry.get("waiting_said") else None
    if w in WORDING["waiting"]:
        return WORDING["waiting"][w]
    first = push_tags[0]
    if first in ("OVER LIMIT", "SLIPPED"):
        return WORDING["by_stage"][stage]
    return WORDING[first]


def main(folder, key_path, limits_path):
    key = json.loads(pathlib.Path(key_path).read_text())
    notes_key = key["notes"]
    real_run = notes_check.run

    def from_key(data, held, export_name, mode="real", live=False, tag="read"):
        out = real_run(data, held, export_name, mode="none")
        for k in out:
            if k in notes_key:
                out[k] = settled_from_key(notes_key[k])
        return out

    notes_check.run = from_key
    try:
        week, result, settled = pipeline.build(folder, "join", "real", None, limits_path)
    finally:
        notes_check.run = real_run

    problems = []
    this = result["data"]["this"]
    on_list = 0
    for r in week["push"]:
        k = r["id"]
        entry = notes_key.get(k)
        want = []
        if entry:
            if entry["step"] == "done":
                want.append("STEP DONE")
            if entry["step"] == "not_a_step":
                want.append("NOT A STEP")
            if entry.get("stage_from_notes"):
                want.append("CHECK STAGE")
        if r["note_tags"] != want:
            problems.append(f"{k}: tags {r['note_tags']}, key wants {want}")
        if k in key.get("note_decoys", {}) and r["note_tags"]:
            problems.append(f"{k}: a decoy was tagged {r['note_tags']}")
        nxt = expected_next(this[k].get("next_step"), r["push_tags"], this[k]["stage"], entry)
        if r["next"] != nxt:
            problems.append(f"{k}: next {r['next']!r}, expected {nxt!r}")
        if len(r["next"]) > pipeline.NEXT_MAX:
            problems.append(f"{k}: next step over {pipeline.NEXT_MAX} characters")
        on_list += 1
    keyed_problems = sum(1 for e in notes_key.values() if e["step"] in ("done", "not_a_step") or e.get("stage_from_notes"))
    if problems:
        print("join test FAILED:")
        for p in problems:
            print(" ", p)
        return 1
    print(f"join test passed: {on_list} push rows; the key's tags and next steps show exactly "
          f"({keyed_problems} keyed note problems in the export, {len(key.get('note_decoys', {}))} decoys)")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(main(a[0] if a else str(ROOT / "sample" / "practice"),
                  a[1] if len(a) > 1 else str(HERE / "keys" / "practice.json"),
                  a[2] if len(a) > 2 else str(ROOT / "limits.json")))
