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

## Who you negotiate against

Every game generates a person: a name, a drawn portrait, and one of **eight
personality types** — the Shark, the Professional, the Burnout, the Hype Guy,
the Bureaucrat, the Live Wire, the Old Head, the Quant. Appearance and
personality are drawn completely independently, so you cannot read a negotiator
off their face. You find out who you drew in the debrief, not before.

Personality is not decoration. It changes how greedy their opening is, how fast
they concede, how honest they are when you ask what they want, and how much
disrespect they will absorb before they walk out for good. **Lowball a Live Wire
and they will overturn the chair and leave.** Massively overpay anyone and they
will sign it with dollar signs in their eyes before you can reread it.

Their face reacts to every offer — bored, thinking, smug, annoyed, furious,
delighted — and they have real opinions, which they will share whether you asked
or not.

## Play

```bash
python3 negotiate.py play                # a random deal
python3 negotiate.py play --seed 42      # replay an exact deal
python3 negotiate.py play --rounds 12    # a longer negotiation

python3 negotiate.py faces               # browse the randomly generated people
python3 negotiate.py faces --expressions # one person in every mood
python3 negotiate.py check               # is live AI dialogue switched on?
```

Each round you can counter-offer, accept, ask what matters to them, **say
something to them in plain English**, re-read your brief, or walk away. A side
bar tracks the price on the table, the estimated annual contract value, and your
score against your walk-away line.

Talking is not cosmetic. Insulting them burns goodwill and shortens their fuse;
being warm buys patience back; telling them you are flexible on a term makes
them stop paying you for it; naming a trade out loud makes them expect it.

## The debrief

When the deal closes (or doesn't), three things happen.

**They drop the act.** Whoever you just negotiated against tells you, in their
own voice, what they saw you do. The Professional is constructive about it. The
Shark tells you what he let you get away with. The Burnout admits he'd have
caved on three terms if you'd pushed.

**A map of every deal that was possible**, with yours marked on it:

```
  their score
  100 +----------------------------------------------
      |o
      |. o.o ...o
      |   ........o.o
      | .   ...........ooo.o
      |  . ..................o.o.o
      |    ... ...................ooo
      |      .........................oo
      |         ..............@..........Boo
      |             ........................ooo
    0 |                                             o
      +----------------------------------------------
       0                              your score  100

  . possible   o efficient   B best you could have had   @ your deal
```

**Then the hard numbers.** A "who won what" table showing, term by term, what
each side was playing for and who took it. The win-win trades you walked past,
stated as concrete swaps. The best package they would ever have signed. Then
the mistakes, worst first — and a grade.

The analysis is exhaustive, not opinion: the simulator knows all 1,280 packages
and both hidden scoresheets, so it can say precisely which trades existed.

One structural fact the debrief is built around: **no single term can ever make
both sides better off.** Every issue on its own is a straight tug of war. Gains
for both only exist when you trade one term against another. That is the whole
game, and it is why "meeting in the middle" on everything is the worst common
outcome.

## Live AI dialogue (optional)

Out of the box every character speaks from 241 hand-written lines and reads your
typed English by intent. If you install the Anthropic SDK and provide a key, the
same characters write their lines fresh instead:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python3 negotiate.py check
```

The language model only chooses the words. Whether an offer is accepted,
refused, or rage-quit is always decided by the rules, so the game cannot be
talked out of its own logic. If the key is missing or the network fails, it
falls back to the written dialogue silently and the game plays identically.

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
| `negosim/opponent.py` | The supplier: concession schedule, learning what you care about, losing their temper |
| `negosim/persona.py` | Eight personality types and 241 lines of dialogue |
| `negosim/character.py` | Random people: name, look and temperament, drawn independently |
| `negosim/portrait.py` | Clipart faces in 256 colours, with thirteen expressions |
| `negosim/intent.py` | Reading what the player typed in plain English |
| `negosim/banter.py` | Choosing the face and the line for the moment |
| `negosim/coach.py` | The debrief: scorecard, win-win trades, mistakes, grade, frontier map |
| `negosim/llm.py` | Optional live dialogue via the Claude API |
| `negosim/game.py` | The playable round loop |
| `negosim/hud.py` | The live side bar |
| `negosim/sheet.py` | Renders the confidential briefs |
| `negosim/ui.py` | Terminal colours and tables |
| `negotiate.py` | Command line entry point |
| `tests/` | Checks that the scenario is actually negotiable and the maths is right |

Python 3.9+. No dependencies. 100 tests: `python3 -m unittest discover -s tests`
