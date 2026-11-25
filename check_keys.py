"""Checks an export and its answer key against the writing rules (sample/RULES.md), the labeling rules
(tests/LABELING.md) and the size table (PLAN.md section 4), before anything reads the export.

    python3 check_keys.py <export folder> <key.json> practice|scored [--quiet]

With --quiet it prints only PASS or FAIL (the data helper runs it this way on the scored export, so nothing about
the scored rows reaches the build chat). It never runs the engine or the notes check: those must not read the
scored export before the lock.
"""
import csv
import datetime as dt
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
STAGES = ["Consultation booked", "Qualified", "Pilot proposed", "Partner said yes", "Order form sent", "Won", "Lost"]
RULES = [f"H{i}" for i in range(1, 16)]
TAGS = ["OVER LIMIT", "SLIPPED", "QUIET", "NONE BOOKED"]
WAITING = ["signer", "question", "order_form", "signature", "quiet", "later_date", "nothing", "other"]
STEP = ["real", "not_a_step", "done", "none"]
WEEK_START, WEEK_END = dt.datetime(2026, 11, 16), dt.datetime(2026, 11, 23)

SIZES = {
    "practice": {"Won": 35, "lost_pre": 10, "lost_q": 15, "Consultation booked": 10, "Qualified": 14, "Pilot proposed": 13,
                 "Partner said yes": 10, "Order form sent": 13, "held": 12, "held_rules": set(RULES[:8]), "data_nm": 6,
                 "push": 10, "push_nm": 5, "noted": 45, "not_a_step": 5, "done": 4, "stage": 4, "decoys": 10, "waiting": 25},
    "scored": {"Won": 20, "lost_pre": 10, "lost_q": 15, "Consultation booked": 12, "Qualified": 18, "Pilot proposed": 16,
               "Partner said yes": 13, "Order form sent": 16, "held": 14, "held_rules": set(RULES), "data_nm": 8,
               "push": 10, "push_nm": 6, "noted": 60, "not_a_step": 6, "done": 5, "stage": 4, "decoys": 12, "waiting": 35,
               "h9_h15": 5},
}
DATA_NM = ["a Consultation booked deal with a past automatic close date", "a Consultation booked deal with no amount",
           "a deal created straight into Qualified", "a deal lost straight from Pilot proposed", "a note after a loss",
           "contact after a win", "an amount just above zero", "two firms in the same city on different domains"]
PUSH_NM = ["days in stage exactly at the limit", "last contact exactly 14 days ago", "close date exactly 6 days later",
           "a close date pulled earlier", "a Consultation booked deal with nothing booked", "a held-out deal that would meet a push rule"]
BANNED = re.compile(r"\b(fees?|referrals?|clients?|injur(y|ies)|lawsuits?|attorneys?|settlements?|courts?|legal|law)\b", re.I)


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def t(s):
    s = (s or "").strip()
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M") if s else None


def check(folder, key_path, kind):
    folder = pathlib.Path(folder)
    key = json.loads(pathlib.Path(key_path).read_text())
    size = SIZES[kind]
    bad = []
    this = {r["deal_id"].strip(): r for r in read(folder / "deals-this-week.csv")}
    last = {r["deal_id"].strip(): r for r in read(folder / "deals-last-week.csv")}
    firms = {r["firm_id"].strip(): r for r in read(folder / "firms.csv")}
    notes = read(folder / "notes.csv")
    team = {r["full_name"].strip().lower() for r in read(HERE / "sample" / "team.csv")}

    # the files
    if len(this) != 120:
        bad.append(f"{len(this)} deals this week, not 120")
    for k in last:
        if k not in this:
            bad.append(f"{k} is in last week's file only")
    for k, r in this.items():
        if len(r.get("next_step", "")) > 32:
            bad.append(f"{k}: Next step over 32 characters")
        c = r.get("create_date", "").strip()
        if c and not (dt.datetime(2026, 6, 1) <= t(c) < WEEK_END):
            bad.append(f"{k}: Create date outside 2026-06-01 to 2026-11-22")
    for f in firms.values():
        if not re.fullmatch(r"(Test )?Firm \d{3,5}", f["name"].strip()) or not re.fullmatch(r"firm\d{3,5}\.example", f["domain"].strip()):
            bad.append(f"firm {f['firm_id']}: name or domain not numbered")
    for n in notes:
        if BANNED.search(n["body"].replace("personal injury", "")):
            bad.append(f"note on {n['deal_id']}: a banned word")
        if re.search(r"\bcases?\b", n["body"]) and not re.search(r"\d+\s+cases?\b|cases a month|cases per month", n["body"]):
            bad.append(f"note on {n['deal_id']}: 'cases' not about case volume")
        if len(n["body"].split()) > 45:
            bad.append(f"note on {n['deal_id']}: over two short sentences")
        if t(n["timestamp"]) and t(n["timestamp"]) > WEEK_END:
            bad.append(f"note on {n['deal_id']}: dated after the export")
        if n["deal_id"].strip() not in this:
            bad.append(f"note on unknown deal {n['deal_id']}")

    # the stage mix
    stages = [r["stage"].strip() for r in this.values()]
    for s in STAGES[:5] + ["Won"]:
        if stages.count(s) != size[s]:
            bad.append(f"{stages.count(s)} {s}, not {size[s]}")
    lost = [r for r in this.values() if r["stage"].strip() == "Lost"]
    lost_q = sum(1 for r in lost if r["entered_qualified"].strip())
    if (len(lost) - lost_q, lost_q) != (size["lost_pre"], size["lost_q"]):
        bad.append(f"Lost {len(lost) - lost_q} before Qualified and {lost_q} qualified, not {size['lost_pre']} and {size['lost_q']}")

    # the key's shape
    for f in ("held_out", "data_near_misses", "push", "push_near_misses", "notes", "note_decoys", "expected"):
        if f not in key:
            bad.append(f"key has no {f}")
    held = key.get("held_out", {})
    for k, rule in held.items():
        if k not in this:
            bad.append(f"held out {k} not in the export")
        if rule not in RULES:
            bad.append(f"held out {k}: unknown rule {rule}")
    if len(held) != size["held"]:
        bad.append(f"{len(held)} held out, not {size['held']}")
    if set(held.values()) - size["held_rules"]:
        bad.append(f"held-out rules outside {sorted(size['held_rules'])}")
    if kind == "scored" and sum(1 for r in held.values() if r in RULES[8:]) != size["h9_h15"]:
        bad.append(f"not {size['h9_h15']} plants from H9 to H15")
    touches = 0
    for k in held:
        r = this.get(k, {})
        st = r.get("stage", "").strip()
        if st in STAGES[1:5] or any(WEEK_START <= (t(r.get(c)) or dt.datetime.min) < WEEK_END for c in ("entered_qualified", "entered_won", "entered_lost")):
            touches += 1
    if touches < 4:
        bad.append(f"only {touches} held-out plants touch a number on the page")
    for k, what in key.get("data_near_misses", {}).items():
        if k in held:
            bad.append(f"data near miss {k} is held out")
        if what not in DATA_NM:
            bad.append(f"data near miss {k}: unnamed kind {what!r}")
    if len(key.get("data_near_misses", {})) < size["data_nm"]:
        bad.append(f"fewer than {size['data_nm']} data near misses")
    push = key.get("push", {})
    for k, tags in push.items():
        if k in held or set(tags) - set(TAGS) or not tags:
            bad.append(f"push {k}: held out or bad tags")
    if len(push) != size["push"]:
        bad.append(f"{len(push)} push cases, not {size['push']}")
    for tag in TAGS:
        if sum(1 for v in push.values() if tag in v) < 2:
            bad.append(f"push rule {tag} met fewer than twice")
    pnm = key.get("push_near_misses", {})
    for k, what in pnm.items():
        if what not in PUSH_NM:
            bad.append(f"push near miss {k}: unnamed kind {what!r}")
        if k in push:
            bad.append(f"push near miss {k} is on the list")
        if (k in held) != (what == "a held-out deal that would meet a push rule"):
            bad.append(f"push near miss {k}: held-out status does not match its kind")
    if len(pnm) < size["push_nm"]:
        bad.append(f"fewer than {size['push_nm']} push near misses")
    if "a held-out deal that would meet a push rule" not in pnm.values():
        bad.append("no held-out deal that would meet a push rule")
    order = key.get("expected", {}).get("push_order", [])
    if sorted(order) != sorted(push):
        bad.append("push_order does not list exactly the push deals")

    # the notes
    noted = {n["deal_id"].strip() for n in notes}
    nk = key.get("notes", {})
    for k, e in nk.items():
        r = this.get(k)
        if r is None or k in held or r["stage"].strip() not in STAGES[:5]:
            bad.append(f"notes key {k}: not an open clean deal")
            continue
        if e.get("step") not in STEP or (e["step"] == "none") != (not r.get("next_step", "").strip()):
            bad.append(f"notes key {k}: step does not fit the Next step text")
        if e.get("stage_from_notes") not in [None] + STAGES or e.get("stage_from_notes") == r["stage"].strip():
            bad.append(f"notes key {k}: stage_from_notes")
        if e.get("waiting") not in [None] + WAITING or bool(e.get("waiting")) != bool(e.get("waiting_said")):
            bad.append(f"notes key {k}: waiting")
    open_clean_noted = [k for k, r in this.items() if k in noted and k not in held and r["stage"].strip() in STAGES[:5]]
    if set(open_clean_noted) != set(nk):
        bad.append("the notes key does not cover exactly the open clean deals with notes")
    if len(nk) < size["noted"]:
        bad.append(f"{len(nk)} open clean deals with notes, fewer than {size['noted']}")
    counts = {"not_a_step": sum(1 for e in nk.values() if e.get("step") == "not_a_step"),
              "done": sum(1 for e in nk.values() if e.get("step") == "done"),
              "stage": sum(1 for e in nk.values() if e.get("stage_from_notes")),
              "waiting": sum(1 for e in nk.values() if e.get("waiting_said"))}
    for c, v in counts.items():
        if v < size[c]:
            bad.append(f"{v} keyed {c}, fewer than {size[c]}")
    decoys = key.get("note_decoys", {})
    if len(decoys) < size["decoys"]:
        bad.append(f"{len(decoys)} decoys, fewer than {size['decoys']}")
    for k in decoys:
        e = nk.get(k)
        if e is None or e.get("step") in ("not_a_step", "done") or e.get("stage_from_notes"):
            bad.append(f"decoy {k} is not clean in the notes key")

    # owners
    for k, r in this.items():
        o = r.get("owner", "").strip().lower()
        if o and o not in team and held.get(k) != "H10":
            bad.append(f"{k}: owner not on the team and not an H10 plant")
    return bad


def main(argv):
    if len(argv) < 4 or argv[3] not in SIZES:
        print(__doc__)
        return 2
    bad = check(argv[1], argv[2], argv[3])
    if "--quiet" in argv:
        print("FAIL" if bad else "PASS")
    else:
        for b in bad:
            print(" ", b)
        print(f"{'FAIL' if bad else 'PASS'}: {len(bad)} problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
