"""The debrief: what you did, what it cost you, and what to do next time.

Everything here is computed from the actual deal space, not from opinion.
The simulator knows all 1,280 packages and both sets of hidden points, so
it can say precisely which trades existed and which ones you walked past.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ui
from .analysis import all_offers, judge, missed_improvements, pareto_frontier, viable_offers
from .deal import BUYER, SELLER, Offer, Scenario

CRITICAL, MAJOR, MINOR, GOOD = "critical", "major", "minor", "good"
SEVERITY_STYLE = {CRITICAL: ("red", "!!"), MAJOR: ("yellow", "!"), MINOR: ("cyan", "-"), GOOD: ("green", "+")}


@dataclass
class PlayLog:
    """What the player actually did, recorded as they did it."""

    asked_priorities: bool = False
    insults_given: int = 0
    warmth_given: int = 0
    revealed_flexibility: list[str] = field(default_factory=list)
    trades_proposed: list[str] = field(default_factory=list)
    your_offers: list[Offer] = field(default_factory=list)
    rounds_used: int = 0
    rounds_available: int = 8


@dataclass
class IssueRow:
    label: str
    your_stake: int
    your_points: int
    their_stake: int
    their_points: int

    @property
    def your_share(self) -> float:
        return 0.0 if self.your_stake == 0 else self.your_points / self.your_stake

    @property
    def their_share(self) -> float:
        return 0.0 if self.their_stake == 0 else self.their_points / self.their_stake

    @property
    def winner(self) -> str:
        if abs(self.your_share - self.their_share) < 0.2:
            return "split"
        return "you" if self.your_share > self.their_share else "them"


@dataclass
class Lesson:
    severity: str
    title: str
    detail: str


@dataclass
class Review:
    scenario: Scenario
    offer: Offer | None
    buyer_score: int
    seller_score: int
    rows: list[IssueRow]
    lessons: list[Lesson]
    grade: str
    grade_note: str
    capture: float          # how much of what was gettable you actually got
    efficiency: float       # how much of the joint pie the two of you found
    best_possible: Offer | None
    best_possible_score: int
    value_left: int
    trades: list["Trade"]


def _issue_rows(scenario: Scenario, offer: Offer) -> list[IssueRow]:
    rows = []
    for key in scenario.issue_keys:
        issue = scenario.issue(key)
        option = offer.option_for(key)
        rows.append(IssueRow(
            label=issue.label,
            your_stake=issue.stake(BUYER),
            your_points=option.points_for(BUYER),
            their_stake=issue.stake(SELLER),
            their_points=option.points_for(SELLER),
        ))
    return rows


@dataclass
class Trade:
    """Concede one term, take another, and both sides come out ahead.

    Note that no single term can ever do this: each issue is a straight tug
    of war, so moving one line always helps one side and hurts the other.
    Gains for both only exist when you SWAP -- which is the entire lesson."""

    give_label: str
    give_from: str
    give_to: str
    take_label: str
    take_from: str
    take_to: str
    you_gain: int
    them_gain: int


def _trades(scenario: Scenario, offer: Offer) -> list[Trade]:
    """Every two-term swap that would have left both of you better off."""
    b0, s0 = offer.score(BUYER), offer.score(SELLER)
    keys = scenario.issue_keys
    found: list[Trade] = []
    for i, give_key in enumerate(keys):
        for take_key in keys[i + 1:]:
            give_issue, take_issue = scenario.issue(give_key), scenario.issue(take_key)
            for give_opt in give_issue.options:
                if give_opt.key == offer.option_for(give_key).key:
                    continue
                for take_opt in take_issue.options:
                    if take_opt.key == offer.option_for(take_key).key:
                        continue
                    swapped = offer.replace(give_key, give_opt.key).replace(
                        take_key, take_opt.key)
                    b, s = swapped.score(BUYER), swapped.score(SELLER)
                    if b < b0 or s < s0 or (b == b0 and s == s0):
                        continue
                    # Name the conceded side first: that is what you hand over.
                    give_delta = give_opt.points_for(BUYER) - offer.option_for(give_key).points_for(BUYER)
                    a, z = (give_key, take_key) if give_delta <= 0 else (take_key, give_key)
                    opts = {give_key: give_opt, take_key: take_opt}
                    found.append(Trade(
                        scenario.issue(a).label, offer.option_for(a).label, opts[a].label,
                        scenario.issue(z).label, offer.option_for(z).label, opts[z].label,
                        b - b0, s - s0))
    found.sort(key=lambda t: (-(t.you_gain + t.them_gain), -t.you_gain))
    # Keep only the best trade per pair of terms, so the list is not repetitive.
    seen, unique = set(), []
    for trade in found:
        pair = (trade.give_label, trade.take_label)
        if pair in seen:
            continue
        seen.add(pair)
        unique.append(trade)
    return unique


def _grade(capture: float, efficiency: float, dealt: bool) -> tuple[str, str]:
    if not dealt:
        return "F", "No deal. A signable package existed and neither of you found it."
    value = 0.65 * capture + 0.35 * efficiency
    for cut, letter, note in (
        (0.90, "A+", "Close to the best outcome available to you. Genuinely well negotiated."),
        (0.80, "A", "Strong. You found the trades and you took most of what was gettable."),
        (0.70, "B", "Solid. You made real trades but left some on the table."),
        (0.58, "C", "Workable deal, ordinary negotiation. The value was there to take."),
        (0.45, "D", "You signed something worse than you needed to."),
    ):
        if value >= cut:
            return letter, note
    return "F", "This deal cost you most of what was available."


def review(outcome, log: PlayLog) -> Review:
    scenario = outcome.scenario
    offer = outcome.offer
    walkaway = scenario.buyer_walkaway

    viable = viable_offers(scenario)
    best_offer, best_score = None, walkaway
    if viable:
        best_offer, best_score, _ = max(viable, key=lambda row: row[1])

    buyer = outcome.buyer_score()
    seller = outcome.seller_score()
    available = max(1, best_score - walkaway)
    capture = max(0.0, min(1.0, (buyer - walkaway) / available))

    if offer is not None:
        verdict = judge(scenario, offer)
        efficiency = verdict.efficiency_pct / 100.0
        rows = _issue_rows(scenario, offer)
        fixes = _trades(scenario, offer)
        value_left = verdict.value_left_on_table
    else:
        efficiency, rows, fixes, value_left = 0.0, [], [], 0

    grade, note = _grade(capture, efficiency, offer is not None)
    lessons = _lessons(outcome, log, scenario, offer, rows, value_left,
                       best_offer, best_score, capture)

    return Review(
        scenario=scenario, offer=offer, buyer_score=buyer, seller_score=seller,
        rows=rows, lessons=lessons, grade=grade, grade_note=note,
        capture=capture, efficiency=efficiency,
        best_possible=best_offer, best_possible_score=best_score,
        value_left=value_left, trades=fixes[:3],
    )


def _lessons(outcome, log, scenario, offer, rows, value_left,
             best_offer, best_score, capture) -> list[Lesson]:
    from .game import QUIT, SIGNED, THEY_RAGED, THEY_WALKED, TIME_OUT, YOU_WALKED

    out: list[Lesson] = []
    walkaway = scenario.buyer_walkaway

    # -- outcomes that dominate everything else ---------------------------
    if offer is not None and offer.score(BUYER) < walkaway:
        out.append(Lesson(CRITICAL, "You signed a deal worse than no deal",
                          f"This package is worth {offer.score(BUYER)} to you. Walking away "
                          f"was worth {walkaway}. Your walk-away number is not a guideline; "
                          f"it is the entire reason you have one."))
    if getattr(outcome, "fleeced", False):
        out.append(Lesson(CRITICAL, "They accepted instantly, and that told you everything",
                          "When the other side signs without a single counter, you were "
                          "never near their limit. An offer accepted on the spot is an "
                          "offer that was too generous. Open worse next time."))
    if outcome.kind == THEY_RAGED:
        out.append(Lesson(CRITICAL, "You pushed them out of the room",
                          "Aggression is a tool, not a personality. You used it on someone "
                          "who had no tolerance for it, and you got nothing. Reading who "
                          "you are dealing with comes before deciding how hard to push."))
    if outcome.kind in (YOU_WALKED, THEY_WALKED, TIME_OUT, QUIT):
        out.append(Lesson(MAJOR, "A deal existed and you did not find it",
                          f"There were {len(viable_offers(scenario))} packages that both of "
                          f"you would have signed. The best of them was worth {best_score} "
                          f"to you, against {walkaway} for walking. No deal is sometimes "
                          f"right. Here it cost you {best_score - walkaway} points."))

    # -- how you allocated your fight -------------------------------------
    if rows:
        biggest = max(rows, key=lambda r: r.your_stake)
        cheapest = min(rows, key=lambda r: r.your_stake)
        if biggest.your_share < 0.4:
            out.append(Lesson(MAJOR, f"You lost {biggest.label.lower()}, your biggest issue",
                              f"It was worth {biggest.your_stake} points to you -- more than "
                              f"any other term -- and you came away with {biggest.your_points}. "
                              f"Whatever else you trade, protect your top issue."))
        if cheapest.your_share > 0.5 and cheapest.their_stake > cheapest.your_stake * 2:
            out.append(Lesson(MAJOR, f"You kept {cheapest.label.lower()}, which you did not need",
                              f"That term was worth only {cheapest.your_stake} points to you "
                              f"and {cheapest.their_stake} to them. Handing it over costs you "
                              f"almost nothing and buys you enormous goodwill. This is the "
                              f"single most reliable trade in the game and you sat on it."))
        middles = sum(1 for key, row in zip(scenario.issue_keys, rows)
                      if _is_middle(scenario, offer, key))
        if middles >= 3:
            out.append(Lesson(MAJOR, "You split the difference on almost everything",
                              f"{middles} of the five terms landed on a middle option. "
                              f"Meeting in the middle feels fair and is usually the worst "
                              f"available deal: it wins you nothing you care about and "
                              f"gives them nothing they care about."))

    # -- what you left behind ----------------------------------------------
    if value_left > 0:
        out.append(Lesson(MAJOR if value_left > 12 else MINOR,
                          f"You left {value_left} points on the table",
                          "That is value neither of you collected. There was a package "
                          "better for BOTH of you than the one you signed, so this is not "
                          "about who won; it is money you both set on fire."))
    elif offer is not None:
        out.append(Lesson(GOOD, "Your deal was efficient",
                          "No package existed that would have been better for both of you. "
                          "Whatever else happened, you and they found the whole pie."))

    # -- behaviour ----------------------------------------------------------
    if not log.asked_priorities:
        out.append(Lesson(MAJOR, "You never asked what mattered to them",
                          "It costs nothing, it costs no round, and most of them will tell "
                          "you something true. You cannot trade efficiently while guessing "
                          "what the other side values."))
    else:
        out.append(Lesson(GOOD, "You asked what they cared about",
                          "That is the highest-return question in any negotiation, and most "
                          "people never ask it once."))

    if log.revealed_flexibility:
        labels = ", ".join(scenario.issue(k).label.lower() for k in log.revealed_flexibility)
        out.append(Lesson(MAJOR, "You told them where you would bend",
                          f"You volunteered that you were flexible on {labels}. Flexibility "
                          f"is a thing you sell, not a thing you announce. Once they know "
                          f"you do not want it, they stop paying you for it."))

    if log.insults_given >= 2:
        out.append(Lesson(MINOR, "You spent goodwill you did not need to spend",
                          "Being rude is occasionally leverage and usually just expensive. "
                          "It shortens their patience and buys you nothing structural."))

    if len(log.your_offers) >= 2:
        first, second = log.your_offers[0], log.your_offers[1]
        drop = first.score(BUYER) - second.score(BUYER)
        if drop > 15:
            out.append(Lesson(MINOR, "You conceded too much, too early",
                              f"Your second offer was {drop} points worse for you than your "
                              f"first. Big early concessions teach the other side that "
                              f"waiting works. Move in small steps and make them pay for each."))
    if log.your_offers and log.your_offers[0].score(BUYER) < 80:
        out.append(Lesson(MINOR, "Your opening offer was too modest",
                          f"You opened at {log.your_offers[0].score(BUYER)} out of 100 for "
                          f"yourself. Your opening is an anchor, not a prediction. Open high "
                          f"enough that you have somewhere to concede from."))

    if outcome.kind == SIGNED and log.rounds_available - log.rounds_used >= 2:
        out.append(Lesson(MINOR, "You signed with rounds to spare",
                          f"You used {log.rounds_used} of {log.rounds_available}. Their "
                          f"demands fall as the clock runs. Unused rounds are unused leverage."))

    if capture >= 0.8 and offer is not None:
        out.append(Lesson(GOOD, "You took most of what was available",
                          f"The most any buyer could have extracted here, given what they "
                          f"would sign, was {best_score}. You got {outcome.buyer_score()}."))

    order = {CRITICAL: 0, MAJOR: 1, MINOR: 2, GOOD: 3}
    out.sort(key=lambda lesson: order[lesson.severity])
    return out


def _is_middle(scenario: Scenario, offer: Offer | None, key: str) -> bool:
    if offer is None:
        return False
    options = scenario.issue(key).options
    index = [o.key for o in options].index(offer.option_for(key).key)
    return 0 < index < len(options) - 1


# -- the picture -----------------------------------------------------------

def frontier_chart(scenario: Scenario, offer: Offer | None,
                   width: int = 46, height: int = 15) -> str:
    """A map of every possible deal, with yours marked on it."""
    grid = [[" " for _ in range(width)] for _ in range(height)]

    def place(b: int, s: int, mark: str, force: bool = False):
        col = round(b / 100 * (width - 1))
        row = (height - 1) - round(s / 100 * (height - 1))
        if 0 <= row < height and 0 <= col < width:
            if force or grid[row][col] == " ":
                grid[row][col] = mark

    # everything that was possible at all
    for o in all_offers(scenario):
        place(o.score(BUYER), o.score(SELLER), ui.paint(".", "dim"))
    # the efficient edge
    for o, b, s in pareto_frontier(scenario):
        place(b, s, ui.paint("o", "cyan"), force=True)
    # the best deal you could have had that they would still sign
    viable = viable_offers(scenario)
    if viable:
        best, bb, bs = max(viable, key=lambda row: row[1])
        place(bb, bs, ui.paint("B", "bold", "yellow"), force=True)
    # where you actually landed
    if offer is not None:
        place(offer.score(BUYER), offer.score(SELLER), ui.paint("@", "bold", "green"), force=True)
    else:
        place(scenario.buyer_walkaway, scenario.seller_walkaway,
              ui.paint("x", "bold", "red"), force=True)

    lines = [ui.paint("  their score", "dim"), "  100 +" + "-" * width]
    for i, row in enumerate(grid):
        label = "      |" if i != height - 1 else "    0 |"
        lines.append(label + "".join(row))
    lines.append("      +" + "-" * width)
    lines.append("       0" + " " * (width - 16) + "your score  100")
    lines.append("")
    lines.append("  " + ui.paint(".", "dim") + " possible   "
                 + ui.paint("o", "cyan") + " efficient   "
                 + ui.paint("B", "bold", "yellow") + " best you could have had   "
                 + (ui.paint("@", "bold", "green") + " your deal" if offer is not None
                    else ui.paint("x", "bold", "red") + " no deal"))
    return "\n".join(lines)


# -- rendering -------------------------------------------------------------

def render(rev: Review) -> str:
    out = [ui.heading("debrief")]

    out.append(ui.subheading("Where your deal sat among every deal that was possible"))
    out.append(frontier_chart(rev.scenario, rev.offer))

    if rev.rows:
        out.append(ui.subheading("Who won what"))
        table_rows = []
        for row in rev.rows:
            verdict = {"you": ui.paint("you took it", "green"),
                       "them": ui.paint("they took it", "red"),
                       "split": ui.paint("split", "dim")}[row.winner]
            table_rows.append([
                row.label,
                f"{row.your_points}/{row.your_stake}",
                f"{row.their_points}/{row.their_stake}",
                verdict,
            ])
        out.append(ui.table(
            ["term", "you got", "they got", "outcome"], table_rows, "lrrl"))
        out.append(ui.paint(
            "  Read the stakes, not the scores: a term worth 5 to you and 35 to them\n"
            "  is one you should be selling, not winning.", "dim"))

    if rev.trades:
        out.append(ui.subheading("Trades you could have made that helped BOTH of you"))
        out.append(ui.paint(
            "  No single term can do this -- each one is a straight tug of war.\n"
            "  Give ground on one, take it on another, and you both come out ahead.", "dim"))
        for trade in rev.trades:
            out.append("")
            out.append(f"  {ui.paint('give', 'yellow')} {trade.give_label}: "
                       f"{ui.paint(trade.give_from, 'dim')} -> {trade.give_to}")
            out.append(f"  {ui.paint('take', 'green')} {trade.take_label}: "
                       f"{ui.paint(trade.take_from, 'dim')} -> {trade.take_to}")
            out.append(ui.paint(
                f"       you +{trade.you_gain}, them +{trade.them_gain}", "bold"))

    if rev.best_possible is not None and rev.offer is not None \
            and rev.best_possible_score > rev.buyer_score:
        out.append(ui.subheading(
            f"The most you could ever have got ({rev.best_possible_score} to you)"))
        out.append(ui.paint("  This is the best package they would still have signed.", "dim"))
        for label, value in rev.best_possible.labels():
            out.append(f"  {label:<20} {value}")

    out.append(ui.subheading("What to do differently"))
    for lesson in rev.lessons:
        style, mark = SEVERITY_STYLE[lesson.severity]
        out.append(f"\n  {ui.paint(mark, style)} {ui.paint(lesson.title, 'bold', style)}")
        out.append(ui.wrap(lesson.detail, "    "))

    out.append("")
    out.append(ui.rule("="))
    pie = f"{rev.efficiency * 100:.0f}%" if rev.offer is not None else "no deal"
    out.append(f"  {ui.paint('GRADE  ' + rev.grade, 'bold')}     "
               f"value captured {rev.capture * 100:.0f}%     "
               f"pie found {pie}")
    out.append(ui.wrap(rev.grade_note, "  "))
    return "\n".join(out)
