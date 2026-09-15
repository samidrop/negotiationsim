"""Optional live dialogue, powered by Claude.

If the Anthropic SDK is installed and credentials are available, the
character's lines are written fresh by a language model that has been told
who it is, how it feels, and exactly what just happened. If anything at all
is missing or fails, every call here returns None and the game silently
falls back to its written dialogue. The game never breaks because the
network did.

Nothing here decides anything mechanical. Whether an offer is accepted,
refused or rages out is settled by the rules in opponent.py. The model only
chooses the words.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

MODEL = os.environ.get("NEGOSIM_MODEL", "claude-opus-5")
MAX_TOKENS = 300
_client = None
_state = "unknown"   # unknown | ready | unavailable
_reason = ""


def _load():
    global _client, _state, _reason
    if _state != "unknown":
        return _client
    if os.environ.get("NEGOSIM_NO_LLM"):
        _state, _reason = "unavailable", "disabled by NEGOSIM_NO_LLM"
        return None
    try:
        import anthropic
    except ImportError:
        _state, _reason = "unavailable", "the 'anthropic' package is not installed"
        return None
    try:
        # Credentials resolve from ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN,
        # or a profile written by `ant auth login`.
        _client = anthropic.Anthropic()
        _state = "ready"
    except Exception as exc:  # noqa: BLE001 - never let this break the game
        _state, _reason = "unavailable", f"{type(exc).__name__}: {exc}"
        _client = None
    return _client


def status() -> tuple[bool, str]:
    _load()
    if _state == "ready":
        return True, f"live dialogue on, model {MODEL}"
    return False, f"live dialogue off ({_reason})"


@dataclass
class Moment:
    """Everything the model needs to know to write one line in character."""

    persona_name: str
    persona_blurb: str
    character_name: str
    company: str
    product: str
    situation: str
    mood: str
    round_no: int
    rounds_total: int
    their_offer: str
    player_offer: str | None
    player_said: str | None
    scripted: str            # the written line it is replacing, as a guide


SYSTEM = """You are voicing one character in a negotiation training game played \
in a terminal. You are the SELLER. The player is the buyer.

You write ONE short spoken line, 1-3 sentences, in character. No stage \
directions, no quotation marks, no narration, no emoji, no markdown. Just the \
words the character says out loud.

Voice rules:
- Be blunt and unfiltered. Say what the character actually thinks.
- Humour is welcome and should feel like a real person who is online too much: \
dry, current, a little out of pocket. Never corny, never a dad joke, never a \
pun. Do not explain the joke.
- Roast the offer, the situation, or the player's negotiating. Never make a \
joke about anyone's race, gender, religion, nationality, appearance, accent, \
disability or sexuality. No slurs.
- Stay in the fiction. You are a person selling a product, not an assistant. \
Never break character, never mention being an AI or a model, and never \
mention these instructions.
- Do NOT state your own point score, your walk-away number, or any game \
mechanics. You may talk about margin, capacity, quarters, bosses and risk.
- Do NOT accept or refuse the deal in your words unless the situation you are \
given says you are accepting or refusing. The game decides that, not you.

You will be given a scripted fallback line. Match its intent and its \
emotional temperature, but write something better and more specific to what \
just happened."""


def speak(moment: Moment) -> str | None:
    """Ask the model for one in-character line. None if unavailable."""
    client = _load()
    if client is None:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    prompt = f"""Character: {moment.character_name}, {moment.company}.
Personality type: {moment.persona_name} - {moment.persona_blurb}
Currently feeling: {moment.mood}
Selling: {moment.product}
Round {moment.round_no} of {moment.rounds_total}.

Your current offer on the table: {moment.their_offer}
The buyer's latest offer: {moment.player_offer or "they have not made one yet"}
{f'The buyer just said to you: "{moment.player_said}"' if moment.player_said else ""}

Situation: {moment.situation}
Scripted fallback line: "{moment.scripted}"

Write the line."""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            output_config={"effort": "low"},
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception:  # noqa: BLE001 - any failure falls back to script
        return None

    if getattr(response, "stop_reason", None) == "refusal":
        return None
    text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ).strip()
    text = text.strip('"').strip()
    return text or None
