"""FastAPI app: streams a bundled scam call over WebSocket.

Protocol (server → client), one JSON message per event:

- ``call_started``   scenario summary
- ``utterance``      {speaker, text, tactics, pressure, threshold, handoff_available}
- ``handoff_engaged`` the stall agent has taken over
- ``agent_reply``    {text, keyed_to, seconds_wasted, time_wasted_total}
- ``call_ended``     {reason, pressure, tactic_counts, time_wasted_total}

Client → server: ``{"action": "handoff"}`` once the gauge crosses the
threshold. A ``speed`` query param scales the scripted delays (0 = instant,
used by tests).
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .agent import StallAgent
from .classifier import ALL_TACTICS, TACTIC_LABELS, classify_utterance
from .gauge import GaugeState, apply_utterance
from .llm import enhance_stall_reply
from .scenarios import Scenario, Utterance, list_scenarios, load_scenario

app = FastAPI(
    title="LIFELINE",
    description="A real-time firewall for phone scams — fully offline demo.",
    version="0.1.0",
)

WS_CLOSE_UNKNOWN_SCENARIO = 4404


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/scenarios")
def get_scenarios() -> dict:
    return {
        "scenarios": [s.summary() for s in list_scenarios()],
        "tactics": [{"tactic": t, "label": TACTIC_LABELS[t]} for t in ALL_TACTICS],
    }


class _CallSession:
    """Drives one scripted call over an accepted WebSocket."""

    def __init__(self, ws: WebSocket, scenario: Scenario, speed: float) -> None:
        self.ws = ws
        self.scenario = scenario
        self.speed = max(0.0, speed)
        self.state = GaugeState()
        self.handoff_requested = asyncio.Event()

    async def _listen(self) -> None:
        while True:
            message = await self.ws.receive_json()
            if message.get("action") == "handoff":
                self.handoff_requested.set()

    async def _pause(self, delay_ms: int) -> None:
        if self.speed > 0:
            await asyncio.sleep(delay_ms / 1000 * self.speed)

    async def _send_utterance(self, utterance: Utterance) -> None:
        hits = classify_utterance(utterance.text) if utterance.speaker == "scammer" else []
        self.state = apply_utterance(self.state, hits)
        await self.ws.send_json(
            {
                "type": "utterance",
                "speaker": utterance.speaker,
                "text": utterance.text,
                "tactics": [h.to_dict() for h in hits],
                **self.state.to_dict(),
            }
        )

    @property
    def _handoff_engaged(self) -> bool:
        return self.handoff_requested.is_set() and self.state.handoff_available

    async def run(self) -> None:
        await self.ws.send_json({"type": "call_started", "scenario": self.scenario.summary()})
        for utterance in self.scenario.utterances:
            if self._handoff_engaged:
                break
            await self._pause(utterance.delay_ms)
            await self._send_utterance(utterance)

        if self._handoff_engaged:
            await self._run_handoff()
            reason = "agent_exhausted_scammer"
        else:
            reason = "script_complete"

        await self.ws.send_json(
            {
                "type": "call_ended",
                "reason": reason,
                **self.state.to_dict(),
            }
        )

    async def _run_handoff(self) -> None:
        agent = StallAgent()
        await self.ws.send_json({"type": "handoff_engaged"})
        for utterance in self.scenario.post_handoff:
            await self._pause(utterance.delay_ms)
            await self._send_utterance(utterance)
            reply = agent.reply_to(utterance.text)
            await self._pause(utterance.delay_ms)
            await self.ws.send_json(
                {
                    "type": "agent_reply",
                    **reply.to_dict(),
                    "text": enhance_stall_reply(utterance.text, reply.text),
                    "time_wasted_total": round(agent.total_seconds_wasted, 1),
                }
            )


@app.websocket("/ws/call")
async def ws_call(ws: WebSocket, scenario: str = "grandson_jail", speed: float = 1.0) -> None:
    await ws.accept()
    try:
        loaded = load_scenario(scenario)
    except FileNotFoundError:
        await ws.close(code=WS_CLOSE_UNKNOWN_SCENARIO, reason=f"unknown scenario: {scenario}")
        return

    session = _CallSession(ws, loaded, speed)
    listener = asyncio.create_task(session._listen())
    try:
        await session.run()
    except WebSocketDisconnect:
        pass
    finally:
        listener.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener
        with contextlib.suppress(RuntimeError):
            await ws.close()
