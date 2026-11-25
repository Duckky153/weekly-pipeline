# How an export's answer key is written

The deals in these files are made up. The key says, for one export, what `PLAN.md` section 3 makes of every deal. It is written with the export, before any code or AI reads it. Only the scorer, `check_keys.py` and `tests/compare.py` open it. Written again on 2026-11-24 after the practice export, and locked with section 3.

## The key file: `tests/keys/<export>.json`

```json
{
  "export": "practice",
  "held_out": {"D1042": "H4", "D1077": "H6"},
  "data_near_misses": {"D1101": "a Consultation booked deal with a past automatic close date"},
  "push": {"D1003": ["OVER LIMIT"], "D1020": ["SLIPPED", "QUIET"]},
  "push_near_misses": {"D1030": "days in stage exactly at the limit", "D1163": "a held-out deal that would meet a push rule"},
  "notes": {
    "D1003": {"step": "real", "stage_from_notes": null, "waiting": "signature", "waiting_said": true},
    "D1019": {"step": "not_a_step", "stage_from_notes": "Pilot proposed", "waiting": null, "waiting_said": false}
  },
  "note_decoys": {"D1044": "a real step that says follow up: Follow up with the revised order form"},
  "expected": {
    "new_qualified": 7, "moved_forward": 8,
    "won": {"count": 3, "value": 186000}, "lost": {"count": 4, "value": 210000},
    "open": {"count": 37, "value": 2900000}, "held_out": {"count": 12, "value": 612000},
    "lost_before_qualified": {"count": 2},
    "chart_new_qualified": [{"week_start": "2026-08-31", "count": 2}],
    "card": {"count": 10, "value": 2115000, "stage": "Order form sent", "stage_count": 3},
    "limits": {"Qualified": 11, "Pilot proposed": 16, "Partner said yes": 15, "Order form sent": 14},
    "push_order": ["D1020", "D1003"]
  }
}
```

(`chart_new_qualified` lists all twelve weeks; `limits` appears in the practice key only, since the scored export uses the locked practice limits.)

## What each field means

- **held_out:** every deal section 3.4 holds out, with the one rule that applies (the lowest number when several do). A deal not listed must pass every check.
- **data_near_misses:** clean deals written to look like a problem (section 4's named list), with which one. They must stay counted.
- **push:** every deal section 3.5 puts on the list, with every tag it earns. A deal not listed must not be on it.
- **push_near_misses:** deals written to sit just inside a push rule, with which one: clean deals, plus the one held-out deal that would meet a push rule (it must stay off the list).
- **notes:** for every open deal that passes every check and has a note, Consultation booked deals included:
  - `step`: `real` (the Next step is an action not yet done), `not_a_step` (a placeholder or a status), `done` (the latest note says it was done or called off), or `none` (no Next step text). A placeholder or status is `not_a_step` even when the notes say it happened.
  - `stage_from_notes`: the stage the notes say the deal has reached, by the event lines of section 3.1 alone (the four Qualified checks are not given to the notes check), when that differs from the recorded stage; else `null`. A Consultation booked deal whose notes say the consultation was held with the person who signs is keyed Qualified.
  - `waiting_said`: whether the latest note says what the deal is waiting on.
  - `waiting`: when it does, one of `signer`, `question`, `order_form`, `signature`, `quiet`, `later_date`, `nothing`, `other`; else `null`.
- **note_decoys:** deals whose notes or Next step are written to look like a problem but are clean (a real step that contains "follow up"; a note that only asks for the step or plans it), with which one. The notes check must leave them untagged.
- **expected:** the numbers of section 3.3, the card, the chart, and the push order of section 3.5, worked out by the key's writer from the rules (a third count beside the engine and the recount).

## Where the "waiting on" options overlap

- A firm that has stopped answering is `quiet`, even when an unsigned order form is out.
- A signer who will sign once the form is sent again is `signature`.
- A firm that asked to come back after a date, before anything more is sent, is `later_date`.
- A meeting or call already booked for the next step is `nothing`.
- Anything that fits none of the seven is `other`.

## Rules for writing it

- Work from the rows and the definitions only, never from code.
- A deal's notes are keyed from their words; "said last counts".
- Every planted problem, near miss, push case and decoy named in `sample/RULES.md` appears in the key.
