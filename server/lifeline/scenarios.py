"""Loader for bundled call scenarios.

Scenarios are plain JSON files under ``data/scenarios`` so the whole demo
runs offline with zero API keys or telephony hardware.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"


@dataclass(frozen=True)
class Utterance:
    speaker: str  # "scammer" | "victim"
    text: str
    delay_ms: int

    def to_dict(self) -> dict:
        return {"speaker": self.speaker, "text": self.text, "delay_ms": self.delay_ms}


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    description: str
    utterances: tuple[Utterance, ...]
    post_handoff: tuple[Utterance, ...]

    def summary(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "utterance_count": len(self.utterances),
        }


def _parse_utterances(raw: list[dict]) -> tuple[Utterance, ...]:
    return tuple(
        Utterance(speaker=u["speaker"], text=u["text"], delay_ms=int(u["delay_ms"])) for u in raw
    )


def load_scenario(scenario_id: str, data_dir: Path = DATA_DIR) -> Scenario:
    path = data_dir / f"{scenario_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"unknown scenario: {scenario_id!r}")
    raw = json.loads(path.read_text())
    return Scenario(
        id=raw["id"],
        title=raw["title"],
        description=raw["description"],
        utterances=_parse_utterances(raw["utterances"]),
        post_handoff=_parse_utterances(raw.get("post_handoff", [])),
    )


def list_scenarios(data_dir: Path = DATA_DIR) -> list[Scenario]:
    return [load_scenario(p.stem, data_dir) for p in sorted(data_dir.glob("*.json"))]
