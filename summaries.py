"""The numbers in the README's two tables, the stage limits and the cost, printed from the run files; and the
page's one test sentence.

    python3 summaries.py page     adds the test sentence to site/data/week.json from runs/scored.json
    python3 summaries.py readme   prints the README's table numbers, the stage limits and the cost

Nothing here computes a result: it only reads runs/*.json (written by score.py), lock.json, limits.json and the
saved answers, so the README and the page can't drift from the runs.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
RUNS = HERE / "runs"
TESTED_LINK = "https://github.com/Duckky153/weekly-pipeline#how-it-was-tested"


def load(name):
    return json.loads((RUNS / name).read_text())


def test_sentence(s):
    p = s["push"]
    wrong = "none" if p["listed_wrongly"] == 0 else str(p["listed_wrongly"])
    return f"The list, on a sample it hadn't seen, matched its answer key: {p['right']} of {p['of']}, {wrong} wrong."


def page():
    week_path = HERE / "site" / "data" / "week.json"
    week = json.loads(week_path.read_text())
    if week.get("export") != "scored":
        raise SystemExit("the page data is not the scored sample; run: python3 pipeline.py export sample/scored --name scored")
    week["test_sentence"] = test_sentence(load("scored.json"))
    week["tested_link"] = TESTED_LINK
    week_path.write_text(json.dumps(week, indent=1, ensure_ascii=False) + "\n")
    print(week["test_sentence"])


def spend():
    path = RUNS / "spend.json"
    return json.loads(path.read_text()) if path.exists() else None


def readme():
    s = load("scored.json")
    n, y, c = s["notes"], s["keyword_yardstick"], s["code_only"]
    lines = [
        ("push list, scored", f"{s['push']['right']} of {s['push']['of']} right for the right reason, {s['push']['listed_wrongly']} listed wrongly"),
        ("held out, scored", f"{s['held_out']['caught']} of {s['held_out']['of']} caught for the right reason, {s['held_out']['held_wrongly']} clean deals held out"),
        ("notes check, scored", f"found {n['found']} of {n['of']}, {n['false_flags']} false flags in {n['clean_chances']} clean chances"),
        ("keyword yardstick, scored", f"found {y['found']} of {y['of']}, {y['false_flags']} false flags in {y['clean_chances']} clean chances"),
        ("code only, scored", f"found {c['found']} of {c['of']}, {c['false_flags']} false flags"),
        ("waiting on, scored", f"{n['waiting']['wrong']} wrong of {n['waiting']['settled']} settled; {n['waiting']['settled']} settled of {n['waiting']['keyed']} keyed"),
        ("waiting on, yardstick", f"{y['waiting']['wrong']} wrong of {y['waiting']['settled']} settled; {y['waiting']['settled']} settled of {y['waiting']['keyed']} keyed"),
        ("repeat read", f"{s['repeat']['changed']} of {s['repeat']['settled_answers']} settled answers changed"),
        ("not read", f"{n['not_read']}"),
        ("near the bar", f"{n['near_bar']} deals"),
    ]
    for who in ("notes_openai_written", "notes_claude_written"):
        if who in s:
            w = s[who]
            lines.append((who.replace("_", " "), f"found {w['found']} of {w['of']}, {w['false_flags']} false flags in {w['clean_chances']}; "
                                                   f"waiting {w['waiting']['wrong']} wrong of {w['waiting']['settled']} settled of {w['waiting']['keyed']} keyed"))
    if (RUNS / "yardstick-by-writer.json").exists():
        for who, w in load("yardstick-by-writer.json").items():
            lines.append((f"yardstick, {who}", f"found {w['found']} of {w['of']}, {w['false_flags']} false flags in {w['clean_chances']}"))
    for f, label in (("other.json", "OpenAI's 40-deal sample"),):
        if (RUNS / f).exists():
            o = load(f)
            lines.append((label, f"push {o['push']['right']} of {o['push']['of']} right, {o['push']['listed_wrongly']} listed wrongly; "
                                 f"held out {o['held_out']['caught']} of {o['held_out']['of']}, {o['held_out']['held_wrongly']} clean deals held out"))
    for f, label in (("practice-check.json", "practice check run"),):
        if (RUNS / f).exists():
            p = load(f)["notes"]
            lines.append((label, f"found {p['found']} of {p['of']}, {p['false_flags']} false flags in {p['clean_chances']}"))
    lim = json.loads((HERE / "limits.json").read_text())
    lines.append(("stage limits", ", ".join(f"{k} {v} days" for k, v in lim.items())))
    sp = spend()
    if sp:
        lines.append(("AI spend", f"${sp['dollars']:.4f} over {sp['requests']} requests ({sp['input_tokens']} input tokens)"))
    for k, v in lines:
        print(f"{k}: {v}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "readme"
    {"page": page, "readme": readme}[cmd]()
