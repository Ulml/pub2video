from __future__ import annotations

from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parent.parent / "output" / "settings.yaml"

DEFAULTS = {
    "pass_threshold": 0.95,
    "max_retries": 2,
    "words_per_minute": 150,
    "demo_mode": True,
}


def load_settings() -> dict:
    if PATH.exists():
        data = yaml.safe_load(PATH.read_text(encoding="utf-8")) or {}
        return {**DEFAULTS, **data}
    return dict(DEFAULTS)


def save_settings(data: dict) -> dict:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    merged = {**DEFAULTS, **data}
    merged["pass_threshold"] = float(merged["pass_threshold"])
    merged["pass_threshold"] = min(0.99, max(0.5, merged["pass_threshold"]))
    PATH.write_text(yaml.safe_dump(merged, allow_unicode=True), encoding="utf-8")
    return merged
