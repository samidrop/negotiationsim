"""Personalities.

Each persona bundles two things that are deliberately kept apart from
appearance: how the character BEHAVES (how greedy their opening is, how
fast they concede, how much disrespect they will absorb before they blow
up) and how they TALK.

You are meant to meet all of these. Practising only against a reasonable
opponent is not practice.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# Situations a line can be written for.
OPEN, INSULT, BELOW, CLOSE = "open", "insult", "below", "close"
ACCEPT, THIN, DELIGHT, RAGE, WALK = "accept", "thin", "delight", "rage", "walk"
PRESSED, THREAT, SMALLTALK, STALL = "pressed", "threat", "smalltalk", "stall"


@dataclass(frozen=True)
class Persona:
    key: str
    name: str
    blurb: str
    tell: str                 # what a sharp negotiator would notice about them
    opening_target: int       # how greedy their first offer is
    concession_rate: float    # 1.0 average; below 1 is stubborn
    insult_margin: int        # points below their floor that counts as an insult
    rage_patience: int        # how many insults before they walk out for good
    delight_at: int           # score at which they gleefully take your money
    hint_honesty: float       # how straight their answer is when you ask
    resting_face: str         # expression when nothing is happening
    lines: dict[str, tuple[str, ...]]


def _p(**kw) -> Persona:
    return Persona(**kw)


SHARK = _p(
    key="shark", name="The Shark",
    blurb="Closes for a living and enjoys it. Will take everything you leave loose.",
    tell="Never volunteers information. Every silence is bait.",
    opening_target=95, concession_rate=0.7, insult_margin=10, rage_patience=3,
    delight_at=84, hint_honesty=0.25, resting_face="smug",
    lines={
        OPEN: (
            "Let's not do the dance where you pretend to be shocked. Here's the paper.",
            "I've got three of these today. You're the one I have the least time for.",
            "I'll save us both an hour: this is the number. Convince me otherwise.",
        ),
        INSULT: (
            "Be serious. I've seen interns open better than that and they were being funny.",
            "That's not an offer, that's a cry for help. Try again.",
            "You walked in here and said that out loud. On purpose. Wild.",
        ),
        BELOW: (
            "Under my floor. Not close, not cute, not happening.",
            "No. And the fact that you thought that might land tells me a lot.",
            "You're negotiating against yourself and still losing. Go again.",
        ),
        CLOSE: (
            "Now you're talking like someone who's done this before. Almost.",
            "That's within shouting distance. I still think you've got more in the tank.",
            "Warmer. I can smell a deal. I just don't like the smell yet.",
        ),
        ACCEPT: (
            "Done. And for the record, you left money on this table. I'm not telling you where.",
            "Signed. You did fine. Fine is a word people use when they mean 'not great'.",
            "I'll take it. Good session. Don't ask me who won.",
        ),
        THIN: (
            "It's thin and you know it's thin. But my quarter closes Friday, so: fine.",
            "I'm signing this out of spite for my own forecast. Congratulations.",
        ),
        DELIGHT: (
            "Sold. SOLD. Before you find a calculator.",
            "Absolutely. Signed. Yes. Do you want a pen? I have a pen. Here's a pen.",
            "That is the single best thing anyone has said to me this quarter. Done.",
        ),
        RAGE: (
            "No. We're done. I've been doing this nineteen years and I don't get talked to like that.",
            "Get out. Genuinely. Take your term sheet and go.",
        ),
        WALK: (
            "Clock's dead and so is this. I'd rather run short than sign that.",
            "No deal. I'll find someone who can count.",
        ),
        PRESSED: (
            "Because I said so, and because I'm the one with the capacity you need.",
            "You want my reasoning? My reasoning is I don't need this deal as much as you do.",
        ),
        THREAT: (
            "Walk then. The door does work. I've watched people use it.",
            "Sure. And on Monday you'll be explaining to your board why you have no supplier.",
        ),
        SMALLTALK: (
            "We're not friends. We can be friendly. Those are different.",
            "Small talk is how people stall when they're losing. Are you losing?",
        ),
        STALL: ("Clock's moving. I bill by the hour and you don't pay me.",),
    },
)

PRO = _p(
    key="pro", name="The Professional",
    blurb="Courteous, prepared, and genuinely trying to find a deal that works.",
    tell="Actually answers questions. Rewards you for asking good ones.",
    opening_target=90, concession_rate=1.1, insult_margin=18, rage_patience=5,
    delight_at=88, hint_honesty=0.85, resting_face="neutral",
    lines={
        OPEN: (
            "Thanks for making the time. I'll open where I'd genuinely like to land, and we can work from there.",
            "Good to meet you. I've done my homework on you, so I'll be direct.",
            "Let's start properly. Here's my opening. I don't expect you to take it.",
        ),
        INSULT: (
            "I'll assume that was an anchor rather than a serious proposal. Let's move past it.",
            "That's below anything I could defend internally. I'd rather not spend rounds there.",
            "I understand the tactic. It costs us a round we don't have many of.",
        ),
        BELOW: (
            "That doesn't clear my approval threshold. I'm not being coy, it genuinely doesn't.",
            "Close on structure, short on substance. The shape is right, the level isn't.",
            "I can't sign that. Tell me which of these terms you actually need and I'll try to build around it.",
        ),
        CLOSE: (
            "That's workable in principle. Let me push on one thing and I think we're there.",
            "We're close enough that I'd like to land this today rather than trade paper again.",
            "I could live with that shape. Give me a little on one term and I'll stop asking.",
        ),
        ACCEPT: (
            "That works. Good negotiation, genuinely. I'll get this to legal today.",
            "Agreed. You handled that well and I don't say that to be nice.",
            "Done. Pleasure. I'd do business with you again, which is the real compliment.",
        ),
        THIN: (
            "It's tighter than I'd like, but it's a deal and a deal beats a gap. Agreed.",
            "I'll take it. We both know who did better here, but I'd rather ship.",
        ),
        DELIGHT: (
            "I... yes. Absolutely yes. I want to note for the record that you didn't have to do that.",
            "Signed. And a piece of free advice for next time: you had far more room than you used.",
        ),
        RAGE: (
            "No. I've been patient and you've spent it. I'm ending this here.",
            "I'm going to stop before I say something unprofessional. We're finished.",
        ),
        WALK: (
            "We're out of time and out of overlap. No hard feelings, but no deal.",
            "I can't get there. Let's part cleanly rather than force something bad.",
        ),
        PRESSED: (
            "Fair question. My capacity is committed eight months out; that's what's driving me.",
            "Because the economics only work for me above a certain line, and I'd rather show you the line than hide it.",
        ),
        THREAT: (
            "That's your call to make. I'd rather you didn't, and I'll move if I can.",
            "Understood. Before you do, tell me the one term that would change your mind.",
        ),
        SMALLTALK: (
            "Ha. Good. Right, where were we.",
            "I appreciate a bit of human in the room. Now, terms.",
        ),
        STALL: ("I do have a hard stop, so let's use the rounds we have.",),
    },
)

BURNOUT = _p(
    key="burnout", name="The Burnout",
    blurb="Checked out three quarters ago. Concedes easily, but might just stop caring entirely.",
    tell="Gives ground fast if you ask plainly. Punishes long speeches by tuning out.",
    opening_target=86, concession_rate=1.5, insult_margin=25, rage_patience=6,
    delight_at=80, hint_honesty=0.7, resting_face="bored",
    lines={
        OPEN: (
            "Sure. Yeah. Here's the thing my boss told me to say. I don't love it either.",
            "Right. Opening offer. I typed it this morning. Allegedly.",
            "Cool cool cool. Numbers. Here. Whenever you're ready.",
        ),
        INSULT: (
            "Damn. Okay. That's a choice.",
            "Yeah, no. I'm tired, not concussed.",
            "That's crazy work. Anyway.",
        ),
        BELOW: (
            "Nah that doesn't clear. Not by a lot. Not by a little either.",
            "Can't do it. My floor's a floor, it's like the one thing I still enforce.",
            "Under. Try again but like, actually try.",
        ),
        CLOSE: (
            "Yeah that's basically fine. I'd take slightly more but I'm not gonna fight you.",
            "Eh. That's close enough that I've stopped reading carefully.",
            "Okay yeah, we're nearly there and I have a 4pm.",
        ),
        ACCEPT: (
            "Yeah alright. Send it. I'm not re-reading that.",
            "Sure. Done. Cool. I'm going to go stare at a wall.",
            "Fine, signed, great, wonderful, I'm logging off.",
        ),
        THIN: (
            "Whatever. Yes. It's Friday somewhere.",
            "Sure. Not my money. Signed.",
        ),
        DELIGHT: (
            "Wait. Say that again. ...Okay yeah I'm awake now. Signed.",
            "Bro. BRO. Yes. Absolutely. I'm putting this in the group chat.",
        ),
        RAGE: (
            "Okay, no. I don't get paid enough to be spoken to like that. I'm out.",
            "You know what? No. Done. Genuinely done. Bye.",
        ),
        WALK: (
            "Time's up and honestly I'm relieved. No deal.",
            "Nah. We're out of rounds and I'm out of energy.",
        ),
        PRESSED: (
            "Honestly? I don't know. It's the number in the spreadsheet.",
            "My reasoning is someone above me has a target and I would like them to stop emailing me.",
        ),
        THREAT: (
            "Okay. I mean, that would be less work for me.",
            "You could. Then we both go home. Not the worst pitch you've made.",
        ),
        SMALLTALK: (
            "Yeah. Same. It's been a long year and it's March.",
            "Mm. You ever think about how we're both just doing this until we die? Anyway, terms.",
        ),
        STALL: ("Are we doing this or are we vibing? Either's fine, genuinely.",),
    },
)

HYPE = _p(
    key="hype", name="The Hype Guy",
    blurb="Enormously friendly. Also the slipperiest person in the room.",
    tell="The warmth is real and so is the squeeze. Don't mistake one for the other.",
    opening_target=93, concession_rate=0.95, insult_margin=14, rage_patience=4,
    delight_at=85, hint_honesty=0.4, resting_face="pleased",
    lines={
        OPEN: (
            "Okay okay okay, love this for us. Two serious people, one table. Here's my opener, don't cry.",
            "First of all? Great energy. Second of all, here's a number that's gonna test that energy.",
            "We are SO going to get this done. Starting here. Purely as a vibe check.",
        ),
        INSULT: (
            "Bro. BRO. That's diabolical. I'm not even mad, I'm impressed by the audacity.",
            "That offer is doing negative aura farming. Respectfully, delete it.",
            "Chat, is this real? You typed that with your hands?",
        ),
        BELOW: (
            "Love the ambition, hate the number. Under my floor, king.",
            "So close to cooking and yet the kitchen is on fire. Can't sign it.",
            "That's mid and I say that with affection. Under my line.",
        ),
        CLOSE: (
            "OH. Now we're talking. That's got legs. Nearly got arms.",
            "Okay that's actually a real offer and I'm going to be annoying about the last bit.",
            "We are THIS close. Give me one more thing and I'll stop yapping.",
        ),
        ACCEPT: (
            "YES. Let's go. Deal. Shaking your hand so hard right now.",
            "Done deal! W for both of us. Mostly me, but a W is a W.",
            "Signed, sealed, and I'm telling everyone we're best friends now.",
        ),
        THIN: (
            "Ugh. Fine. FINE. You wore me down and I'm going to think about it tonight.",
            "Taking it. Not happy. Still taking it. That's growth.",
        ),
        DELIGHT: (
            "Oh my God. Oh my GOD. Yes. Signed. Don't move, don't think, sign here.",
            "That's the most generous thing anyone's done for me since my mum. SOLD.",
        ),
        RAGE: (
            "Nope. I was nice to you. I was SO nice to you. We're done.",
            "Okay the vibe is dead and you killed it. I'm walking.",
        ),
        WALK: (
            "Ahh man. No deal. That one hurts, genuinely.",
            "We ran out of clock. That's so unserious of us both.",
        ),
        PRESSED: (
            "Why? Because I like winning and I'm very charming about it.",
            "Great question. Terrible answer: the number is the number, my guy.",
        ),
        THREAT: (
            "Don't say that. Don't SAY that. We were having a moment.",
            "You'd walk? On me? After everything we've been through in eleven minutes?",
        ),
        SMALLTALK: (
            "See THIS is what I'm talking about. Human connection. Now give me volume.",
            "I love that for you. Genuinely. Anyway I still want your money.",
        ),
        STALL: ("Clock's ticking and I've got a padel court booked.",),
    },
)

BUREAUCRAT = _p(
    key="bureaucrat", name="The Bureaucrat",
    blurb="Hides behind process. Every concession needs a permission slip.",
    tell="'I can't approve that' often means 'I can, and I'd rather not'.",
    opening_target=91, concession_rate=0.85, insult_margin=16, rage_patience=6,
    delight_at=86, hint_honesty=0.5, resting_face="neutral",
    lines={
        OPEN: (
            "I've brought the standard terms. Deviations require sign-off, which I'll warn you is slow.",
            "This is our approved opening position. I didn't write it. I do have to defend it.",
            "Before we start: anything outside this framework goes to committee. Plan accordingly.",
        ),
        INSULT: (
            "I'm not able to record that as a serious proposal. Shall we try again?",
            "That falls outside every band I'm permitted to work in. By some distance.",
            "I would have to escalate that, and I won't, because I'd be laughed at.",
        ),
        BELOW: (
            "That's below my delegated authority. I physically cannot sign it.",
            "Non-compliant with our floor. I'm not being difficult, I'm being supervised.",
            "Can't approve. If you want that, you want my director, and she likes you less than I do.",
        ),
        CLOSE: (
            "That's within a band I could defend. Let me push once and then I'll stop.",
            "I think I can get that through. I'd like one more concession to make the memo easier.",
            "Nearly signable. Give me something I can point at in the write-up.",
        ),
        ACCEPT: (
            "That's within my authority. Approved. I'll circulate the paperwork.",
            "Agreed. This will be a clean memo, which is the highest praise I give.",
            "Signed. Well handled. You made my internal justification very easy.",
        ),
        THIN: (
            "It's at the very edge of what I can defend. I'll take the risk. Once.",
            "Approved, reluctantly, and I'll be writing 'commercially necessary' a lot.",
        ),
        DELIGHT: (
            "Approved. Immediately. Enthusiastically. I will personally hand-carry this to legal.",
            "That is comfortably inside every band I have. Signed. No further questions.",
        ),
        RAGE: (
            "I'm terminating this session. That was unacceptable and it will be minuted.",
            "No. I'm ending the meeting. You can take it up with my director.",
        ),
        WALK: (
            "The window has closed. I'm recording this as no agreement reached.",
            "We've exhausted the process. No deal. I'll file it accordingly.",
        ),
        PRESSED: (
            "Policy. I know that's unsatisfying. It's also true.",
            "Because the approval matrix says so, and the matrix does not take meetings.",
        ),
        THREAT: (
            "That's noted. It doesn't change my authority, but it is noted.",
            "If you walk, I'll have to file a no-deal report. I'd genuinely rather not.",
        ),
        SMALLTALK: (
            "Mm. Yes. Shall we return to the terms?",
            "I'd love to chat but I have a governance call at half past.",
        ),
        STALL: ("I have to release this room shortly, so let's progress.",),
    },
)

VOLATILE = _p(
    key="volatile", name="The Live Wire",
    blurb="Charming at nine, hostile at nine-thirty. Test them carefully or not at all.",
    tell="Real leverage, no filter. Lowball once and you may not get a second round.",
    opening_target=94, concession_rate=1.0, insult_margin=8, rage_patience=1,
    delight_at=83, hint_honesty=0.5, resting_face="neutral",
    lines={
        OPEN: (
            "Right. I'm in a good mood. Let's see how long that lasts. Here's my opener.",
            "I like you already. Don't ruin it. Numbers.",
            "Fair warning: I've had two coffees and no lunch. Here's where we start.",
        ),
        INSULT: (
            "Are you SERIOUS? Look at me. Look at my face. Is this a face that finds that funny?",
            "Oh, we're doing THAT. Okay. Noted. Deeply noted.",
            "You know what that is? Disrespect with a spreadsheet attached.",
        ),
        BELOW: (
            "No. Under. Next.",
            "That's under my line and I think you knew that when you said it.",
            "Nope. And my patience is a resource you're spending fast.",
        ),
        CLOSE: (
            "Okay. Okay! See, that's more like it. Now don't get clever.",
            "That's nearly good. I'm nearly pleased. Both of those are fragile.",
            "Right, that I can work with. Do NOT go backwards from here.",
        ),
        ACCEPT: (
            "YES. Good. Great. See, we could have done that twenty minutes ago.",
            "Done! Shake on it before I reread it.",
            "Deal. I like you again. That's a limited-time offer.",
        ),
        THIN: (
            "Fine. FINE. I'm signing it and I'm going to be weird about it for a week.",
            "Taking it. Under protest. Loudly. Signed.",
        ),
        DELIGHT: (
            "HA! Yes! Sign it, sign it now, don't you dare reread that. HA!",
            "Oh that's beautiful. That's genuinely beautiful. Done. DONE.",
        ),
        RAGE: (
            "NO. Enough! That's it, we're finished, I'm done with this!",
            "Absolutely NOT. I'm done. Do not contact my office.",
        ),
        WALK: (
            "Time. Gone. No deal. I'm not chasing this.",
            "We're out of road and I'm out of patience. Nothing signed.",
        ),
        PRESSED: (
            "Because it's MY plant and MY capacity and I said so.",
            "You want justification? Fine: I have two other buyers and one of them is polite.",
        ),
        THREAT: (
            "Then WALK. Go on. I'll hold the door. I'll hold it open.",
            "Threatening me. In my meeting. Bold. Do it then.",
        ),
        SMALLTALK: (
            "Ha! Yeah. See, you're alright. Don't make me regret saying that.",
            "I'm not doing chit-chat, I'm doing business. But that was funny, I'll give you that.",
        ),
        STALL: ("Move it along. I can feel my mood turning.",),
    },
)

OLDHEAD = _p(
    key="oldhead", name="The Old Head",
    blurb="Thirty years in. Values the relationship, and will use that on you.",
    tell="The stories are real and they're also a clock-management tactic.",
    opening_target=89, concession_rate=0.9, insult_margin=20, rage_patience=4,
    delight_at=87, hint_honesty=0.75, resting_face="pleased",
    lines={
        OPEN: (
            "I've been doing this since before your company had a logo. Here's my number.",
            "I'll tell you what I told your predecessor: I open honest and I finish honest.",
            "Sit down, have a coffee. Then look at this and be upset in your own time.",
        ),
        INSULT: (
            "Son, I've been lowballed by professionals. That wasn't even a good one.",
            "In 1998 a man offered me less than that and I still think about him. Don't be him.",
            "I'll pretend I didn't hear it. That's the last freebie you get.",
        ),
        BELOW: (
            "Below my line. I've held that line through two recessions, I'll hold it through you.",
            "No. And I'll tell you plainly rather than waste your afternoon.",
            "Doesn't clear. Come up, and I'll meet you like a grown-up.",
        ),
        CLOSE: (
            "Now that's the offer of someone who's read the room. Nearly there.",
            "I like that. I want one more thing, then I'll shut up and sign.",
            "That's respectable. Give me a little more and we'll shake on it.",
        ),
        ACCEPT: (
            "Shake my hand. That's a deal, and I don't unshake hands.",
            "Good. That's how it's supposed to go. You'll do well in this business.",
            "Done. And I mean this: you negotiated that properly.",
        ),
        THIN: (
            "It's lean. I've signed leaner. Go on then.",
            "I'll take it, because a deal today beats a maybe in March.",
        ),
        DELIGHT: (
            "Well now. That's very generous of you. Suspiciously generous. Signed, quickly.",
            "Hah! I'm taking that before you call your finance director. Done.",
        ),
        RAGE: (
            "No. I've been in rooms with serious people my whole career and this isn't one. Good day.",
            "That's enough. I don't need this at my age. We're finished.",
        ),
        WALK: (
            "We're out of time. It happens. No hard feelings, no deal.",
            "Not this one. Come back next year with a better mandate.",
        ),
        PRESSED: (
            "Because I've watched companies die taking deals like the one you're asking for.",
            "Thirty years of data, son, and all of it says no.",
        ),
        THREAT: (
            "You'd be the fourth this year. Two came back. Do what you like.",
            "Walk if you must. I'd rather you didn't, and I'd rather you knew that.",
        ),
        SMALLTALK: (
            "Ha! Good. You remind me of someone. He was trouble too.",
            "That's the first interesting thing anyone's said to me today. Now, terms.",
        ),
        STALL: ("Time's getting on and I've a train to catch.",),
    },
)

QUANT = _p(
    key="quant", name="The Quant",
    blurb="Treats this as arithmetic. No warmth, no games, no mercy either.",
    tell="Completely consistent. If you find the logic, you can predict every move.",
    opening_target=92, concession_rate=1.0, insult_margin=15, rage_patience=8,
    delight_at=86, hint_honesty=0.9, resting_face="neutral",
    lines={
        OPEN: (
            "My opening reflects my reservation value plus a negotiating margin. Both are real.",
            "I've modelled this. Here's the opening. I'll tell you now: I concede on a schedule.",
            "I don't bluff, it's inefficient. This is high, and I will come down.",
        ),
        INSULT: (
            "That's more than twenty points below my floor. It isn't an offer, it's noise.",
            "Rejected. The gap isn't bridgeable from there in the rounds remaining.",
            "That proposal has a zero percent acceptance probability. Please revise.",
        ),
        BELOW: (
            "Below my reservation value. I'd take no deal over that, by definition.",
            "Doesn't clear. The deficit is meaningful, not marginal.",
            "No. Tell me which term you weight highest and I'll optimise around it.",
        ),
        CLOSE: (
            "That's inside my acceptable band. I'll test whether you have more first.",
            "Acceptable shape, suboptimal level. One adjustment and I sign.",
            "Positive surplus for me. I'd like more of it. Predictably.",
        ),
        ACCEPT: (
            "Accepted. That clears my threshold. Efficient session.",
            "Agreed. For what it's worth, you traded the right terms.",
            "Signed. Your allocation was better than most people manage.",
        ),
        THIN: (
            "Marginally above my floor. Positive is positive. Accepted.",
            "The surplus is small but real, and no-deal is worth exactly zero. Accepted.",
        ),
        DELIGHT: (
            "Accepted immediately. I want to be clear that you did not have to offer that.",
            "That's a substantial overpayment. I'm taking it. Model your side next time.",
        ),
        RAGE: (
            "I'm terminating. Repeated non-serious proposals have negative expected value.",
            "Enough. You've spent the rounds and my goodwill. Ending here.",
        ),
        WALK: (
            "Rounds exhausted, no overlap reached. Outcome: no deal.",
            "We failed to find the zone. That's a modelling failure on somebody's part.",
        ),
        PRESSED: (
            "My floor is set by my next best alternative. It isn't a posture.",
            "Because below that line, no-deal dominates. That's the whole reasoning.",
        ),
        THREAT: (
            "Then you walk and we both take our fallback. I've priced that outcome.",
            "Understood. Note that walking is worth less to you than three of my current terms.",
        ),
        SMALLTALK: (
            "Noted. Returning to terms.",
            "I'm poor at this part. I'm considerably better at the next part.",
        ),
        STALL: ("Rounds are a depleting resource. We have few left.",),
    },
)

PERSONAS: tuple[Persona, ...] = (
    SHARK, PRO, BURNOUT, HYPE, BUREAUCRAT, VOLATILE, OLDHEAD, QUANT,
)
BY_KEY = {p.key: p for p in PERSONAS}


def random_persona(rng: random.Random) -> Persona:
    return rng.choice(PERSONAS)


def line(persona: Persona, situation: str, rng: random.Random, fallback: str = "") -> str:
    pool = persona.lines.get(situation)
    if not pool:
        return fallback
    return rng.choice(pool)
