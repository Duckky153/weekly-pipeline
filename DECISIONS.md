# Decisions

Each choice and why.

## What the page is for

- **Definitions first.** The posting asks for a weekly view with clear definitions and numbers the team can trust, so the definitions sit top left, every number opens to its deals, and a separately written script recounts every number.
- **A push list as the headline, not more charts.** The posting also asks for finding where the funnel is weak and helping reps close. A list of named deals with an owner and a next step is something a sales meeting can act on; a second chart is not.
- **Not counted, not hidden.** A deal with bad data leaves every number with its reason and who fixes it, so a number never quietly includes a deal it shouldn't. Counted plus not counted always equals the export (a test).

## The rules

- **Stages for this kind of company, mapped to HubSpot's defaults.** HubSpot lets stages be renamed; this build keeps one pipeline. The stage words follow a pilot sale to a law firm (a consultation, a pilot scope, the partner's yes, an order form). Each stage starts at an event, not a discussion, because a stage date is only useful if it marks something that happened.
- **Fifteen data rules, one reason per deal (the lowest rule number).** Each comes from a way a HubSpot export goes wrong: fields HubSpot doesn't require, automatic close dates on early stages, deals dragged back a stage, the same firm entered twice, test records. The edge cases (blank cells, two date formats, the same firm under two IDs, a deal lost last week and won now) were settled one by one where the engine and the recount first disagreed, and written into `DEFINITIONS.md` before the lock.
- **SLIPPED only from Qualified on.** A deal leaving Consultation booked gets its first real close date in place of HubSpot's automatic end-of-month date. Counting that as a slip would put nearly every newly qualified deal on the list. Found while the practice sample was written, fixed before the lock.
- **Stage limits from won practice deals, plus 20%.** How long won deals spent in each stage is a limit the team can argue with; a benchmark from elsewhere is not.
- **Calendar days for day counts, exact times for comparisons.** "17 days in stage" should match a calendar, while "before the export" must be exact.
- **Amount as a yearly estimate, unweighted.** HubSpot's weighted amount uses default stage percentages nobody here measured, so the page shows plain open value and says what an amount is.

## The AI step

- **One AI step, fenced off from the numbers.** The notes check can only add tags and change which next-step wording shows. The flip test checks that it can't move a number, the card, a reason or the list.
- **No page text is written by a model.** Every line is fixed wording picked by code, or the rep's own Next step. An earlier plan to let a small local model draft next steps was dropped.
- **Two reads with the choices reversed, bars set before the read.** Models lean toward what comes first; an answer counts only when both orders agree.
- **A stage check kept by its practice gate.** It would have been dropped if it flagged any clean practice deal or found fewer than half the planted disagreements; after the questions were reworded it found 5 of 6 and flagged none.
- **Keyword rules as the yardstick.** The fair comparison for an AI step is plain rules from the same labeling rules, written without seeing any deal. They did as well on the scored notes, and the README says so.

## The look

- **The company's own visual language, never its marks.** Measured from its public pages: the paper and cream tones, the lavender review card, small capital tags, a rust count badge, a 12-week chart with the latest bar in rust. DM Sans is the company's own body font and open-license; the headline serif is an open-license stand-in (Brygada 1918) picked side by side at 32 px. No logo, product screens, interface text or tag words.
- **Changed at design review.** A navy button and grey tags read as a template, so the button took the violet of the company's own buttons and the tags went lavender. The AI's tags went green so they never look like the rules'.
- **One screen.** Measured at 1360 x 765 and 1920 x 1080, the page fits without scrolling even with every row padded to its longest allowed text (`tests/fit_mock.py`), at under 300 words.

## Left out

Forecasts, weighting, coverage, conversion by stage, rankings of reps, any connection to a real CRM, and drafting text with a model.
