"""The maths that judges a finished deal.

The scenario is small enough (1,280 possible packages) to simply check every
single one, so none of this is an estimate -- it is exhaustive truth.

Key ideas, in plain terms:

  joint score     your points + their points. A bigger pie.
  efficient deal  one where nobody can be made better off without making the
                  other worse off. Also called Pareto-optimal.
  value left on   how many points the two of you COULD have added, between
  the table       you, by swapping terms in a way that hurt neither of you.
                  If this is zero, your deal was efficient.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from functools import lru_cache

from .deal import BUYER, SELLER, Offer, Scenario


def all_offers(scenario: Scenario) -> list[Offer]:
    """Every legal package, all 1,280 of them."""
    menus = [[o.key for o in issue.options] for issue in scenario.issues]
    keys = scenario.issue_keys
    return [
        Offer.build(scenario, dict(zip(keys, combo)))
        for combo in itertools.product(*menus)
    ]


@lru_cache(maxsize=None)
def _scored(scenario: Scenario) -> tuple[tuple[Offer, int, int], ...]:
    return tuple((o, o.score(BUYER), o.score(SELLER)) for o in all_offers(scenario))


def viable_offers(scenario: Scenario) -> list[tuple[Offer, int, int]]:
    """Packages that clear BOTH walk-away scores -- the real zone of agreement."""
    return [
        row
        for row in _scored(scenario)
        if row[1] >= scenario.buyer_walkaway and row[2] >= scenario.seller_walkaway
    ]


def pareto_frontier(scenario: Scenario) -> list[tuple[Offer, int, int]]:
    """Efficient packages: no other package beats them for both sides at once."""
    rows = _scored(scenario)
    best_seller_at_or_above: dict[int, int] = {}
    for _, b, s in rows:
        if s > best_seller_at_or_above.get(b, -1):
            best_seller_at_or_above[b] = s

    frontier = []
    for offer, b, s in rows:
        dominated = any(
            (ob >= b and os >= s) and (ob > b or os > s) for _, ob, os in rows
        )
        if not dominated:
            frontier.append((offer, b, s))
    frontier.sort(key=lambda row: (-row[1], -row[2]))
    # Collapse duplicates that score identically for both sides.
    seen: set[tuple[int, int]] = set()
    unique = []
    for offer, b, s in frontier:
        if (b, s) in seen:
            continue
        seen.add((b, s))
        unique.append((offer, b, s))
    return unique


def max_joint_score(scenario: Scenario) -> int:
    return max(b + s for _, b, s in _scored(scenario))


@dataclass(frozen=True)
class Verdict:
    """The full post-mortem on a settled deal."""

    offer: Offer
    buyer_score: int
    seller_score: int
    buyer_walkaway: int
    seller_walkaway: int
    max_joint: int
    value_left_on_table: int
    best_missed: Offer | None
    best_missed_buyer: int
    best_missed_seller: int
    buyer_best_possible: int  # best you could have had while they still said yes

    @property
    def joint_score(self) -> int:
        return self.buyer_score + self.seller_score

    @property
    def efficiency_pct(self) -> float:
        return 100.0 * self.joint_score / self.max_joint

    @property
    def is_efficient(self) -> bool:
        return self.value_left_on_table == 0

    @property
    def buyer_surplus(self) -> int:
        return self.buyer_score - self.buyer_walkaway

    @property
    def seller_surplus(self) -> int:
        return self.seller_score - self.seller_walkaway

    @property
    def share_of_gains_pct(self) -> float:
        total = self.buyer_surplus + self.seller_surplus
        if total <= 0:
            return 0.0
        return 100.0 * self.buyer_surplus / total


def missed_improvements(
    scenario: Scenario, offer: Offer
) -> list[tuple[Offer, int, int]]:
    """Packages that would have been at least as good for BOTH sides, and
    strictly better for at least one. Sorted by how much they add in total."""
    b0, s0 = offer.score(BUYER), offer.score(SELLER)
    better = [
        row
        for row in _scored(scenario)
        if row[1] >= b0 and row[2] >= s0 and (row[1] > b0 or row[2] > s0)
    ]
    better.sort(key=lambda row: (-(row[1] + row[2] - b0 - s0), -row[1]))
    return better


def judge(scenario: Scenario, offer: Offer) -> Verdict:
    b, s = offer.score(BUYER), offer.score(SELLER)
    better = missed_improvements(scenario, offer)
    if better:
        top_offer, top_b, top_s = better[0]
        left = (top_b + top_s) - (b + s)
    else:
        top_offer, top_b, top_s, left = None, b, s, 0

    viable = viable_offers(scenario)
    buyer_ceiling = max((row[1] for row in viable), default=b)

    return Verdict(
        offer=offer,
        buyer_score=b,
        seller_score=s,
        buyer_walkaway=scenario.buyer_walkaway,
        seller_walkaway=scenario.seller_walkaway,
        max_joint=max_joint_score(scenario),
        value_left_on_table=left,
        best_missed=top_offer,
        best_missed_buyer=top_b,
        best_missed_seller=top_s,
        buyer_best_possible=buyer_ceiling,
    )


def issue_by_issue_diff(a: Offer, b: Offer) -> list[tuple[str, str, str]]:
    """Which terms differ between two packages: (issue label, from, to)."""
    rows = []
    for key in a.scenario.issue_keys:
        oa, ob = a.option_for(key), b.option_for(key)
        if oa.key != ob.key:
            rows.append((a.scenario.issue(key).label, oa.label, ob.label))
    return rows
