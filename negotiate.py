#!/usr/bin/env python3
"""Negotiation simulator - command line entry point.

  python3 negotiate.py play              play a negotiation
  python3 negotiate.py sheet             your confidential brief
  python3 negotiate.py sheet --reveal     ...with the AI's hidden points too
  python3 negotiate.py score price=18 volume=100k payment=net90 delivery=2w exclusivity=global2y
"""

from __future__ import annotations

import argparse
import sys

from negosim import ui
from negosim.analysis import issue_by_issue_diff, judge
from negosim.deal import BUYER, SELLER, SUPPLIER_DEAL, Offer
from negosim.game import start
from negosim.products import generate_scenario
from negosim.sheet import offer_card, scoresheet


def _scenario_for(args: argparse.Namespace):
    """The fixed practice deal, or a freshly generated random one."""
    if getattr(args, "classic", False):
        return SUPPLIER_DEAL
    if getattr(args, "seed", None) is not None:
        return generate_scenario(args.seed)[0]
    return SUPPLIER_DEAL


def _parse_terms(terms: list[str]) -> dict[str, str]:
    choices: dict[str, str] = {}
    for term in terms:
        if "=" not in term:
            raise SystemExit(f"error: '{term}' should look like issue=option")
        key, _, value = term.partition("=")
        choices[key.strip()] = value.strip()
    return choices


def cmd_play(args: argparse.Namespace) -> int:
    start(seed=args.seed, rounds=args.rounds)
    return 0


def cmd_sheet(args: argparse.Namespace) -> int:
    side = SELLER if args.side == "seller" else BUYER
    print(scoresheet(_scenario_for(args), side, reveal=args.reveal))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    scenario = _scenario_for(args)
    if not args.terms:
        print("Give me a package, e.g.:")
        print("  python3 negotiate.py score " + " ".join(
            f"{i.key}={i.options[0].key}" for i in scenario.issues
        ))
        return 1
    try:
        offer = Offer.build(scenario, _parse_terms(args.terms))
    except (ValueError, KeyError) as exc:
        print(f"error: {exc}")
        print("\nValid options:")
        for issue in scenario.issues:
            print(f"  {issue.key}: " + ", ".join(o.key for o in issue.options))
        return 1

    verdict = judge(scenario, offer)
    print(offer_card(offer, BUYER, title="The package"))

    print(ui.heading("result"))
    rows = [
        ["You", str(verdict.buyer_score), str(verdict.buyer_walkaway),
         "yes" if offer.acceptable_to(BUYER) else "NO - you would walk"],
        ["Them", str(verdict.seller_score), str(verdict.seller_walkaway),
         "yes" if offer.acceptable_to(SELLER) else "NO - they would walk"],
    ]
    print(ui.table(["side", "score", "walk-away", "would sign?"], rows, "lrrl"))

    print()
    print(f"Joint score      {verdict.joint_score} of a possible {verdict.max_joint}"
          f"   ({verdict.efficiency_pct:.0f}% of the pie found)")
    print(f"Left on table    {ui.paint(str(verdict.value_left_on_table), 'bold', 'yellow')} points")

    if verdict.best_missed is not None:
        print(ui.subheading("A package that beats this one for BOTH of you:"))
        for label, old, new in issue_by_issue_diff(offer, verdict.best_missed):
            print(f"  {label}: {ui.paint(old, 'dim')} -> {ui.paint(new, 'green')}")
        print(f"  => you {verdict.best_missed_buyer} (up {verdict.best_missed_buyer - verdict.buyer_score}), "
              f"them {verdict.best_missed_seller} (up {verdict.best_missed_seller - verdict.seller_score})")
    else:
        print(ui.paint("\nThis package is efficient - no win-win swap exists.", "green"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="negotiate.py", description="Supplier negotiation simulator."
    )
    subs = parser.add_subparsers(dest="command", required=True)

    p_play = subs.add_parser("play", help="play a negotiation")
    p_play.add_argument("--seed", type=int, default=None,
                        help="replay an exact deal you played before")
    p_play.add_argument("--rounds", type=int, default=8,
                        help="how many rounds before the clock runs out")
    p_play.set_defaults(func=cmd_play)

    p_sheet = subs.add_parser("sheet", help="show a confidential scoresheet")
    p_sheet.add_argument("--side", choices=["buyer", "seller"], default="buyer")
    p_sheet.add_argument("--reveal", action="store_true",
                         help="also show the other side's hidden points")
    p_sheet.add_argument("--seed", type=int, default=None,
                         help="show the brief for a generated deal")
    p_sheet.set_defaults(func=cmd_sheet)

    p_score = subs.add_parser("score", help="score a package, e.g. price=18 volume=100k")
    p_score.add_argument("terms", nargs="*")
    p_score.add_argument("--seed", type=int, default=None)
    p_score.set_defaults(func=cmd_score)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
