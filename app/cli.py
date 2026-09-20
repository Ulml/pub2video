#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.pipeline.orchestrator import run_pipeline
from app.settings_store import load_settings, save_settings


def main() -> None:
    p = argparse.ArgumentParser(description="pub2video — flux agentique publication → récit + vidéo")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--youtube")
    r.add_argument("--pdf")
    r.add_argument("--demo", action="store_true")
    s = sub.add_parser("settings")
    s.add_argument("--threshold", type=float)
    s.add_argument("--retries", type=int)
    args = p.parse_args()

    if args.cmd == "settings":
        cur = load_settings()
        if args.threshold is not None:
            cur["pass_threshold"] = args.threshold
        if args.retries is not None:
            cur["max_retries"] = args.retries
        print(json.dumps(save_settings(cur), indent=2, ensure_ascii=False))
        return

    source = {"kind": "demo", "origin": "demo://koushiappas-2026"}
    if args.pdf:
        source = {"kind": "pdf", "path": args.pdf, "origin": args.pdf}
    elif args.youtube:
        source = {"kind": "youtube", "url": args.youtube, "origin": args.youtube}
    result = run_pipeline(source)
    print(json.dumps(_public(result), indent=2, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 2)


def _public(result: dict) -> dict:
    art = result.get("artifacts") or {}
    return {
        "ok": result["ok"],
        "stopped_at": result["stopped_at"],
        "settings": result["settings"],
        "log": result["log"],
        "narration": (art.get("narrate") or {}).get("text"),
        "video": (art.get("render_video") or {}).get("path"),
        "publication": (art.get("extract_publication") or {}).get("publication"),
    }


if __name__ == "__main__":
    main()
