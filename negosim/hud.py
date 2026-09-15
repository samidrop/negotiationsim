"""The status side bar: what's on the table, what it's worth, where you stand."""

from __future__ import annotations

from . import ui
from .deal import BUYER, Offer, Scenario
from .products import Product, contract_value

SIDEBAR_WIDTH = 27
MAIN_WIDTH = ui.WIDTH - SIDEBAR_WIDTH - 3


def _price_ladder(offer: Offer | None, yours: Offer | None) -> list[str]:
    if offer is None:
        return []
    issue = offer.scenario.issue("price")
    on_table = offer.option_for("price").key
    mine = yours.option_for("price").key if yours else None
    lines = []
    for option in issue.options:
        if option.key == on_table:
            marker, style = ">", ("bold", "yellow")
        elif option.key == mine:
            marker, style = "*", ("cyan",)
        else:
            marker, style = " ", ("dim",)
        lines.append(ui.paint(f"{marker} {option.label:>10}", *style))
    return lines


def sidebar(
    scenario: Scenario,
    product: Product,
    on_table: Offer | None,
    yours: Offer | None,
    round_no: int,
    rounds: int,
) -> list[str]:
    lines: list[str] = []
    lines.append(ui.paint(f"ROUND {round_no} OF {rounds}", "bold"))
    lines.append("")

    lines.append(ui.paint(f"PRICE PER {product.unit.upper()}", "bold"))
    lines.extend(_price_ladder(on_table, yours))
    lines.append(ui.paint("  > theirs  * yours", "dim"))
    lines.append("")

    lines.append(ui.paint("EST. ANNUAL VALUE", "bold"))
    if on_table is not None:
        value = contract_value(on_table)
        lines.append(f"  {ui.paint(f'${value:,.0f}', 'yellow')}  theirs")
    if yours is not None:
        lines.append(f"  {ui.paint(f'${contract_value(yours):,.0f}', 'cyan')}  yours")
    lines.append("")

    lines.append(ui.paint("YOUR SCORE IF SIGNED", "bold"))
    walkaway = scenario.buyer_walkaway
    if on_table is not None:
        score = on_table.score(BUYER)
        lines.append("  " + ui.meter(score, 100, walkaway, width=18))
        verdict = "above your floor" if score >= walkaway else "BELOW YOUR FLOOR"
        style = "green" if score >= walkaway else "red"
        lines.append(f"  {ui.paint(str(score), 'bold')} / 100  " + ui.paint(verdict, style))
    lines.append(ui.paint(f"  walk away = {walkaway}", "dim"))
    lines.append(ui.paint("  (the | on the bar)", "dim"))
    return lines


def view(main: list[str], side: list[str]) -> str:
    return ui.columns(main, side, MAIN_WIDTH)


def wrap_main(text: str, indent: str = "") -> list[str]:
    import textwrap

    return textwrap.wrap(
        text, width=MAIN_WIDTH, initial_indent=indent, subsequent_indent=indent
    ) or [""]
