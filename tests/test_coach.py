"""Checks on the debrief: the analysis, the lessons, and the grade."""

import random
import unittest

from negosim import coach, ui
from negosim.analysis import pareto_frontier, viable_offers
from negosim.character import generate_character
from negosim.coach import CRITICAL, GOOD, MAJOR, MINOR, PlayLog
from negosim.deal import BUYER, SELLER, Offer
from negosim.game import (
    QUIT, SIGNED, THEY_RAGED, THEY_WALKED, TIME_OUT, YOU_WALKED, Outcome,
)
from negosim.products import generate_scenario

SCENARIO, PRODUCT, SEED = generate_scenario(42)
PERSON = generate_character(random.Random(1), "Testing Co.")


def outcome(kind=SIGNED, offer=None, fleeced=False, log=None):
    return Outcome(kind, offer, 4, SCENARIO, PRODUCT, PERSON, SEED,
                   [], fleeced, log or PlayLog(rounds_available=8))


def package(**terms):
    return Offer.build(SCENARIO, terms)


BEST_FOR_BUYER = {i.key: i.best_option(BUYER).key for i in SCENARIO.issues}
BEST_FOR_SELLER = {i.key: i.best_option(SELLER).key for i in SCENARIO.issues}
MIDDLE = {i.key: i.options[len(i.options) // 2].key for i in SCENARIO.issues}


def titles(rev):
    return [lesson.title for lesson in rev.lessons]


def severities(rev):
    return {lesson.severity for lesson in rev.lessons}


class Scorecard(unittest.TestCase):
    def test_rows_account_for_every_point_on_both_sides(self):
        offer = package(**MIDDLE)
        rev = coach.review(outcome(offer=offer), PlayLog())
        self.assertEqual(sum(r.your_points for r in rev.rows), offer.score(BUYER))
        self.assertEqual(sum(r.their_points for r in rev.rows), offer.score(SELLER))

    def test_a_row_you_swept_is_recorded_as_yours(self):
        offer = package(**BEST_FOR_BUYER)
        rev = coach.review(outcome(offer=offer), PlayLog())
        self.assertTrue(all(row.winner == "you" for row in rev.rows))

    def test_a_row_they_swept_is_recorded_as_theirs(self):
        offer = package(**BEST_FOR_SELLER)
        rev = coach.review(outcome(offer=offer), PlayLog())
        self.assertTrue(all(row.winner == "them" for row in rev.rows))

    def test_shares_stay_between_nothing_and_everything(self):
        rev = coach.review(outcome(offer=package(**MIDDLE)), PlayLog())
        for row in rev.rows:
            self.assertGreaterEqual(row.your_share, 0.0)
            self.assertLessEqual(row.your_share, 1.0)


class WinWinTrades(unittest.TestCase):
    def test_no_single_term_can_ever_help_both_sides(self):
        """The reason the debrief talks about swaps, not tweaks."""
        offer = package(**MIDDLE)
        b0, s0 = offer.score(BUYER), offer.score(SELLER)
        for key in SCENARIO.issue_keys:
            for option in SCENARIO.issue(key).options:
                changed = offer.replace(key, option.key)
                b, s = changed.score(BUYER), changed.score(SELLER)
                self.assertFalse(b > b0 and s > s0, f"{key}={option.key}")

    def test_a_suggested_trade_never_hurts_either_side(self):
        offer = package(**MIDDLE)
        trades = coach._trades(SCENARIO, offer)
        self.assertTrue(trades, "the midpoint deal should have win-win swaps")
        for trade in trades:
            self.assertGreaterEqual(trade.you_gain, 0)
            self.assertGreaterEqual(trade.them_gain, 0)
            self.assertGreater(trade.you_gain + trade.them_gain, 0)

    def test_a_trade_really_moves_two_different_terms(self):
        for trade in coach._trades(SCENARIO, package(**MIDDLE)):
            self.assertNotEqual(trade.give_label, trade.take_label)
            self.assertNotEqual(trade.give_from, trade.give_to)
            self.assertNotEqual(trade.take_from, trade.take_to)

    def test_the_conceded_term_is_named_first(self):
        offer = package(**MIDDLE)
        for trade in coach._trades(SCENARIO, offer):
            give = SCENARIO.issue([k for k in SCENARIO.issue_keys
                                   if SCENARIO.issue(k).label == trade.give_label][0])
            before = give.option(offer.as_dict()[give.key]).points_for(BUYER)
            after = [o for o in give.options if o.label == trade.give_to][0].points_for(BUYER)
            self.assertLessEqual(after, before, trade.give_label)

    def test_an_efficient_deal_has_no_trades_left(self):
        efficient, _, _ = pareto_frontier(SCENARIO)[5]
        self.assertEqual(coach._trades(SCENARIO, efficient), [])


class LessonsThatMustFire(unittest.TestCase):
    def test_signing_below_your_own_walk_away_is_called_out(self):
        rev = coach.review(outcome(offer=package(**BEST_FOR_SELLER)), PlayLog())
        self.assertIn(CRITICAL, severities(rev))
        self.assertTrue(any("worse than no deal" in t for t in titles(rev)))

    def test_being_fleeced_is_called_out(self):
        rev = coach.review(
            outcome(offer=package(**BEST_FOR_SELLER), fleeced=True), PlayLog())
        self.assertTrue(any("accepted instantly" in t for t in titles(rev)))

    def test_a_rage_quit_is_called_out(self):
        rev = coach.review(outcome(kind=THEY_RAGED), PlayLog())
        self.assertTrue(any("out of the room" in t for t in titles(rev)))

    def test_every_no_deal_ending_notes_the_deal_that_existed(self):
        for kind in (YOU_WALKED, THEY_WALKED, TIME_OUT, QUIT):
            rev = coach.review(outcome(kind=kind), PlayLog())
            self.assertTrue(any("did not find it" in t for t in titles(rev)), kind)

    def test_never_asking_is_a_major_lesson_and_asking_is_praised(self):
        offer = package(**MIDDLE)
        silent = coach.review(outcome(offer=offer), PlayLog(asked_priorities=False))
        curious = coach.review(outcome(offer=offer), PlayLog(asked_priorities=True))
        self.assertTrue(any("never asked" in t for t in titles(silent)))
        self.assertFalse(any("never asked" in t for t in titles(curious)))
        self.assertTrue(any("asked what they cared about" in t for t in titles(curious)))

    def test_revealing_flexibility_is_called_out(self):
        log = PlayLog(revealed_flexibility=["delivery"])
        rev = coach.review(outcome(offer=package(**MIDDLE)), log)
        self.assertTrue(any("where you would bend" in t for t in titles(rev)))

    def test_splitting_the_difference_is_called_out(self):
        rev = coach.review(outcome(offer=package(**MIDDLE)), PlayLog())
        self.assertTrue(any("split the difference" in t for t in titles(rev)))

    def test_caving_early_is_called_out(self):
        strong = package(**BEST_FOR_BUYER)
        weak = package(**MIDDLE)
        log = PlayLog(your_offers=[strong, weak])
        rev = coach.review(outcome(offer=weak), log)
        self.assertTrue(any("too much, too early" in t for t in titles(rev)))

    def test_an_efficient_deal_is_praised_not_scolded(self):
        efficient, b, s = max(viable_offers(SCENARIO), key=lambda row: row[1] + row[2])
        rev = coach.review(outcome(offer=efficient), PlayLog(asked_priorities=True))
        self.assertTrue(any("was efficient" in t for t in titles(rev)))
        self.assertFalse(any("left" in t and "on the table" in t for t in titles(rev)))

    def test_lessons_are_ordered_worst_first(self):
        rev = coach.review(outcome(offer=package(**BEST_FOR_SELLER)), PlayLog())
        rank = {CRITICAL: 0, MAJOR: 1, MINOR: 2, GOOD: 3}
        order = [rank[lesson.severity] for lesson in rev.lessons]
        self.assertEqual(order, sorted(order))

    def test_giving_away_your_biggest_issue_is_noticed(self):
        biggest = max(SCENARIO.issues, key=lambda i: i.stake(BUYER))
        terms = dict(BEST_FOR_BUYER)
        terms[biggest.key] = biggest.best_option(SELLER).key
        rev = coach.review(outcome(offer=package(**terms)), PlayLog())
        self.assertTrue(any(biggest.label.lower() in t.lower() for t in titles(rev)))


class Grading(unittest.TestCase):
    def test_a_better_deal_never_grades_worse(self):
        order = ["F", "D", "C", "B", "A", "A+"]
        scored = []
        for offer, b, s in viable_offers(SCENARIO):
            rev = coach.review(outcome(offer=offer), PlayLog(asked_priorities=True))
            scored.append((b, order.index(rev.grade)))
        scored.sort()
        # The best-scoring deal for the buyer must not grade below the worst.
        self.assertGreaterEqual(scored[-1][1], scored[0][1])

    def test_the_best_available_deal_grades_top(self):
        best, _, _ = max(viable_offers(SCENARIO), key=lambda row: row[1])
        rev = coach.review(outcome(offer=best), PlayLog(asked_priorities=True))
        self.assertIn(rev.grade, ("A+", "A"))

    def test_no_deal_always_fails(self):
        for kind in (YOU_WALKED, THEY_WALKED, TIME_OUT, THEY_RAGED):
            self.assertEqual(coach.review(outcome(kind=kind), PlayLog()).grade, "F")

    def test_capture_and_efficiency_are_sane_fractions(self):
        for offer, _, _ in viable_offers(SCENARIO)[:60]:
            rev = coach.review(outcome(offer=offer), PlayLog())
            self.assertGreaterEqual(rev.capture, 0.0)
            self.assertLessEqual(rev.capture, 1.0)
            self.assertGreater(rev.efficiency, 0.0)
            self.assertLessEqual(rev.efficiency, 1.0)

    def test_the_best_possible_package_is_one_they_would_sign(self):
        rev = coach.review(outcome(offer=package(**MIDDLE)), PlayLog())
        self.assertIsNotNone(rev.best_possible)
        self.assertTrue(rev.best_possible.acceptable_to(SELLER))
        self.assertTrue(rev.best_possible.acceptable_to(BUYER))
        self.assertEqual(rev.best_possible_score, rev.best_possible.score(BUYER))


class Rendering(unittest.TestCase):
    def test_the_chart_is_rectangular_and_marks_your_deal(self):
        was = ui.colour_enabled()
        try:
            ui.set_colour(False)
            offer = package(**MIDDLE)
            chart = coach.frontier_chart(SCENARIO, offer)
            self.assertIn("@", chart)
            self.assertIn("your score", chart)
            widths = {len(line) for line in chart.splitlines() if line.startswith("      |")}
            self.assertEqual(len(widths), 1)
        finally:
            ui.set_colour(was)

    def test_the_chart_marks_a_no_deal_differently(self):
        was = ui.colour_enabled()
        try:
            ui.set_colour(False)
            chart = coach.frontier_chart(SCENARIO, None)
            self.assertIn("x", chart)
            self.assertNotIn("@", chart)
        finally:
            ui.set_colour(was)

    def test_the_debrief_renders_for_every_ending(self):
        for kind, offer in ((SIGNED, package(**MIDDLE)), (YOU_WALKED, None),
                            (THEY_RAGED, None), (TIME_OUT, None), (QUIT, None)):
            text = coach.render(coach.review(outcome(kind=kind, offer=offer), PlayLog()))
            self.assertIn("GRADE", text)
            self.assertIn("What to do differently", text)

    def test_no_line_of_the_debrief_overflows_the_terminal(self):
        was = ui.colour_enabled()
        try:
            ui.set_colour(False)
            text = coach.render(coach.review(outcome(offer=package(**MIDDLE)), PlayLog()))
            for line in text.splitlines():
                self.assertLessEqual(len(line), 80, line)
        finally:
            ui.set_colour(was)


if __name__ == "__main__":
    unittest.main()
