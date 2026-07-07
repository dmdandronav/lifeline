# LIFELINE

**A real-time firewall for phone scams.** As a call comes in, LIFELINE
transcribes it, classifies each sentence against a taxonomy of social-engineering
tactics, and raises a **scam-pressure gauge**. When the pressure crosses the
threshold, you can hand the call to an **AI agent that takes over and wastes the
scammer's time** — while a counter tallies the seconds it burns.

Runs entirely offline on a bundled, scripted call. No telephony, no API keys,
nothing dialed. An optional LLM layer sharpens the classifier and the stall
replies when `ANTHROPIC_API_KEY` is set.

## Why it matters

Phone and impersonation scams cost victims **$12B+ a year in the US**, and older
adults are hit hardest. The hard part isn't hearing the words — it's recognizing,
in the moment, that "your grandson is in jail and you can't tell anyone" is a
scripted manipulation. LIFELINE makes that structure visible in real time and
gives the target an exit that costs the scammer, not them.

## The 30-second demo

1. Hit **Play the scam call** — a scripted "grandson in jail" call streams in
   sentence by sentence.
2. As each line lands, tactic chips light up — **Urgency**, **Authority**,
   **Payment**, **Secrecy**, **Emotional** — and the pressure gauge climbs.
3. When the gauge crosses the threshold the **Hand off to AI** button arms and
   pulses. Click it.
4. The AI takes the call, cheerfully stalling the scammer, and the **scammer time
   wasted** counter ticks up.

## Architecture

```
 bundled scenario (JSON)
        │  utterance-by-utterance over WebSocket
        ▼
   /ws/call  ──▶  classifier.py   5-tactic rule bank → TacticHit[]     (pure, tested)
        │         gauge.py        accumulate pressure, decay, threshold (pure, tested)
        │         agent.py        StallAgent picks a stall reply        (pure, tested)
        │         llm.py          optional Anthropic refinement (lazy; keyless by default)
        ▼
   React console: transcript · tactic chips · SVG pressure gauge · handoff · time-wasted
```

- **`server/lifeline/classifier.py`** — regex-bank + weight tactic classifier.
- **`server/lifeline/gauge.py`** — immutable pressure accumulator with threshold.
- **`server/lifeline/agent.py`** — the stall agent (reply bank keyed to scammer move).
- **`server/lifeline/app.py`** — FastAPI WebSocket that streams a scenario and runs
  the handoff takeover.
- **`web/`** — React + Vite control-room UI.

## Quick start

```bash
# backend
cd server
pip install -e ".[dev]"
uvicorn lifeline.app:app --reload      # :8000

# tests
pytest -q                              # 67 tests: classifier, gauge, agent, WS app

# frontend (separate terminal)
cd web && npm install && npm run dev   # :5173, proxies /ws + /api to :8000
```

## Ethics & scope

LIFELINE is a **defensive** demo. It ships a scripted call and simulated takeover
agent; it does not connect to a phone network, record anyone, or dial out. The
takeover concept is meant to protect a target and document an attempt — not to
harass. Any real deployment would need consent, jurisdiction-specific call-
recording compliance, and rate limits.

## License

MIT — see [LICENSE](LICENSE).
