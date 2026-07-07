# lifeline (server)

FastAPI backend for LIFELINE: a WebSocket that streams a scripted scam call
through the tactic classifier and pressure gauge, and runs the AI takeover on
hand-off. See the [project README](../README.md) for the full picture.

```bash
pip install -e ".[dev]"
uvicorn lifeline.app:app --reload   # :8000
pytest -q                           # 67 tests
```
