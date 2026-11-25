"""The weekly pipeline engine: every held-out reason, every number and the push list, from the sample CSVs and the rules
in DEFINITIONS.md (PLAN section 3). Sample data. No model is involved here; the notes check (notes_check.py) can only add
tags and choose next-step wording, never change anything this file computes.
"""
import csv
import datetime as dt
import json
import math
from fractions import Fraction
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

EXPORT_THIS = dt.datetime(2026, 11, 23, 0, 0)
EXPORT_LAST = dt.datetime(2026, 11, 16, 0, 0)
WEEK_START, WEEK_END = EXPORT_LAST, EXPORT_THIS

STAGES = ["Consultation booked", "Qualified", "Pilot proposed", "Partner said yes", "Order form sent", "Won", "Lost"]
MAIN = STAGES[:6]                                  # the forward path; Lost comes after every other stage
OPEN_QUAL = ["Qualified", "Pilot proposed", "Partner said yes", "Order form sent"]
FROM_QUAL = ["Qualified", "Pilot proposed", "Partner said yes", "Order form sent", "Won"]
COL = {s: "entered_" + s.lower().replace(" ", "_") for s in STAGES}
PIPELINE = "New business"
TAGS = ["OVER LIMIT", "SLIPPED", "QUIET", "NONE BOOKED"]
REASONS = {
    "H1": "No owner", "H2": "No amount", "H3": "No close date", "H4": "Close date passed, still open", "H5": "Stage skipped",
    "H6": "Same firm as another deal", "H7": "Moved back a stage", "H8": "Contacted after it was lost", "H9": "Lost with no reason",
    "H10": "Owner not on the team", "H11": "Test record", "H12": "No firm on the deal", "H13": "Dates out of order",
    "H14": "Dated after the export", "H15": "Unknown stage or pipeline",
}
FIXER = {"H1": "sales lead", "H6": "sales lead", "H10": "sales lead", "H11": "sales lead", "H13": "sales lead", "H14": "sales lead", "H15": "sales lead"}


# ---------------------------------------------------------------- reading

def ts(s, where=""):
    """A New York date and time. Blank (or only spaces) is None; an unreadable date stops the run."""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"unreadable date {s!r} {where}")


def money(s):
    """An amount; "$" and "," are dropped; unreadable counts as no amount."""
    s = (s or "").strip().replace("$", "").replace(",", "")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def deal_from(row):
    d = {k: (v or "").strip() for k, v in row.items()}
    d["stage"] = d.get("stage", "")
    d["pipeline"] = (row.get("pipeline") or "").strip()
    d["amount_v"] = money(row.get("amount"))
    for k in ("close_date", "create_date", "last_contacted", "last_activity_date", "next_activity_date"):
        d[k + "_t"] = ts(row.get(k), f"in {k} of {d.get('deal_id')}")
    d["entered"] = {s: ts(row.get(COL[s]), f"in {COL[s]} of {d.get('deal_id')}") for s in STAGES}
    return d


def by_id(rows, name):
    out = {}
    for r in rows:
        d = deal_from(r)
        if d["deal_id"] in out:
            raise ValueError(f"deal {d['deal_id']} appears twice in {name}")
        out[d["deal_id"]] = d
    return out


def load(folder, team_path=HERE / "sample" / "team.csv"):
    folder = pathlib.Path(folder)
    this = by_id(read_csv(folder / "deals-this-week.csv"), "deals-this-week.csv")
    last = by_id(read_csv(folder / "deals-last-week.csv"), "deals-last-week.csv")
    firms = {(r.get("firm_id") or "").strip(): {k: (v or "").strip() for k, v in r.items()} for r in read_csv(folder / "firms.csv")}
    team = {r["full_name"].strip().lower() for r in read_csv(team_path)}
    notes = {}
    if (folder / "notes.csv").exists():
        for r in read_csv(folder / "notes.csv"):
            notes.setdefault(r["deal_id"], []).append({"author": r["author"], "t": ts(r["timestamp"]), "body": r["body"]})
        for v in notes.values():
            v.sort(key=lambda n: n["t"] or dt.datetime.min)
    return {"this": this, "last": last, "firms": firms, "team": team, "notes": notes}


# ---------------------------------------------------------------- helpers

def days(event, export=EXPORT_THIS):
    """Whole days: the export's calendar date minus the event's calendar date."""
    return (export.date() - event.date()).days


def id_key(deal_id):
    """Lowest deal ID: by number when the ID is a whole number, else as text."""
    return (0, int(deal_id), "") if deal_id.isdigit() else (1, 0, deal_id)


def is_open(d):
    """Open means one of the five stages from Consultation booked to Order form sent."""
    return d["stage"] in STAGES[:5]


def qualified_or_later(d):
    return d["stage"] in FROM_QUAL or (d["stage"] == "Lost" and d["entered"]["Qualified"] is not None)


def in_week(t):
    return t is not None and WEEK_START <= t < WEEK_END


# ---------------------------------------------------------------- held out (section 3.4)

def rule_hits(d, data):
    """Every rule from H1 to H15 except H6 that this deal breaks."""
    hits = []
    known = d["stage"] in STAGES
    if not (d.get("owner") or "").strip():
        hits.append("H1")
    if qualified_or_later(d) and (d["amount_v"] is None or d["amount_v"] <= 0):
        hits.append("H2")
    if qualified_or_later(d) and d["close_date_t"] is None:
        hits.append("H3")
    if d["stage"] in OPEN_QUAL and d["close_date_t"] is not None and d["close_date_t"] < EXPORT_THIS:
        hits.append("H4")
    later = ["Pilot proposed", "Partner said yes", "Order form sent", "Won"]
    for i, s in enumerate(later):
        if d["entered"][s] is not None and any(d["entered"][e] is None for e in FROM_QUAL[:FROM_QUAL.index(s)]):
            hits.append("H5")
            break
    prev = data["last"].get(d["deal_id"])
    if prev is not None and known and prev["stage"] in STAGES and d["stage"] != "Lost":
        # stage order with Lost after Won: Won or Lost last week and open now, or Lost last week and Won now, moved back
        if STAGES.index(d["stage"]) < STAGES.index(prev["stage"]):
            hits.append("H7")
    if d["stage"] == "Lost" and d["last_contacted_t"] and d["close_date_t"] and d["last_contacted_t"].date() > d["close_date_t"].date():
        hits.append("H8")
    if d["stage"] == "Lost" and not (d.get("closed_lost_reason") or "").strip():
        hits.append("H9")
    owner = (d.get("owner") or "").strip().lower()
    if owner and owner not in data["team"]:
        hits.append("H10")
    firm = data["firms"].get((d.get("firm_id") or "").strip())
    if (d.get("deal_name") or "").lstrip().lower().startswith("test") or (firm and (firm.get("name") or "").lstrip().lower().startswith("test")):
        hits.append("H11")
    if firm is None:
        hits.append("H12")
    if dates_out_of_order(d):
        hits.append("H13")
    if dated_after_export(d):
        hits.append("H14")
    if not known or d["pipeline"] != PIPELINE:
        hits.append("H15")
    return hits


def dates_out_of_order(d):
    ent = d["entered"]
    created = d["create_date_t"]
    if created and any(t is not None and t < created for t in ent.values()):
        return True
    seq = [ent[s] for s in MAIN if ent[s] is not None]
    if any(b < a for a, b in zip(seq, seq[1:])):
        return True
    if ent["Lost"] is not None and any(t is not None and t > ent["Lost"] for s, t in ent.items() if s != "Lost"):
        return True
    if d["stage"] in STAGES:
        if ent[d["stage"]] is None:
            return True
        if d["stage"] in MAIN:
            after = MAIN[MAIN.index(d["stage"]) + 1:] + ["Lost"]
            if any(ent[s] is not None for s in after):
                return True
    return False


def dated_after_export(d):
    ts_list = [d["create_date_t"], d["last_contacted_t"], d["last_activity_date_t"]] + list(d["entered"].values())
    if any(t is not None and t > EXPORT_THIS for t in ts_list):
        return True
    return d["stage"] in ("Won", "Lost") and d["close_date_t"] is not None and d["close_date_t"] > EXPORT_THIS


def held_out(data):
    """{deal_id: rule}: the lowest rule that applies. H6 groups ignore deals held out by H1 to H5."""
    hits = {k: rule_hits(d, data) for k, d in data["this"].items()}
    order = lambda r: int(r[1:])
    low = {k: min(h, key=order) for k, h in hits.items() if h and order(min(h, key=order)) <= 5}
    groups = {}
    for k, d in data["this"].items():
        if k in low or not is_open(d):
            continue
        firm = data["firms"].get((d.get("firm_id") or "").strip())
        if firm and firm.get("domain"):
            groups.setdefault(firm["domain"], []).append(d)
    for members in groups.values():
        if len(members) > 1:
            members.sort(key=lambda d: (d["create_date_t"] or dt.datetime.max, id_key(d["deal_id"])))
            for d in members[1:]:
                hits[d["deal_id"]].append("H6")
    return {k: min(h, key=order) for k, h in hits.items() if h}


# ---------------------------------------------------------------- limits (section 3.5)

def compute_limits(data):
    held = held_out(data)
    spans = {s: [] for s in OPEN_QUAL}
    for k, d in data["this"].items():
        if d["stage"] != "Won" or k in held:
            continue
        ent = [d["entered"][s] for s in FROM_QUAL]
        if any(t is None for t in ent) or any(b < a for a, b in zip(ent, ent[1:])):
            continue
        for s, a, b in zip(OPEN_QUAL, ent, ent[1:]):
            spans[s].append((b.date() - a.date()).days)
    # exact arithmetic: an average of exactly 5 days gives a limit of 6, not 7
    return {s: math.ceil(Fraction(sum(v), len(v)) * Fraction(6, 5)) if v else None for s, v in spans.items()}


# ---------------------------------------------------------------- push list (section 3.5)

def push_tags(d, data, limits):
    tags = []
    entered = d["entered"].get(d["stage"])
    if entered is not None and limits.get(d["stage"]) is not None and days(entered) > limits[d["stage"]]:
        tags.append("OVER LIMIT")
    prev = data["last"].get(d["deal_id"])
    # only a deal that was Qualified through Order form sent last week can slip: a Consultation booked deal's close
    # date is HubSpot's automatic end-of-month date
    if prev is not None and prev["stage"] in OPEN_QUAL and prev["close_date_t"] and d["close_date_t"]:
        if (d["close_date_t"].date() - prev["close_date_t"].date()).days >= 7:
            tags.append("SLIPPED")
    if d["last_contacted_t"] is None or days(d["last_contacted_t"]) > 14:
        tags.append("QUIET")
    if d["next_activity_date_t"] is None:
        tags.append("NONE BOOKED")
    return tags


def push_list(data, limits, held):
    out = {}
    for k, d in data["this"].items():
        if k in held or d["stage"] not in OPEN_QUAL:
            continue
        tags = push_tags(d, data, limits)
        if tags:
            out[k] = tags
    def key(k):
        d = data["this"][k]
        return (-len(out[k]), min(TAGS.index(t) for t in out[k]), -days(d["entered"][d["stage"]]), d["create_date_t"] or dt.datetime.max, id_key(k))
    return out, sorted(out, key=key)


# ---------------------------------------------------------------- numbers (section 3.3)

def numbers(data, held, push, order):
    this, last = data["this"], data["last"]
    clean = {k: d for k, d in this.items() if k not in held}
    amt = lambda d: d["amount_v"] or 0
    new_q = [k for k, d in clean.items() if in_week(d["entered"]["Qualified"])]
    moved = []
    for k, d in clean.items():
        p = last.get(k)
        if p is None or k in new_q or p["stage"] not in OPEN_QUAL or d["stage"] not in OPEN_QUAL:
            continue
        if STAGES.index(d["stage"]) > STAGES.index(p["stage"]):
            moved.append(k)
    won = [k for k, d in clean.items() if in_week(d["entered"]["Won"])]
    lost_q = [k for k, d in clean.items() if in_week(d["entered"]["Lost"]) and d["entered"]["Qualified"] is not None]
    lost_pre = [k for k, d in clean.items() if in_week(d["entered"]["Lost"]) and d["entered"]["Qualified"] is None]
    open_ = [k for k, d in clean.items() if d["stage"] in OPEN_QUAL]
    chart = []
    for i in range(12):
        start = WEEK_START - dt.timedelta(days=7 * (11 - i))
        end = start + dt.timedelta(days=7)
        chart.append(sum(1 for d in clean.values() if d["entered"]["Qualified"] and start <= d["entered"]["Qualified"] < end))
    by_stage = {}
    for k in push:
        by_stage.setdefault(this[k]["stage"], []).append(k)
    card_stage = None
    if by_stage:
        top = max(len(v) for v in by_stage.values())
        card_stage = max((s for s, v in by_stage.items() if len(v) == top), key=STAGES.index)
    return {
        "new_qualified": {"count": len(new_q), "deals": sorted(new_q, key=id_key)},
        "moved_forward": {"count": len(moved), "deals": sorted(moved, key=id_key)},
        "won": {"count": len(won), "value": sum(amt(this[k]) for k in won), "deals": sorted(won, key=id_key)},
        "lost": {"count": len(lost_q), "value": sum(amt(this[k]) for k in lost_q), "deals": sorted(lost_q, key=id_key), "before_qualified": sorted(lost_pre, key=id_key)},
        "open": {"count": len(open_), "value": sum(amt(this[k]) for k in open_), "deals": sorted(open_, key=id_key)},
        "held_out": {"count": len(held), "value": sum(amt(this[k]) for k in held)},
        "chart": chart,
        "card": {"count": len(push), "value": sum(amt(this[k]) for k in push), "stage": card_stage, "stage_count": len(by_stage.get(card_stage, []))},
    }


def run(folder, limits=None):
    data = load(folder)
    if limits is None:
        limits = json.loads((HERE / "limits.json").read_text())
    held = held_out(data)
    push, order = push_list(data, limits, held)
    return {"data": data, "limits": limits, "held_out": held, "push": push, "push_order": order, "numbers": numbers(data, held, push, order)}


def summary(result):
    """The comparable part of a run: what the recount and the key also produce."""
    n = result["numbers"]
    strip = lambda x: {k: v for k, v in x.items() if k not in ("deals", "before_qualified")}
    return {"held_out": result["held_out"], "push": result["push"], "push_order": result["push_order"],
            "numbers": {"new_qualified": n["new_qualified"]["count"], "moved_forward": n["moved_forward"]["count"],
                        "won": strip(n["won"]), "lost": strip(n["lost"]), "lost_before_qualified": len(n["lost"]["before_qualified"]),
                        "open": strip(n["open"]), "held_out": n["held_out"], "chart": n["chart"], "card": n["card"]}}


if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else HERE / "sample" / "practice"
    if len(sys.argv) > 2 and sys.argv[2] == "--limits":
        print(json.dumps(compute_limits(load(folder)), indent=1))
    else:
        print(json.dumps(summary(run(folder)), indent=1, default=str))
