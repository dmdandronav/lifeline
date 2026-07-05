"""Tests for the takeover stall agent and scenario loader."""

import pytest

from lifeline.agent import GENERIC, StallAgent
from lifeline.classifier import AUTHORITY, PAYMENT, URGENCY
from lifeline.scenarios import list_scenarios, load_scenario


class TestStallAgent:
    def test_payment_demand_gets_payment_stall(self):
        reply = StallAgent().reply_to("Read me the gift card codes right now!")
        assert reply.keyed_to == PAYMENT

    def test_urgency_gets_urgency_stall(self):
        reply = StallAgent().reply_to("Hurry up, we're running out of time!")
        assert reply.keyed_to == URGENCY

    def test_authority_gets_authority_stall(self):
        reply = StallAgent().reply_to("This is Officer Daniels from the police department.")
        assert reply.keyed_to == AUTHORITY

    def test_neutral_gets_generic_stall(self):
        reply = StallAgent().reply_to("Are you still there?")
        assert reply.keyed_to == GENERIC

    def test_replies_cycle_without_immediate_repeat(self):
        agent = StallAgent()
        first = agent.reply_to("Buy the gift cards!")
        second = agent.reply_to("Buy the gift cards!")
        assert first.text != second.text

    def test_time_wasted_accumulates(self):
        agent = StallAgent()
        agent.reply_to("Read me the codes!")
        after_one = agent.total_seconds_wasted
        agent.reply_to("Now! Do it now!")
        assert after_one > 0
        assert agent.total_seconds_wasted > after_one

    def test_deterministic_across_instances(self):
        script = ["Buy gift cards!", "Hurry!", "Are you there?"]
        a = [StallAgent().reply_to(s).text for s in script]
        b = [StallAgent().reply_to(s).text for s in script]
        assert a == b

    def test_reply_serialization(self):
        d = StallAgent().reply_to("Hello?").to_dict()
        assert set(d) == {"text", "keyed_to", "seconds_wasted"}


class TestScenarios:
    def test_load_bundled_scenario(self):
        scenario = load_scenario("grandson_jail")
        assert scenario.id == "grandson_jail"
        assert 12 <= len(scenario.utterances) <= 15
        assert len(scenario.post_handoff) >= 5

    def test_utterances_have_speakers_and_delays(self):
        scenario = load_scenario("grandson_jail")
        for u in scenario.utterances + scenario.post_handoff:
            assert u.speaker in ("scammer", "victim")
            assert u.delay_ms > 0
            assert u.text

    def test_unknown_scenario_raises(self):
        with pytest.raises(FileNotFoundError):
            load_scenario("nope")

    def test_list_scenarios_includes_bundled(self):
        ids = [s.id for s in list_scenarios()]
        assert "grandson_jail" in ids

    def test_summary_shape(self):
        summary = load_scenario("grandson_jail").summary()
        assert set(summary) == {"id", "title", "description", "utterance_count"}
