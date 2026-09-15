"""Rendering the confidential scoresheet a negotiator plays from."""

from __future__ import annotations

from . import ui
from .deal import BUYER, PERFECT_SCORE, SELLER, Offer, Scenario


def _brief(scenario: Scenario, side: str) -> str:
    return scenario.buyer_brief if side == BUYER else scenario.seller_brief


def scoresheet(scenario: Scenario, side: str, *, reveal: bool = False) -> str:
    """The private briefing for one side. This is what you play from."""
    out = [ui.heading(f"confidential brief - {scenario.role(side)}")]
    out.append(ui.wrap(_brief(scenario, side)))
    out.append("")
    out.append(
        ui.wrap(
            f"Your walk-away score is {ui.paint(str(scenario.walkaway(side)), 'bold')} "
            f"of a possible {PERFECT_SCORE}. Sign nothing worth less than that; "
            f"no deal is better than a bad deal."
        )
    )

    for issue in scenario.issues:
        weight = issue.stake(side)
        out.append(ui.subheading(f"{issue.label}   ({weight} points at stake)"))
        headers = ["option", "your pts"]
        aligns = "lr"
        if reveal:
            headers.append("their pts")
            aligns += "r"
        rows = []
        for option in issue.options:
            row = [option.label, str(option.points_for(side))]
            if reveal:
                other = SELLER if side == BUYER else BUYER
                row.append(str(option.points_for(other)))
            rows.append(row)
        out.append(ui.table(headers, rows, aligns))

    total_stakes = sorted(
        scenario.issues, key=lambda i: i.stake(side), reverse=True
    )
    ranked = ", ".join(f"{i.label} ({i.stake(side)})" for i in total_stakes)
    out.append("")
    out.append(ui.wrap(f"Your priorities, biggest first: {ranked}", ""))
    return "\n".join(out)


def offer_card(offer: Offer, side: str | None = None, *, title: str = "Package") -> str:
    """A compact view of one package, optionally with one side's points."""
    headers = ["term", "value"]
    aligns = "ll"
    if side:
        headers.append("pts")
        aligns += "r"
    rows = []
    for key in offer.scenario.issue_keys:
        issue = offer.scenario.issue(key)
        option = offer.option_for(key)
        row = [issue.label, option.label]
        if side:
            row.append(str(option.points_for(side)))
        rows.append(row)
    if side:
        rows.append(["", ui.paint("TOTAL", "bold"), ui.paint(str(offer.score(side)), "bold")])
    return f"{ui.subheading(title)}\n" + ui.table(headers, rows, aligns)
