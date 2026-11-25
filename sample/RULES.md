# How the sample exports are written

The deals, firms, people and notes in these files are made up. Nothing in them is real.

The definitions every rule below refers to are in `PLAN.md` section 3 (copied to `DEFINITIONS.md` for the public repo). Read section 3 in full before writing any row. This file was written again from the closed section 3 on 2026-11-24, after the practice export, and is locked with it.

## Files (one folder per export: `sample/practice/`, the scored folder kept by the data helper)

All CSV, UTF-8, header row, HubSpot's field shape. Dates as `YYYY-MM-DD HH:MM` in New York time; an empty cell means blank. No cell starts or ends with a space unless a planted problem calls for it.

- `deals-this-week.csv` (exported Mon 2026-11-23 00:00) and `deals-last-week.csv` (exported Mon 2026-11-16 00:00). Columns: `deal_id, deal_name, stage, pipeline, amount, close_date, owner, create_date, last_contacted, last_activity_date, next_activity_date, next_step, closed_lost_reason, firm_id, entered_consultation_booked, entered_qualified, entered_pilot_proposed, entered_partner_said_yes, entered_order_form_sent, entered_won, entered_lost`.
  - `stage` is one of: Consultation booked, Qualified, Pilot proposed, Partner said yes, Order form sent, Won, Lost. `pipeline` is `New business`.
  - A deal ID appears once per file. A deal in last week's file keeps its `deal_id`. A deal created during the week appears only in this week's file.
  - Last week's file shows each deal as it stood at its export: its stage then, its close date then, and no date after Mon 2026-11-16 00:00.
- `firms.csv`: `firm_id, name, domain, city`. Firms are numbered: `name` is `Firm 2210`, `domain` is `firm2210.example`, `city` a real US city. A duplicate firm has a second `firm_id` with the same domain, written the same way.
- `notes.csv`: `deal_id, author, timestamp, body`. Up to three notes per open deal, dated at or before the export; `author` is a first name (the owner's, or a teammate's). The one named near miss "a note after a loss" puts one note on a lost deal.
- `team.csv` lives in `sample/` (`full_name, role`), shared by every export.

## The week the files describe

This week runs Mon 2026-11-16 00:00 to Mon 2026-11-23 00:00, New York time. Create dates run from 2026-06-01 to 2026-11-22. Every date obeys section 3's rules unless the row is a planted problem of that rule.

- A Consultation booked deal's close date is HubSpot's automatic end-of-month date. When it moves to Qualified, the rep sets a real close date; that change is not a slip (section 3.5).
- An open deal's close date and its next activity date are after the export. A won or lost deal's close date is the day it closed.

## Amounts

Amount is the expected yearly value: a monthly case volume (10 to 80) times a per-case price (between 400 and 1,500 dollars) times 12, rounded to the nearest thousand. Deals in Consultation booked have no amount. The two exports agree on a deal's amount unless the story says it changed. The one named near miss "an amount just above zero" is the only amount not rounded (from $1 to $999).

## Owners and names

Four owners from `sample/team.csv`. Each full name is searched on the web for a real or famous match before use (the data helper logs each search in a private file); none comes from Finch's customers, staff or demo, or from an earlier build's sample. Contact names inside notes are first names only and are checked the same way.

## Sizes and plants

Exactly as `PLAN.md` section 4's size table, for the export being written. "120 deals" counts this week's file; the planted deals are inside the stage mix (a planted won deal counts toward Won).

- The planted held-out problems: one rule each, or keyed by the lowest rule number that applies. Practice plants H1 to H8. The scored export plants 14, of which 5 are drawn privately by the data helper from H9 to H15.
- At least 4 planted held-out problems touch a number on the page; one held-out deal would also meet a push rule.
- The named data near misses and push near misses of section 4, as many as the size table gives for the export, each keyed by name. "A Consultation booked deal with no amount" is met by any booked deal; key one.
- Push cases: each push rule at least twice.
- The notes counts, the keyed note problems, the note decoys and the keyed "waiting on" deals of section 4.

## Notes

Short (one or two sentences), dated, plain sales talk between people at a company that sells an operations service to personal injury law firms. Never fees, referrals, clients, injuries or law; "cases" only for case volume ("about 40 cases a month"). A note can contradict the fields only where the key says it does. Next step text written for a deal is at most 32 characters.

## The key

Written with each deal, before anything reads the files, in the format of `tests/LABELING.md`.
