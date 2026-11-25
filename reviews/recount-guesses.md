# recount.py: where the written rules leave something open

`recount.py` was written from `PLAN.md` section 3 (and section 2's card) and `sample/RULES.md` only. The engine and the page code were not opened. Where the rules left a choice open, the script takes the most literal reading and marks the spot `GUESS n`. Each entry below quotes the rule, says what was unclear and says what the script does. If the engine disagrees with the recount on one of these points, settle the rule first. Don't just change one side to match the other.

## Reading the files

**1. Blank cells and spaces.** RULES.md: "empty means blank." H10 says to compare "ignoring case and leading or trailing spaces", and H11 says "ignoring … leading spaces", but no other rule mentions spaces.
*Unclear:* whether a cell holding only spaces is blank, and whether IDs, stage and pipeline are trimmed.
*Chosen:* every cell is trimmed of surrounding spaces before use. A cell that holds only spaces is blank. Deal IDs, firm IDs, stage, pipeline and owner are compared after trimming.

**2. Date formats.** RULES.md: "Dates as `YYYY-MM-DD HH:MM` in New York time."
*Unclear:* what to do with a close date written as a bare date, a time with seconds, or a date that can't be read at all.
*Chosen:* the script reads `YYYY-MM-DD HH:MM`, and also seconds, a `T` separator, and a bare date (read as 00:00). A non-empty date in any other form stops the recount with an error naming the deal and the column. The script does not guess at such a date or treat it as blank. The next activity date is never parsed, because only its emptiness is used (NONE BOOKED) and H14 says it is "not checked".

**3. A New York time that happens twice.** 3.0: "every comparison of two dates compares instants."
*Unclear:* on 2026-11-01 the clocks go back, so the wall times 01:00 to 01:59 happen twice and the file can't say which one is meant.
*Chosen:* the first one (daylight time).

**4. Amounts that are not plain numbers.** H2: "amount empty or not above zero". 3.3 Held out: "a blank amount counts as zero".
*Unclear:* what to do with an amount like `$96,000`, with one that can't be read, and with a negative amount in a dollar sum.
*Chosen:* `$` and `,` are dropped before reading. An amount that still can't be read counts as no amount: H2 holds the deal out if it is Qualified or later, and the amount counts as zero in any sum. A negative amount is summed as written, so the held-out value can go down, which keeps "counted plus held out equals the export, in dollars" true.

## Held-out rules

**5. H4, "the export date".** "close date before the export date". H14, by contrast, says "the export time".
*Unclear:* whether this means the date or the instant.
*Chosen:* the close-date instant is compared with the export instant, Mon 2026-11-23 00:00. Because the export is at midnight, this gives the same result as "calendar date on or before Nov 22". A close date of exactly 2026-11-23 00:00 has not passed.

**6. What "open" means.** The rules use "open" (H4, H6, Moved forward, push) without defining it.
*Unclear:* whether a deal with a stage outside the seven counts as open.
*Chosen:* open means one of the five stages from Consultation booked to Order form sent. A deal with an unknown stage is neither open nor closed and is not "Qualified or later", so only the rules that don't depend on stage can catch it before H15 (H1, H10, H11, H12, H13's first two parts, H14).

**7. H5, which deals it looks at.** "a Date entered for a stage from Pilot proposed to Won while an earlier stage from Qualified on has none; Lost is never a skip; created straight into Qualified is not a skip".
*Unclear:* whether the test depends on the current stage, and how "Lost is never a skip" applies.
*Chosen:* the test looks only at the Date entered fields, whatever the stage is now, Lost deals included. A Lost date never triggers it, and a missing Consultation booked date never counts as a skip. A deal whose current stage has no date but has no later dates either is left to H13.

**8. H6, how the group is formed.** "among open deals, two or more share a firm domain; every one but the oldest by Create date (then lowest deal ID) is held out; deals already held out by a lower rule don't count toward the group".
*Unclear:* (a) whether Consultation booked deals are in the group; (b) whether an empty domain is shared; (c) whether domains are compared ignoring case; (d) whether deals that a higher rule (H7 to H15) would hold out count toward the group; (e) where a blank Create date sorts.
*Chosen:* (a) Yes, because Consultation booked is open. (b) No: a blank domain, or a firm ID not found in `firms.csv`, puts the deal in no group. (c) No: domains are compared exactly as written, after trimming. (d) Yes: only H1 to H5 remove a deal from the group, so a test record that is older than a real deal makes the real deal H6. (e) Last, so a deal without a Create date is never "the oldest". The push-list order uses the same placement (entry 24).

**9. "Lowest deal ID".** Used in H6 and in the push-list order.
*Unclear:* whether IDs compare as numbers or as text ("9" against "10").
*Chosen:* IDs made only of digits compare as numbers, and any other ID compares as text. IDs made of digits sort before any other ID.

**10. H7, Lost last week and Won now.** "its stage now is earlier in the stage order than last week's; a deal Won or Lost last week and open now counts as moved back; a deal Lost now is never moved back".
*Unclear:* the rule does not cover a deal that was Lost last week and is Won now. It also does not cover a stage outside the seven in either week.
*Chosen:* the stage order as written, with Lost after Won (H13: "Lost comes after every other stage"). Lost last week and Won now is therefore "earlier" and is held out by H7. If either week's stage is outside the seven, H7 does not apply.

**11. H8, "a later day".** "Last contacted is a later day than its close date". But 3.0 says "every comparison of two dates compares instants … only day counts use calendar dates".
*Unclear:* instants or calendar days.
*Chosen:* New York calendar dates, because the rule says "day". A contact later on the same day as the close date is fine. If either date is blank, H8 does not apply.

**12. Which column of team.csv holds the name.** 3.0: "`sample/team.csv` (the four owners: full name, role)". RULES.md gives no column names for this file.
*Unclear:* the header.
*Chosen:* the first of `full_name`, `full name`, `name` or `owner` that appears in the header, otherwise the first column. Names are compared lower-cased and trimmed.

**13. H11, "starts with test".** "the firm name or the deal name, ignoring case and leading spaces, starts with `test`".
*Unclear:* whether a name like "Testa Partners" counts, and whose firm name is meant when the firm is missing.
*Chosen:* it counts: the check is a plain "starts with" with no word boundary. The firm name comes from `firms.csv` through the deal's firm ID. When the firm isn't found, only the deal name is checked, and H12 then applies if nothing lower does.

**14. H13 when the Create date is blank or the stage is unknown.** "a Date entered before the Create date … the current stage has no Date entered; or a stage after the current one has a Date entered".
*Unclear:* what to do when there is nothing to compare with.
*Chosen:* with a blank Create date the first part does not apply; no rule holds a deal out for a blank Create date alone. With a stage outside the seven, the "current stage" parts do not apply, and H15 catches the deal. "Out of stage order" is checked across all filled Date entered values in stage order, with Lost last. Equal instants are in order.

**15. H14, "after".** "a Create date, any Date entered, Last contacted or Last activity date after the export time, or the close date of a won or lost deal after it".
*Unclear:* whether a time exactly at the export counts.
*Chosen:* only strictly later instants count, so 2026-11-23 00:00 itself is fine. "Won or lost" means the stage now.

**16. H15, exact names.** "a stage outside the seven, or a pipeline other than the one new-business pipeline".
*Unclear:* case and spelling.
*Chosen:* exact text after trimming. Stage must be one of the seven names in 3.1 as written, and pipeline must be `New business` (RULES.md). "qualified" in lower case is an unknown stage.

## Numbers

**17. Moved forward.** "in last week's export as Qualified or later and open, open now and in a later stage; never also New qualified; each deal once".
*Unclear:* how "Qualified or later" is judged on last week's row, and whether last week's row must itself pass the checks.
*Chosen:* last week's stage must be Qualified, Pilot proposed, Partner said yes or Order form sent. Of the definition's two cases only these are open, and the "Lost with a Date entered Qualified" case can't be open. Held-out status comes only from this week's export (3.0: "every rule reads this week's export"). A later stage means a later position in the 3.1 order.

**18. Lost and losses before Qualified.** "qualified deals with Date entered Lost in the week; count and value; losses before Qualified are one line in the drawer".
*Unclear:* what "qualified deals" means here, and what the drawer line counts.
*Chosen:* "qualified" uses 3.1's "Qualified or later": a Lost deal with a Date entered Qualified. `lost_before_qualified` counts deals that pass every check, have a Date entered Lost in the week and have no Date entered Qualified.

**19. Won and New qualified, whatever the stage now.** "Date entered Won in the week" and "Date entered Qualified in the week".
*Unclear:* whether the stage now must still be Won or Qualified-or-later.
*Chosen:* no stage condition. Any deal that passes every check and has the date in the week counts. So a deal that entered Qualified on Tuesday and was Lost on Friday is one New qualified and, if qualified, one Lost.

**20. The 12-week chart.** "for each of the 12 weeks ending at this export, deals with Date entered Qualified in that week, counted with this week's held-out status".
*Unclear:* where the week boundaries fall, and which deals are looked at.
*Chosen:* the weeks run Monday 00:00 to Monday 00:00 New York time, going back from 2026-11-23, with the oldest first, so the first week starts 2026-08-31 and the last bar is the week. Only deals in this week's export are counted, minus those held out now.

**21. The card when the push list is empty.** "the stage holding the most of them (a tie goes to the later stage) and how many are there".
*Unclear:* the empty case.
*Chosen:* `stage` is `null` and `stage_count` is 0. Only the four push stages (Qualified to Order form sent) can hold push deals.

## Push list

**22. SLIPPED, "by 7 days or more".** "close date later than in last week's export by 7 days or more".
*Unclear:* calendar days or 7 × 24 hours between the two instants.
*Chosen:* calendar days (this week's close date minus last week's, New York dates), because 3.0 says day counts use calendar dates.

**23. List order, "the higher rule".** "most tags first, then the higher rule in this table order, then the longest days in stage, then Create date, then deal ID".
*Unclear:* when two deals have the same number of tags, whether to compare only each deal's highest tag or their whole tag lists, tag by tag.
*Chosen:* only the highest tag each deal has, because the rule says "the higher rule", in the singular. For example, {OVER LIMIT, QUIET} and {OVER LIMIT, SLIPPED} tie at this step and go on to days in stage.

**24. List order, "then Create date".**
*Unclear:* the direction.
*Chosen:* oldest first, matching H6's "oldest by Create date". A blank Create date sorts last.

## Stage limits

**25. "Whole days between consecutive Date entered values".** 3.5: "the average of whole days between consecutive Date entered values … plus 20%; rounded up".
*Unclear:* (a) calendar-date difference or whole 24-hour periods; (b) how exactly the 20% is added.
*Chosen:* (a) the New York calendar-date difference, the same as every other day count in 3.0. For example, 09-01 23:59 to 09-07 00:01 is 6 days, not 5. (b) Exact fractions: limit = ceiling(average × 6/5). An average of exactly 5 gives 6. Floating-point math gives 6.000000000000001 and rounds up to 7, so this case is worth checking in the engine.

**26. Which deals feed the limits.** "over won practice deals that pass every check and have every stage date from Qualified to Won in order".
*Unclear:* what "won" means, and which files the checks use.
*Chosen:* deals whose stage is Won in the practice `deals-this-week.csv`. The checks run on the practice folder with its own `deals-last-week.csv` and `firms.csv`, and the shared `sample/team.csv`. If no deal qualifies for a stage, the limit is `null`. Without `--limits`, the recount then stops instead of inventing one.

**27. Where the limits come from in a run.** The brief: `[--limits limits.json]`, optional.
*Unclear:* the default.
*Chosen:* `--limits FILE` reads `{"Qualified": n, "Pilot proposed": n, "Partner said yes": n, "Order form sent": n}`, keyed by the exact stage names. Without it, the limits are recounted from `--practice` (default `sample/practice`) by entry 25's rule. The default `--team` is `sample/team.csv` beside `recount.py`.

## What is not recounted, and the output

**28. The notes check and next steps.** 3.6 steps 1 and 2 depend on the notes check ("when the notes check settles it…", "the settled 'waiting on' pick"). The tags STEP DONE, NOT A STEP and CHECK STAGE come from that check too. The brief says `notes.csv` is ignored.
*Unclear:* how much of 3.6 a notes-free recount can check.
*Chosen:* the notes tags and steps 1 and 2 are not recounted. The output adds `next_step_from_first_tag`: step 3's wording (the first tag; by stage for OVER LIMIT and SLIPPED) for every push deal. It matches the page only where neither notes step applied.

**29. Output form.** The brief asks for `{deal_id: rule}`.
*Unclear:* rule number or reason line.
*Chosen:* the rule number, `"H1"` to `"H15"`. The reason lines are in `HELD_OUT_REASON_LINES` in the script. Money is in whole dollars (an int when whole). Tags are listed in table order. Two extra top-level keys are added for the reviewer: `limits` (the limits used) and `next_step_from_first_tag`.

**30. The export dates for every folder.** 3.0 and RULES.md give this week's export as Mon 2026-11-23 00:00 and last week's as Mon 2026-11-16 00:00.
*Unclear:* whether the practice and scored folders could carry other dates.
*Chosen:* both dates are fixed constants for every folder, as RULES.md describes each export.

**31. A deal ID that appears twice in one file.** The rules assume one row per deal ("A deal in last week's file keeps its `deal_id`").
*Unclear:* what to do when an ID repeats.
*Chosen:* the recount stops with an error naming the ID instead of picking a row.

**Update 2026-11-24, after section 3 was clarified.** Section 3 now settles 1, 2, 3, 4 and 31 (3.0 "Reading the cells": cells are trimmed and a cell of only spaces is empty; dates are read as `YYYY-MM-DD HH:MM`, also with seconds, a `T` or a bare date, and an unreadable date stops the run with the deal named, so the next activity date and every date in last week's export are now read as well; the repeated hour of 2026-11-01 is its first occurrence; an amount drops `$` and `,`, and an unreadable one counts as no amount; a deal ID that appears twice in one export stops the run); 6 (3.0 "Open": the five stages from Consultation booked to Order form sent); 8c and 16 (3.0: stage, pipeline and firm domain compared as exact text after trimming); 9 (3.0: whole-number IDs compare as numbers, others as text; sorting whole numbers before text is still the guess); 12 (3.0: team.csv has the columns `full_name, role`, and `full_name` is now required); 17 in part (3.0 "Open" with 3.1: last week's stage must be Qualified through Order form sent; not putting last week's row through the checks is still the guess); 5, 7, 8a, 8b, 8d, 10, 11, 13, 14 and 15 (3.4: H4 uses the export time; H5 looks at any deal whatever its stage now; in H6 only H1 to H5 take a deal out of the group, a deal held out by a higher rule still counts, and a firm with no domain forms no group; H7 puts Lost after Won and leaves a stage outside the seven to H15; H8 compares New York calendar dates; H11 is a plain starts-with; H13 skips the Create date check when it is blank and the current-stage checks for an unknown stage; H14 means strictly after); 19, 20 and 21 (3.3: New qualified and Won count whatever the stage now; the chart's weeks run Monday 00:00 to Monday 00:00 from Mon 2026-08-31; an empty push list has no stage); 22, 23, 24 and 25 (3.5: SLIPPED counts New York calendar days, and only a deal whose stage in last week's export was Qualified through Order form sent can slip, so a deal that was Consultation booked last week cannot; the list order uses each deal's highest tag, then Create date oldest first with a blank one last; the limits use New York calendar dates and exact fractions). Still open: 8e (where a blank Create date sorts in H6), 18, 26, 27, 28, 29 and 30.
