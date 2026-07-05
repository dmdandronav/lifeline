"""Tests for the scam-pressure gauge accumulator."""

from lifeline.classifier import classify_utterance
from lifeline.gauge import DEFAULT_THRESHOLD, GaugeState, apply_utterance

HOSTILE = (
    "This is Officer Daniels — your grandson is in jail and you must wire "
    "the bail money right now, and don't tell anyone."
)
MILD = "You should really act fast on this."
CLEAN = "The weather has been lovely this week."


def run(utterances: list[str], state: GaugeState | None = None) -> GaugeState:
    state = state or GaugeState()
    for text in utterances:
        state = apply_utterance(state, classify_utterance(text))
    return state


def test_initial_state():
    state = GaugeState()
    assert state.pressure == 0.0
    assert state.threshold == DEFAULT_THRESHOLD
    assert not state.handoff_available


def test_pressure_rises_on_tactics():
    state = run([MILD])
    assert state.pressure > 0.0


def test_multi_tactic_rises_faster_than_single():
    assert run([HOSTILE]).pressure > run([MILD]).pressure


def test_pressure_decays_on_clean_utterances():
    pressured = run([HOSTILE, HOSTILE])
    decayed = apply_utterance(pressured, classify_utterance(CLEAN))
    assert decayed.pressure < pressured.pressure


def test_pressure_never_negative():
    state = run([CLEAN] * 10)
    assert state.pressure == 0.0


def test_pressure_capped_at_one():
    state = run([HOSTILE] * 30)
    assert state.pressure <= 1.0


def test_threshold_triggers_handoff():
    state = run([HOSTILE] * 12)
    assert state.pressure >= state.threshold
    assert state.handoff_available


def test_clean_call_never_triggers_handoff():
    state = run([CLEAN, "How are the grandkids?", "See you Sunday for lunch."] * 5)
    assert not state.handoff_available


def test_tactic_counts_accumulate():
    state = run([HOSTILE, HOSTILE])
    assert state.tactic_counts["payment_redirection"] == 2
    assert state.tactic_counts["urgency"] == 2


def test_apply_returns_new_state():
    original = GaugeState()
    updated = apply_utterance(original, classify_utterance(HOSTILE))
    assert original.pressure == 0.0
    assert updated is not original


def test_to_dict_shape():
    d = run([HOSTILE]).to_dict()
    assert set(d) == {"pressure", "threshold", "handoff_available", "tactic_counts"}
