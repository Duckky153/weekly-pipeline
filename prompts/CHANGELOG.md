# Changes to the notes check's questions

Every change made during the practice rounds, with what practice showed. At most two practice rounds; the bars stayed as planned. Nothing is changed after the lock.

## fp-q2 (as planned), practice round 1, 2026-11-24

47 keyed practice deals, both reads each, $0.0046.

- Next step problems: 18 of 18 found; 1 false flag in 67 clean chances ("Follow up with the pricing sheet" read as a placeholder, 0.28 and 0.29 against the 0.30 line).
- Stage disagreements: 1 of 6 found, 0 false flags. In all five misses both reads picked the keyed stage at 0.71 or more, but the companion question ("do the notes say enough to tell which stage...") answered 0.46 to 0.79, under its 0.80 bar. It answered lower on the deals where the notes disagree with the recorded stage than on the clean ones: it was measuring unease with the contradiction, not whether the notes describe an event.
- "Waiting on": settled 24 of 42 keyed, 1 wrong. Most unsettled picks were right in both reads; the companion question ("what this deal is waiting on before it can move to the next stage") answered under 0.75.

## fp-q2.1, for practice round 2

- `step_specific`: added "Words like \"follow up\" or \"check in\" do not make it a placeholder when it also names what will be sent or done", which is what the labeling rules already say; "No" now reads "only a placeholder".
- `stage_said`: now asks whether the notes describe at least one event from the stage list that has already happened, from the notes alone, with "`stage` may be wrong".
- `waiting_said`: now asks whether the latest note says what has to happen, or who has to act, before the deal can move to its next step.
- Bars, options, picks and settling rules unchanged.

## fp-q2.1, practice round 2, 2026-11-24

47 keyed practice deals, both reads each, $0.0052.

- Next step problems: 18 of 18 found; 0 false flags in 67 clean chances.
- Stage disagreements: 5 of 6 found, 0 false flags. The stage check passes the practice gate (it tags no clean practice deal and finds at least half), so it stays.
- "Waiting on": settled 15 of 42 keyed, 1 wrong. The new companion wording answered lower than the planned one.

## fp-q2.2, the set taken to the lock (no new wording)

Chosen question by question from the two rounds: `step_specific` and `stage_said` as in fp-q2.1; `waiting_said` back to the planned fp-q2 wording (24 of 42 settled in round 1, against 15 in round 2). Written here before it runs: fp-q2.2 is final. It is read once on practice as a check, and nothing changes after that run, whatever it shows.

### The check run of fp-q2.2 on practice, 2026-11-24

$0.0052. Next step problems 18 of 18, stage disagreements 5 of 6 (the miss picked the right stage at 0.71 and 0.76, under 0.80), 0 false flags in 67 clean chances; "waiting on" settled 22 of 42 keyed, 1 wrong ("other" in the key, read as `signature`). Nothing was changed after it.

## The keyword yardstick (baseline.py, no AI)

Written by a fresh helper from `tests/LABELING.md`, the Notes section of `sample/RULES.md`, the stage events and `questions.json`, without seeing any deal, key or answer. It was given the same two practice rounds as counts only (found and false flags by kind, "waiting on" settled and wrong), one revision after each.

| Version | Found | False flags | "Waiting on" settled, wrong |
|---|---|---|---|
| As first written | 23 of 24 | 5 of 67 | 30 of 42, 2 wrong |
| Revision 1 | 22 of 24 | 2 of 67 | 32 of 42, 3 wrong |
| Revision 2 (locked) | 23 of 24 | 2 of 67 | 31 of 42, 2 wrong |
