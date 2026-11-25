# Definitions

What every number, check and list on the page means, written before the code and locked before the scored sample was written. `engine.py` follows it; `recount.py` was written from it alone by a separate script writer, without seeing `engine.py`, and must agree on every deal and every number.

The deals are made up. The stage names are this build's proposal for a company that sells an operations service to personal injury law firms.

## 3.0 Inputs

- **Files** (HubSpot field shape): `sample/deals-this-week.csv` and `sample/deals-last-week.csv` (deal ID, deal name, stage, pipeline, amount, close date, owner, create date, last contacted, last activity date, next activity date, next step, closed lost reason, firm ID, and Date entered for each stage); `sample/firms.csv` (firm ID, name, domain, city); `sample/team.csv` (columns `full_name, role`: the four owners); `sample/notes.csv` (deal ID, author first name, timestamp, body).
- **The exports:** this week's at Mon 2026-11-23 00:00, last week's at Mon 2026-11-16 00:00, New York time.
- **The week:** from Mon 2026-11-16 00:00 to Mon 2026-11-23 00:00, New York time. "In the week" compares timestamps as instants: start included, end excluded.
- **Day counts:** the export's New York calendar date minus the event's New York calendar date. "Over" means strictly more than.
- **Date entered:** the first time a deal entered that stage. A deal whose current stage has no Date entered, or that has a Date entered for a stage after its current one, is held out by H13, so days in stage are always counted from a real date and a deal that moved back at any time is held out.
- **Times:** every comparison of two dates compares instants (equal instants are in order); only day counts use calendar dates.
- **Reading the cells:** every cell is trimmed of surrounding spaces; a cell of only spaces is empty. Dates are read as `YYYY-MM-DD HH:MM` (seconds, a `T` or a bare date are also read); an unreadable date stops the run with the deal named. The repeated hour of 2026-11-01 counts as its first occurrence. An amount drops `$` and `,`; an unreadable amount counts as no amount. A deal ID that appears twice in one export stops the run. Stage, pipeline and firm domain are compared as exact text after trimming. "Lowest deal ID" compares whole-number IDs as numbers, others as text.
- **Open:** a deal in one of the five stages from Consultation booked to Order form sent.
- **Which export:** every rule reads this week's export; SLIPPED, Moved forward and H7 also read last week's. A deal not in last week's export has no last-week row: Moved forward and SLIPPED do not apply to it, and H7 does not apply.

## 3.1 Stages (this build's proposal; mapped to HubSpot's default stages in the README)

| Stage | Starts when (event only) | Does not count | Required from here |
|---|---|---|---|
| Consultation booked | a consultation with someone at the firm is booked | | owner |
| Qualified | the consultation was held with the person who signs | a consultation only booked | owner, amount, close date |
| Pilot proposed | a pilot scope (which cases, how many, which work) is sent to the firm | a scope only discussed on a call | same |
| Partner said yes | the owner or managing partner said yes to the pilot scope and price | a yes from anyone else | same |
| Order form sent | the order form is sent for signature | an order form only promised | same |
| Won | the order form has both signatures | sent, or signed by one side | same |
| Lost | the firm said no, or the owner closed it | | owner, lost reason |

**Qualified also needs the four checks** (on the page, not given to the AI): the firm does personal injury work; the person who signs was on the consultation; they named a problem the service handles (intake, case management, records, demands, settlement support); they want to start within 90 days.

**Path:** a deal may be created straight into Consultation booked or Qualified; from Qualified onward no stage is skipped; a deal reaches Won only from Order form sent; Lost is allowed from any stage; deals don't move back.

"Qualified or later" means a deal whose stage is Qualified, Pilot proposed, Partner said yes, Order form sent or Won, or a Lost deal with a Date entered Qualified.

## 3.2 Amount

**Amount is the expected yearly value: the monthly case volume the firm named for after the pilot, times the per-case price, times 12. The rep enters it from Qualified on; it is an estimate, not a commitment.** Won is the pilot's order form signed. Growth after the pilot is separate business, left out (one README line). Open value is not weighted. A qualified lost deal with no amount is held out by H2, so Lost value never adds a blank. The page says "a year" once per panel.

## 3.3 The numbers (over deals that pass every check)

| Number | Rule |
|---|---|
| New qualified deals | Date entered Qualified in the week, whatever the deal's stage now; count |
| Moved forward | in last week's export as Qualified or later and open, open now and in a later stage; never also New qualified; each deal once |
| Won | Date entered Won in the week, whatever the deal's stage now (a deal won and then lost in the week counts in Won and in Lost); count and value |
| Lost | qualified deals with Date entered Lost in the week; count and value; losses before Qualified are one line in the drawer |
| Open pipeline | open deals in Qualified through Order form sent at the export; value and count |
| The 12-week chart | for each of the 12 weeks ending at this export (Monday 00:00 to Monday 00:00, the first from Mon 2026-08-31; start included, end excluded), deals with Date entered Qualified in that week, counted with this week's held-out status |
| Held out | every held-out deal in this week's export; count and value (a blank amount counts as zero) |
| The card | the number of deals on the push list; the sum of their amounts; the stage holding the most of them (a tie goes to the later stage) and how many are there; an empty list has no stage |

Conversion by stage and coverage are not on the page (the README defines both).

## 3.4 Held out of the numbers

A held-out deal is out of every number and off the push list; counted plus held out equals the export, in deals and dollars (a test). One reason per deal: the lowest rule number that applies.

| # | Rule | Exact test | Reason line | Fixes it |
|---|---|---|---|---|
| H1 | No owner | owner empty | No owner | sales lead |
| H2 | No amount | Qualified or later, and amount empty or not above zero | No amount | deal owner |
| H3 | No close date | Qualified or later, and close date empty | No close date | deal owner |
| H4 | Close date passed, still open | in Qualified through Order form sent, close date before the export time (Consultation booked deals exempt: HubSpot sets an automatic end-of-month date) | Close date passed, still open | deal owner |
| H5 | A stage skipped | any deal, whatever its stage now, with a Date entered for a stage from Pilot proposed to Won while an earlier stage from Qualified on has none; Lost is never a skip; created straight into Qualified is not a skip | Stage skipped | deal owner |
| H6 | Same firm, two open deals | among open deals, two or more share a firm domain; every one but the oldest by Create date (a blank Create date last; then lowest deal ID) is held out; deals already held out by a lower rule (H1 to H5) don't count toward the group, while a deal held out by a higher rule still does; a firm with no domain forms no group | Same firm as another deal | sales lead |
| H7 | Moved back a stage | in last week's export, and its stage now is earlier in the stage order than last week's; Lost comes after Won in that order, so a deal Won or Lost last week and open now, or Lost last week and Won now, counts as moved back; a deal Lost now is never moved back; a stage outside the seven in either export is left to H15 | Moved back a stage | deal owner |
| H8 | Contact after lost | Lost, and Last contacted is on a later New York calendar date than its close date (Last activity alone and contact after Won are fine) | Contacted after it was lost | deal owner |
| H9 | Lost with no reason | Lost, and closed lost reason empty | Lost with no reason | deal owner |
| H10 | Owner not on the team | owner not in `sample/team.csv` (compared ignoring case and leading or trailing spaces) | Owner not on the team | sales lead |
| H11 | A test record | the firm name or the deal name, ignoring case and leading spaces, starts with `test` (a plain starts-with, so "Testarossa" counts) | Test record | sales lead |
| H12 | No firm | firm ID empty, or not found in `sample/firms.csv` | No firm on the deal | deal owner |
| H13 | Dates out of order | a Date entered before the Create date; Date entered values out of stage order (Lost comes after every other stage); the current stage has no Date entered; or a stage after the current one has a Date entered (equal instants are in order; a blank Create date skips the first check; an unknown stage skips the last two and is left to H15) | Dates out of order | sales lead |
| H14 | Dated after the export | a Create date, any Date entered, Last contacted or Last activity date strictly after the export time, or the close date of a won or lost deal after it (next activity date and an open deal's close date are expected later and not checked) | Dated after the export | sales lead |
| H15 | Unknown stage or pipeline | a stage outside the seven, or a pipeline other than the one new-business pipeline | Unknown stage or pipeline | sales lead |

Practice plants H1 to H8; the scored export also plants deals of rules practice never exercised, drawn privately by the data helper from H9 to H15; the README lists all fourteen as written before the run and says which practice never tested.

## 3.5 Needs a push

From qualified open deals that pass every check. A deal gets every tag it earns. **List order:** most tags first, then the deal's highest tag in this table order, then the longest days in stage, then Create date (oldest first; a blank one last), then the lowest deal ID.

| Tag | Rule |
|---|---|
| OVER LIMIT | days in the current stage over its limit |
| SLIPPED | close date later than in last week's export by 7 or more New York calendar days; only a deal whose stage in last week's export was Qualified through Order form sent can slip (a deal with no last-week row, or no close date there, cannot; nor can one that was Consultation booked last week, whose close date then was HubSpot's automatic end-of-month date) |
| QUIET | Last contacted empty, or days since it over 14 |
| NONE BOOKED | next activity date empty |

**Stage limits:** for each stage from Qualified to Order form sent, the average of whole days (New York calendar dates) between consecutive Date entered values over won practice deals that pass every check and have every stage date from Qualified to Won in order; plus 20%; rounded up, in exact fractions (an average of exactly 5 days gives 6). Computed by `limits.py` from the practice export after the checks of 3.4 exist (step 3), using only won deals that pass every check.

## 3.6 Next steps (one table, in order)

1. The deal's own Next step text, when the notes check settles it as a real action not yet done (writing rule: at most 32 characters, checked by `check_keys.py`).
2. Else the wording for the settled "waiting on" pick.
3. Else the wording for the first tag; for OVER LIMIT and SLIPPED, by stage.

| Source | Wording (each at most 38 characters with "Next: ") |
|---|---|
| waiting on: the signer hasn't seen the scope | Next: send the scope to the partner |
| waiting on: an answer to the firm's question | Next: answer the firm's open question |
| waiting on: the order form not sent yet | Next: send the order form |
| waiting on: the firm to sign | Next: call about the signature |
| waiting on: the firm to reply | Next: call, then one short email |
| waiting on: a date the firm asked for | Next: set a reminder for their date |
| waiting on: nothing (already booked) | the tag's wording below |
| OVER LIMIT or SLIPPED, Qualified | Next: send the pilot scope |
| OVER LIMIT or SLIPPED, Pilot proposed | Next: ask for a yes on the pilot |
| OVER LIMIT or SLIPPED, Partner said yes | Next: send the order form |
| OVER LIMIT or SLIPPED, Order form sent | Next: call about the signature |
| QUIET | Next: reach the firm this week |
| NONE BOOKED | Next: book the next call |

Sales actions only: no fees, referrals, cases, clients or law.
