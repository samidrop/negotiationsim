"""Turning what just happened into a face and a line of dialogue."""

from __future__ import annotations

import random

from . import persona as P
from . import portrait as X
from .character import Character
from .llm import Moment, speak

# Which face goes with which moment.
FACE_FOR: dict[str, str] = {
    P.OPEN: X.NEUTRAL,
    P.INSULT: X.ANGRY,
    P.BELOW: X.ANNOYED,
    P.CLOSE: X.THINKING,
    P.ACCEPT: X.PLEASED,
    P.THIN: X.SMUG,
    P.DELIGHT: X.DELIGHTED,
    P.RAGE: X.FURIOUS,
    P.WALK: X.ANGRY,
    P.PRESSED: X.SMUG,
    P.THREAT: X.SMUG,
    P.SMALLTALK: X.PLEASED,
    P.STALL: X.BORED,
    P.EPILOGUE_GOOD: X.PLEASED,
    P.EPILOGUE_BAD: X.SMUG,
}

MOOD_FOR: dict[str, str] = {
    P.OPEN: "businesslike, anchoring high",
    P.INSULT: "genuinely offended",
    P.BELOW: "unimpressed",
    P.CLOSE: "interested, still pushing",
    P.ACCEPT: "satisfied",
    P.THIN: "grudging",
    P.DELIGHT: "gleeful - the buyer just massively overpaid",
    P.RAGE: "furious, ending the meeting",
    P.WALK: "cold, done",
    P.PRESSED: "guarded",
    P.THREAT: "called the bluff",
    P.SMALLTALK: "briefly human",
    P.STALL: "impatient",
    P.EPILOGUE_GOOD: "candid, giving credit where it is due",
    P.EPILOGUE_BAD: "candid, telling them what they got wrong",
}

# A loose comic register per personality, used for unprompted asides.
TONE = {
    "shark": "brash", "hype": "brash", "volatile": "brash",
    "burnout": "weary", "oldhead": "weary",
    "pro": "dry", "quant": "dry", "bureaucrat": "corporate",
}

ASIDES = {
    "brash": (
        "You've got the energy of someone who read one book about this.",
        "I can hear your finance director sweating from here.",
        "Genuinely, who taught you to anchor? I want a word with them.",
        "This is the most fun I've had being slightly insulted all week.",
        "You keep looking at the price like it's going to blink first.",
    ),
    "weary": (
        "I've had this exact conversation about four hundred times.",
        "You know what's wild? None of this will matter in five years.",
        "I used to care about winning these. Now I just want lunch.",
        "Every year the numbers change and the meeting doesn't.",
    ),
    "dry": (
        "You're spending your rounds on the one term where neither of us wins.",
        "Noted. Filed. Mildly disagreed with.",
        "I'd say that's clever, but I can see what you're doing from here.",
        "You have four other terms. You've used one.",
    ),
    "corporate": (
        "I'd love to say yes. My approval matrix has other plans.",
        "Circling back to the ask: still outside my band.",
        "I'll take that away and think about it. That's not a yes.",
        "There's a process here, and you're currently arguing with it.",
    ),
}


def face_and_mood(situation: str) -> tuple[str, str]:
    return FACE_FOR.get(situation, X.NEUTRAL), MOOD_FOR.get(situation, "neutral")


def resting_face(character: Character) -> str:
    return character.persona.resting_face


def aside(character: Character, rng: random.Random) -> str | None:
    """An unprompted remark. They do not always have one."""
    tone = TONE.get(character.persona.key, "dry")
    return rng.choice(ASIDES[tone])


def say(
    character: Character,
    situation: str,
    rng: random.Random,
    *,
    context: dict | None = None,
    player_said: str | None = None,
) -> tuple[str, str]:
    """Return (line, expression). Uses the live model when it is available,
    and the written dialogue when it is not."""
    scripted = P.line(character.persona, situation, rng, fallback="...")
    expression, mood = face_and_mood(situation)

    context = context or {}
    live = speak(
        Moment(
            persona_name=character.persona.name,
            persona_blurb=character.persona.blurb,
            character_name=character.name,
            company=character.company,
            product=context.get("product", "components"),
            situation=_describe(situation),
            mood=mood,
            round_no=context.get("round_no", 1),
            rounds_total=context.get("rounds_total", 8),
            their_offer=context.get("their_offer", "not yet tabled"),
            player_offer=context.get("player_offer"),
            player_said=player_said,
            scripted=scripted,
        )
    )
    return (live or scripted), expression


DESCRIPTIONS = {
    P.OPEN: "You are opening the negotiation with an aggressive first offer.",
    P.INSULT: "The buyer just made an offer so low it is insulting. React to the disrespect.",
    P.BELOW: "The buyer's offer is under your floor. Reject it but keep negotiating.",
    P.CLOSE: "The buyer's offer is nearly acceptable. Push for a little more.",
    P.ACCEPT: "You are accepting the buyer's offer. You are happy with it.",
    P.THIN: "You are accepting reluctantly at the deadline because a thin deal beats none.",
    P.DELIGHT: "The buyer has offered you far more than you needed. Accept instantly and gloat.",
    P.RAGE: "You have lost your temper completely and are ending the meeting for good.",
    P.WALK: "Time has run out with no agreement. You are leaving.",
    P.PRESSED: "The buyer asked you to justify your position.",
    P.THREAT: "The buyer threatened to walk away from the deal.",
    P.SMALLTALK: "The buyer made small talk or was friendly.",
    P.STALL: "The buyer is wasting time and you want to move on.",
    P.EPILOGUE_GOOD: ("The negotiation is over and the act is dropped. Tell the buyer, "
                      "honestly, what they did well. You can still be blunt about it."),
    P.EPILOGUE_BAD: ("The negotiation is over and the act is dropped. Tell the buyer, "
                     "honestly, the single biggest thing they got wrong. Be blunt and "
                     "a little smug, but actually useful -- this is the one moment you "
                     "are on their side."),
}


def _describe(situation: str) -> str:
    return DESCRIPTIONS.get(situation, situation)
