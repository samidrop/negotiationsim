"""Checks on the scoring engine and the deal analysis."""

import unittest

from negosim.analysis import (
    all_offers,
    judge,
    max_joint_score,
    missed_improvements,
    pareto_frontier,
    viable_offers,
)
from negosim.deal import BUYER, PERFECT_SCORE, SELLER, SUPPLIER_DEAL, Offer

S = SUPPLIER_DEAL


def offer(**terms):
    return Offer.build(S, terms)


BEST_FOR_BUYER = dict(
    price="18", volume="10k", payment="net90", delivery="2w", exclusivity="global2y"
)
BEST_FOR_SELLER = dict(
    price="26", volume="100k", payment="net15", delivery="12w", exclusivity="none"
)


class ScenarioShape(unittest.TestCase):
    def test_each_side_can_score_exactly_100(self):
        self.assertEqual(offer(**BEST_FOR_BUYER).score(BUYER), PERFECT_SCORE)
        self.assertEqual(offer(**BEST_FOR_SELLER).score(SELLER), PERFECT_SCORE)

    def test_worst_case_is_zero_for_each_side(self):
        self.assertEqual(offer(**BEST_FOR_SELLER).score(BUYER), 0)
        self.assertEqual(offer(**BEST_FOR_BUYER).score(SELLER), 0)

    def test_issue_and_option_keys_are_unique(self):
        self.assertEqual(len(set(S.issue_keys)), len(S.issues))
        for issue in S.issues:
            keys = [o.key for o in issue.options]
            self.assertEqual(len(set(keys)), len(keys), issue.key)

    def test_no_negative_points_anywhere(self):
        for issue in S.issues:
            for option in issue.options:
                self.assertGreaterEqual(option.buyer_points, 0)
                self.assertGreaterEqual(option.seller_points, 0)

    def test_sides_weight_the_issues_differently(self):
        """Without differing weights there would be no win-win trades at all."""
        buyer_rank = sorted(S.issues, key=lambda i: -i.stake(BUYER))
        seller_rank = sorted(S.issues, key=lambda i: -i.stake(SELLER))
        self.assertNotEqual(
            [i.key for i in buyer_rank], [i.key for i in seller_rank]
        )

    def test_volume_is_the_classic_logroll(self):
        """Volume costs the buyer little and is worth a fortune to the seller."""
        volume = S.issue("volume")
        self.assertLess(volume.stake(BUYER), 10)
        self.assertGreater(volume.stake(SELLER), 30)

    def test_price_is_purely_distributive(self):
        """Every price option splits the same total: a pure tug of war."""
        totals = {o.buyer_points + o.seller_points for o in S.issue("price").options}
        self.assertEqual(len(totals), 1)


class OfferValidation(unittest.TestCase):
    def test_missing_issue_is_rejected(self):
        terms = dict(BEST_FOR_BUYER)
        del terms["price"]
        with self.assertRaises(ValueError):
            offer(**terms)

    def test_unknown_option_is_rejected(self):
        terms = dict(BEST_FOR_BUYER, price="99")
        with self.assertRaises(KeyError):
            offer(**terms)

    def test_unknown_issue_is_rejected(self):
        terms = dict(BEST_FOR_BUYER, colour="blue")
        with self.assertRaises(ValueError):
            offer(**terms)

    def test_replace_swaps_one_term_only(self):
        a = offer(**BEST_FOR_BUYER)
        b = a.replace("price", "26")
        self.assertEqual(b.option_for("price").key, "26")
        self.assertEqual(b.option_for("volume").key, a.option_for("volume").key)
        self.assertEqual(a.score(BUYER) - b.score(BUYER), 30)


class DealSpace(unittest.TestCase):
    def test_every_combination_is_enumerated(self):
        expected = 1
        for issue in S.issues:
            expected *= len(issue.options)
        self.assertEqual(len(all_offers(S)), expected)

    def test_a_zone_of_possible_agreement_exists(self):
        """Both walk-aways must be clearable at once, or the game is unwinnable."""
        self.assertGreater(len(viable_offers(S)), 0)

    def test_walk_aways_are_demanding_enough_to_matter(self):
        """Most packages should fail somebody -- otherwise there's no pressure."""
        self.assertLess(len(viable_offers(S)), len(all_offers(S)) / 2)

    def test_frontier_points_are_not_dominated(self):
        frontier = pareto_frontier(S)
        scores = [(b, s) for _, b, s in all_offers_scored()]
        for _, b, s in frontier:
            dominators = [
                1 for ob, os in scores if ob >= b and os >= s and (ob > b or os > s)
            ]
            self.assertEqual(dominators, [], f"({b},{s}) was dominated")

    def test_joint_score_beats_any_single_sided_maximum(self):
        """Trading beats winning: the best joint deal tops 100 + 0."""
        self.assertGreater(max_joint_score(S), PERFECT_SCORE)


def all_offers_scored():
    return [(o, o.score(BUYER), o.score(SELLER)) for o in all_offers(S)]


class Judgement(unittest.TestCase):
    def test_split_the_difference_leaves_value_behind(self):
        """Conceding the midpoint on every issue is the classic blunder."""
        lazy = offer(
            price="22", volume="25k", payment="net30", delivery="8w",
            exclusivity="region1y",
        )
        verdict = judge(S, lazy)
        self.assertGreater(verdict.value_left_on_table, 20)
        self.assertFalse(verdict.is_efficient)

    def test_an_efficient_deal_leaves_nothing_behind(self):
        best_offer, _, _ = pareto_frontier(S)[len(pareto_frontier(S)) // 2]
        verdict = judge(S, best_offer)
        self.assertEqual(verdict.value_left_on_table, 0)
        self.assertTrue(verdict.is_efficient)
        self.assertIsNone(verdict.best_missed)

    def test_improvements_never_hurt_either_side(self):
        lazy = offer(
            price="22", volume="25k", payment="net30", delivery="8w",
            exclusivity="region1y",
        )
        b0, s0 = lazy.score(BUYER), lazy.score(SELLER)
        for _, b, s in missed_improvements(S, lazy):
            self.assertGreaterEqual(b, b0)
            self.assertGreaterEqual(s, s0)

    def test_surplus_and_share_of_gains(self):
        deal = offer(
            price="22", volume="100k", payment="net90", delivery="2w",
            exclusivity="region2y",
        )
        verdict = judge(S, deal)
        self.assertEqual(verdict.buyer_surplus, verdict.buyer_score - S.buyer_walkaway)
        self.assertEqual(verdict.seller_surplus, verdict.seller_score - S.seller_walkaway)
        self.assertGreater(verdict.share_of_gains_pct, 0)
        self.assertLess(verdict.share_of_gains_pct, 100)

    def test_efficiency_is_a_sane_percentage(self):
        for o in (offer(**BEST_FOR_BUYER), offer(**BEST_FOR_SELLER)):
            verdict = judge(S, o)
            self.assertGreater(verdict.efficiency_pct, 0)
            self.assertLessEqual(verdict.efficiency_pct, 100)


if __name__ == "__main__":
    unittest.main()
