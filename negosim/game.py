"""The playable negotiation: rounds, menus, offers, talking, and walking away."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import banter, coach, hud, intent, persona as P, portrait as X, ui
from .analysis import judge
from .character import Character, generate_character
from .deal import BUYER, SELLER, Offer, Scenario
from .opponent import ACCEPT, COUNTER, NO_DEAL, RAGE_QUIT, SellerAgent
from .products import Product, contract_value, generate_scenario
from .sheet import offer_card, scoresheet

SIGNED = "signed"
YOU_WALKED = "you_walked"
THEY_WALKED = "they_walked"
THEY_RAGED = "they_raged"
TIME_OUT = "time_out"
QUIT = "quit"

PORTRAIT_COLUMN = X.WIDTH + 2


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
    character: Character
    seed: int
    history: list[tuple[str, Offer]] = field(default_factory=list)
    fleeced: bool = False      # they gleefully accepted; you overpaid badly
    log: "coach.PlayLog" = field(default_factory=lambda: coach.PlayLog())

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
    def __init__(self, scenario: Scenario, product: Product, character: Character,
                 seed: int, rounds: int = 8, rng: random.Random | None = None):
        self.scenario = scenario
        self.product = product
        self.character = character
        self.seed = seed
        self.rounds = rounds
        self.rng = rng or random.Random(seed)
        self.seller = SellerAgent(scenario, rounds=rounds, rng=self.rng,
                                  persona=character.persona)
        self.on_table: Offer | None = None
        self.your_offer: Offer | None = None
        self.history: list[tuple[str, Offer]] = []
        self.round = 1
        self.log = coach.PlayLog(rounds_available=rounds)

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

    # -- the character speaking -------------------------------------------

    def _context(self) -> dict:
        return {
            "product": self.product.item,
            "round_no": self.round,
            "rounds_total": self.rounds,
            "their_offer": self.on_table.summary() if self.on_table else "not yet tabled",
            "player_offer": self.your_offer.summary() if self.your_offer else None,
        }

    def speak(self, situation: str, player_said: str | None = None,
              extra: str | None = None) -> None:
        line, expression = banter.say(
            self.character, situation, self.rng,
            context=self._context(), player_said=player_said,
        )
        self.render_speech(line, expression, extra)

    def render_speech(self, line: str, expression: str, extra: str | None = None) -> None:
        face = self.character.portrait(expression)
        width = ui.WIDTH - PORTRAIT_COLUMN - 3
        right = [ui.paint(self.character.name, "bold"),
                 ui.paint(f"{self.character.title}, {_tidy(self.character.company)}", "dim"),
                 ""]
        import textwrap
        right += textwrap.wrap(f'"{line}"', width=width) or [""]
        if extra:
            right += [""] + textwrap.wrap(extra, width=width)
        self.say("")
        self.say(ui.columns(face, right, PORTRAIT_COLUMN))

    # -- screens -----------------------------------------------------------

    def show_intro(self) -> None:
        s = self.scenario
        self.say(ui.heading(s.name))
        self.say(ui.wrap(f"You are {ui.paint(_tidy(s.buyer_role), 'bold')}."))
        self.say("")
        self.say(ui.wrap(s.buyer_brief))
        self.say("")
        self.say(ui.wrap(
            f"You have {ui.paint(str(self.rounds), 'bold')} rounds. Your walk-away score is "
            f"{ui.paint(str(s.buyer_walkaway), 'bold')} out of 100. Sign for less than that and "
            f"you did worse than not signing at all."
        ))
        self.render_speech(
            "Right. Let's get into it.", self.character.persona.resting_face,
            extra=(f"Across the table: {self.character.name}. "
                   f"{self.character.describe_appearance().capitalize()}. "
                   f"You have not met them before and you do not know how they negotiate. "
                   f"Find out."),
        )
        self.say("")
        self.say(ui.paint(f"(deal seed {self.seed} -- replay with --seed {self.seed})", "dim"))

    def show_table(self) -> None:
        main: list[str] = []
        if self.on_table is not None:
            main.append(ui.paint("THEIR OFFER ON THE TABLE", "bold", "yellow"))
            main.append(ui.paint(f"  {'term':<17} {'value':<20} {'pts':>3}", "dim"))
            for key in self.scenario.issue_keys:
                issue = self.scenario.issue(key)
                option = self.on_table.option_for(key)
                main.append(f"  {issue.label[:17]:<17} {option.label[:20]:<20} "
                            f"{option.points_for(BUYER):>3}")
            main.append("")
            main.append(ui.paint(f"  Worth {self.on_table.score(BUYER)} to you.", "bold"))
        if self.your_offer is not None:
            main.append("")
            main.append(ui.paint("YOUR LAST OFFER", "bold", "cyan"))
            main.append(f"  worth {self.your_offer.score(BUYER)} to you")
            for key in self.scenario.issue_keys:
                main.append(f"  {self.scenario.issue(key).label[:17]:<17} "
                            f"{self.your_offer.option_for(key).label[:20]}")
        side = hud.sidebar(self.scenario, self.product, self.on_table,
                           self.your_offer, self.round, self.rounds)
        self.say("")
        self.say(hud.view(main, side))

    # -- building an offer -------------------------------------------------

    def build_offer(self) -> Offer | None:
        base = self.your_offer or self.on_table
        choices: dict[str, str] = {}
        self.say(ui.heading("build your offer"))
        self.say(ui.wrap(
            "Pick a number for each term. Press Enter to keep what is shown in "
            "brackets. Type 'x' to abandon this offer."
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

            while True:
                raw = self.ask(f"  choose 1-{len(issue.options)} "
                               f"[Enter = {issue.option(default).label}]: ")
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
        self.say(f"  Estimated annual value: "
                 f"{ui.paint(f'${contract_value(offer):,.0f}', 'cyan')}")
        if offer.score(BUYER) < self.scenario.buyer_walkaway:
            self.say(ui.paint(
                f"  Careful: {offer.score(BUYER)} is below your own walk-away of "
                f"{self.scenario.buyer_walkaway}. You would be signing a loss.", "red"))
        if self.ask("  Send this offer? [Y/n]: ").lower() in ("n", "no"):
            self.say(ui.paint("Not sent.", "dim"))
            return None
        return offer

    # -- talking -----------------------------------------------------------

    def talk(self) -> None:
        """Say something in plain English and see how they take it."""
        self.say(ui.subheading("Say something to them"))
        self.say(ui.paint("  (plain English -- ask a question, push back, make a threat, "
                          "be charming. Enter to cancel.)", "dim"))
        text = self.ask("  you: ")
        if not text:
            return
        self.things_said += 1
        meaning = intent.classify(text)
        named = intent.mentioned_issues(text, self.scenario.issue_keys)

        if meaning == intent.ASK_PRIORITIES:
            self.log.asked_priorities = True
            self.render_speech(
                self.seller.hint(), X.THINKING,
                extra="You asked what drives them. Whether that was the truth "
                      "is your problem to work out.")
            return

        situation, note = self._consequence(meaning, named)
        self.speak(situation, player_said=text)
        if note:
            self.say(ui.paint(f"  {note}", "dim"))

    def _consequence(self, meaning: str, named: list[str]) -> tuple[str, str | None]:
        """What talking actually DOES. Words have mechanical weight here."""
        seller = self.seller
        if meaning == intent.ASK_WHY:
            return P.PRESSED, None
        if meaning == intent.THREATEN_WALK:
            return P.THREAT, "Threats are cheap. They only work if they think you mean it."
        if meaning == intent.INSULT:
            seller.insults += 1
            self.log.insults_given += 1
            return P.INSULT, "That cost you goodwill. Some people have very little to spare."
        if meaning == intent.FLATTER:
            seller.insults = max(0, seller.insults - 1)
            self.log.warmth_given += 1
            return P.SMALLTALK, "Warmth is free and it buys you patience."
        if meaning == intent.SIGNAL_FLEXIBLE:
            for key in named:
                seller.importance[key] = max(0.3, seller.importance[key] - 1.2)
                if key not in self.log.revealed_flexibility:
                    self.log.revealed_flexibility.append(key)
            if named:
                labels = ", ".join(self.scenario.issue(k).label.lower() for k in named)
                return P.SMALLTALK, (f"You just told them you don't care about {labels}. "
                                     f"They will stop paying you for it.")
            return P.SMALLTALK, "You signalled flexibility without saying where. That is safer."
        if meaning == intent.PROPOSE_TRADE:
            for key in named:
                seller.importance[key] += 0.8
                if key not in self.log.trades_proposed:
                    self.log.trades_proposed.append(key)
            if named:
                labels = ", ".join(self.scenario.issue(k).label.lower() for k in named)
                return P.CLOSE, (f"You flagged {labels} as something you want. "
                                 f"Now put it in an actual offer.")
            return P.CLOSE, "Naming a trade out loud is good. Now table it as an offer."
        if meaning == intent.PRESS_DEADLINE:
            return P.STALL, None
        if meaning == intent.SMALLTALK:
            return P.SMALLTALK, None
        return P.SMALLTALK, None

    # -- the loop ----------------------------------------------------------

    def play(self) -> Outcome:
        self.show_intro()
        self.on_table = self.seller.opening_offer()
        self.history.append(("them", self.on_table))
        self.speak(P.OPEN)
        try:
            return self._rounds()
        except QuitGame:
            self.say(ui.paint("\nLeaving the table. Nothing was signed.", "dim"))
            return self._outcome(QUIT, None)

    def _outcome(self, kind: str, offer: Offer | None, fleeced: bool = False) -> Outcome:
        self.log.rounds_used = self.round
        return Outcome(kind, offer, self.round, self.scenario, self.product,
                       self.character, self.seed, self.history, fleeced, self.log)

    def _rounds(self) -> Outcome:
        while self.round <= self.rounds:
            self.show_table()
            self.say(ui.subheading("What do you want to do?"))
            self.say("  1. Make a counter-offer")
            self.say("  2. Accept their offer")
            self.say("  3. Ask what matters most to them")
            self.say("  4. Say something to them (plain English)")
            self.say("  5. Re-read my confidential brief")
            self.say("  6. Walk away from the deal")
            choice = self.ask("  > ")

            if choice == "1":
                outcome = self._counter()
                if outcome:
                    return outcome
            elif choice == "2":
                outcome = self._accept()
                if outcome:
                    return outcome
            elif choice == "3":
                self.log.asked_priorities = True
                self.render_speech(self.seller.hint(), X.THINKING,
                                   extra="Asking cost you nothing. Most people never ask.")
            elif choice == "4":
                self.talk()
            elif choice == "5":
                self.say(scoresheet(self.scenario, BUYER))
            elif choice == "6":
                if self._confirm_walk():
                    return self._outcome(YOU_WALKED, None)
            else:
                self.say(ui.paint("  (type a number from 1 to 6)", "red"))

        self.say(ui.paint("\nThe clock runs out. No agreement was reached.", "red"))
        return self._outcome(TIME_OUT, None)

    def _counter(self) -> Outcome | None:
        offer = self.build_offer()
        if offer is None:
            return None
        self.your_offer = offer
        self.history.append(("you", offer))
        self.log.your_offers.append(offer)

        before = self.seller.last_counter
        reply = self.seller.respond(offer, self.round)
        self.speak(reply.situation)
        # Only a counter-offer represents a movement worth naming.
        if reply.kind == COUNTER:
            moved = self.seller.moved_to(before, reply.offer)
            if moved:
                self.say(ui.paint(f"  They moved: {moved}.", "dim"))

        if reply.kind == ACCEPT:
            fleeced = reply.situation == P.DELIGHT
            self.say(ui.paint("\n  *** They signed your package. ***", "bold", "green"))
            if fleeced:
                self.say(ui.paint(
                    "  They could not sign it fast enough. That is never a good sign.",
                    "yellow"))
            return self._outcome(SIGNED, offer, fleeced)
        if reply.kind == RAGE_QUIT:
            self.say(ui.paint(
                "\n  They shove the chair back hard enough to knock it over, sweep the "
                "term sheet off the table and walk out. The door does not close quietly.",
                "bold", "red"))
            return self._outcome(THEY_RAGED, None)
        if reply.kind == NO_DEAL:
            return self._outcome(THEY_WALKED, None)

        self.on_table = reply.offer
        self.history.append(("them", reply.offer))
        self.round += 1
        return None

    def _accept(self) -> Outcome | None:
        assert self.on_table is not None
        score = self.on_table.score(BUYER)
        if score < self.scenario.buyer_walkaway:
            self.say(ui.paint(
                f"\n  That package is worth {score} to you and your walk-away is "
                f"{self.scenario.buyer_walkaway}. Signing it is worse than signing nothing.",
                "red"))
            if self.ask("  Sign it anyway? [y/N]: ").lower() not in ("y", "yes"):
                return None
        self.say(ui.paint("\n  *** You signed their package. ***", "bold", "green"))
        return self._outcome(SIGNED, self.on_table)

    def _confirm_walk(self) -> bool:
        wa = self.scenario.buyer_walkaway
        best = self.on_table.score(BUYER) if self.on_table else 0
        self.say(ui.wrap(
            f"Walking away scores you {wa}. Their current offer is worth {best}. "
            + ("Walking is the better of the two." if wa > best
               else "Their offer already beats walking away."), "  "))
        return self.ask("  Really walk? [y/N]: ").lower() in ("y", "yes")


# -- the scoreboard --------------------------------------------------------

HEADLINES = {
    SIGNED: "Deal signed.",
    YOU_WALKED: "You walked away. No deal.",
    THEY_WALKED: "They walked away. No deal.",
    THEY_RAGED: "They lost their temper and walked out. No deal.",
    TIME_OUT: "Time ran out. No deal.",
    QUIT: "You left the table.",
}


def summarise(outcome: Outcome) -> str:
    s = outcome.scenario
    out = [ui.heading("result"), ui.paint(HEADLINES[outcome.kind], "bold")]

    if outcome.offer is not None:
        out.append(offer_card(outcome.offer, BUYER, title="The signed package"))
        out.append(f"\n  Annual contract value: ${contract_value(outcome.offer):,.0f}")

    buyer, seller = outcome.buyer_score(), outcome.seller_score()
    out.append("")
    out.append(ui.table(
        ["side", "score", "walk-away", "gain vs walking"],
        [["You", str(buyer), str(s.buyer_walkaway), str(buyer - s.buyer_walkaway)],
         ["Them", str(seller), str(s.seller_walkaway), str(seller - s.seller_walkaway)]],
        "lrrr"))

    if outcome.offer is not None:
        verdict = judge(s, outcome.offer)
        out.append("")
        out.append(f"Joint score    {verdict.joint_score} of a possible {verdict.max_joint}")
        if verdict.value_left_on_table:
            out.append(ui.paint(
                f"Left on table  {verdict.value_left_on_table} points that BOTH of you "
                f"could have had", "yellow"))
        else:
            out.append(ui.paint("Left on table  nothing. That deal was efficient.", "green"))
    else:
        out.append(ui.paint(
            "\nNo deal means you both fall back to your walk-away.", "dim"))

    person = outcome.character
    out.append(ui.subheading("Who you were actually up against"))
    out.append(f"  {person.name} was {ui.paint(person.persona.name, 'bold')}.")
    out.append(ui.wrap(person.persona.blurb, "  "))
    out.append(ui.wrap(f"Tell: {person.persona.tell}", "  "))
    out.append(ui.paint(f"\n(replay this deal: --seed {outcome.seed})", "dim"))
    return "\n".join(out)


def deliver_epilogue(game: "Game", rev) -> None:
    """They drop the act and tell you what they saw. Still in character."""
    situation = P.EPILOGUE_GOOD if rev.grade in ("A+", "A", "B") else P.EPILOGUE_BAD
    game.speak(situation)


def start(seed: int | None = None, rounds: int = 8) -> Outcome:
    scenario, product, seed = generate_scenario(seed)
    rng = random.Random(seed)
    company = scenario.seller_role.split(", ", 1)[-1]
    character = generate_character(rng, company)
    game = Game(scenario, product, character, seed, rounds=rounds, rng=rng)
    outcome = game.play()
    print(summarise(outcome))
    rev = coach.review(outcome, outcome.log)
    deliver_epilogue(game, rev)
    print(coach.render(rev))
    return outcome
