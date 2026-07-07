"""WebSocket integration test: stream the bundled scenario end-to-end."""

from fastapi.testclient import TestClient

from lifeline.app import app

client = TestClient(app)


def test_scenarios_endpoint_lists_bundled_scenario():
    body = client.get("/api/scenarios").json()
    ids = [s["id"] for s in body["scenarios"]]
    assert "grandson_jail" in ids


def test_ws_streams_call_to_completion_without_handoff():
    # speed=0 removes the pacing delays so the test runs instantly.
    with client.websocket_connect("/ws/call?scenario=grandson_jail&speed=0") as ws:
        types = []
        pressures = []
        while True:
            msg = ws.receive_json()
            types.append(msg["type"])
            if msg["type"] == "utterance":
                pressures.append(msg["pressure"])
            if msg["type"] == "call_ended":
                break

    assert types[0] == "call_started"
    assert "utterance" in types
    assert types[-1] == "call_ended"
    # Pressure should climb as the scammer applies tactics.
    assert pressures[-1] > pressures[0]


def test_gauge_crosses_threshold_and_offers_handoff():
    # By the end of the scripted call the accumulated tactics should have pushed
    # the gauge across its threshold, making the hand-off available. (The hand-off
    # takeover flow itself is covered at the unit level in test_agent/test_gauge.)
    with client.websocket_connect("/ws/call?scenario=grandson_jail&speed=0") as ws:
        handoff_offered = False
        while True:
            msg = ws.receive_json()
            if msg.get("type") == "utterance" and msg.get("handoff_available"):
                handoff_offered = True
            if msg["type"] == "call_ended":
                break
    assert handoff_offered


def test_unknown_scenario_closes_cleanly():
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect), client.websocket_connect(
        "/ws/call?scenario=nope&speed=0"
    ) as ws:
        ws.receive_json()
