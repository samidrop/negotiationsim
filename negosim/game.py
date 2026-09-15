"""The playable negotiation: rounds, menus, offers, and walking away."""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass

from . import hud, ui
from .analysis import judge
from .deal import BUYER, SELLER, Offer, Scenario
from .opponent import ACCEPT, COUNTER, NO_DEAL, SellerAgent
from .products import Product, contract_value, generate_scenario
from .sheet import offer_card, scoresheet

SIGNED = "signed"
YOU_WALKED = "you_walked"
THEY_WALKED = "they_walked"
TIME_OUT = "time_out"
QUIT = "quit"


def _tidy(role: str) -> str:
    """Company names like 'Supply Co.' already end in a full stop."""
    return role.rstrip(".")


@dataclass
class Outcome:
    kind: str
    offer: Offer | None
    rounds_used: int
    scenario: Scenario
    product: Product
    seed: int
    history: list[tuple[str, Offer]]

    @property
    def is_deal(self) -> bool:
        return self.kind == SIGNED

    def buyer_score(self) -> int:
        if self.offer is None:
            return self.scenario.buyer_walkaway
        return self.offer.score(BUYER)

    def seller_score(self) -> int:
        if self.offer is None:
            return self.scenario.seller_walkaway
        return self.offer.score(SELLER)


class QuitGame(Exception):
    pass


class Game:
    def __init__(
        self,
        scenario: Scenario,
        product: Product,
        seed: int,
        rounds: int = 8,
        rng: random.Random | None = None,
    ):
        self.scenario = scenario
        self.product = product
        self.seed = seed
        self.rounds = rounds
        self.rng = rng or random.Random(seed)
        self.seller = SellerAgent(scenario, rounds=rounds, rng=self.rng)
        self.on_table: Offer | None = None      # their live offer
        self.your_offer: Offer | None = None    # your last package
        self.history: list[tuple[str, Offer]] = []
        self.round = 1

    # -- input -------------------------------------------------------------

    def ask(self, prompt: str) -> str:
        try:
            return input(ui.paint(prompt, "bold")).strip()
        except EOFError:
            raise QuitGame() from None
        except KeyboardInterrupt:
            print()
            raise QuitGame() from None

    def say(self, text: str = "") -> None:
        print(text)

    # -- screens -----------------------------------------------------------

    def show_intro(self) -> None:
        s = self.scenario
        self.say(ui.heading(s.name))
        self.say(ui.wrap(f"You are {ui.paint(_tidy(s.buyer_role), 'bold')}."))
        self.say("")
        self.say(ui.wrap(s.buyer_brief))
        self.say("")
        self.say(ui.wrap(
            f"Across the table: {ui.paint(_tidy(s.seller_role), 'bold')}. They have their own "
            f"scoresheet and you cannot see it. It is weighted differently from "
            f"yours, which means there are packages that are better for both of "
            f"you than the obvious compromise."
        ))
        self.say("")
        self.say(ui.wrap(
            f"You have {ui.paint(str(self.rounds), 'bold')} rounds. Your walk-away score is "
            f"{ui.paint(str(s.buyer_walkaway), 'bold')} out of 100 -- if you sign for less than "
            f"that, you did worse than not signing at all. Walking away scores you "
            f"exactly {s.buyer_walkaway}."
        ))
        self.say("")
        self.say(ui.paint(f"(deal seed {self.seed} -- replay this exact deal with --seed {self.seed})", "dim"))

    def show_table(self) -> None:
        main: list[str] = []
        if self.on_table is not None:
            main.append(ui.paint("THEIR OFFER ON THE TABLE", "bold", "yellow"))
            main.append(ui.paint(f"  {'term':<17} {'value':<20} {'pts':>3}", "dim"))
            main.append("")
            for label, value in self.on_table.labels():
                pts = self.on_table.option_for(
                    [k for k in self.scenario.issue_keys
                     if self.scenario.issue(k).label == label][0]
                ).points_for(BUYER)
                main.append(f"  {label:<17} {value:<20} {pts:>3}")
            main.append("")
            main.append(ui.paint(
                f"  Worth {self.on_table.score(BUYER)} to you.", "bold"
            ))
        if self.your_offer is not None:
            main.append("")
            main.append(ui.paint("YOUR LAST OFFER", "bold", "cyan"))
            main.append(f"  worth {self.your_offer.score(BUYER)} to you")
            for label, value in self.your_offer.labels():
                main.append(f"  {label:<17} {value}")
        side = hud.sidebar(
            self.scenario, self.product, self.on_table, self.your_offer,
            self.round, self.rounds,
        )
        self.say("")
        self.say(hud.view(main, side))

    # -- building an offer -------------------------------------------------

    def build_offer(self) -> Offer | None:
        """Walk through the five issues, one menu at a time."""
        base = self.your_offer or self.on_table
        choices: dict[str, str] = {}
        self.say(ui.heading("build your offer"))
        self.say(ui.wrap(
            "Pick a number for each term. Press Enter to keep what is shown in "
            "brackets. Type 'x' at any point to abandon this offer."
        ))
        for issue in self.scenario.issues:
            default = base.option_for(issue.key).key if base else issue.options[0].key
            theirs = self.on_table.option_for(issue.key).key if self.on_table else None
            mine = self.your_offer.option_for(issue.key).key if self.your_offer else None

            self.say(ui.subheading(f"{issue.label}  ({issue.stake(BUYER)} pts at stake for you)"))
            for n, option in enumerate(issue.options, 1):
                tags = []
                if option.key == theirs:
                    tags.append(ui.paint("their offer", "yellow"))
                if option.key == mine:
                    tags.append(ui.paint("your last", "cyan"))
                tag = ("  <- " + ", ".join(tags)) if tags else ""
                self.say(f"  {n}. {option.label:<36} {option.points_for(BUYER):>3} pts{tag}")

            default_label = issue.option(default).label
            while True:
                raw = self.ask(f"  choose 1-{len(issue.options)} [Enter = {default_label}]: ")
                if raw.lower() == "x":
                    self.say(ui.paint("Offer abandoned.", "dim"))
                    return None
                if raw == "":
                    choices[issue.key] = default
                    break
                if raw.isdigit() and 1 <= int(raw) <= len(issue.options):
                    choices[issue.key] = issue.options[int(raw) - 1].key
                    break
                self.say(ui.paint("  (type one of the numbers, or Enter)", "red"))

        offer = Offer.build(self.scenario, choices)
        self.say(offer_card(offer, BUYER, title="Your package"))
        self.say(f"  Estimated annual value: {ui.paint(f'${contract_value(offer):,.0f}', 'cyan')}")
        if offer.score(BUYER) < self.scenario.buyer_walkaway:
            self.say(ui.paint(
                f"  Careful: {offer.score(BUYER)} is below your own walk-away of "
                f"{self.scenario.buyer_walkaway}. You would be signing a loss.", "red"
            ))
        confirm = self.ask("  Send this offer? [Y/n]: ").lower()
        if confirm in ("n", "no"):
            self.say(ui.paint("Not sent.", "dim"))
            return None
        return offer

    # -- the loop ----------------------------------------------------------

    def play(self) -> Outcome:
        self.show_intro()
        self.on_table = self.seller.opening_offer()
        self.history.append(("them", self.on_table))
        self.say(ui.subheading(f"{self.scenario.seller_role} opens:"))
        self.say(ui.wrap(
            '"Here is where we start. I have been generous already." ', "  "
        ))

        try:
            return self._rounds()
        except QuitGame:
            self.say(ui.paint("\nLeaving the table. Nothing was signed.", "dim"))
            return Outcome(QUIT, None, self.round, self.scenario, self.product,
                           self.seed, self.history)

    def _rounds(self) -> Outcome:
        while self.round <= self.rounds:
            self.show_table()
            self.say(ui.subheading("What do you want to do?"))
            self.say("  1. Make a counter-offer")
            self.say("  2. Accept their offer")
            self.say("  3. Ask what matters most to them")
            self.say("  4. Re-read my confidential brief")
            self.say("  5. Walk away from the deal")
            choice = self.ask("  > ")

            if choice == "1":
                outcome = self._counter()
                if outcome:
                    return outcome
            elif choice == "2":
                return self._accept()
            elif choice == "3":
                self.say(ui.subheading(f"{self.scenario.seller_role}:"))
                self.say(ui.wrap(f'"{self.seller.hint()}"', "  "))
                self.say(ui.paint(
                    "  (Asking cost you nothing. Most people never ask.)", "dim"))
            elif choice == "4":
                self.say(scoresheet(self.scenario, BUYER))
            elif choice == "5":
                if self._confirm_walk():
                    return Outcome(YOU_WALKED, None, self.round, self.scenario,
                                   self.product, self.seed, self.history)
            else:
                self.say(ui.paint("  (type 1, 2, 3, 4 or 5)", "red"))

        # Clock ran out with nothing signed.
        self.say(ui.paint("\nThe clock runs out. No agreement was reached.", "red"))
        return Outcome(TIME_OUT, None, self.rounds, self.scenario, self.product,
                       self.seed, self.history)

    def _counter(self) -> Outcome | None:
        offer = self.build_offer()
        if offer is None:
            return None
        self.your_offer = offer
        self.history.append(("you", offer))

        reply = self.seller.respond(offer, self.round)
        self.say(ui.subheading(f"{self.scenario.seller_role}:"))
        self.say(ui.wrap(f'"{reply.message}"', "  "))

        if reply.kind == ACCEPT:
            self.say(ui.paint("\n  *** They signed your package. ***", "bold", "green"))
            return Outcome(SIGNED, offer, self.round, self.scenario, self.product,
                           self.seed, self.history)
        if reply.kind == NO_DEAL:
            return Outcome(THEY_WALKED, None, self.round, self.scenario,
                           self.product, self.seed, self.history)

        self.on_table = reply.offer
        self.history.append(("them", reply.offer))
        self.round += 1
        return None

    def _accept(self) -> Outcome:
        assert self.on_table is not None
        score = self.on_table.score(BUYER)
        if score < self.scenario.buyer_walkaway:
            self.say(ui.paint(
                f"\n  That package is worth {score} to you and your walk-away is "
                f"{self.scenario.buyer_walkaway}. Signing it is worse than signing nothing.",
                "red",
            ))
            if self.ask("  Sign it anyway? [y/N]: ").lower() not in ("y", "yes"):
                return self._continue_marker()
        self.say(ui.paint("\n  *** You signed their package. ***", "bold", "green"))
        return Outcome(SIGNED, self.on_table, self.round, self.scenario,
                       self.product, self.seed, self.history)

    def _continue_marker(self) -> Outcome:
        """Used when the player backs out of accepting; resumes the loop."""
        return self._rounds()

    def _confirm_walk(self) -> bool:
        wa = self.scenario.buyer_walkaway
        best = self.on_table.score(BUYER) if self.on_table else 0
        self.say(ui.wrap(
            f"Walking away scores you {wa}. Their current offer is worth {best}. "
            + ("Walking is the better of the two." if wa > best
               else "Their offer already beats walking away."),
            "  ",
        ))
        return self.ask("  Really walk? [y/N]: ").lower() in ("y", "yes")


def summarise(outcome: Outcome) -> str:
    """The plain scoreboard. The full coaching debrief comes later."""
    s = outcome.scenario
    out = [ui.heading("result")]

    headline = {
        SIGNED: "Deal signed.",
        YOU_WALKED: "You walked away. No deal.",
        THEY_WALKED: "They walked away. No deal.",
        TIME_OUT: "Time ran out. No deal.",
        QUIT: "You left the table.",
    }[outcome.kind]
    out.append(ui.paint(headline, "bold"))

    if outcome.offer is not None:
        out.append(offer_card(outcome.offer, BUYER, title="The signed package"))
        out.append(f"\n  Annual contract value: ${contract_value(outcome.offer):,.0f}")

    buyer, seller = outcome.buyer_score(), outcome.seller_score()
    rows = [
        ["You", str(buyer), str(s.buyer_walkaway), str(buyer - s.buyer_walkaway)],
        ["Them", str(seller), str(s.seller_walkaway), str(seller - s.seller_walkaway)],
    ]
    out.append("")
    out.append(ui.table(["side", "score", "walk-away", "gain vs walking"], rows, "lrrr"))

    if outcome.offer is not None:
        verdict = judge(s, outcome.offer)
        out.append("")
        out.append(f"Joint score    {verdict.joint_score} of a possible {verdict.max_joint}")
        left = verdict.value_left_on_table
        if left:
            out.append(ui.paint(
                f"Left on table  {left} points that BOTH of you could have had", "yellow"
            ))
        else:
            out.append(ui.paint("Left on table  nothing. That deal was efficient.", "green"))
    else:
        out.append(ui.paint(
            "\nNo deal means you both fall back to your walk-away. Sometimes that is "
            "the right call. Often it is value neither side could find.", "dim"
        ))
    out.append(ui.paint(f"\n(replay this deal: --seed {outcome.seed})", "dim"))
    return "\n".join(out)


def start(seed: int | None = None, rounds: int = 8) -> Outcome:
    scenario, product, seed = generate_scenario(seed)
    game = Game(scenario, product, seed, rounds=rounds)
    outcome = game.play()
    print(summarise(outcome))
    return outcome
