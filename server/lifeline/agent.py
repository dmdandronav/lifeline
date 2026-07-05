"""The takeover agent: a scripted time-wasting persona.

Once the user hands off the call, "Margaret" (the agent) keeps the scammer
talking with meandering, deterministic stall tactics. Replies are keyed to
the *kind* of pressure the scammer is applying — payment demands get
confused payment questions, urgency gets slow rambling, authority gets
polite bureaucratic doubt — so the banter reads as responsive rather than
random.

Fully offline and deterministic. An optional LLM layer (``lifeline.llm``)
can spice up replies when an API key is present.
"""

from __future__ import annotations

from dataclasses import dataclass

from .classifier import AUTHORITY, PAYMENT, URGENCY, classify_utterance

# Rough speaking rate used to estimate how long each exchange would take on
# a real call: ~150 wpm, i.e. 0.4s per word, plus thinking pauses.
_SECONDS_PER_WORD = 0.4
_PAUSE_SECONDS = 3.0

GENERIC = "generic"

_STALL_BANK: dict[str, tuple[str, ...]] = {
    PAYMENT: (
        "Gift cards, yes, I wrote that down. Now, do they need to be the "
        "shiny ones or the paper ones? My friend Doris got the paper ones once.",
        "I found a card here in my purse — it says 'Blockbuster Video' on it. "
        "Does that one work? It's been in there a while.",
        "The numbers on the back, you said? Hold on, I need my reading "
        "glasses. They're upstairs. This may take a minute, the hip you know.",
        "Now the money — should I write a check? I have my checkbook right "
        "here. Who do I make it out to? Spell it slowly, dear.",
    ),
    URGENCY: (
        "Oh I understand it's urgent, dear. You know, this reminds me of the "
        "time our water heater burst in 1987. Now THAT was urgent.",
        "Yes, yes, right away. Just as soon as my program finishes. Wheel of "
        "Fortune is almost over, there's only one letter left.",
        "I'm moving as fast as I can, sweetheart. These knees were new in "
        "1953, same year as the coronation.",
    ),
    AUTHORITY: (
        "An officer! My late husband was a crossing guard, you know. Maybe "
        "you knew him? Harold? Big fellow, always carried butterscotch.",
        "Now which precinct did you say? I want to send a thank-you card. "
        "I'll need the full mailing address, and your supervisor's name too.",
        "The court, my goodness. Judge Wapner still there? We never missed "
        "an episode.",
    ),
    GENERIC: (
        "I'm sorry dear, you're breaking up. Could you say all of that "
        "again, but slower? Start from the beginning.",
        "Hold on, there's someone at the door. Don't go anywhere... "
        "(footsteps) ...false alarm, it was the wind chimes again.",
        "Which grandson is this about again? I have eleven grandchildren, "
        "you know. There's Kyle, Kevin, Kenneth, the twins...",
        "You sound just like my nephew Bertram. Are you sure you're not "
        "Bertram? He does voices.",
        "Let me get a pen. Okay. No wait, this one's out of ink. Let me get "
        "another pen. Okay, go ahead. Wait — slower, please.",
    ),
}


@dataclass(frozen=True)
class StallReply:
    text: str
    keyed_to: str  # which tactic family the reply responded to
    seconds_wasted: float

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "keyed_to": self.keyed_to,
            "seconds_wasted": round(self.seconds_wasted, 1),
        }


def _key_for(scammer_text: str) -> str:
    hits = classify_utterance(scammer_text)
    for hit in hits:  # hits are sorted by score
        if hit.tactic in (PAYMENT, URGENCY, AUTHORITY):
            return hit.tactic
    return GENERIC


def _estimate_seconds(scammer_text: str, reply_text: str) -> float:
    words = len(scammer_text.split()) + len(reply_text.split())
    return words * _SECONDS_PER_WORD + _PAUSE_SECONDS


class StallAgent:
    """Deterministic stalling persona. One instance per handed-off call."""

    def __init__(self) -> None:
        self._cursors: dict[str, int] = dict.fromkeys(_STALL_BANK, 0)
        self.total_seconds_wasted = 0.0

    def reply_to(self, scammer_text: str) -> StallReply:
        """Produce the next stall reply for a scammer utterance."""
        key = _key_for(scammer_text)
        bank = _STALL_BANK[key]
        cursor = self._cursors[key]
        text = bank[cursor % len(bank)]
        self._cursors[key] = cursor + 1

        seconds = _estimate_seconds(scammer_text, text)
        self.total_seconds_wasted += seconds
        return StallReply(text=text, keyed_to=key, seconds_wasted=seconds)
