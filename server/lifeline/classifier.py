"""Rule-based classifier for social-engineering tactics in scam-call utterances.

The core is deterministic and fully offline: each tactic has a bank of
compiled regex patterns distilled from documented phone-scam scripts
(grandparent scams, IRS impersonation, tech-support scams, gift-card
redirection). An optional LLM layer (see ``lifeline.llm``) can refine these
results when an API key is present, but the rule engine is the source of
truth for tests and the zero-key demo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- Tactic taxonomy -------------------------------------------------------

URGENCY = "urgency"
AUTHORITY = "authority_impersonation"
PAYMENT = "payment_redirection"
SECRECY = "secrecy_isolation"
EMOTIONAL = "emotional_leverage"

ALL_TACTICS = (URGENCY, AUTHORITY, PAYMENT, SECRECY, EMOTIONAL)

TACTIC_LABELS = {
    URGENCY: "Urgency",
    AUTHORITY: "Authority impersonation",
    PAYMENT: "Payment redirection",
    SECRECY: "Secrecy / isolation",
    EMOTIONAL: "Emotional leverage",
}

# --- Pattern banks ---------------------------------------------------------
# Each entry: (regex, weight). Weights express how strongly a phrase signals
# the tactic on its own — a hard payment demand is worth more than a vague
# "soon".


def _bank(patterns: list[tuple[str, float]]) -> list[tuple[re.Pattern[str], float]]:
    return [(re.compile(p, re.IGNORECASE), w) for p, w in patterns]


_PATTERN_BANKS: dict[str, list[tuple[re.Pattern[str], float]]] = {
    URGENCY: _bank(
        [
            (r"\bright (?:now|away)\b", 0.9),
            (r"\bimmediately\b", 0.9),
            (r"\bwithin (?:the )?(?:next )?(?:\d+|one|two|a few) (?:minutes?|hours?)\b", 1.0),
            (r"\bbefore (?:it'?s|it is) too late\b", 1.0),
            (r"\b(?:running out of|no) time\b", 0.9),
            (r"\btime[- ]sensitive\b", 0.8),
            (r"\b(?:act|do it|decide|pay|send it) (?:fast|quickly|now|today)\b", 0.9),
            (r"\bcan'?t wait\b", 0.7),
            (r"\bthis (?:very )?(?:minute|instant)\b", 0.9),
            (r"\bdeadline\b", 0.7),
            (r"\b(?:hurry|urgent(?:ly)?)\b", 0.8),
            (r"\bwhile (?:i|we)(?:'| a)re (?:still )?on the (?:phone|line|call)\b", 0.9),
            (r"\bbefore the (?:court|judge|hearing|arraignment|office) (?:closes|opens)\b", 1.0),
            (r"\blast (?:chance|warning)\b", 1.0),
            (r"\bonly (?:have|has|got) (?:\d+|a few|until)\b", 0.8),
        ]
    ),
    AUTHORITY: _bank(
        [
            (
                r"\b(?:this is|i'?m|i am) "
                r"(?:officer|detective|sergeant|deputy|agent|lieutenant)\b",
                1.0,
            ),
            (r"\b(?:police|sheriff|court(?:house)?|county jail|precinct)\b", 0.8),
            (r"\b(?:public defender|attorney|lawyer) (?:assigned|appointed|representing)\b", 0.9),
            (r"\b(?:irs|internal revenue|social security administration|medicare)\b", 1.0),
            (r"\bfederal (?:agent|investigation|warrant|charges?)\b", 0.9),
            (r"\bbadge (?:number|id)\b", 1.0),
            (r"\bcase (?:number|file|id)\b", 0.8),
            (r"\bwarrant (?:for|out for) (?:your|his|her|the) arrest\b", 1.0),
            (
                r"\b(?:i'?m|i am|this is) (?:with|from|calling from) (?:the )?"
                r"(?:bank|fraud department|security department|microsoft"
                r"|apple support|your grandson'?s? lawyer)\b",
                1.0,
            ),
            (r"\blegal (?:action|proceedings|department)\b", 0.8),
            (r"\bunder (?:federal|state) law\b", 0.8),
            (r"\bofficial (?:notice|business|record)\b", 0.7),
        ]
    ),
    PAYMENT: _bank(
        [
            (r"\bgift ?cards?\b", 1.0),
            (r"\b(?:itunes|google play|amazon|steam|target|walmart) cards?\b", 1.0),
            (r"\bwire (?:transfer|the money|it|funds)\b", 1.0),
            (r"\bwestern union|moneygram\b", 1.0),
            (r"\b(?:bitcoin|crypto(?:currency)?|btc)\b", 1.0),
            (r"\bbail (?:money|bond|amount|is set)\b", 0.9),
            (r"\bcash(?:ier'?s check)?\b", 0.6),
            (r"\b(?:read|give|tell) (?:me|us) the (?:card )?(?:numbers?|codes?|pin)\b", 1.0),
            (r"\bscratch (?:off|the back)\b", 1.0),
            (r"\bcourier (?:will|to) (?:come|pick|collect)\b", 1.0),
            (r"\bzelle|venmo|cash ?app\b", 0.9),
            (r"\bprocessing fee\b", 0.9),
            (r"\b\$[\d,]+\b", 0.5),
            (r"\b(?:send|transfer|pay) (?:the )?(?:money|funds|amount|payment)\b", 0.9),
            (r"\bkeep the receipt\b", 0.7),
        ]
    ),
    SECRECY: _bank(
        [
            (
                r"\bdon'?t (?:tell|call|contact|inform) (?:anyone|anybody|your "
                r"(?:wife|husband|son|daughter|family|kids|children|bank))\b",
                1.0,
            ),
            (r"\b(?:keep|stay) (?:this|it) (?:between us|quiet|secret|confidential)\b", 1.0),
            (r"\bgag order\b", 1.0),
            (r"\bcan'?t (?:talk|speak|say anything) (?:to|about this to) anyone\b", 0.9),
            (r"\bdo not hang up\b", 1.0),
            (r"\bstay on the (?:phone|line|call)\b", 0.9),
            (r"\bdon'?t (?:hang up|end the call)\b", 1.0),
            (r"\bno one (?:else )?(?:can|must|should) know\b", 1.0),
            (
                r"\b(?:tell|say) (?:them|the cashier|the teller) "
                r"(?:it'?s|nothing|you'?re buying)\b",
                0.9,
            ),
            (r"\bif (?:they|anyone) asks?,? (?:say|tell)\b", 0.9),
            (r"\bsealed (?:case|record)\b", 0.8),
            (r"\bconfidential(?:ity)?\b", 0.6),
        ]
    ),
    EMOTIONAL: _bank(
        [
            (r"\b(?:your )?grand(?:son|daughter|child)\b", 0.8),
            (
                r"\b(?:he|she|they)(?:'s| is| are) (?:in (?:jail|trouble|custody"
                r"|the hospital)|hurt|crying|scared|injured)\b",
                1.0,
            ),
            (r"\b(?:car )?accident\b", 0.8),
            (r"\bhospital\b", 0.7),
            (r"\b(?:so|very|really) (?:scared|frightened|upset|ashamed|embarrassed)\b", 0.9),
            (r"\bplease (?:grandma|grandpa|nana|papa)\b", 1.0),
            (r"\bdon'?t (?:want|let) (?:him|her|them) (?:to )?(?:spend|stay|sit)\b", 0.8),
            (r"\bonly you can (?:help|save)\b", 1.0),
            (r"\b(?:he|she) (?:asked|begged) (?:for|us to call) you\b", 0.9),
            (r"\bbroke (?:his|her) nose\b", 0.9),
            (r"\byou(?:'re| are) (?:his|her|their) only (?:hope|chance|option)\b", 1.0),
            (r"\bimagine how (?:scared|alone)\b", 0.9),
            (r"\bwhat kind of grand(?:mother|father|parent)\b", 1.0),
        ]
    ),
}

# A single utterance rarely deserves more credit than this per tactic.
_MAX_TACTIC_SCORE = 1.0
# Minimum aggregate score for a tactic to be reported at all.
_MIN_REPORT_SCORE = 0.5


@dataclass(frozen=True)
class TacticHit:
    """One detected tactic within a single utterance."""

    tactic: str
    score: float
    evidence: tuple[str, ...] = field(default=())

    @property
    def label(self) -> str:
        return TACTIC_LABELS[self.tactic]

    def to_dict(self) -> dict:
        return {
            "tactic": self.tactic,
            "label": self.label,
            "score": round(self.score, 3),
            "evidence": list(self.evidence),
        }


def classify_utterance(text: str) -> list[TacticHit]:
    """Classify a single utterance against the tactic taxonomy.

    Returns hits sorted by descending score. Deterministic and side-effect
    free — safe to call from tests, the WS loop, or a batch pipeline.
    """
    if not text or not text.strip():
        return []

    hits: list[TacticHit] = []
    for tactic, bank in _PATTERN_BANKS.items():
        score = 0.0
        evidence: list[str] = []
        for pattern, weight in bank:
            match = pattern.search(text)
            if match:
                score += weight
                evidence.append(match.group(0))
        if score >= _MIN_REPORT_SCORE:
            hits.append(
                TacticHit(
                    tactic=tactic,
                    score=min(score, _MAX_TACTIC_SCORE),
                    evidence=tuple(evidence),
                )
            )

    return sorted(hits, key=lambda h: h.score, reverse=True)


def classify_transcript(utterances: list[str]) -> list[list[TacticHit]]:
    """Classify a full transcript, one hit-list per utterance."""
    return [classify_utterance(u) for u in utterances]
