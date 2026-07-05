"""Scam-pressure gauge: an accumulator over per-utterance tactic hits.

Pressure rises when manipulation tactics land, decays as clean utterances go
by, and crosses a handoff threshold when the call is clearly hostile. Kept
pure (no I/O, no clocks) so the demo, the WS loop, and the tests all share
identical behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .classifier import TacticHit

# Tuning constants — chosen so the bundled scenario crosses the threshold
# around utterance 6-8, giving the demo a visible ramp.
DEFAULT_THRESHOLD = 0.65
_RISE_PER_SCORE = 0.11  # pressure gained per unit of tactic score
_STACKING_BONUS = 0.05  # extra pressure per additional distinct tactic in one utterance
_DECAY_PER_CLEAN = 0.04  # pressure lost per clean utterance
_MAX_PRESSURE = 1.0


@dataclass(frozen=True)
class GaugeState:
    """Immutable snapshot of the pressure gauge."""

    pressure: float = 0.0
    threshold: float = DEFAULT_THRESHOLD
    tactic_counts: dict[str, int] = field(default_factory=dict)

    @property
    def handoff_available(self) -> bool:
        return self.pressure >= self.threshold

    def to_dict(self) -> dict:
        return {
            "pressure": round(self.pressure, 3),
            "threshold": self.threshold,
            "handoff_available": self.handoff_available,
            "tactic_counts": dict(self.tactic_counts),
        }


def apply_utterance(state: GaugeState, hits: list[TacticHit]) -> GaugeState:
    """Fold one classified utterance into the gauge, returning a new state.

    - Tactic hits raise pressure proportionally to their scores, with a
      stacking bonus when several distinct tactics land in one sentence.
    - Clean utterances decay pressure slightly — a call that stops
      pressuring you slowly earns back trust.
    """
    if not hits:
        return replace(state, pressure=max(0.0, state.pressure - _DECAY_PER_CLEAN))

    rise = sum(h.score for h in hits) * _RISE_PER_SCORE
    if len(hits) > 1:
        rise += (len(hits) - 1) * _STACKING_BONUS

    counts = dict(state.tactic_counts)
    for hit in hits:
        counts[hit.tactic] = counts.get(hit.tactic, 0) + 1

    return replace(
        state,
        pressure=min(_MAX_PRESSURE, state.pressure + rise),
        tactic_counts=counts,
    )
