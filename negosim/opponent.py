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

from . import persona as P
from .deal import BUYER, SELLER, Offer, Scenario
from .persona import Persona

ACCEPT = "accept"
COUNTER = "counter"
NO_DEAL = "no_deal"
RAGE_QUIT = "rage_quit"


@dataclass
class Reply:
    """What the seller does, and which situation the game should voice."""

    kind: str
    offer: Offer | None
    situation: str


class SellerAgent:
    """Plays the supplier across a fixed number of rounds."""

    def __init__(self, scenario: Scenario, rounds: int = 8,
                 rng: random.Random | None = None, persona: Persona | None = None):
        self.scenario = scenario
        self.rounds = rounds
        self.rng = rng or random.Random()
        self.persona = persona or P.PRO
        self.walkaway = scenario.seller_walkaway

        # Every package, scored once up front.
        from .analysis import all_offers

        self._catalogue = [(o, o.score(SELLER)) for o in all_offers(scenario)]

        # What the seller believes the buyer cares about. Starts flat and is
        # updated by watching which terms the buyer clings to.
        self.importance: dict[str, float] = {k: 1.0 for k in scenario.issue_keys}
        self.last_player_offer: Offer | None = None
        self.last_counter: Offer | None = None
        self.opening_target = self.persona.opening_target
        self.insults = 0
        self.walked_out = False

    # -- what the seller wants this round ----------------------------------

    def target(self, round_no: int) -> int:
        """Its minimum acceptable score, sliding down as the clock runs.
        A stubborn personality concedes more slowly than a generous one."""
        floor = self.walkaway + 3
        if self.rounds <= 1:
            return floor
        progress = (round_no - 1) / (self.rounds - 1)
        progress = min(1.0, progress * self.persona.concession_rate)
        return round(self.opening_target - (self.opening_target - floor) * progress)

    def is_insulting(self, offer: Offer) -> int:
        """0 if the offer is merely bad, 1 if rude, 2 if outrageous."""
        gap = self.walkaway - offer.score(SELLER)
        if gap < self.persona.insult_margin:
            return 0
        return 2 if gap >= self.persona.insult_margin * 2 else 1

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

        # They have handed over far more than they needed to. Take it, gladly.
        if mine >= self.persona.delight_at:
            return Reply(ACCEPT, player_offer, P.DELIGHT)

        severity = self.is_insulting(player_offer)
        if severity:
            self.insults += severity
            if self.insults > self.persona.rage_patience:
                self.walked_out = True
                return Reply(RAGE_QUIT, None, P.RAGE)
            if not final_round:
                counter = self._advance(target)
                return Reply(COUNTER, counter, P.INSULT)

        if mine >= target:
            return Reply(ACCEPT, player_offer, P.ACCEPT)

        if final_round:
            if mine >= self.walkaway:
                return Reply(ACCEPT, player_offer, P.THIN)
            return Reply(NO_DEAL, None, P.WALK)

        counter = self._advance(target)
        return Reply(COUNTER, counter, P.BELOW if mine < self.walkaway else P.CLOSE)

    def _advance(self, target: int) -> Offer:
        """Produce the next counter, never hardening on the last one."""
        ceiling = self.last_counter.score(SELLER) if self.last_counter else None
        counter = self._pick(target, ceiling)
        if self.last_counter is not None and self._preference_guess(counter) < self._preference_guess(self.last_counter):
            counter = self.last_counter
        self.last_counter = counter
        return counter

    def moved_to(self, before: Offer | None, after: Offer | None) -> str | None:
        if before is None or after is None:
            return None
        return self._describe_move(before, after)

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
        """An answer to 'what matters most to you?'. How straight it is
        depends entirely on who you are talking to."""
        ranked = sorted(self.scenario.issues, key=lambda i: -i.stake(SELLER))
        honest = self.rng.random() < self.persona.hint_honesty
        if honest:
            top, second, cheap = ranked[0], ranked[1], ranked[-1]
            return (
                f"{top.label} is the one that decides whether this is worth doing "
                f"for me, with {second.label.lower()} behind it. {cheap.label} I "
                f"have more room on than you'd think."
            )
        # Not lying exactly. Just pointing at the wrong thing on purpose.
        decoy = ranked[1] if len(ranked) > 1 else ranked[0]
        return (
            f"{decoy.label} is what I'm being measured on this quarter, so that's "
            f"where I'm least flexible. Everything else I can look at."
        )
