"""Run agents in SSOT order. Each output is judged before the next stage."""
from __future__ import annotations

from typing import Any, Callable

from app.agents import runtime
from app.judge import Verdict, judge
from app.settings_store import load_settings
from app.ssot_loader import load_contracts, load_ssot


AGENTS: dict[str, Callable[..., dict]] = {
    "ingest": lambda ctx: runtime.ingest(ctx["source"]),
    "extract_publication": lambda ctx: runtime.extract_publication(ctx["ingest"]),
    "explain_plain": lambda ctx: runtime.explain_plain(ctx["extract_publication"]),
    "chapterize": lambda ctx: runtime.chapterize(ctx["explain_plain"]),
    "narrate": lambda ctx: runtime.narrate(ctx["chapterize"], ctx["extract_publication"]),
    "storyboard": lambda ctx: runtime.storyboard(ctx["narrate"], int(ctx["settings"]["words_per_minute"])),
    "render_video": lambda ctx: runtime.render_video(ctx["storyboard"]),
}


def run_pipeline(source: dict[str, Any]) -> dict[str, Any]:
    ssot = load_ssot()
    contracts = load_contracts()
    settings = load_settings()
    global_threshold = float(settings["pass_threshold"])
    retries = int(settings["max_retries"])

    ctx: dict[str, Any] = {"source": source, "settings": settings}
    log: list[dict[str, Any]] = []

    for stage in ssot["stages"]:
        aid = stage["id"]
        contract = contracts[aid]
        threshold = float(contract.get("pass_threshold") or global_threshold)
        last_verdict: Verdict | None = None
        payload: dict[str, Any] = {}
        attempt = 0
        while attempt <= retries:
            attempt += 1
            payload = AGENTS[aid](ctx)
            last_verdict = judge(aid, contract, payload, threshold)
            log.append(
                {
                    "agent": aid,
                    "title": stage["title"],
                    "attempt": attempt,
                    "score": last_verdict.score,
                    "passed": last_verdict.passed,
                    "threshold": threshold,
                    "checks": last_verdict.checks,
                    "notes": last_verdict.notes,
                    "contract": {
                        "must": contract.get("must"),
                        "forbidden": contract.get("forbidden"),
                    },
                }
            )
            if last_verdict.passed:
                break
        if last_verdict is None or not last_verdict.passed:
            return {
                "ok": False,
                "stopped_at": aid,
                "settings": settings,
                "log": log,
                "artifacts": ctx,
            }
        ctx[aid] = payload

    return {"ok": True, "stopped_at": None, "settings": settings, "log": log, "artifacts": ctx}
