"""The negotiation scenario: issues, options, and each side's hidden points.

Two sides negotiate: BUYER (the human player) and SELLER (the AI supplier).
Every issue has a fixed menu of options. Each option is worth a different
number of points to each side, and the two sides weight the issues
differently -- that asymmetry is what makes win-win trades possible.

Each side's point totals are built so that getting its single best option on
every issue would score exactly 100.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

BUYER = "buyer"
SELLER = "seller"
SIDES = (BUYER, SELLER)

PERFECT_SCORE = 100


@dataclass(frozen=True)
class Option:
    """One choice on one issue, plus what it is worth to each side."""

    key: str
    label: str
    buyer_points: int
    seller_points: int

    def points_for(self, side: str) -> int:
        if side == BUYER:
            return self.buyer_points
        if side == SELLER:
            return self.seller_points
        raise ValueError(f"unknown side: {side!r}")


@dataclass(frozen=True)
class Issue:
    """One negotiable term, with its menu of options (best-for-buyer first)."""

    key: str
    label: str
    unit: str
    options: tuple[Option, ...]

    def option(self, key: str) -> Option:
        for option in self.options:
            if option.key == key:
                return option
        raise KeyError(f"issue {self.key!r} has no option {key!r}")

    def max_points(self, side: str) -> int:
        return max(o.points_for(side) for o in self.options)

    def min_points(self, side: str) -> int:
        return min(o.points_for(side) for o in self.options)

    def stake(self, side: str) -> int:
        """How much this issue can swing a side's score: its weight."""
        return self.max_points(side) - self.min_points(side)

    def best_option(self, side: str) -> Option:
        return max(self.options, key=lambda o: o.points_for(side))


@dataclass(frozen=True)
class Scenario:
    """A complete negotiation setup: the issues plus both walk-away scores."""

    name: str
    buyer_role: str
    seller_role: str
    buyer_brief: str
    seller_brief: str
    issues: tuple[Issue, ...]
    buyer_walkaway: int
    seller_walkaway: int

    def issue(self, key: str) -> Issue:
        for issue in self.issues:
            if issue.key == key:
                return issue
        raise KeyError(f"no issue named {key!r}")

    @property
    def issue_keys(self) -> tuple[str, ...]:
        return tuple(i.key for i in self.issues)

    def walkaway(self, side: str) -> int:
        return self.buyer_walkaway if side == BUYER else self.seller_walkaway

    def role(self, side: str) -> str:
        return self.buyer_role if side == BUYER else self.seller_role


@dataclass(frozen=True)
class Offer:
    """One complete package: exactly one option chosen on every issue."""

    scenario: Scenario
    choices: tuple[tuple[str, str], ...]  # (issue_key, option_key) pairs

    @classmethod
    def build(cls, scenario: Scenario, choices: dict[str, str]) -> "Offer":
        missing = [k for k in scenario.issue_keys if k not in choices]
        if missing:
            raise ValueError(f"offer is missing issues: {', '.join(missing)}")
        extra = [k for k in choices if k not in scenario.issue_keys]
        if extra:
            raise ValueError(f"offer has unknown issues: {', '.join(extra)}")
        ordered = []
        for issue in scenario.issues:
            issue.option(choices[issue.key])  # validates the option key
            ordered.append((issue.key, choices[issue.key]))
        return cls(scenario, tuple(ordered))

    def as_dict(self) -> dict[str, str]:
        return dict(self.choices)

    def option_for(self, issue_key: str) -> Option:
        return self.scenario.issue(issue_key).option(self.as_dict()[issue_key])

    def score(self, side: str) -> int:
        return sum(self.option_for(k).points_for(side) for k in self.scenario.issue_keys)

    def joint_score(self) -> int:
        return self.score(BUYER) + self.score(SELLER)

    def acceptable_to(self, side: str) -> bool:
        return self.score(side) >= self.scenario.walkaway(side)

    def replace(self, issue_key: str, option_key: str) -> "Offer":
        choices = self.as_dict()
        choices[issue_key] = option_key
        return Offer.build(self.scenario, choices)

    def labels(self) -> list[tuple[str, str]]:
        return [
            (self.scenario.issue(k).label, self.option_for(k).label)
            for k in self.scenario.issue_keys
        ]

    def summary(self) -> str:
        return " | ".join(f"{label}: {value}" for label, value in self.labels())


def _issue(key: str, label: str, unit: str, rows: Iterable[tuple]) -> Issue:
    return Issue(key, label, unit, tuple(Option(*row) for row in rows))


# --------------------------------------------------------------------------
# The scenario. Each column of points sums to 100 at its best.
#
#   weight for the buyer (you)      weight for the seller (AI)
#   price        30                 price        30   <- pure tug of war
#   delivery     25                 delivery      5   <- you should win this
#   payment      20                 payment      15   <- you should win this
#   exclusivity  20                 exclusivity  15   <- you should win this
#   volume        5                 volume       35   <- give this away
# --------------------------------------------------------------------------

SUPPLIER_DEAL = Scenario(
    name="Component supply agreement",
    buyer_role="Head of Procurement, Northwind Devices",
    seller_role="VP Sales, Castellan Components",
    buyer_brief=(
        "You buy a critical component. You need it cheap and you need it fast, "
        "and your cash is tight so late payment helps. Locking the supplier out "
        "of your rivals is worth real money. Committing to huge volume is a "
        "liability you would rather avoid."
    ),
    seller_brief=(
        "You sell components. Your plant lives or dies on volume commitments, "
        "so a big order is worth more to you than almost anything. You want a "
        "healthy price and to be paid quickly, and staying free to sell to "
        "other customers matters. Your lead times are flexible."
    ),
    issues=(
        _issue(
            "price",
            "Price per unit",
            "USD",
            [
                # key,   label,  buyer, seller
                ("18", "$18.00", 30, 0),
                ("20", "$20.00", 22, 8),
                ("22", "$22.00", 15, 15),
                ("24", "$24.00", 7, 23),
                ("26", "$26.00", 0, 30),
            ],
        ),
        _issue(
            "volume",
            "Volume commitment",
            "units/year",
            [
                ("10k", "10,000 units", 5, 0),
                ("25k", "25,000 units", 3, 12),
                ("50k", "50,000 units", 2, 24),
                ("100k", "100,000 units", 0, 35),
            ],
        ),
        _issue(
            "payment",
            "Payment terms",
            "days",
            [
                ("net90", "Net 90", 20, 0),
                ("net60", "Net 60", 13, 5),
                ("net30", "Net 30", 7, 10),
                ("net15", "Net 15", 0, 15),
            ],
        ),
        _issue(
            "delivery",
            "Delivery window",
            "lead time",
            [
                ("2w", "2 weeks", 25, 0),
                ("4w", "4 weeks", 17, 1),
                ("8w", "8 weeks", 8, 3),
                ("12w", "12 weeks", 0, 5),
            ],
        ),
        _issue(
            "exclusivity",
            "Exclusivity",
            "scope",
            [
                ("global2y", "Exclusive to us, global, 2 years", 20, 0),
                ("region2y", "Exclusive to us, our region, 2 years", 13, 5),
                ("region1y", "Exclusive to us, our region, 1 year", 7, 10),
                ("none", "No exclusivity", 0, 15),
            ],
        ),
    ),
    buyer_walkaway=42,
    seller_walkaway=45,
)
