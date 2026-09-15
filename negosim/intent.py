"""Reading plain English.

When the player types a sentence instead of picking a menu number, this
works out what they were trying to DO. It is deliberately simple and
transparent: a scored keyword match. When a live language model is
available it handles the reply instead, but the intent still drives the
character's expression and any mechanical consequence.
"""

from __future__ import annotations

import re

ASK_PRIORITIES = "ask_priorities"
ASK_WHY = "ask_why"
THREATEN_WALK = "threaten_walk"
FLATTER = "flatter"
INSULT = "insult"
PROPOSE_TRADE = "propose_trade"
SIGNAL_FLEXIBLE = "signal_flexible"
PRESS_DEADLINE = "press_deadline"
SMALLTALK = "smalltalk"
CONFUSED = "confused"

PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (ASK_PRIORITIES, (
        r"\bwhat (do you|matters|are you|would you)\b", r"\bmost important\b",
        r"\bpriorit", r"\bcare (most )?about\b", r"\bwhat.*\bneed\b",
        r"\bwhich.*\bmatter", r"\bwhat's driving\b", r"\bwhat is driving\b",
    )),
    (ASK_WHY, (
        r"\bwhy\b", r"\bjustify\b", r"\bexplain\b", r"\bhow come\b",
        r"\bwhere.*number.*from\b", r"\bon what basis\b",
    )),
    (THREATEN_WALK, (
        r"\bwalk (away|out)\b", r"\bleave the table\b", r"\bno deal\b",
        r"\banother supplier\b", r"\bcompetitor\b", r"\bgo elsewhere\b",
        r"\bwe're done\b", r"\bi'?ll take my\b", r"\bfind someone else\b",
    )),
    (FLATTER, (
        r"\brespect\b", r"\bappreciate\b", r"\bgood (point|offer)\b",
        r"\bfair enough\b", r"\bnice\b", r"\bpleasure\b", r"\blike working\b",
        r"\bthank you\b", r"\bthanks\b", r"\bimpress",
    )),
    (INSULT, (
        r"\bridiculous\b", r"\bjoke\b", r"\binsult", r"\bpathetic\b",
        r"\bwaste of (my )?time\b", r"\bclown\b", r"\bnonsense\b",
        r"\brobbery\b", r"\bripping me off\b", r"\bgreedy\b", r"\bdelusional\b",
    )),
    (PROPOSE_TRADE, (
        r"\bif you\b.*\bi(')?ll\b", r"\bin (exchange|return)\b", r"\btrade\b",
        r"\bgive you\b", r"\bswap\b", r"\bin that case\b", r"\bi can (give|offer|do)\b",
        r"\bwould you take\b", r"\bhow about\b",
    )),
    (SIGNAL_FLEXIBLE, (
        r"\bflexible\b", r"\bdon'?t (really )?care about\b", r"\bnot (that )?important to (me|us)\b",
        r"\bhappy to move\b", r"\bcan live with\b", r"\bopen to\b",
    )),
    (PRESS_DEADLINE, (
        r"\btime\b", r"\bhurry\b", r"\bquick", r"\bclose (this|it) (out|today)\b",
        r"\bwrap (this )?up\b", r"\brunning out\b",
    )),
    (SMALLTALK, (
        r"\bhow are you\b", r"\bweekend\b", r"\bweather\b", r"\bcoffee\b",
        r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgood morning\b", r"\bnice to meet\b",
        r"\blunch\b", r"\bfamily\b", r"\bholiday\b",
    )),
)


def classify(text: str) -> str:
    """Best guess at what the player meant. One intent, most specific wins."""
    lowered = text.lower().strip()
    if not lowered:
        return CONFUSED
    scores: dict[str, int] = {}
    for intent, patterns in PATTERNS:
        hits = sum(1 for pattern in patterns if re.search(pattern, lowered))
        if hits:
            scores[intent] = hits
    if not scores:
        return CONFUSED
    # Prefer the intent with the most matches; ties break toward the
    # consequential intents rather than the social ones.
    priority = {
        THREATEN_WALK: 5, INSULT: 5, PROPOSE_TRADE: 4, ASK_PRIORITIES: 4,
        SIGNAL_FLEXIBLE: 3, ASK_WHY: 3, PRESS_DEADLINE: 2, FLATTER: 1, SMALLTALK: 0,
    }
    return max(scores, key=lambda k: (scores[k], priority.get(k, 0)))


def mentioned_issues(text: str, issue_keys: tuple[str, ...]) -> list[str]:
    """Which of the five issues the player named, if any."""
    lowered = text.lower()
    words = {
        "price": ("price", "unit cost", "per unit", "cost", "cheaper", "expensive", "$"),
        "volume": ("volume", "units", "quantity", "commit", "order size", "annual"),
        "payment": ("payment", "net ", "terms", "pay ", "invoice", "cash"),
        "delivery": ("delivery", "lead time", "weeks", "fast", "ship", "schedule"),
        "exclusivity": ("exclusiv", "exclusive", "compet", "rights", "lock"),
    }
    found = []
    for key in issue_keys:
        for needle in words.get(key, ()):
            if needle in lowered:
                found.append(key)
                break
    return found
