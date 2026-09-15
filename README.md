# Negotiation Simulator

A terminal negotiation trainer. You play Head of Procurement buying a critical
component. An AI character plays the supplier's VP of Sales. You haggle across
five issues, sign a deal, and then find out how much value the two of you threw
away — and what you should have done instead.

The point is not to "win". It is to notice that some issues are cheap for you
and precious for them (and vice versa), and to trade those rather than split
every difference down the middle.

Every game generates a **random product** — facial tissue, lithium cells, solar
microinverters, oat milk — with its own realistic prices and volumes, and freshly
randomised hidden point values. The generator guarantees that a zone of possible
agreement exists but is narrow, so a deal is always available and never easy.

## The five issues

| Issue | Options |
|---|---|
| Price per unit | $18 / $20 / $22 / $24 / $26 |
| Volume commitment | 10k / 25k / 50k / 100k units a year |
| Payment terms | Net 15 / 30 / 60 / 90 |
| Delivery window | 2 / 4 / 8 / 12 weeks |
| Exclusivity | none / regional 1yr / regional 2yr / global 2yr |

Each side privately scores every option. A perfect sweep is 100 points. Each
side also has a **walk-away score** — sign nothing worth less than that.

## Play

```bash
python3 negotiate.py play                # a random deal
python3 negotiate.py play --seed 42      # replay an exact deal
python3 negotiate.py play --rounds 12    # a longer negotiation
```

Each round you can counter-offer, accept, ask what matters to them, re-read your
brief, or walk away. A side bar tracks the price on the table, the estimated
annual contract value, and your score against your walk-away line.

## Inspect

```bash
python3 negotiate.py sheet              # your confidential brief
python3 negotiate.py sheet --reveal     # ...with the AI's secret points too
python3 negotiate.py sheet --side seller

# Score any package you like:
python3 negotiate.py score price=22 volume=25k payment=net30 delivery=8w exclusivity=region1y

# Run the checks on the maths:
python3 -m unittest discover -s tests
```

## How it is built

| File | What it does |
|---|---|
| `negosim/deal.py` | The scenario: issues, options, and both sides' secret points |
| `negosim/analysis.py` | Scores every one of the 1,280 possible packages and finds the win-win swaps you missed |
| `negosim/products.py` | Random products and guaranteed-negotiable scenario generation |
| `negosim/opponent.py` | The supplier: concession schedule, and learning what you care about |
| `negosim/game.py` | The playable round loop |
| `negosim/hud.py` | The live side bar |
| `negosim/sheet.py` | Renders the confidential briefs |
| `negosim/ui.py` | Terminal colours and tables |
| `negotiate.py` | Command line entry point |
| `tests/` | Checks that the scenario is actually negotiable and the maths is right |

Python 3.9+. No dependencies.
