"""The supplier's decision making.

This is a rule-based negotiator, not a language model. It is deliberately
competent: it concedes on a schedule, it watches which terms you refuse to
give up, and when it concedes it tries to concede the things IT does not
care about. That makes it a fair sparring partner and it keeps the game
logic honest before a language model is wired in.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .deal import BUYER, SELLER, Offer, Scenario

ACCEPT = "accept"
COUNTER = "counter"
NO_DEAL = "no_deal"


@dataclass
class Reply:
    kind: str
    offer: Offer | None
    message: str


class SellerAgent:
    """Plays the supplier across a fixed number of rounds."""

    def __init__(self, scenario: Scenario, rounds: int = 8, rng: random.Random | None = None):
        self.scenario = scenario
        self.rounds = rounds
        self.rng = rng or random.Random()
        self.walkaway = scenario.seller_walkaway

        # Every package, scored once up front.
        from .analysis import all_offers

        self._catalogue = [(o, o.score(SELLER)) for o in all_offers(scenario)]

        # What the seller believes the buyer cares about. Starts flat and is
        # updated by watching which terms the buyer clings to.
        self.importance: dict[str, float] = {k: 1.0 for k in scenario.issue_keys}
        self.last_player_offer: Offer | None = None
        self.last_counter: Offer | None = None
        self.opening_target = 92
        self.insults = 0

    # -- what the seller wants this round ----------------------------------

    def target(self, round_no: int) -> int:
        """Its minimum acceptable score, sliding down as the clock runs."""
        floor = self.walkaway + 3
        if self.rounds <= 1:
            return floor
        progress = (round_no - 1) / (self.rounds - 1)
        return round(self.opening_target - (self.opening_target - floor) * progress)

    # -- learning from the buyer -------------------------------------------

    def _preference_guess(self, offer: Offer) -> float:
        """How good the seller GUESSES this package is for the buyer. Options
        are listed best-for-buyer first, so an early option scores high."""
        total = 0.0
        for issue in self.scenario.issues:
            options = issue.options
            index = [o.key for o in options].index(offer.option_for(issue.key).key)
            closeness = (len(options) - 1 - index) / (len(options) - 1)
            total += self.importance[issue.key] * closeness
        return total

    def observe(self, offer: Offer) -> None:
        """Update beliefs from the buyer's latest package. Terms the buyer
        holds firm on look important; terms they give ground on look cheap."""
        for issue in self.scenario.issues:
            keys = [o.key for o in issue.options]
            index = keys.index(offer.option_for(issue.key).key)
            if self.last_player_offer is None:
                if index == 0:
                    self.importance[issue.key] += 0.4
                continue
            was = keys.index(self.last_player_offer.option_for(issue.key).key)
            if index > was:  # they conceded here: it must be cheap for them
                self.importance[issue.key] = max(0.4, self.importance[issue.key] - 0.6)
            elif index == was and index <= 1:  # they are dug in on their best
                self.importance[issue.key] += 0.8
        self.last_player_offer = offer

    # -- making offers -----------------------------------------------------

    def _pick(self, minimum: int, ceiling: int | None = None) -> Offer:
        """The package worth at least `minimum` to the seller that it believes
        the buyer will like most. This is what 'concede cleverly' looks like."""
        pool = [(o, s) for o, s in self._catalogue if s >= minimum]
        if ceiling is not None:
            tighter = [(o, s) for o, s in pool if s <= ceiling]
            pool = tighter or pool
        if not pool:
            pool = [max(self._catalogue, key=lambda row: row[1])]
        best = max(pool, key=lambda row: (self._preference_guess(row[0]), -row[1]))
        return best[0]

    def opening_offer(self) -> Offer:
        offer = self._pick(self.opening_target, self.opening_target + 6)
        self.last_counter = offer
        return offer

    def respond(self, player_offer: Offer, round_no: int) -> Reply:
        self.observe(player_offer)
        mine = player_offer.score(SELLER)
        target = self.target(round_no)
        final_round = round_no >= self.rounds

        if mine >= target:
            return Reply(ACCEPT, player_offer, self._accept_line(mine, target))

        if final_round:
            if mine >= self.walkaway:
                return Reply(ACCEPT, player_offer, self._reluctant_line())
            return Reply(NO_DEAL, None, self._walk_line(mine))

        if mine < self.walkaway - 12:
            self.insults += 1

        ceiling = self.last_counter.score(SELLER) if self.last_counter else None
        counter = self._pick(target, ceiling)
        # Never counter with something worth LESS to the buyer than last time;
        # a negotiator who goes backwards is just wasting the clock.
        if self.last_counter is not None and self._preference_guess(counter) < self._preference_guess(self.last_counter):
            counter = self.last_counter
        moved = self._describe_move(self.last_counter, counter)
        self.last_counter = counter
        return Reply(COUNTER, counter, self._counter_line(mine, moved, round_no))

    # -- flavour text ------------------------------------------------------

    def _describe_move(self, before: Offer | None, after: Offer) -> str | None:
        if before is None:
            return None
        for issue in self.scenario.issues:
            a, b = before.option_for(issue.key), after.option_for(issue.key)
            if a.key != b.key:
                return f"{issue.label.lower()} to {b.label}"
        return None

    def _accept_line(self, mine: int, target: int) -> str:
        if mine >= target + 10:
            return self.rng.choice([
                "Done. I'll have paper drawn up this afternoon.",
                "That works for us. Let's sign it before either of us thinks harder.",
                "Agreed. Pleasure doing business.",
            ])
        return self.rng.choice([
            "That's within what I can approve. We have a deal.",
            "Alright. It's tighter than I'd like, but I'll take it.",
            "Fine. Let's close on that.",
        ])

    def _reluctant_line(self) -> str:
        return self.rng.choice([
            "It's the last hour and something beats nothing. I'll sign it.",
            "Against my better judgement, and only because the quarter ends Friday: agreed.",
            "I'll take it. Don't tell my board how thin this is.",
        ])

    def _walk_line(self, mine: int) -> str:
        return self.rng.choice([
            "No. I'd rather run the line empty than sign that. We're done here.",
            "That doesn't clear my floor and we're out of time. I'm walking.",
            "I can't make that work at any point on the calendar. Let's part friends.",
        ])

    def _counter_line(self, mine: int, moved: str | None, round_no: int) -> str:
        pressure = ""
        if round_no >= self.rounds - 1:
            pressure = " And we're nearly out of road here."
        elif round_no >= self.rounds - 2:
            pressure = " I'd like to land this soon."

        if mine < self.walkaway - 12:
            opener = self.rng.choice([
                "That's not in the neighbourhood of workable.",
                "I'll be blunt: that one loses me money.",
                "You're going to have to be serious with me.",
            ])
        elif mine < self.walkaway:
            opener = self.rng.choice([
                "Closer, but it's still under my floor.",
                "I can see what you're doing, but that doesn't clear my bar.",
                "Not yet. That's below what I can sign.",
            ])
        else:
            opener = self.rng.choice([
                "We're in the right area now.",
                "That's signable in principle, but I think I can do better.",
                "Warm. Let me put one more version to you.",
            ])

        if moved:
            return f"{opener} Here's my move: I'll go {moved}.{pressure}"
        return f"{opener} Here's where I am.{pressure}"

    def hint(self) -> str:
        """An honest but self-serving answer to 'what matters most to you?'"""
        ranked = sorted(self.scenario.issues, key=lambda i: -i.stake(SELLER))
        top, second = ranked[0], ranked[1]
        cheap = ranked[-1]
        return (
            f"Honestly? {top.label} is the one that decides whether this deal is "
            f"worth doing for me, with {second.label.lower()} behind it. "
            f"{cheap.label} I have more room on than you'd think. "
            f"Though don't take that as an invitation to squeeze me on price."
        )
