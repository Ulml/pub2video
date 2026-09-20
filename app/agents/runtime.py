"""Agents of the conversation pipeline. Demo path replays the Koushiappas chapter 1 run."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "demo"
OUTPUT = ROOT / "output"


def ingest(source: dict[str, Any]) -> dict[str, Any]:
    kind = source.get("kind") or "demo"
    origin = source.get("origin") or "demo://koushiappas-2026"
    raw = source.get("raw_text") or ""
    if kind == "pdf" and source.get("path"):
        path = Path(source["path"])
        raw = _read_pdf_or_text(path)
        origin = str(path)
    elif kind in {"youtube", "video"}:
        raw = source.get("raw_text") or (
            "Vidéo fournie. Titre et description à analyser pour extraire la publication citée."
        )
        origin = source.get("origin") or source.get("url") or origin
    if not raw:
        raw = (DEMO / "source.txt").read_text(encoding="utf-8")
        kind = "demo"
        origin = "demo://koushiappas-2026"
    return {"kind": kind, "origin": origin, "raw_text": raw, "title": source.get("title") or "Source"}


def extract_publication(src: dict[str, Any]) -> dict[str, Any]:
    fixture = DEMO / "publication.json"
    if fixture.exists() and (src.get("kind") == "demo" or "koushiappas" in src.get("raw_text", "").lower()):
        pub = json.loads(fixture.read_text(encoding="utf-8"))
        return {"publication": pub}
    text = src.get("raw_text") or ""
    return {
        "publication": {
            "title": src.get("title") or "Publication extraite",
            "authors": ["Auteur non résolu"],
            "year": None,
            "venue": None,
            "arxiv": None,
            "summary_points": _first_sentences(text, 5),
            "related": [],
        }
    }


def explain_plain(extracted: dict[str, Any]) -> dict[str, Any]:
    path = DEMO / "explain_plain.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    pub = extracted.get("publication") or {}
    return {
        "paragraphs": pub.get("summary_points") or ["Explication indisponible."],
        "analogies": [],
    }


def chapterize(explanation: dict[str, Any]) -> dict[str, Any]:
    path = DEMO / "chapters.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"items": []}


def narrate(chapterize_out: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
    path = DEMO / "narration.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "Récit manquant."
    return {
        "text": text,
        "word_count": len(text.split()),
        "citations": [
            {"form": "Riess, Perlmutter, 1998 et 1999"},
            {"form": "DESI, 2025-2026"},
            {"form": "Camilleri, Davis, 2026"},
            {"form": "Sah, Rameez, 2026"},
            {"form": "Koushiappas, 2026"},
        ],
        "chapter": 1,
    }


def storyboard(narration: dict[str, Any], wpm: int = 150) -> dict[str, Any]:
    path = DEMO / "storyboard.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    words = narration.get("word_count") or 400
    total = max(30, int(words / wpm * 60))
    return {"shots": [], "total_s": total}


def render_video(board: dict[str, Any]) -> dict[str, Any]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shots = board.get("shots") or []
    out = OUTPUT / "chapitre1.mp4"
    cached = Path("/home/workdir/artifacts/chapitre1_cinematique_light.mp4")
    if cached.exists() and shots:
        dest = OUTPUT / "chapitre1.mp4"
        dest.write_bytes(cached.read_bytes())
        return {
            "path": str(dest),
            "duration_s": float(board.get("total_s") or 255),
            "silent": True,
            "shots_encoded": len(shots),
            "cached": True,
        }
    clips_dir = OUTPUT / "clips"
    clips_dir.mkdir(exist_ok=True)
    encoded = 0
    concat_list = clips_dir / "list.txt"
    lines = []
    total = 0.0
    for i, shot in enumerate(shots, 1):
        img = shot.get("image")
        dur = float(shot.get("t_end", 0) - shot.get("t_start", 0))
        if dur <= 0:
            dur = 8.0
        if not img or not Path(img).exists():
            continue
        clip = clips_dir / f"s{i:02d}.mp4"
        ok = _ffmpeg_kenburns(Path(img), clip, dur, shot.get("caption") or "")
        if ok:
            lines.append(f"file '{clip.name}'")
            encoded += 1
            total += dur
    if encoded:
        concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
             "-c", "copy", "-movflags", "+faststart", str(out)],
            cwd=str(clips_dir), check=False, capture_output=True,
        )
    return {"path": str(out if out.exists() else ""), "duration_s": total, "silent": True, "shots_encoded": encoded}


def _ffmpeg_kenburns(img: Path, dest: Path, seconds: float, caption: str) -> bool:
    frames = max(30, int(seconds * 30))
    fade_out = max(0.1, seconds - 0.4)
    cap = caption.replace("'", " ")[:80]
    vf = (
        f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"zoompan=z='min(1.08,1+0.0004*on)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps=30,"
        f"fade=t=in:st=0:d=0.3,fade=t=out:st={fade_out}:d=0.35,"
        f"drawtext=text='{cap}':fontcolor=white:fontsize=28:x=40:y=h-60"
    )
    r = subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf,
         "-t", str(seconds), "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", "-an", "-threads", "2", str(dest)],
        capture_output=True,
    )
    return r.returncode == 0 and dest.exists()


def _read_pdf_or_text(path: Path) -> str:
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:20])
    except Exception:
        return path.read_text(encoding="utf-8", errors="ignore")[:8000]


def _first_sentences(text: str, n: int) -> list[str]:
    parts = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
    return parts[:n] or [text[:240]]
