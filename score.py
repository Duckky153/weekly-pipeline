"""Scores a run against an export's answer key (PLAN.md section 7). Written before the scored read; it only reads
the key, the export, the saved answers and the code's results.

    python3 score.py <export folder> <key.json> --name <export name> [--out runs/<file>.json] [--stage-off]

Prints and writes:
- the push list: right deals for the right reason (all keyed tags, no extra), and deals listed that should not be;
- held-out problems caught for the right reason, and clean deals held out by mistake;
- the notes check: found, of the keyed note problems it can see; false flags, of the clean chances;
- "waiting on" picks: wrong of settled, settled of keyed;
- the same for the code-only yardstick (no notes check: no tags, so nothing found and nothing flagged).
"""
import json
import pathlib
import sys

import engine
import notes_check

HERE = pathlib.Path(__file__).resolve().parent


def score_data(result, key):
    held, push = result["held_out"], result["push"]
    kh, kp = key["held_out"], key["push"]
    caught = sum(1 for k, r in kh.items() if held.get(k) == r)
    wrongly_held = sorted(k for k in held if k not in kh)
    right_push = sum(1 for k, tags in kp.items() if sorted(push.get(k, [])) == sorted(tags))
    wrongly_listed = sorted(k for k in push if k not in kp)
    return {
        "push": {"right": right_push, "of": len(kp), "listed_wrongly": len(wrongly_listed), "listed_wrongly_ids": wrongly_listed,
                 "order_matches_key": result["push_order"] == key.get("expected", {}).get("push_order")},
        "held_out": {"caught": caught, "of": len(kh), "held_wrongly": len(wrongly_held), "held_wrongly_ids": wrongly_held},
    }


def score_notes(settled, key, stage_on=True):
    nk = key["notes"]
    found = chances = flags = 0
    problems = 0
    misses, false_flags = [], []
    waiting_settled = waiting_wrong = waiting_keyed = 0
    for k, e in nk.items():
        s = settled.get(k)
        if s is None:
            continue
        got = notes_check.tags(s)
        # the step: one problem or one clean chance per deal with a Next step
        if e["step"] in ("not_a_step", "done"):
            problems += 1
            want = "NOT A STEP" if e["step"] == "not_a_step" else "STEP DONE"
            if want in got:
                found += 1
            else:
                misses.append(f"{k} {want}")
            other = "STEP DONE" if want == "NOT A STEP" else "NOT A STEP"
            if other in got:
                flags += 1
                chances += 1
                false_flags.append(f"{k} {other} (keyed {want})")
        elif e["step"] == "real":
            chances += 1
            if "NOT A STEP" in got or "STEP DONE" in got:
                flags += 1
                false_flags.append(f"{k} {[t for t in got if t != 'CHECK STAGE']}")
        # the stage
        if stage_on:
            if e.get("stage_from_notes"):
                problems += 1
                if s["stage_from_notes"] == e["stage_from_notes"]:
                    found += 1
                else:
                    misses.append(f"{k} CHECK STAGE {e['stage_from_notes']} (got {s['stage_from_notes']})")
            else:
                chances += 1
                if s["stage_from_notes"]:
                    flags += 1
                    false_flags.append(f"{k} CHECK STAGE {s['stage_from_notes']}")
        # waiting on
        if e.get("waiting_said") and e.get("waiting") not in (None, "other"):
            waiting_keyed += 1
        if s["waiting"]:
            waiting_settled += 1
            if s["waiting"] != e.get("waiting"):
                waiting_wrong += 1
    return {"found": found, "of": problems, "false_flags": flags, "clean_chances": chances,
            "misses": misses, "false_flag_list": false_flags,
            "waiting": {"wrong": waiting_wrong, "settled": waiting_settled, "keyed": waiting_keyed},
            "near_bar": sum(1 for s in settled.values() if s.get("near_bar")),
            "not_read": sum(1 for s in settled.values() if s["read"] in ("broken", "missing", "not read"))}


def yardstick(result):
    """The keyword yardstick (baseline.py, no AI) settled in the notes check's shape, over the same deals."""
    import baseline
    data, held = result["data"], result["held_out"]
    out = {}
    for k in notes_check.readable(data, held):
        d = data["this"][k]
        st = notes_check.state_for(data, d)
        if "latest_note" not in st and "next_step" not in st:
            continue
        r = baseline.settle(d["stage"], d.get("next_step", ""), st.get("latest_note", ""),
                            st.get("earlier_notes", "") if st.get("earlier_notes") != "(none)" else "")
        waiting = r.get("waiting") if r.get("waiting") not in (None, "other") else None
        stage = r.get("stage_from_notes") if r.get("stage_from_notes") != d["stage"] else None
        out[k] = {"read": "keywords", "step": r.get("step", "unsure"), "stage_from_notes": stage, "waiting": waiting,
                  "near_bar": [], "reads": {}}
    return out


def repeat_changes(first, second):
    """Settled answers that change between two reads of the same requests (step, stage, waiting per deal)."""
    changed = total = 0
    for k, a in first.items():
        b = second.get(k)
        if b is None or a["read"] != "read" or b["read"] != "read":
            continue
        for f in ("step", "stage_from_notes", "waiting"):
            settled_a = a[f] not in (None, "unsure", "none")
            settled_b = b[f] not in (None, "unsure", "none")
            if settled_a or settled_b:
                total += 1
                changed += a[f] != b[f]
    return {"changed": changed, "settled_answers": total}


def score_other(folder, key_path):
    """OpenAI's own 40-deal export: data checks and the push list only (the notes check does not read it)."""
    key = json.loads(pathlib.Path(key_path).read_text())
    result = engine.run(folder, json.loads((HERE / "limits.json").read_text()))
    return score_data(result, key)


def main(argv):
    if argv[1] == "--other":
        out = score_other(argv[2], argv[3])
        if "--out" in argv:
            (HERE / argv[argv.index("--out") + 1]).write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps(out))
        return 0
    folder, key_path = argv[1], argv[2]
    name = argv[argv.index("--name") + 1]
    stage_on = "--stage-off" not in argv and notes_check.SETTINGS["stage_check"]
    key = json.loads(pathlib.Path(key_path).read_text())
    result = engine.run(folder, json.loads((HERE / "limits.json").read_text()))
    settled = notes_check.run(result["data"], result["held_out"], name, mode="real")
    code_only = notes_check.run(result["data"], result["held_out"], name, mode="none")
    out = {"export": name, "questions": notes_check.Q["version"], "stage_check": stage_on,
           **score_data(result, key),
           "notes": score_notes(settled, key, stage_on),
           "code_only": score_notes(code_only, key, stage_on)}
    if (HERE / "baseline.py").exists():
        out["keyword_yardstick"] = score_notes(yardstick(result), key, stage_on)
    if "--openai-notes" in argv:
        ids = set(json.loads((HERE / argv[argv.index("--openai-notes") + 1]).read_text())["deals"])
        sub = dict(key, notes={k: v for k, v in key["notes"].items() if k in ids})
        out["notes_openai_written"] = score_notes({k: v for k, v in settled.items() if k in ids}, sub, stage_on)
        out["notes_claude_written"] = score_notes({k: v for k, v in settled.items() if k not in ids},
                                                  dict(key, notes={k: v for k, v in key["notes"].items() if k not in ids}), stage_on)
    if "--repeat" in argv:
        again = notes_check.run(result["data"], result["held_out"], argv[argv.index("--repeat") + 1], mode="real")
        out["repeat"] = repeat_changes(settled, again)
    if "--out" in argv:
        p = HERE / argv[argv.index("--out") + 1]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=1) + "\n")
    n, d = out["notes"], out
    print(f"push list: {d['push']['right']} of {d['push']['of']} right, {d['push']['listed_wrongly']} listed wrongly")
    print(f"held out: {d['held_out']['caught']} of {d['held_out']['of']} caught, {d['held_out']['held_wrongly']} held wrongly")
    print(f"notes: found {n['found']} of {n['of']}, false flags {n['false_flags']} of {n['clean_chances']}; "
          f"waiting wrong {n['waiting']['wrong']} of {n['waiting']['settled']} settled, settled {n['waiting']['settled']} of {n['waiting']['keyed']} keyed; "
          f"not read {n['not_read']}; near the bar {n['near_bar']}")
    if "keyword_yardstick" in out:
        y = out["keyword_yardstick"]
        print(f"keyword yardstick: found {y['found']} of {y['of']}, false flags {y['false_flags']} of {y['clean_chances']}; "
              f"waiting wrong {y['waiting']['wrong']} of {y['waiting']['settled']} settled, settled {y['waiting']['settled']} of {y['waiting']['keyed']} keyed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
