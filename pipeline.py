"""Weekly Pipeline: builds the page's data from an export, and runs the checks around it.

    python3 pipeline.py export [folder] [--name practice] [--notes real|none]   writes site/data/week.json
    python3 pipeline.py flip [folder] [--name practice]                          the flip test (exit 1 on any change)
    python3 pipeline.py recount [folder]                                         engine against the recount
    python3 pipeline.py serve [port]                                             serves site/ on 127.0.0.1

Everything on the page with a number in it is written here by code. The notes check only adds tags and can change
which next-step wording shows (PLAN.md section 5).
"""
import datetime as dt
import json
import pathlib
import subprocess
import sys

import engine
import notes_check

HERE = pathlib.Path(__file__).resolve().parent
SITE_DATA = HERE / "site" / "data" / "week.json"
DEFS = json.loads((HERE / "definitions.json").read_text())


def whole(v):
    v = v or 0
    return int(v) if float(v).is_integer() else v


def rule(key):
    return DEFS["rules"][key].format(range=f"{day(engine.WEEK_START)} to {day(engine.WEEK_END - dt.timedelta(days=1))}",
                                     export=weekday_day(engine.EXPORT_THIS))

STATUS_MAX, FIRM_MAX, NEXT_MAX, REASON_MAX = 34, 22, 38, 30


# ---------------------------------------------------------------- formatting

def money(v):
    v = v or 0
    if v >= 1_000_000:
        s = f"{v / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"${s}M"
    if v >= 1_000:
        return f"${round(v / 1000):,}K"
    return f"${v:,.0f}"


def day(t):
    return f"{t.strftime('%b')} {t.day}"


def weekday_day(t):
    return f"{t.strftime('%a')} {t.strftime('%b')} {t.day}"


def plural(n, one, many):
    return f"{n} {one if n == 1 else many}"


# ---------------------------------------------------------------- rows

def firm_of(data, d):
    f = data["firms"].get(d.get("firm_id") or "")
    return (f or {}).get("name", ""), (f or {}).get("city", "")


def owner_name(data, d):
    names = {n.lower(): n for n in data.get("team_names", [])}
    return names.get(d.get("owner", "").lower(), d.get("owner", ""))


def deal_row(data, d, extra=None):
    firm, city = firm_of(data, d)
    row = {"id": d["deal_id"], "firm": firm, "city": city, "owner": owner_name(data, d), "stage": d["stage"],
           "amount": whole(d["amount_v"]), "amount_text": money(d["amount_v"]) if d["amount_v"] else "no amount"}
    if extra:
        row.update(extra)
    return row


def status_line(d, tags, data):
    first = tags[0]
    if first == "OVER LIMIT":
        return f"{d['stage']} · {engine.days(d['entered'][d['stage']])} days"
    if first == "SLIPPED":
        prev = data["last"][d["deal_id"]]
        return f"Close date {day(prev['close_date_t'])} to {day(d['close_date_t'])}"
    return d["stage"]


def contact_text(d):
    if d["last_contacted_t"] is None:
        return "no contact logged"
    n = engine.days(d["last_contacted_t"])
    return "last contact today" if n == 0 else f"last contact {plural(n, 'day', 'days')} ago"


# ---------------------------------------------------------------- the page's data

def tag_text(d, tag, data, limits):
    """One plain line per push tag, written by code (kept by the flip test)."""
    if tag == "OVER LIMIT":
        return f"{engine.days(d['entered'][d['stage']])} days in {d['stage']}; the limit is {limits[d['stage']]}."
    if tag == "SLIPPED":
        prev = data["last"][d["deal_id"]]
        return f"Close date moved from {day(prev['close_date_t'])} to {day(d['close_date_t'])} since last week."
    if tag == "QUIET":
        return "No contact logged." if d["last_contacted_t"] is None else f"Last contact {engine.days(d['last_contacted_t'])} days ago; the limit is 14."
    if tag == "NONE BOOKED":
        return "Nothing on the calendar for this deal."
    raise ValueError(tag)


def note_tag_text(d, tag, settled):
    """One plain line per notes tag (removed by the flip test with the tags)."""
    if tag == "STEP DONE":
        return f"The deal's own next step, \"{d['next_step']}\", is done or called off, by the latest note."
    if tag == "NOT A STEP":
        return f"The deal's own next step, \"{d['next_step']}\", is too vague to act on."
    if tag == "CHECK STAGE":
        return f"The notes say it has reached {settled['stage_from_notes']}; the deal says {d['stage']}."
    raise ValueError(tag)


def recount_check(folder, limits_path, n):
    """Runs the separately written recount on the same files; per number, whether it got the same."""
    cmd = [sys.executable, str(HERE / "recount.py"), str(folder), "--limits", str(limits_path)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("recount failed: " + out.stderr.strip())
    theirs = json.loads(out.stdout)["numbers"]
    mine = {"new_qualified": n["new_qualified"]["count"], "moved_forward": n["moved_forward"]["count"],
            "won": {"count": n["won"]["count"], "value": whole(n["won"]["value"])},
            "lost": {"count": n["lost"]["count"], "value": whole(n["lost"]["value"])},
            "open": {"count": n["open"]["count"], "value": whole(n["open"]["value"])},
            "held_out": {"count": n["held_out"]["count"], "value": whole(n["held_out"]["value"])}}
    res = {}
    for k, v in mine.items():
        tv = theirs.get(k)
        tv = {"count": tv["count"], "value": whole(tv["value"])} if isinstance(tv, dict) else tv
        res[k] = {"same": tv == v, "theirs": tv if isinstance(tv, int) else (tv or {}).get("count")}
    return res


def build(folder, name, notes_mode="real", limits=None, limits_path=None):
    limits_path = limits_path or HERE / "limits.json"
    if limits is None:
        limits = json.loads(pathlib.Path(limits_path).read_text())
    result = engine.run(folder, limits)
    data, held, push, order, n = result["data"], result["held_out"], result["push"], result["push_order"], result["numbers"]
    data["team_names"] = [r["full_name"].strip() for r in engine.read_csv(HERE / "sample" / "team.csv")]
    this = data["this"]
    settled = notes_check.run(data, held, name, mode=notes_mode)

    push_rows = []
    for k in order:
        d, t = this[k], push[k]
        s = settled.get(k)
        note_tags = notes_check.tags(s) if s else []
        text, source = notes_check.next_step(d, t, s)
        shown = (t + note_tags)[:2]
        push_rows.append(deal_row(data, d, {
            "contact": contact_text(d),
            "status": status_line(d, t, data),
            "push_tags": t,
            "days_in_stage": engine.days(d["entered"][d["stage"]]),
            "limit": result["limits"].get(d["stage"]),
            "close_date": day(d["close_date_t"]) if d["close_date_t"] else None,
            "last_close_date": day(data["last"][k]["close_date_t"]) if k in data["last"] and data["last"][k]["close_date_t"] else None,
            "tag_text": {tag: tag_text(d, tag, data, result["limits"]) for tag in t},
            # what the notes check may change (the flip test removes these)
            "tags": shown,
            "note_tags": note_tags,
            "note_tag_text": {tag: note_tag_text(d, tag, s) for tag in note_tags},
            "next": text,
            "next_source": source,
            "next_source_label": {"notes": "from the notes", "stage": "from the stage"}.get(source),
        }))

    def rows(ids, extra=lambda d: {}):
        out = [deal_row(data, this[k], extra(this[k])) for k in ids]
        return sorted(out, key=lambda r: (this[r["id"]]["create_date_t"] or dt.datetime.max, engine.id_key(r["id"])))

    def entered_on(stage):
        return lambda d: {"date": day(d["entered"][stage]) if d["entered"][stage] else None}

    held_rows = []
    for k in sorted(held, key=lambda k: (engine.REASONS[held[k]], engine.id_key(k))):
        held_rows.append(deal_row(data, this[k], {"rule": held[k], "reason": engine.REASONS[held[k]],
                                                  "fixes": engine.FIXER.get(held[k], "deal owner")}))

    card_n, card_v = n["card"]["count"], n["card"]["value"]
    card_line = f"{plural(card_n, 'deal needs', 'deals need')} a push." if card_n else "No deal needs a push this week."
    card_detail = None
    if card_n:
        where, k = n["card"]["stage"], n["card"]["stage_count"]
        subj = ("It" if k == 1 else "All") if k == card_n else words_count(k)
        one = k == 1
        tail = {
            "Qualified": f"{subj} {'has' if one else 'have'} no pilot scope sent yet.",
            "Pilot proposed": f"{subj} {'has' if one else 'have'} a pilot scope out with the firm.",
            "Partner said yes": f"{subj} {'has' if one else 'have'} the partner's yes but no order form yet.",
            "Order form sent": f"{subj} {'is' if one else 'are'} waiting on a signed order form.",
        }[where]
        card_detail = f"{money(card_v)} a year between them. {tail}"

    chart = []
    for i, count in enumerate(n["chart"]):
        start = engine.WEEK_START - dt.timedelta(days=7 * (11 - i))
        end = start + dt.timedelta(days=7)
        ids = [k for k, d in this.items() if k not in held and d["entered"]["Qualified"] and start <= d["entered"]["Qualified"] < end]
        assert len(ids) == count
        chart.append({"week": day(start), "week_end": day(end - dt.timedelta(days=1)), "count": count, "last": i == 11,
                      "rows": rows(ids, entered_on("Qualified"))})
    lim = result["limits"]
    limits_text = " · ".join((f"{s} {lim[s]} days" if i == 0 else f"{s} {lim[s]}").replace(" ", "\u00a0")
                             for i, s in enumerate(engine.OPEN_QUAL))

    week = {
        "export": name,
        "week": {"start": weekday_day(engine.WEEK_START), "end": weekday_day(engine.WEEK_END - dt.timedelta(days=1)),
                 "export_day": weekday_day(engine.EXPORT_THIS)},
        "definitions": DEFS["card"],
        "limits": result["limits"],
        "limits_text": limits_text,
        "recount": recount_check(folder, limits_path, n),
        "push_rule": DEFS["rules"]["push"],
        "test_sentence": None,
        "tested_link": None,
        "card": {"count": card_n, "value": whole(card_v), "line": card_line, "detail": card_detail,
                 "stage": n["card"]["stage"], "stage_count": n["card"]["stage_count"]},
        "numbers": [
            {"key": "new_qualified", "empty": "No deal entered Qualified.", "label": "New qualified", "count": n["new_qualified"]["count"],
             "rule": rule("new_qualified"), "rows": rows(n["new_qualified"]["deals"], entered_on("Qualified"))},
            {"key": "moved_forward", "empty": "No deals moved forward.", "label": "Moved forward", "count": n["moved_forward"]["count"],
             "rule": rule("moved_forward"),
             "rows": rows(n["moved_forward"]["deals"], lambda d: {"from": data["last"][d["deal_id"]]["stage"]})},
            {"key": "won", "empty": "No deal was won.", "label": "Won", "count": n["won"]["count"], "value": whole(n["won"]["value"]),
             "value_text": money(n["won"]["value"]), "rule": rule("won"),
             "rows": rows(n["won"]["deals"], entered_on("Won"))},
            {"key": "lost", "empty": "No qualified deal was lost.", "label": "Lost", "count": n["lost"]["count"], "value": whole(n["lost"]["value"]),
             "value_text": money(n["lost"]["value"]), "rule": rule("lost"),
             "rows": rows(n["lost"]["deals"], lambda d: {"date": day(d["entered"]["Lost"]), "why": d.get("closed_lost_reason", "")}),
             "before_qualified": len(n["lost"]["before_qualified"])},
            {"key": "open", "empty": "No open deals.", "label": "Open", "count": n["open"]["count"], "value": whole(n["open"]["value"]),
             "value_text": money(n["open"]["value"]), "rule": rule("open"),
             "rows": rows(n["open"]["deals"])},
        ],
        "held_out": {"count": n["held_out"]["count"], "value": whole(n["held_out"]["value"]),
                     "value_text": money(n["held_out"]["value"]), "rule": rule("held_out"), "rows": held_rows},
        "push": push_rows,
        "chart": chart,
        "chart_rule": rule("chart"),
    }
    return week, result, settled


def words_count(k):
    words = ["None", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]
    return words[k] if k < len(words) else str(k)


# ---------------------------------------------------------------- the flip test

NOTE_FIELDS = ("tags", "note_tags", "note_tag_text", "next", "next_source", "next_source_label")


def without_notes(week):
    w = json.loads(json.dumps(week))
    for r in w["push"]:
        for f in NOTE_FIELDS:
            r.pop(f, None)
    return json.dumps(w, sort_keys=True, ensure_ascii=False)


def flip(folder, name, limits=None, limits_path=None):
    outs = {m: without_notes(build(folder, name, m, limits, limits_path)[0]) for m in notes_check.MODES}
    base = outs["real"]
    changed = [m for m, o in outs.items() if o != base]
    return changed, len(base)


# ---------------------------------------------------------------- command line

def main(argv):
    cmd = argv[1] if len(argv) > 1 else "export"
    rest, opts, pos = argv[2:], {}, []
    i = 0
    while i < len(rest):
        if rest[i] == "--live":
            i += 1
        elif rest[i].startswith("--"):
            opts[rest[i]] = rest[i + 1] if i + 1 < len(rest) else ""
            i += 2
        else:
            pos.append(rest[i])
            i += 1
    folder = pos[0] if pos and cmd != "serve" else str(HERE / "sample" / "practice")
    name = opts.get("--name", pathlib.Path(folder).name)
    limits_path = opts.get("--limits")
    limits = json.loads(pathlib.Path(limits_path).read_text()) if limits_path else None
    if cmd == "export":
        week, result, settled = build(folder, name, opts.get("--notes", "real"), limits, limits_path)
        SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
        SITE_DATA.write_text(json.dumps(week, indent=1, ensure_ascii=False) + "\n")
        print(f"site/data/week.json: {len(result['data']['this'])} deals, {week['card']['count']} need a push, "
              f"{week['held_out']['count']} held out")
    elif cmd == "flip":
        changed, size = flip(folder, name, limits, limits_path)
        if changed:
            print("flip test FAILED: the page changed with", ", ".join(changed))
            return 1
        print(f"flip test passed: every number, the card, the held-out reasons and the push list are byte-identical "
              f"with the real read, all yes or first option, all no or last option, and no read ({size} characters)")
    elif cmd == "read":
        # the paid read (or a replay of saved answers): python3 pipeline.py read <folder> --name practice [--live] [--only D1,D2] [--tag smoke]
        limits = limits or json.loads((HERE / "limits.json").read_text())
        result = engine.run(folder, limits)
        only = set(opts["--only"].split(",")) if opts.get("--only") else None
        live = "--live" in rest
        before = notes_check.jev_check.spent()
        out = notes_check.run(result["data"], result["held_out"], name, mode="real", live=live,
                              tag=opts.get("--tag", "read"), only=only)
        from collections import Counter
        print("deals:", len(out), "| reads:", dict(Counter(v["read"] for v in out.values())),
              "| steps:", dict(Counter(v["step"] for v in out.values())),
              "| CHECK STAGE:", sum(1 for v in out.values() if v["stage_from_notes"]),
              "| waiting settled:", sum(1 for v in out.values() if v["waiting"]),
              "| near the bar:", sum(1 for v in out.values() if v["near_bar"]))
        print(f"spent this run ${notes_check.jev_check.spent() - before:.4f}; build total ${notes_check.jev_check.spent():.4f} of ${notes_check.jev_check.CAP:.2f}")
    elif cmd == "recount":
        args = [sys.executable, str(HERE / "tests" / "compare.py"), folder] + (["--limits", limits_path] if limits_path else [])
        return subprocess.run(args).returncode
    elif cmd == "serve":
        import http.server
        import functools
        port = int(pos[0]) if pos else 8765
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE / "site"))
        print(f"http://127.0.0.1:{port}/")
        http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
