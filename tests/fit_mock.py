"""The fit mock (PLAN.md section 2): practice rows padded to the length limits, so the scored rows (which nobody
reads before the lock) can be no longer than what was tried here. Padding uses the letter n, an average width.

    python3 tests/fit_mock.py <out folder>

Copies site/ into <out folder> with data/week.json replaced by a padded copy of the practice page data: every firm
name 22 characters, every status line 34, every next step 38 with "Next: ", every held-out reason 30, the longest
city and owner name in practice on every row, the two widest tags on every row, the card at its longest stage and
the five numbers at three digits with seven-figure values.
"""
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LIMITS = {"firm": 22, "status": 34, "next": 38, "reason": 30}


def pad(s, n, fill="m"):
    s = s or ""
    return (s + " " + fill * n)[:n] if len(s) < n else s[:n]


def main(out):
    out = pathlib.Path(out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "site", out)
    w = json.loads((ROOT / "site" / "data" / "week.json").read_text())
    rows = w["push"]
    longest_city = max((r["city"] for r in rows), key=len)
    longest_owner = max((r["owner"] for r in rows), key=len)
    for r in rows:
        r["firm"] = pad(r["firm"], LIMITS["firm"], "n")
        r["city"] = longest_city
        r["owner"] = longest_owner
        r["contact"] = "no contact yet" if len("no contact yet") > len("99 days ago") else "99 days ago"
        r["status"] = pad("Close date Nov 30 to Dec 14", LIMITS["status"], "n")
        r["next"] = pad("Next: send the scope to the partner", LIMITS["next"], "n")
        r["tags"] = ["NONE BOOKED", "CHECK STAGE"]
    for r in w["held_out"]["rows"]:
        r["reason"] = pad(r["reason"], LIMITS["reason"], "n")
    for n in w["numbers"]:
        n["count"] = 888
        if "value_text" in n:
            n["value_text"] = "$88.8M"
    w["held_out"]["count"] = 888
    w["held_out"]["value_text"] = "$88.8M"
    w["card"]["line"] = "88 deals need a push."
    w["card"]["detail"] = "$88.8M a year between them. Eight are at Partner said yes."
    w["test_sentence"] = "The list, on a sample it hadn't seen: 10 of 10 right, 10 wrong."
    w["tested_link"] = "#"
    w["limits_text"] = "Qualified 88 days · Pilot proposed 88 · Partner said yes 88 · Order form sent 88."
    (out / "data" / "week.json").write_text(json.dumps(w, indent=1, ensure_ascii=False))
    print("fit mock written to", out)


if __name__ == "__main__":
    main(sys.argv[1])
