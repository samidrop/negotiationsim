"""Checks on the character: their face, their personality, and their words."""

import random
import unittest

from negosim import banter, intent, portrait as X, ui
from negosim import persona as P
from negosim.character import generate_character, random_look
from negosim.deal import BUYER, SELLER, Offer
from negosim.opponent import ACCEPT, COUNTER, NO_DEAL, RAGE_QUIT, SellerAgent
from negosim.persona import PERSONAS
from negosim.products import generate_scenario

SITUATIONS = (P.OPEN, P.INSULT, P.BELOW, P.CLOSE, P.ACCEPT, P.THIN,
              P.DELIGHT, P.RAGE, P.WALK, P.PRESSED, P.THREAT, P.SMALLTALK)


class Portraits(unittest.TestCase):
    def test_every_expression_draws_without_crashing(self):
        rng = random.Random(1)
        for _ in range(25):
            look = random_look(rng)
            for expression in X.EXPRESSIONS:
                lines = X.draw(look, expression)
                self.assertEqual(len(lines), X.HEIGHT, expression)

    def test_every_hair_style_and_accessory_draws(self):
        base = random_look(random.Random(2))
        import dataclasses
        for hair in X.HAIR_STYLES:
            X.draw(dataclasses.replace(base, hair=hair))
        for accessory in set(X.ACCESSORIES):
            X.draw(dataclasses.replace(base, accessory=accessory))
        for facial in set(X.FACIAL_HAIR):
            X.draw(dataclasses.replace(base, facial_hair=facial))
        for eyewear in set(X.EYEWEAR):
            X.draw(dataclasses.replace(base, eyewear=eyewear))
        for name, cut in X.ATTIRE:
            X.draw(dataclasses.replace(base, attire_name=name, attire_cut=cut))

    def test_a_portrait_never_exceeds_its_column(self):
        """It sits beside text, so an over-wide line would break the layout."""
        was = ui.colour_enabled()
        try:
            for enabled in (True, False):
                ui.set_colour(enabled)
                rng = random.Random(5)
                for _ in range(20):
                    look = random_look(rng)
                    for expression in X.EXPRESSIONS:
                        for line in X.draw(look, expression):
                            self.assertLessEqual(ui.visible_len(line), X.WIDTH)
        finally:
            ui.set_colour(was)

    def test_expressions_actually_differ(self):
        look = random_look(random.Random(3))
        was = ui.colour_enabled()
        try:
            ui.set_colour(False)
            rendered = {e: "\n".join(X.draw(look, e)) for e in X.EXPRESSIONS}
            self.assertGreater(len(set(rendered.values())), 8)
            self.assertNotEqual(rendered[X.FURIOUS], rendered[X.DELIGHTED])
        finally:
            ui.set_colour(was)

    def test_skin_tones_span_a_wide_range(self):
        self.assertGreaterEqual(len(set(X.SKIN_TONES)), 6)


class CharacterGeneration(unittest.TestCase):
    def test_appearance_is_independent_of_personality(self):
        """No personality should be tied to any look. Anyone can be anyone."""
        seen: dict[str, set] = {}
        rng = random.Random(0)
        for _ in range(600):
            person = generate_character(rng, "Testing Co.")
            seen.setdefault(person.persona.key, set()).add(person.look.skin)
        for key, tones in seen.items():
            self.assertGreater(len(tones), 3, f"{key} was drawn too narrowly")

    def test_every_personality_can_appear(self):
        rng = random.Random(4)
        drawn = {generate_character(rng, "Testing Co.").persona.key for _ in range(400)}
        self.assertEqual(drawn, {p.key for p in PERSONAS})

    def test_names_vary(self):
        rng = random.Random(6)
        names = {generate_character(rng, "Testing Co.").name for _ in range(60)}
        self.assertGreater(len(names), 40)

    def test_appearance_description_reads_as_english(self):
        rng = random.Random(8)
        for _ in range(40):
            text = generate_character(rng, "Testing Co.").describe_appearance()
            self.assertTrue(text)
            self.assertNotIn("none", text)


class Personalities(unittest.TestCase):
    def test_every_persona_has_a_line_for_every_situation(self):
        for person in PERSONAS:
            for situation in SITUATIONS:
                pool = person.lines.get(situation)
                self.assertTrue(pool, f"{person.key} has nothing for {situation}")
                for line in pool:
                    self.assertTrue(line.strip())

    def test_personas_are_behaviourally_distinct(self):
        """If they all played the same, there would be nothing to practise."""
        openings = {p.opening_target for p in PERSONAS}
        rates = {p.concession_rate for p in PERSONAS}
        patience = {p.rage_patience for p in PERSONAS}
        self.assertGreater(len(openings), 3)
        self.assertGreater(len(rates), 3)
        self.assertGreater(len(patience), 3)

    def test_every_persona_has_a_face_for_every_situation(self):
        for situation in SITUATIONS:
            self.assertIn(situation, banter.FACE_FOR)
            self.assertIn(banter.FACE_FOR[situation], X.EXPRESSIONS)

    def test_banter_returns_a_line_and_a_valid_face(self):
        rng = random.Random(9)
        person = generate_character(rng, "Testing Co.")
        for situation in SITUATIONS:
            line, face = banter.say(person, situation, rng)
            self.assertTrue(line.strip())
            self.assertIn(face, X.EXPRESSIONS)

    def test_dialogue_avoids_slurs_and_identity_jokes(self):
        """The brief was blunt, not cruel. Guard it with a test."""
        banned = ("race", "racist", "retard", "tranny", "faggot", "nigg",
                  "your mother", "fat ", "ugly")
        for person in PERSONAS:
            for pool in person.lines.values():
                for line in pool:
                    lowered = line.lower()
                    for word in banned:
                        self.assertNotIn(word, lowered, f"{person.key}: {line}")


class PlainEnglish(unittest.TestCase):
    CASES = (
        ("what matters most to you?", intent.ASK_PRIORITIES),
        ("which of these do you actually care about", intent.ASK_PRIORITIES),
        ("why is your price that high", intent.ASK_WHY),
        ("I'll walk away and find another supplier", intent.THREATEN_WALK),
        ("this offer is ridiculous, it's a joke", intent.INSULT),
        ("if you give me net 90 I can do more volume", intent.PROPOSE_TRADE),
        ("I'm flexible on the delivery window", intent.SIGNAL_FLEXIBLE),
        ("let's wrap this up quickly", intent.PRESS_DEADLINE),
        ("how was your weekend", intent.SMALLTALK),
        ("asdfgh qwerty", intent.CONFUSED),
    )

    def test_intents_are_read_correctly(self):
        for text, expected in self.CASES:
            self.assertEqual(intent.classify(text), expected, text)

    def test_empty_input_is_not_an_intent(self):
        self.assertEqual(intent.classify("   "), intent.CONFUSED)

    def test_named_issues_are_picked_out(self):
        keys = ("price", "volume", "payment", "delivery", "exclusivity")
        self.assertEqual(intent.mentioned_issues("I need net 60 terms", keys), ["payment"])
        self.assertIn("delivery", intent.mentioned_issues("lead time is critical", keys))
        self.assertIn("volume", intent.mentioned_issues("I can commit to more units", keys))
        self.assertEqual(intent.mentioned_issues("hello there", keys), [])


def _agent(persona, seed=42, rounds=8):
    scenario, _, _ = generate_scenario(seed)
    return scenario, SellerAgent(scenario, rounds, random.Random(seed), persona)


class PersonalityDrivesBehaviour(unittest.TestCase):
    def test_a_short_fuse_blows_up_sooner_than_a_long_one(self):
        greedy_terms = None
        results = {}
        for person in (P.VOLATILE, P.QUANT):
            scenario, agent = _agent(person)
            agent.opening_offer()
            greedy_terms = {i.key: i.best_option(BUYER).key for i in scenario.issues}
            lowball = Offer.build(scenario, greedy_terms)
            rounds_survived = 0
            for round_no in range(1, 9):
                reply = agent.respond(lowball, round_no)
                rounds_survived = round_no
                if reply.kind == RAGE_QUIT:
                    break
            results[person.key] = rounds_survived
        self.assertLess(results["volatile"], results["quant"])

    def test_an_outrageous_lowball_counts_double(self):
        scenario, agent = _agent(P.PRO)
        mild = _offer_worth(scenario, SELLER, scenario.seller_walkaway - 20)
        savage = Offer.build(
            scenario, {i.key: i.best_option(BUYER).key for i in scenario.issues})
        self.assertGreaterEqual(agent.is_insulting(savage), agent.is_insulting(mild))
        self.assertEqual(agent.is_insulting(savage), 2)

    def test_overpaying_wildly_is_snapped_up_on_the_spot(self):
        for person in PERSONAS:
            scenario, agent = _agent(person)
            gift = Offer.build(
                scenario, {i.key: i.best_option(SELLER).key for i in scenario.issues})
            reply = agent.respond(gift, 1)
            self.assertEqual(reply.kind, ACCEPT, person.key)
            self.assertEqual(reply.situation, P.DELIGHT, person.key)

    def test_a_stubborn_persona_concedes_more_slowly(self):
        _, shark = _agent(P.SHARK)
        _, burnout = _agent(P.BURNOUT)
        self.assertGreater(shark.target(4), burnout.target(4))

    def test_no_persona_ever_signs_below_its_floor_before_the_deadline(self):
        for person in PERSONAS:
            scenario, agent = _agent(person, rounds=6)
            thin = _offer_worth(scenario, SELLER, scenario.seller_walkaway - 1)
            if thin is None:
                continue
            for round_no in range(1, 6):
                reply = agent.respond(thin, round_no)
                if reply.kind == ACCEPT:
                    self.fail(f"{person.key} accepted below its floor")
                if reply.kind == RAGE_QUIT:
                    break

    def test_a_dishonest_persona_sometimes_misdirects_you(self):
        """The Shark should not reliably tell you what it actually wants."""
        scenario, agent = _agent(P.SHARK)
        top = max(scenario.issues, key=lambda i: i.stake(SELLER)).label
        answers = [agent.hint() for _ in range(40)]
        truthful = sum(1 for a in answers if a.startswith(top))
        self.assertLess(truthful, len(answers))

    def test_an_honest_persona_usually_tells_you_the_truth(self):
        scenario, agent = _agent(P.QUANT)
        top = max(scenario.issues, key=lambda i: i.stake(SELLER)).label
        answers = [agent.hint() for _ in range(40)]
        truthful = sum(1 for a in answers if a.startswith(top))
        self.assertGreater(truthful, len(answers) // 2)


def _offer_worth(scenario, side, target):
    from negosim.analysis import all_offers
    best = None
    for offer in all_offers(scenario):
        score = offer.score(side)
        if score <= target and (best is None or score > best.score(side)):
            best = offer
    return best


class LiveModelIsOptional(unittest.TestCase):
    def test_status_reports_cleanly_either_way(self):
        from negosim import llm
        available, message = llm.status()
        self.assertIsInstance(available, bool)
        self.assertTrue(message)

    def test_the_game_still_speaks_with_the_model_switched_off(self):
        import os
        from negosim import llm
        was = os.environ.get("NEGOSIM_NO_LLM")
        os.environ["NEGOSIM_NO_LLM"] = "1"
        try:
            llm._state = "unknown"
            rng = random.Random(11)
            person = generate_character(rng, "Testing Co.")
            line, face = banter.say(person, P.OPEN, rng)
            self.assertTrue(line.strip())
            self.assertIn(face, X.EXPRESSIONS)
        finally:
            llm._state = "unknown"
            if was is None:
                os.environ.pop("NEGOSIM_NO_LLM", None)
            else:
                os.environ["NEGOSIM_NO_LLM"] = was


if __name__ == "__main__":
    unittest.main()
