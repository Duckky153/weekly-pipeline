"""The notes check (question set fp-q2, PLAN.md section 5): reads each open deal's notes through jev_check, and
settles by code's rules whether the Next step is a real action, whether the notes say it is done, which stage the
notes say the deal has reached, and what the deal is waiting on.

It adds tags (STEP DONE, NOT A STEP, CHECK STAGE) and can change which next-step wording shows. It never changes a
number, a held-out reason, the card sentences, or who is on the push list and in what order: it is given none of
them, and the flip test proves the rest of the page does not move.

What the model sees, per deal: the recorded stage name; the Next step text; the stage lines (event and "does not
count" only); the latest note and up to two earlier notes as "First name: words". Never amounts, dates, owners,
other deals, held-out reasons or counts. This file never opens the answer keys.
"""
import json
import pathlib

import engine
import jev_check

HERE = pathlib.Path(__file__).resolve().parent
Q = json.loads((HERE / "questions.json").read_text())
SETTINGS = json.loads((HERE / "settings.json").read_text())
WORDING = json.loads((HERE / "wording.json").read_text())
READ = Q["read"]
NOTE_TAGS = ["STEP DONE", "NOT A STEP", "CHECK STAGE"]
MODES = ("real", "yes_first", "no_last", "none")


# ---------------------------------------------------------------- what the model sees

def stage_lines():
    return "\n".join(f"{s}: {line}" for s, line in Q["options"]["stages"].items())


def deal_notes(data, deal_id):
    """Notes dated at or before the export, oldest first."""
    return [n for n in data["notes"].get(deal_id, []) if n["t"] is not None and n["t"] <= engine.EXPORT_THIS]


def note_line(n):
    return f"{n['author'].strip()}: {' '.join(n['body'].split())}"


def state_for(data, deal):
    notes = deal_notes(data, deal["deal_id"])
    state = {"stage": deal["stage"], "stages": stage_lines()}
    if deal.get("next_step"):
        state["next_step"] = deal["next_step"]
    if notes:
        state["latest_note"] = note_line(notes[-1])
        earlier = notes[:-1][-SETTINGS["earlier_notes"]:]
        state["earlier_notes"] = "\n".join(note_line(n) for n in earlier) if earlier else "(none)"
    return state


def asked(state):
    """The questions this deal's inputs allow (a question is asked only when its inputs exist)."""
    out = []
    for qid, spec in READ.items():
        if qid.startswith("stage_") and not SETTINGS["stage_check"]:
            continue
        if all(k in state for k in spec["needs"]):
            out.append(qid)
    return out


def request_for(data, deal):
    state = state_for(data, deal)
    qids = asked(state)
    if not qids:
        return None
    qs = {}
    for qid in qids:
        spec = READ[qid]
        if spec["type"] == "noul":
            qs[qid] = {"type": "noul", "instructions": spec["q"]}
        else:
            qs[qid] = {"type": "choice", "instructions": spec["q"], "criteria": dict(Q["options"][spec["options"]])}
    return {"model": jev_check.MODEL, "state": state, "questions": qs}


def readable(data, held):
    """Every open deal that passes every check, in deal ID order."""
    return [k for k in sorted(data["this"], key=engine.id_key) if k not in held and engine.is_open(data["this"][k])]


# ---------------------------------------------------------------- the answers

def synthetic(body, mode):
    """Both reads made up for the flip test: every yes-or-no at 1 and every pick on its first option, or every
    yes-or-no at 0 and every pick on its last option."""
    answers = {}
    for qid, q in body["questions"].items():
        if q["type"] == "noul":
            answers[qid] = {"noul": 1.0 if mode == "yes_first" else 0.0}
        else:
            opts = list(q["criteria"])
            pick = opts[0] if mode == "yes_first" else opts[-1]
            answers[qid] = {"choice": pick, "probabilities": {o: (1.0 if o == pick else 0.0) for o in opts}}
    read = {"answers": answers, "input_tokens": 0}
    return read, read


def p_yes(read, qid):
    try:
        v = read["answers"][qid]["noul"]
        return float(v) if isinstance(v, (int, float)) else None
    except (KeyError, TypeError):
        return None


def p_pick(ans):
    c = ans.get("choice")
    return (ans.get("probabilities") or {}).get(c, ans.get("confidence", 0)) or 0


# ---------------------------------------------------------------- settling (code's rules, PLAN section 5)

def settle(body, a, b, status="read"):
    """One deal's settled answers. Without both reads, everything stays at its safe default."""
    out = {"read": status, "step": "none", "stage_from_notes": None, "waiting": None, "near_bar": [], "reads": {}}
    if body is None:
        out["read"] = "no request"
        return out
    qs = body["questions"]
    if "next_step" in body["state"]:
        out["step"] = "unsure"
    if a is None or b is None:
        return out
    near = Q["near"]

    def lo(qid):
        x, y = p_yes(a, qid), p_yes(b, qid)
        return None if x is None or y is None else min(x, y)

    def hi(qid):
        x, y = p_yes(a, qid), p_yes(b, qid)
        return None if x is None or y is None else max(x, y)

    def both_pick(qid, bar):
        try:
            x, y = a["answers"][qid], b["answers"][qid]
        except (KeyError, TypeError):
            return None, None
        p = min(p_pick(x), p_pick(y))
        if x.get("choice") == y.get("choice") and p >= bar:
            return x["choice"], p
        return None, (p if x.get("choice") == y.get("choice") else None)

    def mark_near(qid, value, bar):
        """Written to the run file only: the bar alone decides."""
        if value is not None and abs(value - bar) <= near:
            out["near_bar"].append(qid)

    for qid in qs:
        out["reads"][qid] = {"a": a["answers"].get(qid), "b": b["answers"].get(qid)}

    # the Next step: NOT A STEP is checked first (the field itself), then STEP DONE (the notes)
    if "step_specific" in qs:
        low, high = lo("step_specific"), hi("step_specific")
        bars = READ["step_specific"]
        done = lo("step_done") if "step_done" in qs else None
        if high is not None and high <= bars["not_a_step"]:
            out["step"] = "not_a_step"
        elif done is not None and done >= READ["step_done"]["done"]:
            out["step"] = "done"
        elif low is not None and low >= bars["real"]:
            out["step"] = "real"
        else:
            out["step"] = "unsure"
        mark_near("step_specific", low, bars["real"])
        mark_near("step_specific", high, bars["not_a_step"])
        if "step_done" in qs:
            mark_near("step_done", done, READ["step_done"]["done"])

    # the stage the notes say the deal has reached
    if "stage_said" in qs:
        said = lo("stage_said")
        mark_near("stage_said", said, READ["stage_said"]["yes"])
        stage, p = both_pick("stage_pick", READ["stage_pick"]["pick"])
        if stage is None:
            mark_near("stage_pick", p, READ["stage_pick"]["pick"])
        if said is not None and said >= READ["stage_said"]["yes"] and stage is not None and stage != body["state"]["stage"]:
            out["stage_from_notes"] = stage

    # what the deal is waiting on
    if "waiting_said" in qs:
        said = lo("waiting_said")
        mark_near("waiting_said", said, READ["waiting_said"]["yes"])
        pick, p = both_pick("waiting_pick", READ["waiting_pick"]["pick"])
        if pick is None:
            mark_near("waiting_pick", p, READ["waiting_pick"]["pick"])
        if said is not None and said >= READ["waiting_said"]["yes"] and pick is not None and pick != "other":
            out["waiting"] = pick
    out["near_bar"] = sorted(set(out["near_bar"]))
    return out


def tags(settled):
    t = []
    if settled["step"] == "done":
        t.append("STEP DONE")
    if settled["step"] == "not_a_step":
        t.append("NOT A STEP")
    if settled["stage_from_notes"]:
        t.append("CHECK STAGE")
    return t


def next_step(deal, push_tags, settled):
    """PLAN section 3.6: the deal's own Next step when settled as a real action not yet done; else the wording for
    the settled "waiting on" pick; else the wording for the first push tag (by stage for OVER LIMIT and SLIPPED).
    Returns (text, source) with source "deal", "notes" or "stage"."""
    if settled and settled["step"] == "real" and deal.get("next_step"):
        s = deal["next_step"]
        if len(s) > 1 and not s[1].isupper():
            s = s[0].lower() + s[1:]
        return "Next: " + s, "deal"
    w = settled["waiting"] if settled else None
    if w and w in WORDING["waiting"]:
        return WORDING["waiting"][w], "notes"
    first = push_tags[0] if push_tags else None
    if first in ("OVER LIMIT", "SLIPPED"):
        return WORDING["by_stage"][deal["stage"]], "stage"
    if first in ("QUIET", "NONE BOOKED"):
        return WORDING[first], "stage"
    return None, None


# ---------------------------------------------------------------- one run over an export

def run(data, held, export_name, mode="real", live=False, tag="read", only=None):
    """{deal_id: settled} for every readable deal. Modes: real (saved answers, or paid when live), yes_first and
    no_last (made-up answers for the flip test), none (no read at all)."""
    if mode not in MODES:
        raise ValueError(mode)
    ids = readable(data, held)
    if only is not None:
        ids = [k for k in ids if k in only]
    bodies = {k: request_for(data, data["this"][k]) for k in ids}
    if mode == "real" and live:
        jev_check.preflight(2 * sum(1 for b in bodies.values() if b is not None))
    out = {}
    for k in ids:
        body = bodies[k]
        if body is None or mode == "none":
            out[k] = settle(body, None, None, "no request" if body is None else "not read")
            continue
        if mode in ("yes_first", "no_last"):
            a, b = synthetic(body, mode)
            out[k] = settle(body, a, b, mode)
            continue
        a, b, meta = jev_check.two_reads(body, f"{Q['version']}/{export_name}", k, tag, live)
        status = "broken" if meta.get("broken") else "missing" if meta.get("missing") else "read"
        out[k] = settle(body, a, b, status)
        out[k]["fingerprint"] = meta["fingerprint"]
    return out


def requests_needed(data, held):
    return sum(1 for k in readable(data, held) if request_for(data, data["this"][k]) is not None)
