#!/usr/bin/env python3
"""recount.py: an independent recount of the Weekly Pipeline page.

Written from PLAN.md section 3 (and section 2's card) and sample/RULES.md only.
It does not read or import the engine or any page code, so the page's own
numbers can be checked against it.

Usage:
  python3 recount.py <export folder> [--team sample/team.csv] [--limits limits.json]
  python3 recount.py <practice folder> --print-limits

The export folder holds deals-this-week.csv, deals-last-week.csv and firms.csv
(notes.csv is ignored). Without --limits, the four stage limits are recounted
from --practice (default sample/practice) by section 3.5's rule.

Places where section 3 leaves something open are listed, with the choice made,
in reviews/recount-guesses.md; the code marks each one "GUESS n". Where section 3
has since settled one, the mark reads "settled in 3.x" instead.

Python 3.9+ standard library only.
"""

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
NEW_YORK = ZoneInfo("America/New_York")


class ExportError(Exception):
    """A file cannot be read as section 3 and RULES.md describe it."""


# --------------------------------------------------------------------------
# 3.1 Stages
# --------------------------------------------------------------------------

# The stage order. Lost comes after every other stage (H13).
STAGES = [
    "Consultation booked",
    "Qualified",
    "Pilot proposed",
    "Partner said yes",
    "Order form sent",
    "Won",
    "Lost",
]

ENTERED_COLUMN = {
    "Consultation booked": "entered_consultation_booked",
    "Qualified": "entered_qualified",
    "Pilot proposed": "entered_pilot_proposed",
    "Partner said yes": "entered_partner_said_yes",
    "Order form sent": "entered_order_form_sent",
    "Won": "entered_won",
    "Lost": "entered_lost",
}

OPEN_STAGES = STAGES[0:5]              # Consultation booked .. Order form sent (settled in 3.0)
QUALIFIED_TO_ORDER_FORM = STAGES[1:5]  # Qualified .. Order form sent
PIPELINE = "New business"              # H15: the one new-business pipeline

# RULES.md column names.
DEAL_COLUMNS = [
    "deal_id", "deal_name", "stage", "pipeline", "amount", "close_date", "owner",
    "create_date", "last_contacted", "last_activity_date", "next_activity_date",
    "next_step", "closed_lost_reason", "firm_id",
] + [ENTERED_COLUMN[stage] for stage in STAGES]
LAST_WEEK_COLUMNS = ["deal_id", "stage", "close_date"]  # all that the rules use from last week
# Every date cell; an unreadable one stops the run, in either export (settled in 3.0).
DATE_COLUMNS = [
    "close_date", "create_date", "last_contacted", "last_activity_date", "next_activity_date",
] + [ENTERED_COLUMN[stage] for stage in STAGES]
FIRM_COLUMNS = ["firm_id", "name", "domain", "city"]


# --------------------------------------------------------------------------
# 3.0 Times
# --------------------------------------------------------------------------

class Moment:
    """One timestamp from the files, written in New York time.

    .instant is the exact moment (UTC): every comparison of two dates uses it.
    .day is the New York calendar date: only day counts use it.
    """

    def __init__(self, local):
        self.local = local
        # Settled in 3.0: a wall time that happens twice (2026-11-01 01:00-01:59) is the first one.
        self.instant = local.replace(tzinfo=NEW_YORK, fold=0).astimezone(timezone.utc)
        self.day = local.date()


# The exports: this week's at Mon 2026-11-23 00:00, last week's at Mon 2026-11-16 00:00.
# GUESS 30: every export folder (practice and scored) carries these two dates.
THIS_EXPORT_LOCAL = datetime(2026, 11, 23, 0, 0)
LAST_EXPORT_LOCAL = datetime(2026, 11, 16, 0, 0)
THIS_EXPORT = Moment(THIS_EXPORT_LOCAL)

# The week: Mon 2026-11-16 00:00 to Mon 2026-11-23 00:00; start included, end excluded.
WEEK_START = Moment(LAST_EXPORT_LOCAL)
WEEK_END = THIS_EXPORT

FAR_FUTURE = datetime.max.replace(tzinfo=timezone.utc)


def in_window(moment, start, end):
    """'In the week' compares instants: start included, end excluded."""
    return moment is not None and start.instant <= moment.instant < end.instant


def is_before(a, b):
    """Strictly earlier as instants (equal instants are in order)."""
    return a.instant < b.instant


def is_after(a, b):
    """Strictly later as instants."""
    return a.instant > b.instant


def calendar_days(later, earlier):
    """A day count: New York calendar date minus New York calendar date."""
    return (later.day - earlier.day).days


def days_before_export(moment):
    """Day counts: the export's New York calendar date minus the event's."""
    return calendar_days(THIS_EXPORT, moment)


# Settled in 3.0: the written format first; seconds, a "T" and a bare date are also read.
DATE_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
]


def parse_moment(text, where):
    """Empty means blank (None). A date that cannot be read stops the recount."""
    if text == "":
        return None
    for date_format in DATE_FORMATS:
        try:
            return Moment(datetime.strptime(text, date_format))
        except ValueError:
            continue
    raise ExportError(f"cannot read the date {text!r} ({where})")


# --------------------------------------------------------------------------
# 3.2 Amount
# --------------------------------------------------------------------------

def parse_amount(text):
    """The amount in dollars, or None when blank or unreadable (settled in 3.0)."""
    if text == "":
        return None
    try:
        value = Decimal(text.replace("$", "").replace(",", ""))
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def money(value):
    """A Decimal sum as a JSON number: whole dollars as an int."""
    return int(value) if value == value.to_integral_value() else float(value)


def deal_id_key(deal_id):
    """'Lowest deal ID' compares whole-number IDs as numbers, others as text
    (settled in 3.0). Whole numbers sort before text (GUESS 9)."""
    if deal_id.isascii() and deal_id.isdigit():  # ASCII only: int() refuses "²"
        return (0, int(deal_id), deal_id)
    return (1, 0, deal_id)


# --------------------------------------------------------------------------
# Reading the files
# --------------------------------------------------------------------------

def read_csv(path, required_columns):
    """Rows as dicts. Every cell is trimmed of surrounding spaces (settled in 3.0)."""
    if not os.path.isfile(path):
        raise ExportError(f"missing file: {path}")
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = [(name or "").strip() for name in (reader.fieldnames or [])]
        missing = [column for column in required_columns if column not in header]
        if missing:
            raise ExportError(f"{path} lacks the column(s): {', '.join(missing)}")
        rows = []
        for raw in reader:
            row = {}
            for key, value in raw.items():
                if key is None:  # cells beyond the header
                    continue
                row[key.strip()] = (value or "").strip()
            rows.append(row)
    return rows, header


class Deal:
    """One row of deals-this-week.csv."""

    def __init__(self, row, file_name):
        self.id = row["deal_id"]

        def where(column):
            return f"{file_name}, deal {self.id}, column {column}"

        self.name = row["deal_name"]
        self.stage = row["stage"]
        self.pipeline = row["pipeline"]
        self.amount = parse_amount(row["amount"])
        self.close_date = parse_moment(row["close_date"], where("close_date"))
        self.owner = row["owner"]
        self.create_date = parse_moment(row["create_date"], where("create_date"))
        self.last_contacted = parse_moment(row["last_contacted"], where("last_contacted"))
        self.last_activity = parse_moment(row["last_activity_date"], where("last_activity_date"))
        # Read so that an unreadable one stops the run (settled in 3.0); only whether it
        # is empty is used (NONE BOOKED), and H14 does not check it.
        self.next_activity = parse_moment(row["next_activity_date"], where("next_activity_date"))
        self.lost_reason = row["closed_lost_reason"]
        self.firm_id = row["firm_id"]
        self.entered = {
            stage: parse_moment(row[ENTERED_COLUMN[stage]], where(ENTERED_COLUMN[stage]))
            for stage in STAGES
        }

    def value(self):
        """For sums: a blank amount counts as zero."""
        return self.amount if self.amount is not None else Decimal(0)


class LastWeekRow:
    """One row of deals-last-week.csv: only the stage and close date are used.

    Every date cell it has is still read, so an unreadable one stops the run
    (settled in 3.0)."""

    def __init__(self, row):
        self.id = row["deal_id"]
        self.stage = row["stage"]
        dates = {
            column: parse_moment(row[column], f"deals-last-week.csv, deal {self.id}, column {column}")
            for column in DATE_COLUMNS if column in row
        }
        self.close_date = dates["close_date"]


class Export:
    """Everything one recount reads."""

    def __init__(self, deals, last_week, firms, team):
        self.deals = deals            # this week's rows, in file order
        self.by_id = {deal.id: deal for deal in deals}
        self.last_week = last_week    # deal ID -> LastWeekRow
        self.firms = firms            # firm ID -> firms.csv row
        self.team = team              # owner full names, lower case


def read_team(path):
    """team.csv: columns full_name, role; the four owners (settled in 3.0)."""
    rows, _ = read_csv(path, ["full_name"])
    # H10 compares ignoring case and leading or trailing spaces.
    return {row["full_name"].strip().lower() for row in rows if row["full_name"].strip()}


def load_export(folder, team_path):
    this_rows, _ = read_csv(os.path.join(folder, "deals-this-week.csv"), DEAL_COLUMNS)
    deals = [Deal(row, "deals-this-week.csv") for row in this_rows]
    seen = set()
    for deal in deals:
        if deal.id in seen:  # settled in 3.0
            raise ExportError(f"deal ID {deal.id} appears twice in deals-this-week.csv")
        seen.add(deal.id)

    last_rows, _ = read_csv(os.path.join(folder, "deals-last-week.csv"), LAST_WEEK_COLUMNS)
    last_week = {}
    for row in last_rows:
        entry = LastWeekRow(row)
        if entry.id in last_week:  # settled in 3.0
            raise ExportError(f"deal ID {entry.id} appears twice in deals-last-week.csv")
        last_week[entry.id] = entry

    firm_rows, _ = read_csv(os.path.join(folder, "firms.csv"), FIRM_COLUMNS)
    firms = {}
    for row in firm_rows:
        if row["firm_id"] != "":
            firms.setdefault(row["firm_id"], row)

    return Export(deals, last_week, firms, read_team(team_path))


# --------------------------------------------------------------------------
# Shared definitions
# --------------------------------------------------------------------------

def is_open(deal):
    return deal.stage in OPEN_STAGES


def is_qualified_or_later(deal):
    """'Qualified or later': stage Qualified, Pilot proposed, Partner said yes,
    Order form sent or Won, or a Lost deal with a Date entered Qualified."""
    if deal.stage in STAGES[1:6]:
        return True
    return deal.stage == "Lost" and deal.entered["Qualified"] is not None


def firm_of(deal, export):
    if deal.firm_id == "":
        return None
    return export.firms.get(deal.firm_id)


def create_order_key(deal):
    """'By Create date', oldest first; a blank Create date sorts last (settled in 3.5
    for the push list; for H6 still GUESS 8)."""
    if deal.create_date is None:
        return (1, FAR_FUTURE)
    return (0, deal.create_date.instant)


# --------------------------------------------------------------------------
# 3.4 Held out of the numbers
# --------------------------------------------------------------------------

HELD_OUT_REASON_LINES = {
    "H1": "No owner",
    "H2": "No amount",
    "H3": "No close date",
    "H4": "Close date passed, still open",
    "H5": "Stage skipped",
    "H6": "Same firm as another deal",
    "H7": "Moved back a stage",
    "H8": "Contacted after it was lost",
    "H9": "Lost with no reason",
    "H10": "Owner not on the team",
    "H11": "Test record",
    "H12": "No firm on the deal",
    "H13": "Dates out of order",
    "H14": "Dated after the export",
    "H15": "Unknown stage or pipeline",
}


def h1_no_owner(deal, export):
    """owner empty"""
    return deal.owner == ""


def h2_no_amount(deal, export):
    """Qualified or later, and amount empty or not above zero"""
    return is_qualified_or_later(deal) and (deal.amount is None or not deal.amount > 0)


def h3_no_close_date(deal, export):
    """Qualified or later, and close date empty"""
    return is_qualified_or_later(deal) and deal.close_date is None


def h4_close_date_passed(deal, export):
    """in Qualified through Order form sent, close date before the export time
    (Consultation booked deals exempt)"""
    return (deal.stage in QUALIFIED_TO_ORDER_FORM
            and deal.close_date is not None
            and is_before(deal.close_date, THIS_EXPORT))  # settled in 3.4: the export time


def h5_stage_skipped(deal, export):
    """any deal, whatever its stage now, with a Date entered for a stage from Pilot
    proposed to Won while an earlier stage from Qualified on has none; Lost is never
    a skip; created straight into Qualified is not a skip"""
    for position in range(2, 6):  # Pilot proposed .. Won, whatever the stage now (settled in 3.4)
        if deal.entered[STAGES[position]] is None:
            continue
        for earlier in STAGES[1:position]:  # Qualified .. the stage before it
            if deal.entered[earlier] is None:
                return True
    return False


def h6_same_firm(export, held_so_far):
    """among open deals, two or more share a firm domain; every one but the oldest
    by Create date (then lowest deal ID) is held out; deals already held out by a
    lower rule (H1 to H5) don't count toward the group, while a deal held out by a
    higher rule still does; a firm with no domain forms no group.
    Returns the deal IDs held out."""
    groups = {}
    for deal in export.deals:
        if not is_open(deal) or deal.id in held_so_far:  # held_so_far: H1 to H5 only
            continue
        firm = firm_of(deal, export)
        domain = firm["domain"] if firm is not None else ""
        if domain == "":  # settled in 3.4: no domain, no group
            continue
        groups.setdefault(domain, []).append(deal)  # settled in 3.0: exact text after trimming
    held = []
    for group in groups.values():
        if len(group) < 2:
            continue
        group.sort(key=lambda deal: (create_order_key(deal), deal_id_key(deal.id)))
        held.extend(deal.id for deal in group[1:])
    return held


def h7_moved_back(deal, export):
    """in last week's export, and its stage now is earlier in the stage order than
    last week's; Lost comes after Won in that order, so a deal Won or Lost last week
    and open now, or Lost last week and Won now, counts as moved back; a deal Lost
    now is never moved back; a stage outside the seven in either export is left to H15"""
    last = export.last_week.get(deal.id)
    if last is None or deal.stage == "Lost":
        return False
    if deal.stage not in STAGES or last.stage not in STAGES:  # settled in 3.4
        return False
    return STAGES.index(deal.stage) < STAGES.index(last.stage)


def h8_contact_after_lost(deal, export):
    """Lost, and Last contacted is on a later New York calendar date than its close date"""
    if deal.stage != "Lost" or deal.last_contacted is None or deal.close_date is None:
        return False
    return deal.last_contacted.day > deal.close_date.day  # settled in 3.4: calendar dates


def h9_lost_no_reason(deal, export):
    """Lost, and closed lost reason empty"""
    return deal.stage == "Lost" and deal.lost_reason == ""


def h10_owner_not_on_team(deal, export):
    """owner not in team.csv (ignoring case and leading or trailing spaces)"""
    return deal.owner.strip().lower() not in export.team


def h11_test_record(deal, export):
    """the firm name or the deal name, ignoring case and leading spaces, starts with test"""
    names = [deal.name]
    firm = firm_of(deal, export)
    if firm is not None:
        names.append(firm["name"])
    return any(name.lstrip().lower().startswith("test") for name in names)  # settled in 3.4


def h12_no_firm(deal, export):
    """firm ID empty, or not found in firms.csv"""
    return firm_of(deal, export) is None


def h13_dates_out_of_order(deal, export):
    """a Date entered before the Create date; Date entered values out of stage order
    (Lost comes after every other stage); the current stage has no Date entered;
    or a stage after the current one has a Date entered (equal instants are in order;
    a blank Create date skips the first check; an unknown stage skips the last two)"""
    dated = [deal.entered[stage] for stage in STAGES if deal.entered[stage] is not None]
    if deal.create_date is not None:  # settled in 3.4
        if any(is_before(entered, deal.create_date) for entered in dated):
            return True
    for earlier, later in zip(dated, dated[1:]):
        if is_before(later, earlier):
            return True
    if deal.stage in STAGES:  # settled in 3.4
        if deal.entered[deal.stage] is None:
            return True
        for later_stage in STAGES[STAGES.index(deal.stage) + 1:]:
            if deal.entered[later_stage] is not None:
                return True
    return False


def h14_dated_after_export(deal, export):
    """a Create date, any Date entered, Last contacted or Last activity date strictly
    after the export time, or the close date of a won or lost deal after it"""
    checked = [deal.create_date, deal.last_contacted, deal.last_activity]
    checked += [deal.entered[stage] for stage in STAGES]
    if deal.stage in ("Won", "Lost"):
        checked.append(deal.close_date)
    return any(moment is not None and is_after(moment, THIS_EXPORT) for moment in checked)  # settled in 3.4


def h15_unknown_stage_or_pipeline(deal, export):
    """a stage outside the seven, or a pipeline other than the one new-business pipeline"""
    return deal.stage not in STAGES or deal.pipeline != PIPELINE  # settled in 3.0: exact text


RULES_BEFORE_H6 = [
    ("H1", h1_no_owner),
    ("H2", h2_no_amount),
    ("H3", h3_no_close_date),
    ("H4", h4_close_date_passed),
    ("H5", h5_stage_skipped),
]

RULES_AFTER_H6 = [
    ("H7", h7_moved_back),
    ("H8", h8_contact_after_lost),
    ("H9", h9_lost_no_reason),
    ("H10", h10_owner_not_on_team),
    ("H11", h11_test_record),
    ("H12", h12_no_firm),
    ("H13", h13_dates_out_of_order),
    ("H14", h14_dated_after_export),
    ("H15", h15_unknown_stage_or_pipeline),
]


def first_rule(deal, export, rules):
    for rule, test in rules:
        if test(deal, export):
            return rule
    return None


def find_held_out(export):
    """One reason per deal: the lowest rule number that applies.
    Returns {deal ID: "H<n>"} in file order."""
    held = {}
    for deal in export.deals:
        rule = first_rule(deal, export, RULES_BEFORE_H6)
        if rule:
            held[deal.id] = rule
    for deal_id in h6_same_firm(export, held):
        held[deal_id] = "H6"
    for deal in export.deals:
        if deal.id not in held:
            rule = first_rule(deal, export, RULES_AFTER_H6)
            if rule:
                held[deal.id] = rule
    return {deal.id: held[deal.id] for deal in export.deals if deal.id in held}


# --------------------------------------------------------------------------
# 3.5 Needs a push
# --------------------------------------------------------------------------

PUSH_TAGS = ["OVER LIMIT", "SLIPPED", "QUIET", "NONE BOOKED"]  # the table order


def days_in_stage(deal):
    """Days in the current stage, counted from its Date entered (a real date: H13)."""
    return days_before_export(deal.entered[deal.stage])


def push_tags(deal, export, limits):
    """Every tag the deal earns, in table order."""
    tags = []
    # OVER LIMIT: days in the current stage over its limit ("over" = strictly more).
    if days_in_stage(deal) > limits[deal.stage]:
        tags.append("OVER LIMIT")
    # SLIPPED: close date later than in last week's export by 7 or more New York
    # calendar days (settled in 3.5); only a deal whose stage in last week's export
    # was Qualified through Order form sent can slip: no last-week row, no close date
    # there, or Consultation booked last week (HubSpot's automatic date) cannot.
    last = export.last_week.get(deal.id)
    if (last is not None and last.stage in QUALIFIED_TO_ORDER_FORM
            and last.close_date is not None and deal.close_date is not None):
        if calendar_days(deal.close_date, last.close_date) >= 7:
            tags.append("SLIPPED")
    # QUIET: Last contacted empty, or days since it over 14.
    if deal.last_contacted is None or days_before_export(deal.last_contacted) > 14:
        tags.append("QUIET")
    # NONE BOOKED: next activity date empty.
    if deal.next_activity is None:
        tags.append("NONE BOOKED")
    return tags


def push_order_key(deal, tags):
    """Most tags first, then the deal's highest tag in table order, then the longest
    days in stage, then Create date (oldest first; a blank one last), then the lowest
    deal ID (settled in 3.5)."""
    return (
        -len(tags),
        PUSH_TAGS.index(tags[0]),
        -days_in_stage(deal),
        create_order_key(deal),
        deal_id_key(deal.id),
    )


def find_push(export, held, limits):
    """From qualified open deals that pass every check."""
    tags_by_id = {}
    for deal in export.deals:
        if deal.id in held or deal.stage not in QUALIFIED_TO_ORDER_FORM:
            continue
        tags = push_tags(deal, export, limits)
        if tags:
            tags_by_id[deal.id] = tags
    order = sorted(tags_by_id, key=lambda deal_id: push_order_key(export.by_id[deal_id],
                                                                  tags_by_id[deal_id]))
    return {deal_id: tags_by_id[deal_id] for deal_id in order}, order


# --------------------------------------------------------------------------
# 3.6 Next steps: only step 3 can be recounted without the notes (GUESS 28)
# --------------------------------------------------------------------------

NEXT_BY_STAGE = {
    "Qualified": "Next: send the pilot scope",
    "Pilot proposed": "Next: ask for a yes on the pilot",
    "Partner said yes": "Next: send the order form",
    "Order form sent": "Next: call about the signature",
}


def next_step_from_first_tag(deal, tags):
    """The wording for the first tag; for OVER LIMIT and SLIPPED, by stage."""
    first = tags[0]
    if first in ("OVER LIMIT", "SLIPPED"):
        return NEXT_BY_STAGE[deal.stage]
    if first == "QUIET":
        return "Next: reach the firm this week"
    return "Next: book the next call"  # NONE BOOKED


# --------------------------------------------------------------------------
# 3.3 The numbers (over deals that pass every check)
# --------------------------------------------------------------------------

def count_and_value(deals):
    return {"count": len(deals), "value": money(sum((deal.value() for deal in deals), Decimal(0)))}


def compute_numbers(export, held, push_order):
    counted = [deal for deal in export.deals if deal.id not in held]

    # New qualified deals: Date entered Qualified in the week; count.
    new_qualified = [deal for deal in counted
                     if in_window(deal.entered["Qualified"], WEEK_START, WEEK_END)]
    new_qualified_ids = {deal.id for deal in new_qualified}

    # Moved forward: in last week's export as Qualified or later and open, open now
    # and in a later stage; never also New qualified; each deal once. Last week's
    # stage must be open and Qualified or later (settled in 3.0 and 3.1); last week's
    # row is not itself put through the checks (GUESS 17).
    moved_forward = []
    for deal in counted:
        last = export.last_week.get(deal.id)
        if last is None or last.stage not in QUALIFIED_TO_ORDER_FORM:
            continue
        if not is_open(deal) or STAGES.index(deal.stage) <= STAGES.index(last.stage):
            continue
        if deal.id in new_qualified_ids:
            continue
        moved_forward.append(deal)  # deal IDs are unique, so each deal once

    # Won: Date entered Won in the week, whatever the stage now; count and value.
    # (settled in 3.3, as is New qualified's "whatever the deal's stage now")
    won = [deal for deal in counted if in_window(deal.entered["Won"], WEEK_START, WEEK_END)]

    # Lost: qualified deals with Date entered Lost in the week; count and value;
    # losses before Qualified are one line in the drawer. (GUESS 18)
    lost_in_week = [deal for deal in counted
                    if in_window(deal.entered["Lost"], WEEK_START, WEEK_END)]
    lost = [deal for deal in lost_in_week if is_qualified_or_later(deal)]
    lost_before_qualified = [deal for deal in lost_in_week if not is_qualified_or_later(deal)]

    # Open pipeline: open deals in Qualified through Order form sent at the export.
    open_pipeline = [deal for deal in counted if deal.stage in QUALIFIED_TO_ORDER_FORM]

    # Held out: every held-out deal in this week's export; a blank amount counts as zero.
    held_deals = [deal for deal in export.deals if deal.id in held]

    # The 12-week chart: for each of the 12 weeks ending at this export, deals with
    # Date entered Qualified in that week, counted with this week's held-out status.
    # Monday 00:00 to Monday 00:00, the first from Mon 2026-08-31 (settled in 3.3)
    chart = []
    for weeks_back in range(12, 0, -1):  # oldest first; the last bar is the week
        start = Moment(THIS_EXPORT_LOCAL - timedelta(days=7 * weeks_back))
        end = Moment(THIS_EXPORT_LOCAL - timedelta(days=7 * (weeks_back - 1)))
        chart.append(sum(1 for deal in counted if in_window(deal.entered["Qualified"], start, end)))

    # The card: the number of deals on the push list; the sum of their amounts; the
    # stage holding the most of them (a tie goes to the later stage) and how many.
    push_deals = [export.by_id[deal_id] for deal_id in push_order]
    card = count_and_value(push_deals)
    card_stage, card_stage_count = None, 0  # settled in 3.3: an empty list has no stage
    for stage in QUALIFIED_TO_ORDER_FORM:  # earlier to later, so a tie goes to the later
        in_stage = sum(1 for deal in push_deals if deal.stage == stage)
        if in_stage > 0 and in_stage >= card_stage_count:
            card_stage, card_stage_count = stage, in_stage
    card["stage"] = card_stage
    card["stage_count"] = card_stage_count

    return {
        "new_qualified": len(new_qualified),
        "moved_forward": len(moved_forward),
        "won": count_and_value(won),
        "lost": count_and_value(lost),
        "lost_before_qualified": len(lost_before_qualified),
        "open": count_and_value(open_pipeline),
        "held_out": count_and_value(held_deals),
        "chart": chart,
        "card": card,
    }


# --------------------------------------------------------------------------
# Stage limits (3.5)
# --------------------------------------------------------------------------

def has_every_stage_date_in_order(deal):
    """Every stage date from Qualified to Won present and in order."""
    dates = [deal.entered[stage] for stage in STAGES[1:6]]
    if any(moment is None for moment in dates):
        return False
    return all(not is_before(later, earlier) for earlier, later in zip(dates, dates[1:]))


def recount_limits(export_folder, team_path=None):
    """For each stage from Qualified to Order form sent, the average of whole days
    between consecutive Date entered values over won practice deals that pass every
    check and have every stage date from Qualified to Won in order; plus 20%;
    rounded up. Exact fractions, so 5 days x 1.2 is 6, not 7. Whole days are New
    York calendar dates (25 settled in 3.5); which deals are "won" (GUESS 26).
    Returns {stage: days}; a stage with no such deal gets None."""
    export = load_export(export_folder, team_path or default_team_path())
    held = find_held_out(export)
    won = [deal for deal in export.deals
           if deal.stage == "Won" and deal.id not in held and has_every_stage_date_in_order(deal)]
    limits = {}
    for position in range(1, 5):  # Qualified .. Order form sent
        stage, next_stage = STAGES[position], STAGES[position + 1]
        gaps = [calendar_days(deal.entered[next_stage], deal.entered[stage]) for deal in won]
        if not gaps:
            limits[stage] = None
            continue
        average = Fraction(sum(gaps), len(gaps))
        limits[stage] = math.ceil(average * Fraction(6, 5))
    return limits


def read_limits(path):
    """limits.json: {"Qualified": 9, "Pilot proposed": ..., ...} in days (GUESS 27)."""
    if not os.path.isfile(path):
        raise ExportError(f"missing limits file: {path}")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    limits = {}
    for stage in QUALIFIED_TO_ORDER_FORM:
        value = data.get(stage) if isinstance(data, dict) else None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ExportError(f"{path} has no number of days for {stage!r}")
        limits[stage] = value
    return limits


# --------------------------------------------------------------------------
# The whole recount
# --------------------------------------------------------------------------

def default_team_path():
    return os.path.join(HERE, "sample", "team.csv")


def recount(export_folder, team_path, limits):
    export = load_export(export_folder, team_path)
    held = find_held_out(export)
    push, push_order = find_push(export, held, limits)
    return {
        "held_out": held,
        "push": push,
        "push_order": push_order,
        "numbers": compute_numbers(export, held, push_order),
        # Extras for the reviewer (GUESS 28, 29): the limits used, and 3.6 step 3.
        "limits": limits,
        "next_step_from_first_tag": {
            deal_id: next_step_from_first_tag(export.by_id[deal_id], tags)
            for deal_id, tags in push.items()
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Independent recount of the Weekly Pipeline page.")
    parser.add_argument("export_folder", help="folder with deals-this-week.csv, deals-last-week.csv, firms.csv")
    parser.add_argument("--team", default=default_team_path(), help="team.csv (default: sample/team.csv)")
    parser.add_argument("--limits", help="limits.json; if left out, the limits are recounted from --practice")
    parser.add_argument("--practice", default=os.path.join(HERE, "sample", "practice"),
                        help="practice export used when --limits is left out (default: sample/practice)")
    parser.add_argument("--print-limits", action="store_true",
                        help="print recount_limits(export_folder) and stop")
    args = parser.parse_args(argv)

    try:
        if args.print_limits:
            print(json.dumps(recount_limits(args.export_folder, args.team), indent=2))
            return 0
        if args.limits:
            limits = read_limits(args.limits)
        else:
            limits = recount_limits(args.practice, args.team)
            missing = [stage for stage, days in limits.items() if days is None]
            if missing:
                raise ExportError("no won practice deal to set the limit for: " + ", ".join(missing))
        print(json.dumps(recount(args.export_folder, args.team, limits), indent=2))
        return 0
    except ExportError as error:
        print(f"recount.py: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
