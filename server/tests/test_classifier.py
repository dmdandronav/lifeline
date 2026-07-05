"""Tests for the rule-based tactic classifier."""

import pytest

from lifeline.classifier import (
    AUTHORITY,
    EMOTIONAL,
    PAYMENT,
    SECRECY,
    URGENCY,
    classify_transcript,
    classify_utterance,
)


def tactics_of(text: str) -> set[str]:
    return {hit.tactic for hit in classify_utterance(text)}


# --- Urgency ---------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "You need to do this right now, there is no time.",
        "The payment must arrive within the next two hours.",
        "Act fast — this is your last chance before it's too late.",
        "This is urgent, the deadline is today.",
        "You have to stay with me and pay now, while we're on the call.",
    ],
)
def test_urgency_detected(text):
    assert URGENCY in tactics_of(text)


# --- Authority impersonation -------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "This is Officer Daniels from the county jail.",
        "I'm calling from the IRS about unpaid taxes.",
        "There is a warrant out for your arrest, case number 88-431.",
        "I'm the public defender assigned to your grandson's case.",
        "My badge number is 4471, this is official business.",
    ],
)
def test_authority_detected(text):
    assert AUTHORITY in tactics_of(text)


# --- Payment redirection -----------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Go buy four Google Play cards and read me the codes.",
        "You'll need to wire the money through Western Union.",
        "The bail is set at $8,500 in cash.",
        "Scratch off the back and give me the card numbers.",
        "A courier will come by to pick up the payment tonight.",
    ],
)
def test_payment_detected(text):
    assert PAYMENT in tactics_of(text)


# --- Secrecy / isolation -----------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Don't tell anyone about this, not even your daughter.",
        "There's a gag order, so you can't discuss the case.",
        "Do not hang up — stay on the line with me the whole time.",
        "If they ask, say the cards are a birthday present.",
        "No one else can know about this, keep it between us.",
    ],
)
def test_secrecy_detected(text):
    assert SECRECY in tactics_of(text)


# --- Emotional leverage ------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Your grandson is in jail and he's very scared.",
        "He was in a car accident and broke his nose.",
        "Please grandma, I don't want to stay here overnight.",
        "He begged us to call you — you're his only hope.",
        "Imagine how scared he is, sitting in that cell alone.",
    ],
)
def test_emotional_detected(text):
    assert EMOTIONAL in tactics_of(text)


# --- Negatives: ordinary conversation must NOT trigger -----------------------


@pytest.mark.parametrize(
    "text",
    [
        "Hi grandma, how are you doing today?",
        "The weather has been lovely this week.",
        "I watered the plants and fed the cat.",
        "Let me check my calendar and call you back tomorrow.",
        "We had dinner at the new Italian place on Main Street.",
        "Sure, I can help you set up the printer this weekend.",
    ],
)
def test_clean_utterances_have_no_tactics(text):
    assert tactics_of(text) == set()


# --- Multi-tactic and structural behaviour -----------------------------------


def test_multi_tactic_utterance():
    text = (
        "This is Officer Daniels — your grandson is in jail and you must "
        "wire the bail money right now, and don't tell anyone."
    )
    detected = tactics_of(text)
    assert {AUTHORITY, EMOTIONAL, PAYMENT, URGENCY, SECRECY} <= detected


def test_hits_sorted_by_score_descending():
    text = "Buy gift cards and scratch off the back, and do it quickly."
    hits = classify_utterance(text)
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_hits_carry_evidence():
    hits = classify_utterance("Go buy iTunes cards immediately.")
    payment = next(h for h in hits if h.tactic == PAYMENT)
    assert any("itunes" in e.lower() for e in payment.evidence)


def test_scores_bounded_zero_to_one():
    text = (
        "This is Officer Daniels with badge number 4471 from the police, "
        "there is a warrant for your arrest under federal law, case number 12."
    )
    for hit in classify_utterance(text):
        assert 0.0 < hit.score <= 1.0


def test_empty_and_whitespace_utterances():
    assert classify_utterance("") == []
    assert classify_utterance("   \n  ") == []


def test_classifier_is_deterministic():
    text = "Wire the money now and don't tell your family."
    assert classify_utterance(text) == classify_utterance(text)


def test_classify_transcript_shape():
    transcript = [
        "Hello, is this Mrs. Alvarez?",
        "Your grandson is in jail and needs bail money right now.",
    ]
    results = classify_transcript(transcript)
    assert len(results) == 2
    assert results[0] == []
    assert len(results[1]) >= 2


def test_to_dict_serialization():
    hit = classify_utterance("Buy gift cards now.")[0]
    d = hit.to_dict()
    assert set(d) == {"tactic", "label", "score", "evidence"}
    assert isinstance(d["evidence"], list)
