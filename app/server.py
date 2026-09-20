#!/usr/bin/env python3
"""Minimal stdlib UI for the agentic pipeline."""
from __future__ import annotations

import html as htmlmod
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.pipeline.orchestrator import run_pipeline
from app.settings_store import load_settings, save_settings
from app.ssot_loader import load_contracts, load_ssot, save_contract

HOST, PORT = "0.0.0.0", 8765


def page(body: str, title: str = "pub2video") -> bytes:
    doc = f"""<!doctype html>
<html lang="fr"><head>
<meta charset="utf-8"/>
<title>{title}</title>
<style>
:root {{ --navy:#0B1D36; --gold:#E0B03A; --cream:#F4EFE4; --card:#132A45; --mute:#9AA8B8; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family: Georgia, serif; background:var(--navy); color:var(--cream); }}
header {{ padding:28px 40px 12px; border-bottom:1px solid #1c3a5a; }}
header small {{ color:var(--gold); letter-spacing:.18em; font-family:sans-serif; font-size:12px; }}
h1 {{ margin:6px 0 0; font-size:32px; }}
main {{ padding:28px 40px 60px; max-width:1100px; }}
form, .card {{ background:var(--card); padding:22px; border-radius:14px; margin:0 0 22px; }}
label {{ display:block; font-family:sans-serif; font-size:13px; color:var(--mute); margin:12px 0 6px; }}
input[type=text], input[type=number], textarea {{ width:100%; padding:10px 12px; border:0; border-radius:8px; background:#0B1D36; color:white; font-family:sans-serif; }}
textarea {{ min-height:110px; }}
button {{ background:var(--gold); color:#0B1D36; border:0; padding:10px 18px; border-radius:8px; font-weight:700; cursor:pointer; margin-top:16px; }}
.row {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.ok {{ color:#7dcea0; }} .bad {{ color:#e07a5f; }}
ol.flow {{ padding-left:20px; }}
.shot {{ font-family:sans-serif; font-size:13px; color:var(--mute); }}
pre {{ white-space:pre-wrap; line-height:1.45; }}
a {{ color:var(--gold); }}
</style></head><body>
<header><small>FLUX AGENTIQUE</small><h1>pub2video</h1></header>
<main>{body}</main>
</body></html>"""
    return doc.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._html(self._home())
        elif parsed.path == "/run":
            self._html(self._run(parse_qs(parsed.query)))
        elif parsed.path == "/settings":
            qs = parse_qs(parsed.query)
            if "threshold" in qs:
                save_settings({
                    "pass_threshold": float(qs["threshold"][0]),
                    "max_retries": int(qs.get("retries", ["2"])[0]),
                    "words_per_minute": int(qs.get("wpm", ["150"])[0]),
                })
            self._html(self._settings())
        elif parsed.path == "/contracts":
            self._html(self._contracts())
        elif parsed.path.startswith("/file/"):
            self._file(parsed.path[len("/file/"):])
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        qs = parse_qs(raw)
        if self.path == "/run":
            self._html(self._run(qs))
        elif self.path == "/contracts":
            agent_id = (qs.get("id") or [""])[0]
            if agent_id:
                save_contract(agent_id, {
                    "pass_threshold": (qs.get("pass_threshold") or ["0.95"])[0],
                    "must": (qs.get("must") or [""])[0],
                    "forbidden": (qs.get("forbidden") or [""])[0],
                })
            self._html(self._contracts(saved=agent_id))
        else:
            self.send_error(404)

    def _home(self) -> bytes:
        ssot = load_ssot()
        settings = load_settings()
        stages = "".join(f"<li><strong>{s['title']}</strong> — {s['purpose']}</li>" for s in ssot["stages"])
        body = f"""
        <p>Chaque agent a un contrat. Un juge bloque la suite sous le seuil
        (défaut {settings['pass_threshold']*100:.0f} %).</p>
        <div class="row">
          <form method="post" action="/run">
            <h3>Lancer</h3>
            <label>URL YouTube</label>
            <input type="text" name="youtube" placeholder="https://youtu.be/..."/>
            <label>Ou chemin PDF / texte</label>
            <input type="text" name="pdf" placeholder="/chemin/vers/papier.pdf"/>
            <button name="demo" value="1">Rejouer le démo Koushiappas 2026</button>
            <button type="submit">Lancer sur l'entrée</button>
          </form>
          <div class="card">
            <h3>Réglages</h3>
            <p>Seuil actuel : <strong>{settings['pass_threshold']}</strong></p>
            <p><a href="/settings">Seuil global</a> · <a href="/contracts">Contrats des agents</a></p>
            <ol class="flow">{stages}</ol>
          </div>
        </div>
        """
        return page(body)

    def _settings(self) -> bytes:
        s = load_settings()
        body = f"""
        <form method="get" action="/settings">
          <h3>Seuil du juge</h3>
          <label>pass_threshold (0.50 à 0.99)</label>
          <input type="number" step="0.01" min="0.5" max="0.99" name="threshold" value="{s['pass_threshold']}"/>
          <label>retries</label>
          <input type="number" name="retries" value="{s['max_retries']}"/>
          <label>mots / minute</label>
          <input type="number" name="wpm" value="{s['words_per_minute']}"/>
          <button>Enregistrer</button>
        </form>
        <p><a href="/contracts">Contrats</a> · <a href="/">Retour</a></p>
        """
        return page(body, "Réglages")

    def _contracts(self, saved: str = "") -> bytes:
        contracts = load_contracts()
        blocks = []
        if saved:
            blocks.append(f"<p class='ok'>Contrat enregistré : {htmlmod.escape(saved)}</p>")
        for cid, c in contracts.items():
            must = htmlmod.escape("\n".join(c.get("must") or []))
            forb = htmlmod.escape("\n".join(c.get("forbidden") or []))
            title = htmlmod.escape(str(c.get("title") or cid))
            thr = c.get("pass_threshold", 0.95)
            blocks.append(f"""
                <form method="post" action="/contracts" class="card">
                  <h3>{title} <small class="shot">({htmlmod.escape(cid)})</small></h3>
                  <input type="hidden" name="id" value="{htmlmod.escape(cid)}"/>
                  <label>Seuil de ce contrat</label>
                  <input type="number" step="0.01" min="0.5" max="0.99" name="pass_threshold" value="{thr}"/>
                  <label>Doit</label>
                  <textarea name="must">{must}</textarea>
                  <label>Interdit</label>
                  <textarea name="forbidden">{forb}</textarea>
                  <button>Enregistrer ce contrat</button>
                </form>
                """)
        body = "<h3>Contrats agents</h3><p>Une ligne = une clause.</p>" + "".join(blocks)
        body += '<p><a href="/">Retour</a></p>'
        return page(body, "Contrats")

    def _run(self, qs: dict) -> bytes:
        if qs.get("demo") or not (qs.get("youtube") or qs.get("pdf")):
            source = {"kind": "demo", "origin": "demo://koushiappas-2026"}
        elif qs.get("pdf"):
            source = {"kind": "pdf", "path": qs["pdf"][0], "origin": qs["pdf"][0]}
        else:
            source = {"kind": "youtube", "url": qs["youtube"][0], "origin": qs["youtube"][0]}
        result = run_pipeline(source)
        rows = []
        for step in result["log"]:
            klass = "ok" if step["passed"] else "bad"
            rows.append(
                f"<div class='card'><strong class='{klass}'>{step['title']}</strong> "
                f"— score {step['score']} / seuil {step['threshold']}</div>"
            )
        art = result.get("artifacts") or {}
        narr = htmlmod.escape((art.get("narrate") or {}).get("text") or "")
        video = (art.get("render_video") or {}).get("path") or ""
        vid_html = ""
        if video and Path(video).exists():
            vid_html = f'<video controls src="/file/{Path(video).name}" style="width:100%;border-radius:12px"></video>'
        body = f"<p>Pipeline {'terminé' if result['ok'] else 'arrêté'}.</p>{vid_html}<h3>Juge</h3>{''.join(rows)}<h3>Récit</h3><div class='card'><pre>{narr}</pre></div><p><a href='/'>Nouvelle course</a></p>"
        return page(body, "Course")

    def _file(self, name: str) -> None:
        path = ROOT / "output" / Path(name).name
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"pub2video http://127.0.0.1:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
