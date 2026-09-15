"""Generating the person sitting across the table.

Name, appearance and personality are drawn INDEPENDENTLY of one another.
There is deliberately no correlation between how someone looks and how they
negotiate -- any face can be paired with any temperament. That is both the
honest way to build it and the point of the exercise: you cannot read a
negotiator off their appearance.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from . import portrait
from .persona import Persona, random_persona

FIRST_NAMES = (
    "Dana", "Marcus", "Priya", "Tomas", "Aisha", "Gunnar", "Mei", "Rafael",
    "Ngozi", "Katya", "Idris", "Siobhan", "Hiroshi", "Fatima", "Bjorn", "Lucia",
    "Omar", "Ingrid", "Kwame", "Rosa", "Dmitri", "Yuki", "Amara", "Sean",
    "Leila", "Andres", "Nadia", "Piotr", "Sofia", "Malik", "Elena", "Jun",
    "Grace", "Hassan", "Freya", "Diego", "Anika", "Theo", "Zainab", "Caleb",
    "Mirembe", "Lars", "Imani", "Valentina", "Ravi", "Noor", "Otto", "Chiamaka",
)
LAST_NAMES = (
    "Okafor", "Lindqvist", "Ferreira", "Nakamura", "Osei", "Whitfield", "Bekele",
    "Castellanos", "Petrov", "Haddad", "O'Rourke", "Tanaka", "Mbeki", "Novak",
    "Delgado", "Ferrante", "Achebe", "Sorensen", "Rahman", "Kowalski", "Diallo",
    "Marchetti", "Yilmaz", "Nkemdirim", "Bergstrom", "Aguilar", "Chaudhry",
    "Vasquez", "Kaminski", "Adeyemi", "Moreau", "Silva", "Hoffman", "Baptiste",
    "Ivanova", "Qureshi", "Lindgren", "Obi", "Salvatore", "Mwangi", "Duarte",
)


@dataclass(frozen=True)
class Character:
    name: str
    title: str
    company: str
    look: portrait.Look
    persona: Persona

    @property
    def full_title(self) -> str:
        return f"{self.name}, {self.title}, {self.company}"

    def describe_appearance(self) -> str:
        bits = [self.look.attire_name]
        if self.look.eyewear != "none":
            bits.append({"glasses": "wire glasses", "round": "round glasses",
                         "thick": "heavy black frames"}[self.look.eyewear])
        if self.look.facial_hair not in ("clean",):
            bits.append({"stubble": "a few days of stubble", "moustache": "a moustache",
                         "goatee": "a goatee", "beard": "a beard",
                         "fullbeard": "a full beard"}[self.look.facial_hair])
        if self.look.accessory != "none":
            bits.append({"cigar": "an unlit cigar they keep rolling between their fingers",
                         "toothpick": "a toothpick they never remove",
                         "earpiece": "an earpiece they never take out",
                         "pen": "a pen tucked behind one ear",
                         "vape": "a vape they are not supposed to use indoors"}[self.look.accessory])
        return ", ".join(bits)

    def portrait(self, expression: str = portrait.NEUTRAL) -> list[str]:
        return portrait.draw(self.look, expression)


def random_look(rng: random.Random) -> portrait.Look:
    attire_name, attire_cut = rng.choice(portrait.ATTIRE)
    return portrait.Look(
        skin=rng.choice(portrait.SKIN_TONES),
        hair_colour=rng.choice(portrait.HAIR_COLOURS),
        hair=rng.choice(portrait.HAIR_STYLES),
        facial_hair=rng.choice(portrait.FACIAL_HAIR),
        eyewear=rng.choice(portrait.EYEWEAR),
        accessory=rng.choice(portrait.ACCESSORIES),
        attire_name=attire_name,
        attire_cut=attire_cut,
        attire_colour=rng.choice(portrait.ATTIRE_COLOURS),
        shirt_colour=rng.choice((255, 253, 189, 195, 224, 230)),
    )


def generate_character(rng: random.Random, company: str, title: str = "VP of Sales") -> Character:
    return Character(
        name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
        title=title,
        company=company,
        look=random_look(rng),
        persona=random_persona(rng),
    )
