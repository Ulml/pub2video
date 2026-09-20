"""Judge: scores an agent output against its contract."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Verdict:
    agent_id: str
    score: float
    passed: bool
    threshold: float
    checks: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""


def _has(text: str, needles: list[str]) -> bool:
    blob = (text or "").lower()
    return any(n.lower() in blob for n in needles)


def judge(agent_id: str, contract: dict[str, Any], payload: dict[str, Any], threshold: float) -> Verdict:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    if agent_id == "ingest":
        add("kind valide", payload.get("kind") in {"video", "youtube", "pdf", "demo"})
        add("origin présente", bool(payload.get("origin")))
        add("raw_text non vide", len(str(payload.get("raw_text") or "")) > 40)
        add("pas de papier inventé ici", True)
    elif agent_id == "extract_publication":
        pub = payload.get("publication") or payload
        add("titre", bool(pub.get("title")))
        add("auteurs", bool(pub.get("authors")))
        add("année", bool(pub.get("year")))
        add("points factuels", len(pub.get("summary_points") or []) >= 3)
        add("source identifiée", bool(pub.get("venue") or pub.get("arxiv")))
    elif agent_id == "explain_plain":
        text = " ".join(payload.get("paragraphs") or [])
        add("texte long", len(text) > 400)
        add("analogies", len(payload.get("analogies") or []) >= 3)
        jargon = ["commutation", "friedmann", "hamiltonien", "w_eff", "minisuperspace"]
        add("jargon brut absent", not _has(text, jargon), "termes techniques bruts")
        add("limites mentionnées", _has(text, ["limite", "ne fait pas", "n'explique pas", "pas encore"]))
    elif agent_id == "chapterize":
        items = payload.get("items") or []
        add("4 à 8 chapitres", 4 <= len(items) <= 8)
        first = (items[0].get("title") if items else "") or ""
        add("chapitre 1 = constat", "constat" in first.lower())
        add("chaque chapitre a un but", all(i.get("purpose") for i in items))
    elif agent_id == "narrate":
        text = payload.get("text") or ""
        add("style raconté", "slide" not in text.lower())
        add("citations courtes", all(c.get("form", "").count(",") <= 2 for c in payload.get("citations") or [{}]))
        add("premier trou", "premier trou" in text.lower())
        add("second trou", "second trou" in text.lower())
        add("ouverture suivante", _has(text, ["suite", "chapitre 2", "porte c"]))
        add("longueur", len(text) > 800)
    elif agent_id == "storyboard":
        shots = payload.get("shots") or []
        add("5 à 9 plans", 5 <= len(shots) <= 9)
        add("durées présentes", all("t_start" in s and "t_end" in s for s in shots))
        add("motion décrite", all(s.get("motion") for s in shots))
        add("pas un plan par phrase", len(shots) <= 9)
    elif agent_id == "render_video":
        add("chemin", bool(payload.get("path")))
        add("muet", payload.get("silent") is True)
        add("durée", float(payload.get("duration_s") or 0) > 10)
        add("plans encodés", int(payload.get("shots_encoded") or 0) >= 5)
    else:
        add("agent connu", False, agent_id)

    total = max(len(checks), 1)
    score = sum(1 for c in checks if c["ok"]) / total
    return Verdict(
        agent_id=agent_id,
        score=round(score, 3),
        passed=score + 1e-9 >= threshold,
        threshold=threshold,
        checks=checks,
        notes=f"{sum(c['ok'] for c in checks)}/{total} clauses",
    )
