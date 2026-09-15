"""Random scenario generation: a different product and a different deal
every time you play, while keeping the negotiation genuinely winnable.

Every generated scenario is guaranteed to satisfy three properties:

  1. Each side can score at most 100 points.
  2. A zone of possible agreement exists -- there are packages that clear
     BOTH walk-away scores -- but it is a minority of the packages, so you
     have to work for it.
  3. The two sides rank the issues differently, so win-win trades exist.
"""

from __future__ import annotations

import dataclasses
import itertools
import random

from .deal import BUYER, SELLER, Issue, Offer, Option, Scenario

# --------------------------------------------------------------------------
# What is being bought and sold.
# --------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Product:
    item: str           # what changes hands
    unit: str           # the countable unit, singular
    unit_plural: str
    mid_price: float    # the middle rung of the price ladder
    volumes: tuple[int, int, int, int]
    buyer_kind: str     # what the buyer's business does with it
    seller_kind: str    # what the seller's business is

    @property
    def short_unit(self) -> str:
        """'case of 12' is fine in prose but too long for a table column."""
        return self.unit.split(" of ")[0]


CATALOG: tuple[Product, ...] = (
    Product("facial tissue", "case", "cases", 18.40, (8_000, 20_000, 45_000, 90_000),
            "a national drugstore chain", "a paper converting mill"),
    Product("lithium cells", "cell", "cells", 4.75, (50_000, 150_000, 400_000, 900_000),
            "an e-bike manufacturer", "a battery fabricator"),
    Product("cold brew concentrate", "keg", "kegs", 62.00, (1_200, 3_000, 7_500, 16_000),
            "a coffee shop group", "a specialty roastery"),
    Product("corrugated shipping boxes", "bundle", "bundles", 11.20, (25_000, 60_000, 140_000, 300_000),
            "an online retailer", "a packaging plant"),
    Product("stainless fasteners", "box of 500", "boxes", 27.50, (6_000, 15_000, 36_000, 80_000),
            "an appliance assembler", "a fastener works"),
    Product("organic oat milk", "case of 12", "cases", 21.80, (10_000, 26_000, 60_000, 130_000),
            "a grocery chain", "a plant-milk dairy"),
    Product("nitrile gloves", "case of 1000", "cases", 46.00, (4_000, 11_000, 26_000, 55_000),
            "a hospital network", "a medical supplies maker"),
    Product("recycled printer paper", "pallet", "pallets", 385.00, (900, 2_200, 5_000, 11_000),
            "a government print office", "a paper recycler"),
    Product("bicycle disc brake rotors", "unit", "units", 8.90, (20_000, 55_000, 130_000, 280_000),
            "a bicycle brand", "a components machinist"),
    Product("espresso machine gaskets", "pack of 50", "packs", 33.00, (3_000, 8_000, 19_000, 42_000),
            "an appliance service network", "a rubber moulder"),
    Product("solar microinverters", "unit", "units", 118.00, (2_000, 5_500, 13_000, 28_000),
            "a rooftop solar installer", "a power electronics firm"),
    Product("hardwood flooring planks", "carton", "cartons", 74.50, (3_500, 9_000, 21_000, 46_000),
            "a homebuilding group", "a timber mill"),
)

BUYER_COMPANIES = (
    "Northwind", "Cobalt Row", "Harrow & Vale", "Meridian", "Fairweather",
    "Bright Harbor", "Kestrel", "Ironwood", "Tallgrass", "Lumen", "Redpoint",
)
SELLER_COMPANIES = (
    "Castellan", "Orsini", "Pelham Works", "Brightside", "Aldergate",
    "Voss & Sons", "Quarry Lane", "Marchetti", "Stonefield", "Halcyon",
)
COMPANY_SUFFIX = ("Industries", "Supply Co.", "Group", "Manufacturing", "Partners", "Works")


# --------------------------------------------------------------------------
# Turning weights into point ladders.
# --------------------------------------------------------------------------


def _ladder(top: int, steps: int) -> list[int]:
    """Evenly spaced points from `top` down to 0, across `steps` rungs."""
    if steps < 2:
        return [top]
    return [round(top * (steps - 1 - i) / (steps - 1)) for i in range(steps)]


def _random_split(total: int, parts: int, low: int, high: int, rng: random.Random) -> list[int]:
    """Split `total` into `parts` whole numbers, each between low and high."""
    if parts * low > total or parts * high < total:
        raise ValueError(f"cannot split {total} into {parts} parts in [{low},{high}]")
    while True:
        cuts = [rng.randint(low, high) for _ in range(parts)]
        drift = total - sum(cuts)
        for _ in range(400):
            if drift == 0:
                return cuts
            i = rng.randrange(parts)
            step = 1 if drift > 0 else -1
            if low <= cuts[i] + step <= high:
                cuts[i] += step
                drift -= step


def _money(amount: float) -> str:
    if amount >= 1000:
        return f"${amount:,.0f}"
    return f"${amount:,.2f}"


def parse_volume(key: str) -> int:
    """Turn a shorthand volume key such as '28k' or '2m' back into a number."""
    key = key.strip().lower()
    if key.endswith("m"):
        return int(float(key[:-1]) * 1_000_000)
    if key.endswith("k"):
        return int(float(key[:-1]) * 1_000)
    return int(float(key))


def contract_value(offer: Offer) -> float:
    """Price per unit times annual volume: the headline number of the deal."""
    price = float(offer.option_for("price").key)
    volume = parse_volume(offer.option_for("volume").key)
    return price * volume


# --------------------------------------------------------------------------
# The generator.
# --------------------------------------------------------------------------


def generate_scenario(seed: int | None = None) -> tuple[Scenario, Product, int]:
    """Build a fresh, guaranteed-negotiable scenario. Returns the scenario,
    the product being traded, and the seed that produced it (so you can
    replay the exact same deal)."""
    if seed is None:
        seed = random.randrange(1, 1_000_000)
    rng = random.Random(seed)
    product = rng.choice(CATALOG)

    buyer_co = f"{rng.choice(BUYER_COMPANIES)} {rng.choice(COMPANY_SUFFIX)}"
    seller_co = f"{rng.choice(SELLER_COMPANIES)} {rng.choice(COMPANY_SUFFIX)}"

    # --- weights -----------------------------------------------------------
    # Price is a pure tug of war: whatever one side gains, the other loses.
    price_weight = rng.choice((28, 30, 32))
    # Volume is the great logroll: cheap for the buyer, precious for the seller.
    buyer_volume = rng.randint(3, 7)
    seller_volume = rng.randint(30, 38)

    buyer_rest = 100 - price_weight - buyer_volume
    seller_rest = 100 - price_weight - seller_volume
    # The buyer cares much more than the seller about the remaining three
    # issues, which is precisely where the trades are hiding.
    buyer_soft = _random_split(buyer_rest, 3, 14, 32, rng)
    seller_soft = _random_split(seller_rest, 3, 3, 17, rng)
    rng.shuffle(buyer_soft)
    rng.shuffle(seller_soft)

    # --- price ladder ------------------------------------------------------
    mid = product.mid_price
    multipliers = (0.86, 0.93, 1.00, 1.08, 1.16)
    if mid >= 100:
        prices = [round(mid * m) for m in multipliers]
    else:
        prices = [round(mid * m, 2) for m in multipliers]
    buyer_price_pts = _ladder(price_weight, len(prices))
    price = Issue(
        "price", f"Price per {product.short_unit}", "USD",
        tuple(
            # seller points are exactly what the buyer gives up: a zero sum rung
            Option(f"{p}", _money(p), bp, price_weight - bp)
            for p, bp in zip(prices, buyer_price_pts)
        ),
    )

    # --- volume ------------------------------------------------------------
    buyer_vol_pts = _ladder(buyer_volume, 4)
    seller_vol_pts = list(reversed(_ladder(seller_volume, 4)))
    volume = Issue(
        "volume", "Volume commitment", f"{product.unit_plural}/year",
        tuple(
            Option(_volume_key(v), f"{v:,} {product.unit_plural}", bp, sp)
            for v, bp, sp in zip(product.volumes, buyer_vol_pts, seller_vol_pts)
        ),
    )

    # --- the three soft issues --------------------------------------------
    payment = _soft_issue(
        "payment", "Payment terms", "days",
        [("net90", "Net 90"), ("net60", "Net 60"), ("net30", "Net 30"), ("net15", "Net 15")],
        buyer_soft[0], seller_soft[0],
    )
    delivery = _soft_issue(
        "delivery", "Delivery window", "lead time",
        [("2w", "2 weeks"), ("4w", "4 weeks"), ("8w", "8 weeks"), ("12w", "12 weeks")],
        buyer_soft[1], seller_soft[1],
    )
    exclusivity = _soft_issue(
        "exclusivity", "Exclusivity", "scope",
        [
            ("global2y", "Global, 2 years"),
            ("region2y", "Our region, 2 years"),
            ("region1y", "Our region, 1 year"),
            ("none", "None"),
        ],
        buyer_soft[2], seller_soft[2],
    )

    issues = (price, volume, payment, delivery, exclusivity)
    scenario = Scenario(
        name=f"{product.item.title()} supply agreement",
        buyer_role=f"Head of Procurement, {buyer_co}",
        seller_role=f"VP of Sales, {seller_co}",
        buyer_brief=_buyer_brief(product, buyer_co, seller_co, issues),
        seller_brief=_seller_brief(product, seller_co, buyer_co, issues),
        issues=issues,
        buyer_walkaway=45,
        seller_walkaway=45,
    )
    return _set_walkaways(scenario, rng), product, seed


def _volume_key(volume: int) -> str:
    if volume >= 1_000_000:
        return f"{volume // 1_000_000}m"
    if volume >= 1_000:
        return f"{volume // 1_000}k"
    return str(volume)


def _soft_issue(key, label, unit, options, buyer_top, seller_top) -> Issue:
    """An issue where the best option for the buyer is the worst for the
    seller, but the two sides weight the whole issue very differently."""
    buyer_pts = _ladder(buyer_top, len(options))
    seller_pts = list(reversed(_ladder(seller_top, len(options))))
    return Issue(
        key, label, unit,
        tuple(
            Option(k, lbl, bp, sp)
            for (k, lbl), bp, sp in zip(options, buyer_pts, seller_pts)
        ),
    )


def _rank_phrase(issues, side, top_n=2) -> str:
    ranked = sorted(issues, key=lambda i: -i.stake(side))
    return " and ".join(i.label.lower() for i in ranked[:top_n])


def _buyer_brief(product, buyer_co, seller_co, issues) -> str:
    return (
        f"{buyer_co} is {product.buyer_kind}. You are buying {product.item} from "
        f"{seller_co} and you are the one who signs. What moves your numbers most "
        f"is {_rank_phrase(issues, BUYER)}. Committing to a big annual volume is "
        f"a liability you would rather not carry, so if they want one, sell it "
        f"dearly."
    )


def _seller_brief(product, seller_co, buyer_co, issues) -> str:
    return (
        f"{seller_co} is {product.seller_kind}. Your plant runs on committed "
        f"volume, so a large annual order is worth more to you than almost "
        f"anything else on the table. After that, {_rank_phrase(issues, SELLER)} "
        f"matter most."
    )


# --------------------------------------------------------------------------
# Walk-away scores, chosen so that a deal is possible but not easy.
# --------------------------------------------------------------------------

TARGET_VIABLE_FRACTION = (0.10, 0.30)


def _all_score_pairs(scenario: Scenario) -> list[tuple[int, int]]:
    menus = [[o.key for o in issue.options] for issue in scenario.issues]
    keys = scenario.issue_keys
    pairs = []
    for combo in itertools.product(*menus):
        offer = Offer.build(scenario, dict(zip(keys, combo)))
        pairs.append((offer.score(BUYER), offer.score(SELLER)))
    return pairs


def _set_walkaways(scenario: Scenario, rng: random.Random) -> Scenario:
    """Pick walk-away scores so the zone of possible agreement is real but
    narrow: roughly 10-30% of all packages should satisfy both sides."""
    pairs = _all_score_pairs(scenario)
    total = len(pairs)
    low, high = TARGET_VIABLE_FRACTION

    # Slight asymmetry keeps the two sides from feeling like mirror images.
    tilt = rng.randint(-3, 3)
    best = None
    for base in range(60, 24, -1):
        buyer_wa, seller_wa = base + tilt, base - tilt
        viable = sum(1 for b, s in pairs if b >= buyer_wa and s >= seller_wa)
        fraction = viable / total
        if low <= fraction <= high:
            best = (buyer_wa, seller_wa)
            break
        if fraction > high:
            # We have overshot into "too easy"; the previous rung was tighter
            # but had no agreement zone, so take this one anyway.
            best = best or (buyer_wa, seller_wa)
            break
    if best is None:
        best = (40, 40)
    return dataclasses.replace(
        scenario, buyer_walkaway=best[0], seller_walkaway=best[1]
    )
