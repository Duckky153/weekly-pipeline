"""Keyword yardstick for the Finch notes check: plain rules, no AI, Python stdlib only.

Written from tests/LABELING.md, the Notes part of sample/RULES.md, DEFINITIONS.md 3.1 and questions.json alone, without
seeing any deal, note or answer key. Revisions use practice counts only (how many found and wrongly flagged), never deals.
"""
import re

STAGES = ["Consultation booked", "Qualified", "Pilot proposed", "Partner said yes", "Order form sent", "Won", "Lost"]
DAY = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tues?|wed|thu(rs?)?|fri|sat|sun)"
MONTHS = r"(january|february|march|april|may|june|july|august|september|october|november|december)"
NEG = r"\b(not|never|yet to|no longer)\b|n't\b"
PLAN = (r"\b(will|going to|plan(s|ning)? to|promised|wants?|hopes?|needs? to|should|would|could|trying to|asked|asking|"
        r"requested|once|if|until|being)\b|'ll\b|'d\b|\bto( be| have| get)?\s*$")   # an ask or a plan, not a deed
# ---- Next step ---------------------------------------------------------------------------------------------------------
VERBS = (r"\b(send|resend|email|e-mail|call|phone|ring|text|book|schedule|set up|meet|demo|draft|share|present|walk|review|"
         r"go over|confirm|introduce|intro|ask|invite|get|sign|countersign|prepare|prep|revise|update|finali[sz]e|deliver|"
         r"forward|write|run|show|quote|kick off|start|visit)\b")
PLACEHOLDER = (r"\b(follow[- ]?ups?|check[- ]?ins?|touch(ing)? base|circle back|keep (it |them )?warm|reach out|ping|nudge|"
               r"chase|tbd|tbc|stay in touch|next steps?)\b( (by |via )?(email|call|note|text))?")
STATUS = (r"\b(waiting|awaiting|pending|on hold|stalled|under review|in review|out for signature|with (their|the|her|his) "
          r"(managing )?partners?|partners? reviewing)\b|^[^,;]*\b(sent|signed|received|done)\b")
OBJ = (r"(order form|scope|pilot|proposal|pricing|price|quote|contract|agreement|deck|case study|references?|numbers|"
       r"answers?|summary|recap|agenda|invoice|timeline|paperwork|samples?|terms)")
OBJWORDS = set(re.findall(r"[a-z]{3,}", OBJ))
FILLER = set("with w on re about the a an to and for of s his her their our new revised updated again in at by next this "
             "week weeks month today tomorrow tmrw eow eod asap am pm morning afternoon after before end".split())
FAMILIES = [  # step verbs -> the words a note uses once that action is done (the first is the "send" family)
    (r"send|resend|share|email|e-mail|forward|deliver|draft|prepare|prep|revise|update|write|finali[sz]e",
     r"sent|resent|emailed|shared|forwarded|delivered|went out|is out|signed"),
    (r"call|phone|ring|text", r"called|spoke|talked|texted|caught|had (the|a|our) call|call (went|was held)"),
    (r"meet|demo|present|walk|review|go over|show|run|visit",
     r"met|demoed|presented|walked|reviewed|went over|showed|ran|visited|had (the|a|our) (meeting|demo|review)"),
    (r"book|schedule|set up", r"booked|scheduled|set up|on the calendar"), (r"confirm", r"confirmed"),
    (r"introduce|intro", r"introduced"), (r"ask", r"asked"), (r"invite", r"invited"), (r"get", r"got|received"),
    (r"sign|countersign", r"signed|countersigned"), (r"quote", r"quoted"), (r"kick off|start", r"kicked off|started")]
CALLED_OFF = r"\b(cancel+ed|called off|calling off|scrapped|dropped|no longer (need|needed|happening)|not needed|off the table)\b"
RESCHEDULED = r"\b(re-?schedul\w*|rebook\w*|moved|pushed|postponed)\b"
# ---- Stage events (DEFINITIONS 3.1, event lines only) ------------------------------------------------------------------
CON = r"\b(consult(ation)?|intro call|first call|first meeting|discovery call)\b"
EVENTS = [
    ("Consultation booked", r"\b(booked|scheduled|set up|confirmed|locked in)\b[^.;]{0,25}" + CON + "|" + CON
     + r"[^.;]{0,20}\b(booked|scheduled|set|confirmed|on the calendar)\b"),
    ("Qualified", r"\b(had|held|did|ran|finished|wrapped)\b[^.;]{0,20}" + CON + "|" + CON
     + r"[^.;]{0,20}\b(went|was held|happened|is done)\b"),
    ("Pilot proposed", r"\b(sent|resent|emailed|shared|forwarded)\b[^.;]{0,30}\b(scope|pilot (plan|proposal|outline))\b"
     r"|\b(scope|pilot (plan|proposal))\b[^.;]{0,20}\b(sent|went out|is out|emailed)\b"),
    ("Partner said yes", r"\b(said yes|says yes|approved|signed off|agreed|okayed|ok'd|green-?lit|accepted|on board)\b[^.;]{0,30}"
     r"\b(scope|pilot|price|pricing|terms|proposal)\b|\b(scope|pilot|price|pricing|proposal)\b[^.;]{0,25}\b(approved|"
     r"signed off|accepted)\b|\bsaid yes\b(?! to (a|the|another) (call|meeting|demo|consult))"),
    ("Order form sent", r"\b(sent|resent|emailed|issued|signed)\b(?! off)[^.;]{0,30}\border form\b"
     r"|\border form\b[^.;]{0,25}\b(sent|went out|is out|out for signature|signed)\b(?! off)"),
    ("Won", r"\b(countersigned|both signed|fully signed|fully executed|signed by both|both signatures|closed won)\b"),
    ("Lost", r"\b(said no|says no|turned (us|it) down|passed on|(went|going) with (another|a different|someone else|a competitor)"
     r"|decided against|not moving forward|not interested|closing (it|this) out|closed (it|this) (out|lost)|marked (it )?lost)\b")]
ROLES = r"managing partner|founding partner|name partner|senior partner|owner|principal|MP|signer"
SIGNER_ROLE = r"\b(" + ROLES.lower() + r"|who signs|decision[- ]maker)\b"
OTHER_ROLE = (r"\b(associate|junior partner|paralegal|office manager|intake|case manager|assistant|coordinator|administrator|"
              r"operations|ops|marketing)\b")
ABSENT = r"\b(without|wasn't|was not|missed|couldn't make|no-?show)\b"
# ---- Waiting on (latest note only); the order carries LABELING.md's tie rules ------------------------------------------
MEET = r"\b(call|meeting|demo|review|walkthrough|session|consult(ation)?|sit-?down|visit)\b"
WAITING = {
    "quiet": r"\b(stopped (answering|replying|responding)|(gone|went) (quiet|dark|silent)|no (reply|response|answer|word|"
        r"callback)|not (replying|answering|responding)|(hasn't|haven't|has not|have not) (replied|answered|responded|heard|"
        r"gotten back|called back)|ghost(ed|ing)?|(two|three|several|\d) (voicemails|emails|messages|tries)|left (a |another "
        r")?(voicemail|message)|(can't|couldn't) reach|nothing back|not heard back|heard nothing|chased (twice|again))\b",
    "later_date": r"\b(asked|wants?|told (us|me)|said)\b[^.;]{0,25}\b(come back|circle back|reconnect|check back|revisit|talk "
        r"again|try again|follow up|hold off|wait|call back|reach out)\b[^.;]{0,30}\b((after|until|till|past|in|on) )?(" + MONTHS
        + "|" + DAY + r"|q[1-4]|new year|holidays|tax season|next (week|month|quarter|year)|the (first|end|new year|holidays)|"
        r"\w+ (weeks|months))\b|\b(not until|until after|nothing until|hold off until)\b",   # a date, not "once" or "after X"
    "nothing": MEET + r"[^.;]{0,25}\b(booked|scheduled|set|confirmed|locked in|on the calendar|on the books)\b|\b(booked|"
        r"scheduled|set up|confirmed|locked in)\b[^.;]{0,30}" + MEET + r"|\b((calendar )?invite (sent|accepted)|accepted "
        r"the invite|on (the|his|her|their|our) calendar)\b",
    "signature": r"\b(signature|signing(?! off)|docusign)\b|\b(to|will|'ll|ready to|going to) sign\b(?! off)|\bsign (it|the "
        r"order form|once|when|after|by|this|next|" + DAY + r")\b|\b(has|have|got|received|reviewing|looking over) the order "
        r"form\b|\border form\b[^.;]{0,25}\b(with (him|her|them)|unsigned|not (yet )?signed|back|returned)\b",   # not "sign off"
    "signer": r"\b(hasn't|has not|haven't|not yet|yet to|never)\b[^.;]{0,15}\b(seen|reviewed|looked at|read)\b[^.;]{0,25}\b(scope|"
        r"pilot|proposal|it)\b|\b(take|taking|bring|bringing|show|showing|pass|passing|run|running|forward|forwarding|share|"
        r"sharing) (it|the scope|this|the pilot( scope)?)\b[^.;]{0,15}\b(to|by|past|in front of) (the |her |his |their )?"
        r"(managing |founding |name |senior )?(partners?|owner|boss|signer)\b|\b(with|waiting on|waiting for) (the|her|his|"
        r"their) (managing |founding |name )?(partners?|owner)\b|\b(partner|owner)('s)? (review|sign-?off|approval|eyes)\b",
    "question": r"\b((?<!no )questions?|asked (about|how|whether|if|what|why|when|who)|asking (about|how|whether|if|what)|"
        r"wants? to know|wanted to know|wondering|needs? to know|waiting on (our|an|my) (answer|reply|numbers)|owe \w+ (an? )?"
        r"(answer|answers|reply)|(wants|needs|asked for) (more )?(detail|details|clarity|a breakdown|references|examples)|"
        r"concern(ed|s)? about|worried about|pushback|unclear)\b",
    "order_form": r"\border form\b[^.;]{0,30}\b(not (yet )?(sent|out)|hasn't (gone|been sent)|yet to|next|to follow|coming|"
        r"goes out|going out|will go|being (drafted|sent|prepared)|drafted)\b|(\b(send|sending|draft|drafting|prepare|preparing|"
        r"owe (him|her|them)|asked for|wants|ready for|promised)\b|(n't|\bnot) (yet )?sent\b)[^.;]{0,20}\border form\b"}
AGAIN = r"\b(again|resend|re-send|resent|another copy|new copy)\b"   # "will sign once it is sent again" stays signature
PENDING = r"\b(hasn't|has not|not yet|yet to|still needs to)\b[^.;]{0,20}\b(say yes|said yes|approved?|sign(ed)? off|weighed in)\b"
DENY = {  # words saying the recorded stage's own event has not happened (3.1's "does not count")
    "Qualified": r"\b(only|just) booked\b|" + CON + r"[^.;]{0,20}(\b(booked|set|scheduled) for\b|" + RESCHEDULED
        + r"|\b(tomorrow|next week)\b)|" + RESCHEDULED + r"[^.;]{0,20}" + CON + "|" + CON + r"[^.;]{0,40}" + ABSENT,
    "Pilot proposed": r"\b(discussed|talked through|talked about|went over|walked through|covered|working on|putting together|"
        r"drafting|writing|preparing)\b[^.;]{0,30}\bscope\b|\bscope\b[^.;]{0,25}\b(to follow|next|coming|not (yet )?sent|being "
        r"drafted|in progress)\b|(n't|\bnot) (yet )?sent[^.;]{0,15}\bscope\b",
    "Partner said yes": OTHER_ROLE + r"[^.;]{0,40}\b(said yes|approved|agreed|signed off)\b|" + PENDING + "|" + WAITING["signer"],
    "Order form sent": WAITING["order_form"]}

def body(note):
    """Drop a leading date and 'Name:' so only the note's words remain."""
    return re.sub(r"^\s*(\[?[\d/-]+\]?[\s:,-]*)?([A-Z][a-z]+( [A-Z][a-z]+)?:\s*)?", "", note or "").strip()

def said(pattern, text, inner=True, near=None):
    """A non-question clause states it as done (not negated, asked for or planned), naming a `near` word if given."""
    for sent in [x for x in re.findall(r"[^.;!?]+[.;!?]*", text.lower()) if not x.strip().endswith("?")]:
        for clause in re.split(r",|\bbut\b|\bthough\b|\bwhile\b", sent):
            for m in re.finditer(pattern, clause):
                if re.search(NEG + "|" + PLAN, clause[:m.start()]) or (inner and re.search(NEG, m.group())):
                    continue
                if near is None or any(re.search(r"\b%s\b" % re.escape(w), clause) for w in near):
                    return True
    return False

def step_kind(step):
    """none / not_a_step / real / unsure, from the Next step text alone."""
    s = step.strip().lower()
    if not s:
        return "none"
    if not re.match(r"(\w+ to )?" + VERBS, s) and re.search(STATUS, s):
        return "not_a_step"
    rest = re.sub(PLACEHOLDER, " ", s)
    if re.search(VERBS, rest) or (rest != s and re.search(r"\bwith (the |a |an |our |new |revised |updated )*" + OBJ, rest)):
        return "real"                               # an action, or "follow up with the revised order form"
    if rest == s or re.search(r"\b" + OBJ + r"\b", rest):
        return "unsure"                             # no known words, or "follow up on scope": a topic, not an action
    names = {w.lower() for w in re.findall(r"\b[A-Z][a-z]+\b", step)}
    left = [w for w in re.findall(r"[a-z]+", rest) if w not in FILLER | names and not re.fullmatch(DAY + "|" + MONTHS, w)]
    return "unsure" if left else "not_a_step"       # only a placeholder, a name and a time

def step_done(step, note):
    """The latest note says the step was done or called off, in a clause naming the step's thing or person."""
    keys = [w for w in re.findall(r"[a-z]{3,}", step.lower()) if w not in FILLER and not re.fullmatch(DAY, w)]
    names = {w for w in map(str.lower, re.findall(r"\b[A-Z][a-z]+\b", step)) if w not in OBJWORDS and not re.fullmatch(VERBS, w)}
    things = [w for w in keys if w in OBJWORDS] or [w for w in keys if w in names]
    acts = [w for w in keys if w not in names] + ["it"]
    if not re.search(RESCHEDULED, note.lower()) and said(CALLED_OFF, note, False, acts):
        return True                                 # "cancelled the demo" calls off "Demo Thursday"
    quiet = re.search(WAITING["quiet"], note.lower())   # a call or meeting that reached no one was not done
    for i, (verbs, done_words) in enumerate(FAMILIES):
        near = things + ["it"] if i == 0 else [] if quiet and i < 3 else keys + ["it", "him", "her", "them"]
        if re.search(r"\b(" + verbs + r")\b", step.lower()) and said(r"\b(" + done_words + r")\b", note, near=near):
            return True
    return said(r"\b(done|finished|completed|took care of|handled)\b", note, near=keys or None)

def notes_stage(notes, everything):
    """Index of the latest stage whose starting event the notes say has happened, or None."""
    names = re.findall(r"\b([A-Z][a-z]+)(?:, (?:who is )?(?:the |their )?| is (?:the |their )?| \()(?:" + ROLES + ")",
                       everything) + re.findall(r"\b([A-Z][a-z]+) (?:signs|is the one who signs)\b", everything)
    best = None
    for sent in re.findall(r"[^.;!?]+[.;!?]*", " ".join(n for n in notes if n)):
        low = sent.lower()
        signer_here = re.search(SIGNER_ROLE, low) or any(re.search(r"\b%s\b" % n.lower(), low) for n in names)
        for i, (stage, pattern) in enumerate(EVENTS):
            if not said(pattern, sent, inner=(stage != "Lost")):
                continue
            if stage == "Qualified" and (not signer_here or re.search(ABSENT, low)):
                i = 0                               # held without the signer still shows it was booked
            if stage == "Partner said yes" and (re.search(PENDING, notes[-1].lower()) or re.search(OTHER_ROLE, low)
                                                and (not signer_here or re.search(NEG, low))):
                continue                            # a yes from anyone else does not count
            best = i if best is None else max(best, i)
    return best

def settle(stage, next_step, latest_note, earlier_notes):
    """stage: the deal's recorded stage name; next_step: its Next step text ('' if none);
    latest_note and earlier_notes: strings like 'Nora: words' ('' if none; earlier_notes may hold up to two lines).
    Returns {"step": "real"|"not_a_step"|"done"|"unsure"|"none", "stage_from_notes": <stage name or None>,
             "waiting": <one of signer, question, order_form, signature, quiet, later_date, nothing, or None>}"""
    latest = body(latest_note)
    notes = [body(line) for line in (earlier_notes or "").splitlines() if line.strip()] + [latest]
    step = step_kind(next_step or "")
    step = "done" if step == "real" and latest and step_done(next_step, latest) else step
    low, waiting = latest.lower(), None
    for name, pattern in WAITING.items() if latest else []:
        hit = said(pattern, latest) if name == "nothing" else re.search(pattern, low)
        if hit and not (name == "signature" and re.search(WAITING["order_form"], low) and not re.search(AGAIN, low)):
            waiting = name                          # "ready to sign" before any order form went out is order_form
            break
    found, in_latest = (notes_stage(n, " ".join(notes)) for n in (notes, [latest]))
    found = max(found or 0, 4) if waiting == "signature" else found   # the firm already has an order form to sign
    rec, result = (STAGES.index(stage) if stage in STAGES else None), None   # older history alone is no disagreement
    if rec is None or (found is not None and found > rec):
        result = found                              # the notes show a later event than the recorded stage
    elif stage in DENY and re.search(DENY[stage], " ".join(notes).lower()):
        result = max(found or 0, rec - 1)           # the notes say the recorded stage's event has not happened
    elif found is not None and found < rec and in_latest == found:
        result = found                              # the latest note itself describes only an earlier event
    return {"step": step, "stage_from_notes": None if result is None or result == rec else STAGES[result], "waiting": waiting}

if __name__ == "__main__":
    examples = [  # made up from the rules, not from any data
        ("Pilot proposed", "Send order form", "Ravi: Sent Priya the order form; she will sign.", "Ravi: Priya (owner) said yes."),
        ("Qualified", "Check in next week", "Ravi: Left two voicemails for Tom, no reply since the consult.", ""),
        ("Consultation booked", "Call Tom re scope", "Ravi: Held the consult with Tom (owner); he asked about billing.", ""),
        ("Order form sent", "Follow up with revised order form", "Ravi: Tom asked us to come back after tax season.", ""),
        ("Partner said yes", "", "Ravi: Demo with Priya booked for Tuesday.", "Ravi: Priya (owner) said yes to the pilot.")]
    for ex in examples:
        print(ex[0], "|", ex[1] or "(no step)", "->", settle(*ex))
