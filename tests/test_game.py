"""Checks on scenario generation and on the supplier's behaviour."""

import random
import unittest

from negosim.analysis import all_offers, judge, viable_offers
from negosim.deal import BUYER, PERFECT_SCORE, SELLER, Offer
from negosim.opponent import ACCEPT, COUNTER, NO_DEAL, SellerAgent
from negosim.products import CATALOG, contract_value, generate_scenario, parse_volume

SEEDS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 500, 777, 999]


class GeneratedScenarios(unittest.TestCase):
    def test_every_seed_gives_each_side_a_perfect_100(self):
        for seed in SEEDS:
            scenario, _, _ = generate_scenario(seed)
            for side in (BUYER, SELLER):
                best = Offer.build(
                    scenario,
                    {i.key: i.best_option(side).key for i in scenario.issues},
                )
                self.assertEqual(best.score(side), PERFECT_SCORE, f"seed {seed}")

    def test_every_seed_has_a_real_zone_of_agreement(self):
        """There must be packages both sides would sign, or the game is rigged."""
        for seed in SEEDS:
            scenario, _, _ = generate_scenario(seed)
            self.assertGreater(len(viable_offers(scenario)), 0, f"seed {seed}")

    def test_the_zone_of_agreement_is_never_a_walkover(self):
        """Most packages should fail somebody, so the player has to work."""
        for seed in SEEDS:
            scenario, _, _ = generate_scenario(seed)
            fraction = len(viable_offers(scenario)) / len(all_offers(scenario))
            self.assertLess(fraction, 0.45, f"seed {seed} was too easy")

    def test_win_win_trades_always_exist(self):
        """The whole lesson depends on the two sides ranking issues differently."""
        for seed in SEEDS:
            scenario, _, _ = generate_scenario(seed)
            buyer_rank = [i.key for i in sorted(scenario.issues, key=lambda i: -i.stake(BUYER))]
            seller_rank = [i.key for i in sorted(scenario.issues, key=lambda i: -i.stake(SELLER))]
            self.assertNotEqual(buyer_rank, seller_rank, f"seed {seed}")

    def test_price_stays_a_pure_tug_of_war(self):
        for seed in SEEDS:
            scenario, _, _ = generate_scenario(seed)
            totals = {
                o.buyer_points + o.seller_points
                for o in scenario.issue("price").options
            }
            self.assertEqual(len(totals), 1, f"seed {seed}")

    def test_volume_is_always_the_sellers_obsession(self):
        for seed in SEEDS:
            scenario, _, _ = generate_scenario(seed)
            volume = scenario.issue("volume")
            self.assertLess(volume.stake(BUYER), volume.stake(SELLER), f"seed {seed}")

    def test_the_same_seed_always_gives_the_same_deal(self):
        a, pa, _ = generate_scenario(4321)
        b, pb, _ = generate_scenario(4321)
        self.assertEqual(a, b)
        self.assertEqual(pa, pb)

    def test_different_seeds_give_different_deals(self):
        products = {generate_scenario(s)[1].item for s in range(40)}
        self.assertGreater(len(products), 3)

    def test_a_seed_is_returned_even_when_not_supplied(self):
        _, _, seed = generate_scenario()
        self.assertIsInstance(seed, int)
        self.assertGreater(seed, 0)

    def test_contract_value_is_price_times_volume(self):
        scenario, product, _ = generate_scenario(7)
        offer = Offer.build(
            scenario,
            {i.key: i.options[0].key for i in scenario.issues},
        )
        price = float(offer.option_for("price").key)
        volume = parse_volume(offer.option_for("volume").key)
        self.assertAlmostEqual(contract_value(offer), price * volume)

    def test_volume_shorthand_round_trips(self):
        self.assertEqual(parse_volume("28k"), 28_000)
        self.assertEqual(parse_volume("2m"), 2_000_000)
        self.assertEqual(parse_volume("900"), 900)

    def test_catalogue_entries_are_well_formed(self):
        for product in CATALOG:
            self.assertGreater(product.mid_price, 0)
            self.assertEqual(len(product.volumes), 4)
            self.assertEqual(sorted(product.volumes), list(product.volumes))


def fresh(seed=42, rounds=8):
    scenario, product, seed = generate_scenario(seed)
    return scenario, SellerAgent(scenario, rounds=rounds, rng=random.Random(seed))


class SellerBehaviour(unittest.TestCase):
    def test_it_opens_greedily_but_not_absurdly(self):
        for seed in SEEDS[:6]:
            _, agent = fresh(seed)
            opening = agent.opening_offer()
            self.assertGreaterEqual(opening.score(SELLER), 88, f"seed {seed}")

    def test_its_demands_fall_every_round(self):
        _, agent = fresh()
        targets = [agent.target(r) for r in range(1, agent.rounds + 1)]
        self.assertEqual(targets, sorted(targets, reverse=True))
        self.assertGreaterEqual(targets[-1], agent.walkaway)

    def test_it_never_signs_below_its_own_walk_away(self):
        for seed in SEEDS[:8]:
            scenario, agent = fresh(seed, rounds=5)
            worst = Offer.build(
                scenario,
                {i.key: i.best_option(BUYER).key for i in scenario.issues},
            )
            for round_no in range(1, 6):
                reply = agent.respond(worst, round_no)
                self.assertNotEqual(reply.kind, ACCEPT, f"seed {seed} round {round_no}")

    def test_it_signs_a_package_that_is_generous_to_it(self):
        scenario, agent = fresh()
        generous = Offer.build(
            scenario,
            {i.key: i.best_option(SELLER).key for i in scenario.issues},
        )
        self.assertEqual(agent.respond(generous, 1).kind, ACCEPT)

    def test_it_concedes_rather_than_hardening(self):
        """Each counter must be worth no more to the seller than the last."""
        scenario, agent = fresh(rounds=8)
        offer = Offer.build(
            scenario, {i.key: i.best_option(BUYER).key for i in scenario.issues}
        )
        previous = agent.opening_offer().score(SELLER)
        for round_no in range(1, 8):
            reply = agent.respond(offer, round_no)
            if reply.kind != COUNTER:
                break
            current = reply.offer.score(SELLER)
            self.assertLessEqual(current, previous, f"hardened in round {round_no}")
            previous = current

    def test_it_walks_at_the_deadline_rather_than_signing_a_loss(self):
        scenario, agent = fresh(rounds=3)
        insulting = Offer.build(
            scenario, {i.key: i.best_option(BUYER).key for i in scenario.issues}
        )
        reply = agent.respond(insulting, 3)
        self.assertEqual(reply.kind, NO_DEAL)

    def test_it_takes_a_thin_deal_at_the_deadline_over_nothing(self):
        scenario, agent = fresh(rounds=3)
        thin = _package_worth(scenario, SELLER, scenario.seller_walkaway)
        reply = agent.respond(thin, 3)
        self.assertEqual(reply.kind, ACCEPT)

    def test_its_hint_names_the_issue_it_truly_cares_about_most(self):
        scenario, agent = fresh()
        top = max(scenario.issues, key=lambda i: i.stake(SELLER))
        self.assertIn(top.label, agent.hint())

    def test_it_learns_which_terms_you_refuse_to_give_up(self):
        """Holding firm on a term should raise the seller's estimate of it."""
        scenario, agent = fresh()
        agent.opening_offer()
        stubborn = Offer.build(
            scenario, {i.key: i.best_option(BUYER).key for i in scenario.issues}
        )
        before = agent.importance["delivery"]
        for round_no in range(1, 4):
            agent.respond(stubborn, round_no)
        self.assertGreater(agent.importance["delivery"], before)

    def test_a_concession_lowers_the_sellers_estimate_of_that_term(self):
        scenario, agent = fresh()
        agent.opening_offer()
        firm = Offer.build(
            scenario, {i.key: i.best_option(BUYER).key for i in scenario.issues}
        )
        agent.respond(firm, 1)
        before = agent.importance["delivery"]
        caved = firm.replace("delivery", scenario.issue("delivery").options[-1].key)
        agent.respond(caved, 2)
        self.assertLess(agent.importance["delivery"], before)


def _package_worth(scenario, side, at_least):
    """Find any package worth at least `at_least` to `side`."""
    best = None
    for offer in all_offers(scenario):
        score = offer.score(side)
        if score >= at_least and (best is None or score < best.score(side)):
            best = offer
    return best


class DealQualityOfPlay(unittest.TestCase):
    def test_a_stubborn_player_gets_no_deal_and_scores_their_walk_away(self):
        """Refusing to move is a strategy, and it is usually a losing one."""
        scenario, agent = fresh(rounds=6)
        agent.opening_offer()
        never_moving = Offer.build(
            scenario, {i.key: i.best_option(BUYER).key for i in scenario.issues}
        )
        outcome = None
        for round_no in range(1, 7):
            outcome = agent.respond(never_moving, round_no)
        self.assertEqual(outcome.kind, NO_DEAL)

    def test_judge_still_works_on_a_generated_scenario(self):
        scenario, _, _ = generate_scenario(99)
        offer = Offer.build(
            scenario, {i.key: i.options[1].key for i in scenario.issues}
        )
        verdict = judge(scenario, offer)
        self.assertGreaterEqual(verdict.value_left_on_table, 0)
        self.assertLessEqual(verdict.efficiency_pct, 100)


if __name__ == "__main__":
    unittest.main()
