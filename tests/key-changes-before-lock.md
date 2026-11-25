# Key changes before the lock (scored export)

Every change to `key.json` after it was first written, before the lock, is logged here with the reason and who settled it.

## 2026-11-24

- `key.json` first written by the data helper from the rows and the locked DEFINITIONS.md, with the 15 other-family deals' key entries merged as OpenAI's model wrote them (unchanged except for format). The scored key check passed.
- The label audit (OpenAI's model on 20 of the 45 Claude-family noted deals) left differences in `private/audit-differences.json`. None is settled yet and the key has not been changed for any of them. A separate reader settles each one; every change that follows is logged below.

## Changes

Settled 2026-11-24 by a fresh settler from `tests/LABELING.md` and DEFINITIONS.md section 3.1 (option meanings from section 3.6). One change, nine kept.

- D5249, waiting, "other" -> "signer", disagreed: reader; changed because the latest note says the scope went to Colette, who "will review it with the owner", so the signer has not seen the scope ("waiting on: the signer hasn't seen the scope"), and LABELING.md keeps `other` for "Anything that fits none of the seven". waiting_said stays true, so the entry stays consistent.
- D5065, waiting, "order_form" kept (audit said "other"); the latest note says "The order form still hasn't gone out", which is the `order_form` option ("the order form not sent yet"), and `other` is only for "Anything that fits none of the seven".
- D5077, step, "not_a_step" kept (audit said "real"); "Check in with Vance" names no action, and LABELING.md says `not_a_step` is "a placeholder or a status", while `real` needs an action not yet done.
- D5138, step, "not_a_step" kept (audit said "real"); a bare "Follow up" is a placeholder (`not_a_step`: "a placeholder or a status"), unlike the decoy "a real step that says follow up: Follow up with the revised order form".
- D5140, waiting_said, true kept (audit said false); the latest note says "The order form is being drafted now", which says what the deal is waiting on ("whether the latest note says what the deal is waiting on").
- D5140, waiting, "order_form" kept (audit said null); with waiting_said true the latest note's unsent, still-drafting form is the `order_form` option ("the order form not sent yet").
- D5225, waiting, "signer" kept (audit said "other"); the latest note says "Nothing in writing yet; she wants the written scope first", so the signer has not seen the scope (`signer`: "the signer hasn't seen the scope"), and `other` is only for "Anything that fits none of the seven".
- D5239, step, "not_a_step" kept (audit said "real"); "Circle back next week" names no action, so it is "a placeholder or a status" (`not_a_step`).
- D5284, step, "not_a_step" kept (audit said "real"); "Check in after Thanksgiving" gives a time but no action, so it is "a placeholder or a status" (`not_a_step`); the firm's request is captured by `later_date`.
- D5299, waiting, "nothing" kept (audit said "other"); the consultation with the owner is booked for Nov 25, and the tie rule says "A meeting or call already booked for the next step is `nothing`".
