"""Writes the fixture export: one breaking and one clean deal for each rule of
PLAN.md section 3.4, each named near miss, each push rule and push near miss,
and the edge cases of sections 3.0 and 3.3. Every deal and firm is made up.

    python3 tests/fixture/make_fixture.py

Writes tests/fixture/export/ (the four CSVs and limits.json) and
tests/fixture/expected.json: what section 3 makes of each planted deal,
worked out by hand from the rules, beside the engine and the recount.
"""
import csv
import datetime as dt
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "export"

STAGES = ["Consultation booked", "Qualified", "Pilot proposed", "Partner said yes", "Order form sent", "Won", "Lost"]
COL = {s: "entered_" + s.lower().replace(" ", "_") for s in STAGES}
FIELDS = ["deal_id", "deal_name", "stage", "pipeline", "amount", "close_date", "owner", "create_date",
          "last_contacted", "last_activity_date", "next_activity_date", "next_step", "closed_lost_reason",
          "firm_id"] + [COL[s] for s in STAGES]
EXPORT_LAST = dt.datetime(2026, 11, 16, 0, 0)
LIMITS = {"Qualified": 12, "Pilot proposed": 14, "Partner said yes": 12, "Order form sent": 12}
CITIES = ["Phoenix", "Tampa", "Denver", "Atlanta", "Houston", "Charlotte", "Columbus", "Nashville"]

deals, last_overrides, firms, notes = [], {}, [], []
expect_held, expect_push, expect_push_order, checks = {}, {}, [], {}
_firm_no = [2200]


def T(s):
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M")


def fmt(t):
    return t.strftime("%Y-%m-%d %H:%M") if isinstance(t, dt.datetime) else (t or "")


def new_firm(domain=None, name=None, city=None):
    _firm_no[0] += 1
    n = _firm_no[0]
    fid = str(n)
    firms.append({"firm_id": fid, "name": name or f"Firm {n}", "domain": domain or f"firm{n}.example",
                  "city": city or CITIES[n % len(CITIES)]})
    return fid


def path_dates(stage, current_entered, step_days=7, lost_from=None, won_at=None):
    """Date entered values for a clean path to `stage`: the current stage entered
    at `current_entered`, each earlier stage `step_days` before the next."""
    ent = {s: None for s in STAGES}
    if stage == "Lost":
        top = STAGES.index(lost_from)
        ent["Lost"] = current_entered
        anchor = current_entered - dt.timedelta(days=step_days)
    elif stage == "Won":
        top = STAGES.index("Won")
        anchor = current_entered
    else:
        top = STAGES.index(stage)
        anchor = current_entered
    for i in range(top, -1, -1):
        ent[STAGES[i]] = anchor
        anchor = anchor - dt.timedelta(days=step_days)
    return ent


def deal(did, stage, *, entered_at="2026-11-12 10:00", lost_from="Pilot proposed", ent=None, last_stage=None,
         last_close=None, held=None, push=None, **kw):
    """One deal. Defaults make a clean deal that earns no push tag."""
    t_cur = T(entered_at)
    e = path_dates(stage if stage in STAGES else "Qualified", t_cur, lost_from=lost_from)
    if ent:
        for k, v in ent.items():
            e[k] = T(v) if v else None
    created = min(t for t in e.values() if t is not None)
    closed = stage in ("Won", "Lost")
    row = {
        "deal_id": did,
        "deal_name": f"Firm pilot {did}",
        "stage": stage,
        "pipeline": "New business",
        "amount": "" if stage == "Consultation booked" else "240000",
        "close_date": fmt(e["Won"] if stage == "Won" else e["Lost"] if stage == "Lost" else T("2026-12-18 17:00")),
        "owner": "Nora Kessel",
        "create_date": fmt(created),
        "last_contacted": "2026-11-19 11:00" if not closed else fmt(e["Won"] or e["Lost"]),
        "last_activity_date": "2026-11-19 11:00" if not closed else fmt(e["Won"] or e["Lost"]),
        "next_activity_date": "" if closed else "2026-11-26 10:00",
        "next_step": "" if closed else "Send the order form",
        "closed_lost_reason": "Chose another vendor" if stage == "Lost" else "",
        "firm_id": None,
    }
    for k, v in e.items():
        row[COL[k]] = fmt(v)
    for k, v in kw.items():
        row[k] = v
    if row["firm_id"] is None:
        row["firm_id"] = new_firm()
    deals.append(row)
    if last_stage is not None or last_close is not None:
        last_overrides[did] = {"stage": last_stage, "close_date": last_close}
    if held:
        expect_held[did] = held
    if push:
        expect_push[did] = push
    return did


def last_week_row(row):
    """Last week's row: the same deal as it stood at Mon 2026-11-16 00:00."""
    r = dict(row)
    entered = {s: (T(row[COL[s]]) if row[COL[s]] else None) for s in STAGES}
    for k in ("last_contacted", "last_activity_date"):
        if r[k] and T(r[k]) >= EXPORT_LAST:
            r[k] = ""
    for s in STAGES:
        if entered[s] and entered[s] >= EXPORT_LAST:
            r[COL[s]] = ""
    reached = [s for s in STAGES if r[COL[s]]]
    r["stage"] = reached[-1] if reached else row["stage"]
    if r["stage"] not in ("Won", "Lost"):
        r["closed_lost_reason"] = ""
        if row["stage"] in ("Won", "Lost"):
            r["close_date"] = "2026-12-18 17:00"
            r["next_activity_date"] = "2026-11-20 10:00"
    if r["stage"] == "Consultation booked":
        r["amount"] = ""
    o = last_overrides.get(row["deal_id"], {})
    if o.get("stage"):
        r["stage"] = o["stage"]
    if o.get("close_date"):
        r["close_date"] = o["close_date"]
    return r


# =========================================================== held out, one breaking and one clean per rule

# H1 no owner
deal("F101", "Pilot proposed", owner="", held="H1")
deal("F102", "Pilot proposed", owner="  Nora Kessel ")                       # spaces trimmed: counted
deal("F103", "Qualified", owner="", amount="", held="H1")                   # H1 and H2: the lowest wins
# H2 no amount
deal("F201", "Qualified", amount="", held="H2")
deal("F202", "Partner said yes", amount="0", held="H2")
deal("F203", "Consultation booked", amount="")                              # near miss: Consultation booked with no amount
deal("F204", "Qualified", amount="1")                                       # near miss: an amount just above zero
deal("F205", "Qualified", amount="$264,000")                                # "$" and "," dropped
deal("F206", "Lost", lost_from="Pilot proposed", amount="", held="H2", entered_at="2026-11-18 14:00")  # qualified lost, blank amount
# H3 no close date
deal("F301", "Qualified", close_date="", held="H3")
deal("F302", "Consultation booked", close_date="")                          # Consultation booked needs no close date
# H4 close date passed, still open
deal("F401", "Order form sent", close_date="2026-11-22 18:00", held="H4")
deal("F402", "Consultation booked", close_date="2026-10-31 23:59")          # near miss: automatic past close date
deal("F403", "Qualified", close_date="2026-11-23 00:00")                    # equal to the export: not before it
# H5 a stage skipped
deal("F501", "Order form sent", ent={"Partner said yes": ""}, held="H5")
deal("F502", "Qualified", ent={"Consultation booked": ""})                  # near miss: created straight into Qualified
deal("F503", "Lost", lost_from="Pilot proposed", entered_at="2026-11-18 14:00")  # near miss: lost straight from Pilot proposed
deal("F504", "Won", entered_at="2026-11-18 10:00", ent={"Order form sent": ""}, held="H5")
# H6 same firm, two open deals
dom = "firm2601.example"
deal("F601", "Qualified", firm_id=new_firm(dom), create_date="2026-09-01 10:00",
     ent={"Consultation booked": "2026-09-01 10:00"})
deal("F602", "Pilot proposed", firm_id=new_firm(dom), held="H6")
dom = "firm2602.example"
deal("10", "Qualified", firm_id=new_firm(dom))
deal("9", "Qualified", firm_id=new_firm(dom))                               # same Create date: lowest ID 9 kept (numeric order)
expect_held["10"] = "H6"
dom = "firm2603.example"
deal("F605", "Qualified", owner="", firm_id=new_firm(dom), held="H1",
     ent={"Consultation booked": "2026-08-01 10:00"})                       # older, but held out by H1: not in the group
deal("F606", "Qualified", firm_id=new_firm(dom))                            # so F606 stays counted
dom = "firm2604.example"
deal("F607", "Won", firm_id=new_firm(dom), entered_at="2026-11-18 10:00",
     ent={"Consultation booked": "2026-08-01 10:00"})                       # Won is not open
deal("F608", "Qualified", firm_id=new_firm(dom))                            # so F608 stays counted
deal("F609", "Qualified", firm_id=new_firm(city="Boise"))                   # near miss: same city,
deal("F610", "Qualified", firm_id=new_firm(city="Boise"))                   # different domains
dom = "firm2605.example"
deal("F611", "Qualified", owner="Rep Not Listed", firm_id=new_firm(dom), held="H10",
     ent={"Consultation booked": "2026-08-01 10:00"})                       # H10 is higher than H6: still in the group, oldest
deal("F612", "Qualified", firm_id=new_firm(dom), held="H6")
# H7 moved back a stage
deal("F701", "Pilot proposed", ent={"Partner said yes": "2026-11-13 10:00"}, last_stage="Partner said yes", held="H7")
deal("F702", "Order form sent", ent={"Won": "2026-11-14 10:00"}, last_stage="Won", held="H7")
deal("F703", "Won", entered_at="2026-11-18 10:00", ent={"Lost": "2026-11-14 10:00"}, last_stage="Lost",
     closed_lost_reason="", held="H7")                                      # Lost last week, Won now
deal("F704", "Lost", lost_from="Pilot proposed", entered_at="2026-11-18 14:00", last_stage="Pilot proposed")  # Lost now: never moved back
deal("F705", "Pilot proposed", entered_at="2026-11-18 10:00")               # Qualified last week: moved forward
deal("F706", "Pilot proposed", ent={"Consultation booked": "2026-11-17 09:00", "Qualified": "2026-11-18 09:00",
                                    "Pilot proposed": "2026-11-20 10:00"})  # created this week: no last-week row
deal("F708", "Pilot proposed", entered_at="2026-11-19 10:00",
     ent={"Qualified": "2026-11-17 10:00", "Consultation booked": "2026-11-10 10:00"},
     last_stage="Qualified")                                                # Qualified last week, Date entered now in the week: New qualified only
deal("F709", "Lost", ent={"Order form sent": "2026-11-10 10:00", "Won": "2026-11-17 10:00",
                          "Lost": "2026-11-20 10:00"}, lost_from="Order form sent")  # Won and then Lost in the week
deal("F710", "Lost", lost_from="Consultation booked", entered_at="2026-11-19 10:00", amount="")  # lost before Qualified
# H8 contact after lost
deal("F801", "Lost", entered_at="2026-11-17 10:00", last_contacted="2026-11-19 10:00", held="H8")
deal("F802", "Lost", entered_at="2026-11-17 10:00", last_contacted="2026-11-17 16:00")  # same day, later hour: fine
notes.append({"deal_id": "F802", "author": "Nora", "timestamp": "2026-11-18 09:00",
              "body": "Sent a short thank-you after they said no."})            # near miss: a note after a loss
deal("F803", "Won", entered_at="2026-11-18 10:00", last_contacted="2026-11-20 10:00")  # near miss: contact after a win
deal("F804", "Lost", entered_at="2026-11-17 10:00", last_activity_date="2026-11-20 10:00")  # Last activity alone is fine
# H9 lost with no reason
deal("F901", "Lost", entered_at="2026-11-18 14:00", closed_lost_reason="", held="H9")
deal("F902", "Lost", entered_at="2026-11-18 14:00", closed_lost_reason="Timing")
# H10 owner not on the team
deal("F1001", "Qualified", owner="Rep Not Listed", held="H10")
deal("F1002", "Qualified", owner="nora kessel")                             # case ignored: counted
# H11 a test record
deal("F1101", "Qualified", deal_name="TEST deal please ignore", held="H11")
deal("F1102", "Qualified", firm_id=new_firm(name="  Test Firm 2399"), held="H11")
deal("F1103", "Qualified", deal_name="Firm 2311 contest pilot")             # "test" inside the name: counted
deal("F1104", "Qualified", deal_name="Testarossa pilot", held="H11")        # a plain starts-with
# H12 no firm
deal("F1201", "Qualified", firm_id="", held="H12")
deal("F1202", "Qualified", firm_id="9999", held="H12")
# H13 dates out of order
deal("F1301", "Qualified", create_date="2026-11-11 10:00", held="H13")      # Date entered before the Create date
deal("F1302", "Pilot proposed", ent={"Qualified": "2026-11-13 10:00"}, held="H13")  # Pilot before Qualified
deal("F1303", "Qualified", ent={"Qualified": ""}, held="H13")               # current stage has no Date entered
deal("F1304", "Qualified", ent={"Pilot proposed": "2026-11-14 10:00"}, last_stage="Qualified", held="H13")  # a later stage has a date
deal("F1305", "Qualified", ent={"Consultation booked": "2026-11-12 10:00"}, create_date="2026-11-12 10:00")  # equal instants: in order
# H14 dated after the export
deal("F1401", "Qualified", last_activity_date="2026-11-23 09:00", held="H14")
deal("F1402", "Won", entered_at="2026-11-20 10:00", close_date="2026-11-24 12:00", held="H14")
deal("F1403", "Qualified", last_contacted="2026-11-23 00:00")               # equal to the export: not after it
# H15 unknown stage or pipeline
deal("F1501", "Closed won", held="H15")
deal("F1502", "Qualified", pipeline="Renewals", held="H15")
deal("F1503", " Qualified ")                                                # spaces trimmed: counted
# the chart's first week starts Mon 2026-08-31 00:00
deal("F1601", "Qualified", ent={"Qualified": "2026-08-31 00:00", "Consultation booked": "2026-08-25 10:00"},
     entered_at="2026-08-31 00:00", push=["OVER LIMIT"])
deal("F1602", "Qualified", ent={"Qualified": "2026-08-30 23:59", "Consultation booked": "2026-08-25 10:00"},
     entered_at="2026-08-30 23:59", push=["OVER LIMIT"])

# =========================================================== Needs a push (limits: tests/fixture/export/limits.json)

deal("F2001", "Pilot proposed", entered_at="2026-11-07 10:00", push=["OVER LIMIT"])   # 16 days, limit 14
deal("F2002", "Pilot proposed", entered_at="2026-11-09 23:30")              # near miss: exactly 14 calendar days
deal("F2003", "Pilot proposed", entered_at="2026-11-08 23:30", push=["OVER LIMIT"])   # 15 calendar days, 14.02 elapsed
deal("F2101", "Qualified", close_date="2026-12-08 17:00", last_close="2026-12-01 17:00", push=["SLIPPED"])
deal("F2102", "Qualified", close_date="2026-12-07 17:00", last_close="2026-12-01 17:00")  # near miss: exactly 6 days later
deal("F2103", "Qualified", close_date="2026-12-03 17:00", last_close="2026-12-10 17:00")  # near miss: pulled earlier
deal("F2104", "Qualified", close_date="2026-12-08 01:00", last_close="2026-12-01 23:00", push=["SLIPPED"])  # 7 calendar days
deal("F2105", "Qualified", entered_at="2026-11-18 10:00", close_date="2026-12-18 17:00",
     last_close="2026-11-30 23:59")                                         # near miss: Consultation booked last week, automatic date
deal("F2201", "Qualified", last_contacted="2026-11-08 10:00", push=["QUIET"])          # 15 days
deal("F2202", "Qualified", last_contacted="", push=["QUIET"])                         # never contacted
deal("F2203", "Qualified", last_contacted="2026-11-09 23:00")               # near miss: exactly 14 days
deal("F2301", "Partner said yes", next_activity_date="", push=["NONE BOOKED"])
deal("F2302", "Order form sent", next_activity_date="", push=["NONE BOOKED"])
deal("F2303", "Consultation booked", next_activity_date="", last_contacted="2026-10-01 10:00")  # near miss: not qualified
deal("F2304", "Qualified", amount="", last_contacted="", held="H2")         # near miss: held out, would be QUIET
deal("F2401", "Order form sent", entered_at="2026-11-01 10:00", last_contacted="", next_activity_date="",
     push=["OVER LIMIT", "QUIET", "NONE BOOKED"])
deal("F2402", "Pilot proposed", close_date="2026-12-20 17:00", last_close="2026-12-02 17:00",
     last_contacted="2026-11-01 10:00", push=["SLIPPED", "QUIET"])
deal("F2403", "Pilot proposed", last_contacted="2026-11-01 10:00", next_activity_date="", push=["QUIET", "NONE BOOKED"])
# ties among QUIET-only deals: longest days in stage, then Create date, then deal ID
deal("F2501", "Qualified", entered_at="2026-11-13 10:00", last_contacted="2026-11-02 10:00", push=["QUIET"])  # 10 days
deal("F2502", "Qualified", entered_at="2026-11-18 10:00", last_contacted="2026-11-02 10:00", push=["QUIET"])  # 5 days
deal("F2503", "Pilot proposed", entered_at="2026-11-13 10:00", ent={"Consultation booked": "2026-07-01 10:00"},
     last_contacted="2026-11-02 10:00", push=["QUIET"])                     # 10 days, created earlier than F2501
deal("100", "Pilot proposed", entered_at="2026-11-13 10:00", last_contacted="2026-11-02 10:00", push=["QUIET"])
deal("77", "Pilot proposed", entered_at="2026-11-13 10:00", last_contacted="2026-11-02 10:00", push=["QUIET"])

# F1601 and F1602 are in Qualified since late August: OVER LIMIT (84 and 85 days)

# =========================================================== expected push order (by hand from section 3.5)
expect_push_order = [
    "F2401",                     # three tags
    "F2402",                     # two tags, highest SLIPPED
    "F2403",                     # two tags, highest QUIET
    "F1602", "F1601",            # OVER LIMIT: 85 days, 84 days
    "F2001", "F2003",            # OVER LIMIT: 16 days, 15 days
    "F2101", "F2104",            # SLIPPED: 11 days in stage, same Create date: by deal ID
    "F2201", "F2202",            # QUIET: 11 days in stage, same Create date: by deal ID
    "F2503", "77", "100", "F2501",  # QUIET: 10 days; created Jul 1, then Oct 30 (77 before 100 as numbers), then Nov 6
    "F2502",                     # QUIET: 5 days
    "F2302", "F2301",            # NONE BOOKED: 11 days each; F2302 created Oct 15, F2301 Oct 22
]

checks = {
    "moved_forward_includes": ["F705"],
    "moved_forward_excludes": ["F708", "F706", "F704"],
    "new_qualified_includes": ["F706", "F708", "F2105"],
    "won_includes": ["F709", "F607", "F803"],
    "lost_includes": ["F709", "F503", "F704", "F802", "F804", "F902"],
    "lost_before_qualified_includes": ["F710"],
    "open_excludes": ["F203", "F302", "F402", "F2303"],
    "chart_week_1_includes": ["F1601"],
    "chart_excludes": ["F1602"],
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    seen = set()
    for r in deals:
        assert r["deal_id"] not in seen, r["deal_id"]
        seen.add(r["deal_id"])
    this_rows = deals
    last_rows = [last_week_row(r) for r in deals if r["create_date"] and T(r["create_date"]) < EXPORT_LAST]
    for name, rows, fields in (("deals-this-week.csv", this_rows, FIELDS), ("deals-last-week.csv", last_rows, FIELDS),
                               ("firms.csv", firms, ["firm_id", "name", "domain", "city"]),
                               ("notes.csv", notes, ["deal_id", "author", "timestamp", "body"])):
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    (OUT / "limits.json").write_text(json.dumps(LIMITS, indent=2) + "\n")
    (HERE / "expected.json").write_text(json.dumps({
        "held_out": dict(sorted(expect_held.items())),
        "push": dict(sorted(expect_push.items())),
        "push_order": expect_push_order,
        "checks": checks,
    }, indent=2) + "\n")
    print(f"{len(this_rows)} deals this week, {len(last_rows)} last week, {len(firms)} firms, "
          f"{len(expect_held)} held out, {len(expect_push)} on the push list")


if __name__ == "__main__":
    main()
