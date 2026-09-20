"""Single source of truth for the pipeline and agent contracts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent
SSOT_PATH = ROOT / "ssot" / "pipeline.yaml"
CONTRACTS_DIR = ROOT / "contracts"


def load_ssot() -> dict[str, Any]:
    return yaml.safe_load(SSOT_PATH.read_text(encoding="utf-8"))


def load_contracts() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(CONTRACTS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data and "id" in data:
            data["_path"] = str(path)
            out[data["id"]] = data
    return out


def save_contract(agent_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    contracts = load_contracts()
    if agent_id not in contracts:
        raise KeyError(agent_id)
    current = contracts[agent_id]
    path = Path(current["_path"])
    if "pass_threshold" in fields:
        current["pass_threshold"] = min(0.99, max(0.5, float(fields["pass_threshold"])))
    if "must" in fields:
        current["must"] = _lines(fields["must"])
    if "forbidden" in fields:
        current["forbidden"] = _lines(fields["forbidden"])
    dump = {k: v for k, v in current.items() if k != "_path"}
    path.write_text(yaml.safe_dump(dump, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return dump


def _lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [ln.strip() for ln in str(value).splitlines() if ln.strip()]
